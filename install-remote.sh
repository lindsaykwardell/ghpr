#!/bin/bash
#
# Install ghpr — GitHub PR Monitor
#
#   curl -fsSL https://raw.githubusercontent.com/lindsaywardell/ghpr/main/install-remote.sh | bash
#
set -e

REPO="lindsaywardell/ghpr"
INSTALL_DIR="$HOME/.ghpr"
BIN_DIR="/usr/local/bin"
BIN_LINK="$BIN_DIR/ghpr"

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

if [ -d "$INSTALL_DIR" ]; then
    echo "  Updating existing installation..."
    git -C "$INSTALL_DIR" pull --ff-only --quiet
else
    echo "  Cloning $REPO..."
    git clone --quiet "https://github.com/$REPO.git" "$INSTALL_DIR"
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

# ── Icon ─────────────────────────────────────────────────────────────────────

if [ ! -f "github.png" ]; then
    echo "  Generating menu bar icon..."
    python3 create_icon.py
fi

# ── Symlink ──────────────────────────────────────────────────────────────────

echo "  Linking ghpr to $BIN_LINK..."
if ln -sf "$INSTALL_DIR/ghpr" "$BIN_LINK" 2>/dev/null; then
    :
else
    sudo ln -sf "$INSTALL_DIR/ghpr" "$BIN_LINK"
fi

# ── Done ─────────────────────────────────────────────────────────────────────

echo ""
echo "  ✓ ghpr installed successfully!"
echo ""
echo "  Get started:"
echo "    ghpr setup      Configure which repos to monitor"
echo "    ghpr start      Start the menu bar app"
echo "    ghpr install    Auto-start on login"
echo ""
echo "  Installed to: $INSTALL_DIR"
echo ""
