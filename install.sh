#!/bin/bash
#
# Install ghpr — GitHub PR Monitor
#
# Remote:
#   curl -fsSL https://raw.githubusercontent.com/lindsaykwardell/ghpr/main/install.sh | bash
#
# Local (from cloned repo):
#   ./install.sh
#
set -e

REPO="lindsaykwardell/ghpr"
INSTALL_DIR="$HOME/.ghpr"
BIN_DIR="/usr/local/bin"
BIN_LINK="$BIN_DIR/ghpr"
PLIST_NAME="com.githubprcount.plist"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo ""
echo "  Installing ghpr — GitHub PR Monitor"
echo "  ───────────────────────────────────"
echo ""

# ── Prerequisites ────────────────────────────────────────────────────────────

if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required but not found."
    exit 1
fi

if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is required but not found."
    echo "  Install it with: brew install gh"
    exit 1
fi

if ! gh auth status &> /dev/null; then
    echo "Error: GitHub CLI is not authenticated."
    echo "  Run: gh auth login"
    exit 1
fi

if ! command -v git &> /dev/null; then
    echo "Error: git is required but not found."
    exit 1
fi

# ── Clone / update ───────────────────────────────────────────────────────────

# Detect if running from inside a cloned repo (local install)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/ghpr" ] && [ -f "$SCRIPT_DIR/gh_pr_menu.py" ]; then
    # Running locally from cloned repo — copy to ~/.ghpr if not already there
    if [ "$SCRIPT_DIR" != "$INSTALL_DIR" ]; then
        echo "  Copying to $INSTALL_DIR..."
        rm -rf "$INSTALL_DIR"
        cp -R "$SCRIPT_DIR" "$INSTALL_DIR"
    fi
else
    # Running via curl | bash — clone the repo
    if [ -d "$INSTALL_DIR" ]; then
        echo "  Updating existing installation..."
        git -C "$INSTALL_DIR" pull --ff-only --quiet
    else
        echo "  Cloning $REPO..."
        git clone --quiet "https://github.com/$REPO.git" "$INSTALL_DIR"
    fi
fi

# ── Venv & dependencies ─────────────────────────────────────────────────────

cd "$INSTALL_DIR"

if [ ! -d "venv" ]; then
    echo "  Creating virtual environment..."
    python3 -m venv venv
fi

echo "  Installing dependencies..."
venv/bin/pip install -r requirements.txt --quiet
venv/bin/pip install pyobjc-framework-Quartz --quiet

# ── Icons ────────────────────────────────────────────────────────────────────

if [ ! -f "github.png" ] || [ ! -f "app_icon.png" ]; then
    echo "  Generating icons..."
    python3 create_icon.py
fi

# ── Symlink ──────────────────────────────────────────────────────────────────

echo "  Linking ghpr to $BIN_LINK..."
if ln -sf "$INSTALL_DIR/ghpr" "$BIN_LINK" 2>/dev/null; then
    :
else
    sudo ln -sf "$INSTALL_DIR/ghpr" "$BIN_LINK"
fi

# ── Interactive repo config ──────────────────────────────────────────────────

needs_config=false
if [ ! -f "config.json" ]; then
    needs_config=true
else
    # Check if repos array is empty
    repo_count=$(python3 -c "import json; print(len(json.load(open('config.json')).get('repos', [])))" 2>/dev/null || echo "0")
    if [ "$repo_count" = "0" ]; then
        needs_config=true
    fi
fi

if [ "$needs_config" = true ] && [ -t 0 ]; then
    echo ""
    echo "  Which repositories would you like to monitor?"
    echo "  Enter repos in owner/repo format, one per line."
    echo "  Press Enter on an empty line when done."
    echo ""

    repos=()
    while true; do
        read -rp "    Repo (or blank to finish): " repo
        if [ -z "$repo" ]; then
            break
        fi
        if [[ "$repo" != *"/"* ]]; then
            echo "      Invalid format — use owner/repo (e.g., octocat/Hello-World)"
            continue
        fi
        repos+=("$repo")
    done

    if [ ${#repos[@]} -gt 0 ]; then
        # Build JSON using python for correctness
        python3 -c "
import json, sys
repos = sys.argv[1:]
config = {'repos': repos, 'poll_interval_seconds': 300}
with open('config.json', 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')
" "${repos[@]}"
        echo ""
        echo "  Saved config.json with ${#repos[@]} repo(s)."
    elif [ ! -f "config.json" ]; then
        # Create empty config so the app can start
        echo '{"repos": [], "poll_interval_seconds": 300}' > config.json
        echo ""
        echo "  No repos entered. Add repos later with: ghpr config add owner/repo"
    fi
fi

# ── LaunchAgent ──────────────────────────────────────────────────────────────

RUN_SH="$INSTALL_DIR/run.sh"

# Stop existing agent if present
if launchctl list 2>/dev/null | grep -q com.githubprcount; then
    echo "  Stopping existing instance..."
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
fi

echo "  Installing LaunchAgent..."
mkdir -p "$(dirname "$PLIST_PATH")"
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.githubprcount</string>

    <key>ProgramArguments</key>
    <array>
        <string>${RUN_SH}</string>
    </array>

    <key>WorkingDirectory</key>
    <string>${INSTALL_DIR}</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/tmp/githubprcount.stdout.log</string>

    <key>StandardErrorPath</key>
    <string>/tmp/githubprcount.stderr.log</string>
</dict>
</plist>
EOF

launchctl load "$PLIST_PATH"

# ── Done ─────────────────────────────────────────────────────────────────────

echo ""
echo "  ✓ ghpr installed and running!"
echo ""
echo "  Manage repos:"
echo "    ghpr config add owner/repo      Add a repo to monitor"
echo "    ghpr config remove owner/repo   Remove a repo"
echo "    ghpr config list                List monitored repos"
echo ""
echo "  Other commands:"
echo "    ghpr status       Show daemon status"
echo "    ghpr restart      Restart the daemon"
echo "    ghpr uninstall    Remove everything"
echo ""
echo "  Installed to: $INSTALL_DIR"
echo ""
