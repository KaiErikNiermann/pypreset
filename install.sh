#!/usr/bin/env bash
set -euo pipefail

# pypreset installer script
# Installs the CLI tool to make it available system-wide

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_METHOD="${1:-pipx}"

echo "🔧 Installing pypreset..."

case "$INSTALL_METHOD" in
    pipx)
        # Preferred method: isolated environment with pipx
        if ! command -v pipx &> /dev/null; then
            echo "📦 pipx not found, installing it first..."
            python3 -m pip install --user pipx
            python3 -m pipx ensurepath
        fi
        
        echo "📦 Installing with pipx (isolated environment)..."
        pipx install "$SCRIPT_DIR" --force
        echo "✅ Installed! Run 'pypreset --help' to get started."
        ;;
    
    pip)
        # Alternative: install with pip to user directory
        echo "📦 Installing with pip (user install)..."
        pip install --user "$SCRIPT_DIR"
        echo "✅ Installed! Run 'pypreset --help' to get started."
        echo "⚠️  Make sure ~/.local/bin is in your PATH"
        ;;
    
    dev)
        # Development mode: editable install
        echo "📦 Installing in development mode..."
        pip install --user -e "$SCRIPT_DIR"
        echo "✅ Installed in editable mode! Changes to source will be reflected immediately."
        ;;
    
    system)
        # System-wide install (requires sudo)
        echo "📦 Installing system-wide (requires sudo)..."
        sudo pip install "$SCRIPT_DIR"
        echo "✅ Installed system-wide!"
        ;;
    
    *)
        echo "Usage: $0 [pipx|pip|dev|system]"
        echo ""
        echo "Methods:"
        echo "  pipx   - Install in isolated environment (recommended)"
        echo "  pip    - Install to ~/.local/bin"
        echo "  dev    - Editable install for development"
        echo "  system - System-wide install (requires sudo)"
        exit 1
        ;;
esac

echo ""
echo "Try it out:"
echo "  pypreset list-presets"
echo "  pypreset create my-project --preset cli-tool"
