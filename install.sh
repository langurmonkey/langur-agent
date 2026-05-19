#!/usr/bin/env bash
# Langur Agent installer
# Usage: curl -fsSL https://codeberg.org/langurmonkey/langur-agent/raw/branch/master/install.sh | bash

set -euo pipefail

# Configuration
REPO="langur-agent"
OWNER="langurmonkey"
BRANCH="${BRANCH:-master}"
REPO_URL="https://codeberg.org/$OWNER/$REPO.git"

# XDG-compliant paths with macOS support
if [ "$(uname)" = "Darwin" ]; then
    export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/Library}"
    export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/Library/Preferences}"
    export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/Library/Caches}"
fi

XDG_DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
INSTALL_DIR="${INSTALL_DIR:-$XDG_DATA/langur-agent/repository}"

# Detect Python
if command -v python3 &>/dev/null; then
    PYVER="python3"
elif command -v python &>/dev/null; then
    PYVER="python"
else
    echo "Error: No Python found. Install Python 3.13+ and try again."
    exit 1
fi

# Detect pip
PIP_CMD=""
if command -v pip3 &>/dev/null; then
    PIP_CMD="pip3"
elif command -v pip &>/dev/null; then
    PIP_CMD="pip"
else
    echo "Error: pip not found. Install pip and try again."
    exit 1
fi

# Determine install target
if [ -n "$INSTALL_DIR" ]; then
    TARGET="--target=$INSTALL_DIR"
    echo "Installing to custom directory: $INSTALL_DIR"
else
    if command -v pipx &>/dev/null; then
        echo "Using pipx for installation..."
        PIP_CMD="pipx"
        TARGET=""
    else
        TARGET="--break-system-packages"
        PIP_CMD="pip3"
        echo "Installing system-wide (requires --break-system-packages)..."
    fi
fi

# Clone or update the repository
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Updating existing installation..."
    cd "$INSTALL_DIR"
    git fetch origin
    git checkout "$BRANCH"
    git pull origin "$BRANCH"
else
    echo "Cloning langur-agent repository..."
    mkdir -p "$(dirname "$INSTALL_DIR")"
    git clone --branch "$BRANCH" --single-branch "$REPO_URL" "$INSTALL_DIR"
fi

# Install from local source
echo "Installing langur-agent..."
if [ "$PIP_CMD" = "pipx" ]; then
    pipx install "$INSTALL_DIR" --force
else
    $PIP_CMD install "$TARGET" "$INSTALL_DIR" --quiet
fi

# Create default config if not exists
XDG_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}"
CONFIG_DIR="$XDG_CONFIG/langur-agent"
if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
    mkdir -p "$CONFIG_DIR"
    echo "Creating default config at $CONFIG_DIR/config.yaml"
    cat > "$CONFIG_DIR/config.yaml" << 'EOF'
# Langur Agent Configuration
model:
  provider: openai
  name: gpt-4o-mini
  api_key: ""
  base_url: ""

agent:
  max_turns: 50
  system_prompt: "You are a helpful assistant, expert in many domains of science and engineering. Respond concisely and clearly. No fluff."
  stream: true
  chat_max_chars: 64000
EOF
fi

# Show next steps
echo ""
echo "✅ langur-agent installed successfully!"
echo ""
echo "Next steps:"
echo "  1. Edit config: nano ~/.config/langur-agent/config.yaml"
echo "  2. Run: langur-agent"
echo "  3. Update: langur-agent --update"
echo "  4. One-shot: langur-agent 'your query'"
