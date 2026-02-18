#!/bin/bash

PLIST_PATH="$HOME/Library/LaunchAgents/com.githubprcount.plist"

if [ -f "$PLIST_PATH" ]; then
    echo "Stopping and removing LaunchAgent..."
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    rm "$PLIST_PATH"
    echo "GitHub PR Monitor uninstalled."
else
    echo "LaunchAgent not found — nothing to uninstall."
fi
