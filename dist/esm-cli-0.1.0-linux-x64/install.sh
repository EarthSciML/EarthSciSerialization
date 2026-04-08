#!/bin/bash
set -euo pipefail

# ESM CLI Installer Script
INSTALL_DIR="${HOME}/.local/bin"
BINARY_NAME="esm"

echo "Installing ESM CLI..."

# Create install directory
mkdir -p "$INSTALL_DIR"

# Copy binary
cp "$BINARY_NAME" "$INSTALL_DIR/"
chmod +x "${INSTALL_DIR}/${BINARY_NAME}"

# Add to PATH if not already there
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo "Adding $INSTALL_DIR to PATH..."

    # Determine shell config file
    if [ -n "${ZSH_VERSION:-}" ]; then
        SHELL_CONFIG="$HOME/.zshrc"
    elif [ -n "${BASH_VERSION:-}" ]; then
        SHELL_CONFIG="$HOME/.bashrc"
    else
        SHELL_CONFIG="$HOME/.profile"
    fi

    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_CONFIG"
    echo "Added $INSTALL_DIR to PATH in $SHELL_CONFIG"
    echo "Please restart your shell or run: source $SHELL_CONFIG"
fi

echo "✓ ESM CLI installed successfully!"
echo "Run 'esm --help' to get started."