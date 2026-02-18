#!/bin/bash
cd "$(dirname "$0")"

# Ensure Homebrew binaries (including gh) are on PATH
# LaunchAgents don't inherit the user's shell PATH
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

if [ ! -d "venv" ]; then
    echo "Run ./setup.sh first!"
    exit 1
fi

exec venv/bin/python gh_pr_menu.py
