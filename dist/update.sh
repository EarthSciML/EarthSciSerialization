#!/bin/bash
set -euo pipefail

# ESM CLI Universal Installer/Updater
# Auto-detects platform and downloads the appropriate binary

REPO="ctessum/EarthSciSerialization"
INSTALL_DIR="${HOME}/.local/bin"

# Detect platform
detect_platform() {
    local os="$(uname -s)"
    local arch="$(uname -m)"

    case "$os" in
        "Linux")
            case "$arch" in
                "x86_64"|"amd64") echo "linux-x64" ;;
                "aarch64"|"arm64") echo "linux-arm64" ;;
                *) echo "unsupported" ;;
            esac
            ;;
        "Darwin")
            case "$arch" in
                "x86_64") echo "macos-x64" ;;
                "arm64") echo "macos-arm64" ;;
                *) echo "unsupported" ;;
            esac
            ;;
        "CYGWIN"*|"MINGW"*|"MSYS"*)
            case "$arch" in
                "x86_64"|"amd64") echo "windows-x64" ;;
                *) echo "unsupported" ;;
            esac
            ;;
        *)
            echo "unsupported"
            ;;
    esac
}

# Get latest release info from GitHub
get_latest_release() {
    curl -s "https://api.github.com/repos/$REPO/releases/latest" | \
        grep '"tag_name":' | \
        sed -E 's/.*"([^"]+)".*/\1/'
}

# Main installation function
main() {
    echo "🔍 ESM CLI Universal Installer"
    echo "==============================="

    local platform="$(detect_platform)"
    if [ "$platform" = "unsupported" ]; then
        echo "❌ Unsupported platform: $(uname -s) $(uname -m)"
        echo ""
        echo "Supported platforms:"
        echo "  - Linux x64"
        echo "  - macOS x64 (Intel)"
        echo "  - macOS ARM64 (Apple Silicon)"
        echo "  - Windows x64"
        exit 1
    fi

    echo "🖥️  Detected platform: $platform"

    # Get latest version from GitHub releases
    echo "🔍 Checking for latest version..."
    local latest_version="$(get_latest_release)"
    if [ -z "$latest_version" ]; then
        echo "❌ Failed to get latest version from GitHub"
        echo "Please visit: https://github.com/$REPO/releases"
        exit 1
    fi

    echo "📦 Latest version: $latest_version"

    # Check if already installed and up to date
    if command -v esm &> /dev/null; then
        local current_version="$(esm --version 2>/dev/null | grep -o 'v[0-9.]*' || echo 'unknown')"
        if [ "$current_version" = "$latest_version" ]; then
            echo "✅ Already up to date ($current_version)"
            exit 0
        fi
        echo "🔄 Updating from $current_version to $latest_version"
    else
        echo "🆕 Installing ESM CLI $latest_version"
    fi

    # Determine archive extension
    local archive_ext="tar.gz"
    if [[ "$platform" == *"windows"* ]]; then
        archive_ext="zip"
    fi

    # Download binary
    local download_url="https://github.com/$REPO/releases/download/$latest_version/esm-cli-${latest_version#v}-$platform.$archive_ext"
    local temp_dir="$(mktemp -d)"

    echo "⬇️  Downloading from GitHub..."
    echo "   $download_url"

    cd "$temp_dir"
    if ! curl -L -f -o "esm-cli.$archive_ext" "$download_url"; then
        echo "❌ Download failed. Please check:"
        echo "   1. Internet connection"
        echo "   2. Release exists for your platform"
        echo "   3. GitHub is accessible"
        rm -rf "$temp_dir"
        exit 1
    fi

    # Extract archive
    echo "📦 Extracting archive..."
    if [ "$archive_ext" = "zip" ]; then
        if ! command -v unzip &> /dev/null; then
            echo "❌ 'unzip' command not found. Please install unzip."
            rm -rf "$temp_dir"
            exit 1
        fi
        unzip -q "esm-cli.zip"
    else
        tar -xzf "esm-cli.tar.gz"
    fi

    # Find the binary
    local binary_name="esm"
    if [[ "$platform" == *"windows"* ]]; then
        binary_name="esm.exe"
    fi

    local binary_path="$(find . -name "$binary_name" -type f | head -1)"
    if [ -z "$binary_path" ]; then
        echo "❌ Binary not found in archive"
        rm -rf "$temp_dir"
        exit 1
    fi

    # Install binary
    echo "🔧 Installing to $INSTALL_DIR..."
    mkdir -p "$INSTALL_DIR"
    cp "$binary_path" "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/$binary_name"

    # Add to PATH if needed
    if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
        echo "📝 Adding $INSTALL_DIR to PATH..."

        # Determine shell config file
        if [ -n "${ZSH_VERSION:-}" ]; then
            SHELL_CONFIG="$HOME/.zshrc"
        elif [ -n "${BASH_VERSION:-}" ]; then
            SHELL_CONFIG="$HOME/.bashrc"
        else
            SHELL_CONFIG="$HOME/.profile"
        fi

        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_CONFIG"
        echo "✏️  Added to PATH in $SHELL_CONFIG"
        echo "🔄 Please restart your shell or run: source $SHELL_CONFIG"
    fi

    # Cleanup
    rm -rf "$temp_dir"

    echo ""
    echo "✅ ESM CLI successfully installed/updated to $latest_version!"
    echo ""
    echo "🚀 Quick start:"
    echo "   esm --help          # Show all available commands"
    echo "   esm validate file.esm    # Validate an ESM file"
    echo "   esm info file.esm        # Show file information"
    echo ""
    echo "📖 For more information:"
    echo "   https://github.com/$REPO"
}

# Run main function
main "$@"