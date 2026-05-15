#!/usr/bin/env bash
# Langur Agent installer
# Usage: curl -fsSL https://raw.githubusercontent.com/<user>/langur-agent/main/install.sh | bash

set -euo pipefail

VERSION="${VERSION:-0.1.0}"
REPO="${REPO:-langur-agent}"
OWNER="${OWNER:-jumpinglangur}"
PYVER="${PYVER:-}"
INSTALL_DIR="${INSTALL_DIR:-}"

# Detect Python
if [ -z "$PYVER" ]; then
    if command -v python3 &>/dev/null; then
        PYVER="python3"
    elif command -v python &>/dev/null; then
        PYVER="python"
    else
        echo "Error: No Python found. Install Python 3.13+ and try again."
        exit 1
    fi
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
    # Try pipx first (recommended for CLI tools)
    if command -v pipx &>/dev/null; then
        echo "Using pipx for installation..."
        PIP_CMD="pipx"
    else
        TARGET="--break-system-packages"
        PIP_CMD="pip3"
        echo "Installing system-wide (requires --break-system-packages)..."
    fi
fi

# Download wheel
WHEEL_URL="https://github.com/$OWNER/$REPO/releases/download/v$VERSION/langur_agent-$VERSION-py3-none-any.whl"
echo "Downloading langur-agent $VERSION..."

TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

if ! curl -fsSL -o "$TMPDIR/langur_agent.whl" "$WHEEL_URL"; then
    echo "Warning: Failed to download from GitHub releases."
    echo "Falling back to PyPI..."
    
    # Try PyPI
    PYPI_URL="https://pypi.io/packages/langur-agent/langur-agent/$VERSION/langur_agent-$VERSION-py3-none-any.whl"
    if ! curl -fsSL -o "$TMPDIR/langur_agent.whl" "$PYPI_URL"; then
        echo "Error: Failed to download langur-agent from PyPI."
        echo ""
        echo "Install manually:"
        echo "  pip install langur-agent"
        exit 1
    fi
fi

# Install
echo "Installing langur-agent..."
if [ "$PIP_CMD" = "pipx" ]; then
    pipx install "$TMPDIR/langur_agent.whl" --force
else
    $PIP_CMD install "$TARGET" "$TMPDIR/langur_agent.whl" --quiet
fi

# Create default config if not exists
CONFIG_DIR="$HOME/.config/langur-agent"
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
echo "✅ langur-agent $VERSION installed successfully!"
echo ""
echo "Next steps:"
echo "  1. Edit config: nano ~/.config/langur-agent/config.yaml"
echo "  2. Run: langur-agent"
echo "  3. One-shot: langur-agent 'your query'"
