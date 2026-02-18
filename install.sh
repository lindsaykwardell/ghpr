#!/bin/bash
set -e

cd "$(dirname "$0")"
APP_DIR="$(pwd)"
PLIST_NAME="com.githubprcount.plist"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME"

if [ ! -d "venv" ]; then
    echo "Error: Run ./setup.sh first!"
    exit 1
fi

# Unload existing agent if present
if launchctl list | grep -q com.githubprcount; then
    echo "Stopping existing instance..."
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
fi

echo "Installing LaunchAgent..."
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.githubprcount</string>

    <key>ProgramArguments</key>
    <array>
        <string>${APP_DIR}/run.sh</string>
    </array>

    <key>WorkingDirectory</key>
    <string>${APP_DIR}</string>

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

echo "GitHub PR Monitor installed and running!"
echo "It will start automatically on login."
echo ""
echo "To stop:      ./uninstall.sh"
echo "To view logs:  tail -f /tmp/githubprcount.stderr.log"
