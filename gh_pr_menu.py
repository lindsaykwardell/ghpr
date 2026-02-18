#!/usr/bin/env python3
"""GitHub PR Menu Bar App - Shows PRs you created or are tagged in."""

import json
import os
import subprocess
import threading
import time
import webbrowser

import AppKit
import rumps

# Hide from Dock and Cmd-Tab app switcher
info = AppKit.NSBundle.mainBundle().infoDictionary()
info["LSBackgroundOnly"] = "1"

# Set custom app icon for notifications (overrides default Python rocket icon)
APP_DIR = os.path.dirname(os.path.abspath(__file__))
app_icon_path = os.path.join(APP_DIR, "app_icon.png")
if os.path.exists(app_icon_path):
    app_icon = AppKit.NSImage.alloc().initWithContentsOfFile_(app_icon_path)
    AppKit.NSApplication.sharedApplication().setApplicationIconImage_(app_icon)

CONFIG_PATH = os.path.join(APP_DIR, "config.json")
STATE_PATH = os.path.join(APP_DIR, "state.json")
GITHUB_ICON_PATH = None
for ext in ("pdf", "png", "icns"):
    path = os.path.join(APP_DIR, f"github.{ext}")
    if os.path.exists(path):
        GITHUB_ICON_PATH = path
        break


def build_icon_images():
    """Build normal (template/white) and notification (white + red dot) NSImages."""
    if not GITHUB_ICON_PATH:
        return None, None

    base = AppKit.NSImage.alloc().initWithContentsOfFile_(GITHUB_ICON_PATH)
    if not base:
        return None, None

    size = base.size()

    # Normal icon: template so macOS renders it white on dark / black on light
    normal = base.copy()
    normal.setTemplate_(True)
    normal.setSize_(AppKit.NSMakeSize(22, 22))

    # Notification icon: white branch + red dot, non-template for color
    notify = AppKit.NSImage.alloc().initWithSize_(size)
    notify.lockFocus()

    # Draw the base icon as-is
    base.drawAtPoint_fromRect_operation_fraction_(
        AppKit.NSZeroPoint, AppKit.NSZeroRect,
        AppKit.NSCompositingOperationSourceOver, 1.0,
    )

    # Draw red dot in top-right
    dot_d = 8.0
    dot_rect = AppKit.NSMakeRect(size.width - dot_d, size.height - dot_d, dot_d, dot_d)
    dot_path = AppKit.NSBezierPath.bezierPathWithOvalInRect_(dot_rect)
    AppKit.NSColor.redColor().setFill()
    dot_path.fill()

    notify.unlockFocus()
    notify.setTemplate_(False)
    notify.setSize_(AppKit.NSMakeSize(22, 22))

    return normal, notify


ICON_NORMAL, ICON_NOTIFY = build_icon_images()


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_state():
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"seen_urls": [], "comment_counts": {}, "review_states": {}, "ci_states": {}}


def save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def get_github_username():
    result = subprocess.run(
        ["gh", "api", "user", "--jq", ".login"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to get GitHub username: {result.stderr}")
    return result.stdout.strip()


def fetch_prs_for_repo(repo, username):
    prs = []
    fields = "number,title,url,updatedAt,isDraft,reviewDecision,statusCheckRollup,author,comments"

    result = subprocess.run(
        [
            "gh", "pr", "list",
            "--repo", repo, "--author", username, "--state", "open",
            "--json", fields, "--limit", "50",
        ],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode == 0 and result.stdout.strip():
        for pr in json.loads(result.stdout):
            pr["repo"] = repo
            pr["reason"] = "author"
            prs.append(pr)

    result = subprocess.run(
        [
            "gh", "pr", "list",
            "--repo", repo,
            "--search", f"is:open is:pr review-requested:{username}",
            "--json", fields, "--limit", "50",
        ],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode == 0 and result.stdout.strip():
        for pr in json.loads(result.stdout):
            pr["repo"] = repo
            pr["reason"] = "reviewer"
            if not any(p["url"] == pr["url"] for p in prs):
                prs.append(pr)

    return prs


def fetch_all_prs(repos, username):
    all_prs = []
    lock = threading.Lock()

    def fetch_repo(repo):
        try:
            repo_prs = fetch_prs_for_repo(repo, username)
            with lock:
                all_prs.extend(repo_prs)
        except Exception as e:
            print(f"Error fetching PRs for {repo}: {e}")

    threads = [threading.Thread(target=fetch_repo, args=(repo,)) for repo in repos]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    all_prs.sort(key=lambda pr: pr.get("updatedAt", ""), reverse=True)
    return all_prs


def get_comment_count(pr):
    comments = pr.get("comments", [])
    return len(comments) if isinstance(comments, list) else 0


def get_author_login(pr):
    author = pr.get("author", {})
    return author.get("login", "unknown") if isinstance(author, dict) else "unknown"


def get_pr_status_emoji(pr):
    """Return a colored circle emoji indicating PR state.

    Priority order:
    - Draft (gray)      -> \u26ab
    - CI failing        -> \U0001f534 (red)
    - CI passing        -> \U0001f7e2 (green)
    - CI pending        -> \U0001f7e1 (yellow)
    """
    if pr.get("isDraft"):
        return "\u26ab"  # gray/black circle for drafts

    ci_state = get_ci_state(pr)

    if ci_state == "failing":
        return "\U0001f534"  # red circle

    if ci_state == "passing":
        return "\U0001f7e2"  # green circle

    return "\U0001f7e1"  # yellow circle (CI pending)


def get_ci_state(pr):
    """Return 'passing', 'pending', or 'failing' based on CI checks."""
    checks = pr.get("statusCheckRollup", [])
    ci_state = "passing"
    if checks:
        for check in checks:
            typename = check.get("__typename", "")
            if typename == "CheckRun":
                conclusion = check.get("conclusion", "")
                status = check.get("status", "")
                if status != "COMPLETED":
                    ci_state = "pending"
                elif conclusion not in ("SUCCESS", "NEUTRAL", "SKIPPED"):
                    return "failing"
            elif typename == "StatusContext":
                state = check.get("state", "")
                if state == "PENDING":
                    ci_state = "pending"
                elif state not in ("SUCCESS",):
                    return "failing"
    return ci_state


def format_pr_columns(pr, is_new=False, has_new_comments=False):
    """Return column values for a PR menu item."""
    status = get_pr_status_emoji(pr)

    if is_new:
        activity = "\U0001f195"  # 🆕
    elif has_new_comments:
        activity = "\U0001f4ac"  # 💬
    elif pr.get("reviewDecision") == "APPROVED":
        activity = "\u2705"  # ✅ approved
    elif pr.get("reviewDecision") == "CHANGES_REQUESTED":
        activity = "\u274c"  # ❌ changes requested
    else:
        activity = "    "  # blank placeholder to keep alignment

    author = get_author_login(pr)
    repo_short = pr["repo"].split("/")[-1]
    title = pr["title"]

    return status, activity, author, repo_short, title


def build_attributed_menu_title(status, activity, author, repo, title):
    """Build an NSAttributedString with tab stops for column alignment."""
    # Tab stops for: status | activity | author | repo | title
    tab_stops = AppKit.NSMutableArray.alloc().init()
    positions = [28, 56, 180, 290]  # points
    for pos in positions:
        stop = AppKit.NSTextTab.alloc().initWithType_location_(
            AppKit.NSLeftTabStopType, pos
        )
        tab_stops.addObject_(stop)

    para = AppKit.NSMutableParagraphStyle.alloc().init()
    para.setTabStops_(tab_stops)

    font = AppKit.NSFont.menuFontOfSize_(13)

    attrs = {
        AppKit.NSFontAttributeName: font,
        AppKit.NSParagraphStyleAttributeName: para,
    }

    text = f"{status}\t{activity}\t{author}\t{repo}\t{title}"
    return AppKit.NSAttributedString.alloc().initWithString_attributes_(text, attrs)


class GitHubPRApp(rumps.App):
    def __init__(self):
        super().__init__("GitHub PRs", quit_button=None)

        if ICON_NORMAL:
            self.icon = GITHUB_ICON_PATH  # initial load; we override in _set_icon
        else:
            self.title = "\u2630"

        self.config = load_config()
        self.username = None
        self.prs = []
        self.has_unseen = False
        self._first_fetch = True

        # Per-PR status tracking
        self._new_pr_urls = set()       # PRs added since last "mark seen"
        self._new_comment_urls = set()  # PRs with new comments since last "mark seen"

        state = load_state()
        self._seen_urls = set(state.get("seen_urls", []))
        self._comment_counts = state.get("comment_counts", {})
        self._review_states = state.get("review_states", {})
        self._ci_states = state.get("ci_states", {})

        self.menu = [
            rumps.MenuItem("Loading...", callback=None),
            None,
            rumps.MenuItem("Refresh Now", callback=self.manual_refresh),
            rumps.MenuItem("Quit", callback=self.quit_app),
        ]

        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _set_icon(self, notify=False):
        """Set the menu bar icon, using template (white) or notification (white + red dot)."""
        image = ICON_NOTIFY if notify else ICON_NORMAL
        if not image:
            return
        try:
            # Set the NSImage directly on rumps internals and trigger refresh
            self._icon_nsimage = image
            self._nsapp.setStatusBarIcon()
        except AttributeError:
            pass

    def _poll_loop(self):
        self._do_fetch()
        while True:
            time.sleep(self.config["poll_interval_seconds"])
            self._do_fetch()

    def _do_fetch(self):
        try:
            if self.username is None:
                self.username = get_github_username()

            self.config = load_config()
            new_prs = fetch_all_prs(self.config["repos"], self.username)

            new_pr_urls = {pr["url"] for pr in new_prs}
            new_comment_counts = {pr["url"]: get_comment_count(pr) for pr in new_prs}
            new_review_states = {pr["url"]: pr.get("reviewDecision", "") for pr in new_prs}
            new_ci_states = {pr["url"]: get_ci_state(pr) for pr in new_prs}

            if self._first_fetch:
                self._seen_urls = new_pr_urls
                self._comment_counts = new_comment_counts
                self._review_states = new_review_states
                self._ci_states = new_ci_states
                self._first_fetch = False
            else:
                # Detect new PRs
                added_urls = new_pr_urls - self._seen_urls
                for pr in new_prs:
                    url = pr["url"]
                    repo_short = pr["repo"].split("/")[-1]
                    subtitle = f"{repo_short}#{pr['number']}"

                    if url in added_urls:
                        self.has_unseen = True
                        self._new_pr_urls.add(url)
                        author = get_author_login(pr)
                        rumps.notification(
                            title="New PR",
                            subtitle=subtitle,
                            message=f"{pr['title']} (by @{author})",
                            sound=True,
                        )
                        continue

                    # Detect review status changes
                    old_review = self._review_states.get(url, "")
                    new_review = new_review_states.get(url, "")
                    if new_review != old_review and new_review:
                        self.has_unseen = True
                        if new_review == "APPROVED":
                            rumps.notification(
                                title="PR Approved",
                                subtitle=subtitle,
                                message=pr["title"],
                                sound=True,
                            )
                        elif new_review == "CHANGES_REQUESTED":
                            rumps.notification(
                                title="Changes Requested",
                                subtitle=subtitle,
                                message=pr["title"],
                                sound=True,
                            )

                    # Detect CI status changes
                    old_ci = self._ci_states.get(url, "")
                    new_ci = new_ci_states.get(url, "")
                    if new_ci != old_ci and old_ci:
                        self.has_unseen = True
                        if new_ci == "passing":
                            rumps.notification(
                                title="CI Passing",
                                subtitle=subtitle,
                                message=pr["title"],
                                sound=True,
                            )
                        elif new_ci == "failing":
                            rumps.notification(
                                title="CI Failing",
                                subtitle=subtitle,
                                message=pr["title"],
                                sound=True,
                            )

                # Detect new comments
                for url, new_count in new_comment_counts.items():
                    old_count = self._comment_counts.get(url, 0)
                    if new_count > old_count:
                        pr = next((p for p in new_prs if p["url"] == url), None)
                        if pr:
                            self.has_unseen = True
                            self._new_comment_urls.add(url)
                            repo_short = pr["repo"].split("/")[-1]
                            added = new_count - old_count
                            noun = "comment" if added == 1 else "comments"
                            rumps.notification(
                                title=f"New {noun} on PR",
                                subtitle=f"{repo_short}#{pr['number']}",
                                message=f"{added} new {noun}: {pr['title']}",
                                sound=True,
                            )

                self._comment_counts = new_comment_counts
                self._review_states = new_review_states
                self._ci_states = new_ci_states

            self._seen_urls = (self._seen_urls & new_pr_urls) | new_pr_urls
            self.prs = new_prs
            self._save_state()
            self._update_menu()
        except Exception as e:
            print(f"Error during fetch: {e}")

    def _save_state(self):
        save_state({
            "seen_urls": list(self._seen_urls),
            "comment_counts": self._comment_counts,
            "review_states": self._review_states,
            "ci_states": self._ci_states,
        })

    def _update_menu(self):
        # Update icon (white normally, white + red dot when unseen)
        self._set_icon(notify=self.has_unseen)

        # Show count next to icon when there are unseen items
        if self.has_unseen and self.prs:
            self.title = f" ({len(self.prs)})"
        elif not ICON_NORMAL:
            self.title = "\u2630"
        else:
            self.title = None

        menu_items = []       # (rumps.MenuItem | None)
        attributed_items = [] # parallel list: NSAttributedString or None

        if not self.prs:
            menu_items.append(rumps.MenuItem("No open PRs", callback=None))
            attributed_items.append(None)
        else:
            authored = [pr for pr in self.prs if pr["reason"] == "author"]
            review_requested = [pr for pr in self.prs if pr["reason"] == "reviewer"]

            if authored:
                menu_items.append(rumps.MenuItem("--- My PRs ---", callback=None))
                attributed_items.append(None)
                for pr in authored:
                    is_new = pr["url"] in self._new_pr_urls
                    has_new_comments = pr["url"] in self._new_comment_urls
                    cols = format_pr_columns(pr, is_new=is_new, has_new_comments=has_new_comments)
                    attr_str = build_attributed_menu_title(*cols)
                    item = rumps.MenuItem(cols[4], callback=self._make_open_callback(pr["url"]))
                    menu_items.append(item)
                    attributed_items.append(attr_str)

            if review_requested:
                if authored:
                    menu_items.append(None)
                    attributed_items.append(None)
                menu_items.append(rumps.MenuItem("--- Review Requested ---", callback=None))
                attributed_items.append(None)
                for pr in review_requested:
                    is_new = pr["url"] in self._new_pr_urls
                    has_new_comments = pr["url"] in self._new_comment_urls
                    cols = format_pr_columns(pr, is_new=is_new, has_new_comments=has_new_comments)
                    attr_str = build_attributed_menu_title(*cols)
                    item = rumps.MenuItem(cols[4], callback=self._make_open_callback(pr["url"]))
                    menu_items.append(item)
                    attributed_items.append(attr_str)

        menu_items.append(None)
        attributed_items.append(None)
        menu_items.append(rumps.MenuItem("Mark All Seen", callback=self.mark_seen))
        attributed_items.append(None)
        menu_items.append(rumps.MenuItem("Refresh Now", callback=self.manual_refresh))
        attributed_items.append(None)
        menu_items.append(rumps.MenuItem("Quit", callback=self.quit_app))
        attributed_items.append(None)

        self.menu.clear()
        for item, attr_str in zip(menu_items, attributed_items):
            if item is None:
                self.menu.add(rumps.separator)
            else:
                self.menu.add(item)
                if attr_str:
                    item._menuitem.setAttributedTitle_(attr_str)

    def _make_open_callback(self, url):
        def callback(_):
            # Clear this PR's unseen status
            self._new_pr_urls.discard(url)
            self._new_comment_urls.discard(url)
            if not self._new_pr_urls and not self._new_comment_urls:
                self.has_unseen = False
            self._update_menu()
            webbrowser.open(url)
        return callback

    def mark_seen(self, _):
        self.has_unseen = False
        self._new_pr_urls.clear()
        self._new_comment_urls.clear()
        self._update_menu()

    def manual_refresh(self, _):
        self.has_unseen = False
        self._new_pr_urls.clear()
        self._new_comment_urls.clear()
        threading.Thread(target=self._do_fetch, daemon=True).start()

    def quit_app(self, _):
        rumps.quit_application()


if __name__ == "__main__":
    GitHubPRApp().run()
