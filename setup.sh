#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "Setting up GitHub PR Menu Bar App..."
echo ""

# Check prerequisites
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required but not found."
    exit 1
fi

if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is required but not found."
    echo "Install it with: brew install gh"
    exit 1
fi

if ! gh auth status &> /dev/null; then
    echo "Error: GitHub CLI is not authenticated."
    echo "Run: gh auth login"
    exit 1
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Installing dependencies..."
venv/bin/pip install -r requirements.txt --quiet
venv/bin/pip install pyobjc-framework-Quartz --quiet

# Generate menu bar icon if it doesn't exist
if [ ! -f "github.png" ]; then
    echo "Generating menu bar icon..."
    python3 create_icon.py
fi

# Configure repos interactively if config doesn't exist
if [ ! -f "config.json" ]; then
    echo ""
    echo "Which repositories would you like to monitor?"
    echo "Enter repos in owner/repo format, one per line."
    echo "Press Enter on an empty line when done."
    echo ""

    repos=()
    while true; do
        read -rp "  Repo (or blank to finish): " repo
        if [ -z "$repo" ]; then
            break
        fi
        # Basic format validation
        if [[ "$repo" != *"/"* ]]; then
            echo "    Invalid format — use owner/repo (e.g., octocat/Hello-World)"
            continue
        fi
        repos+=("$repo")
    done

    if [ ${#repos[@]} -eq 0 ]; then
        echo ""
        echo "No repos entered. Creating config.json with a placeholder."
        echo "Edit config.json before running the app."
        repos=("owner/repo-name")
    fi

    # Build JSON
    json_repos=""
    for i in "${!repos[@]}"; do
        json_repos+="    \"${repos[$i]}\""
        if [ $i -lt $((${#repos[@]} - 1)) ]; then
            json_repos+=","
        fi
        json_repos+=$'\n'
    done

    cat > config.json << EOF
{
  "repos": [
${json_repos}  ],
  "poll_interval_seconds": 300
}
EOF
    echo ""
    echo "Saved config.json with ${#repos[@]} repo(s)."
fi

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Run ./run.sh to start the app manually"
echo "  2. Run ./install.sh to auto-start on login"
echo ""
echo "You can edit config.json at any time — changes are picked up automatically."
