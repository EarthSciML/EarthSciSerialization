#!/bin/bash
set -euo pipefail

# Cross-platform binary distribution build script for EarthSciSerialization
# Builds native executables for multiple platforms and packages them for distribution

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${PROJECT_ROOT}/dist"
VERSION="${ESM_VERSION:-$(cat "${PROJECT_ROOT}/workspace.json" | grep -o '"version": "[^"]*' | cut -d'"' -f4)}"
PLATFORMS="${ESM_PLATFORMS:-linux-x64 macos-x64 macos-arm64 windows-x64}"

echo "Building EarthSciSerialization binaries v${VERSION}"
echo "Target platforms: ${PLATFORMS}"
echo "Build directory: ${BUILD_DIR}"

# Clean and create build directory
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}"

# Function to build Rust binary for a specific platform
build_rust_binary() {
    local platform=$1
    local rust_target=""
    local binary_name="esm"
    local archive_ext="tar.gz"

    case $platform in
        "linux-x64")
            rust_target="x86_64-unknown-linux-gnu"
            ;;
        "macos-x64")
            rust_target="x86_64-apple-darwin"
            ;;
        "macos-arm64")
            rust_target="aarch64-apple-darwin"
            ;;
        "windows-x64")
            rust_target="x86_64-pc-windows-gnu"
            binary_name="esm.exe"
            archive_ext="zip"
            ;;
        *)
            echo "Unsupported platform: $platform"
            return 1
            ;;
    esac

    echo "Building Rust binary for $platform ($rust_target)..."

    cd "${PROJECT_ROOT}/packages/earthsci-toolkit"

    # Install target if needed
    rustup target add "$rust_target" || true

    # Build binary
    cargo build --release --target "$rust_target" --bin esm

    # Create distribution directory
    local dist_dir="${BUILD_DIR}/esm-cli-${VERSION}-${platform}"
    mkdir -p "$dist_dir"

    # Copy binary
    cp "target/${rust_target}/release/${binary_name}" "$dist_dir/"

    # Copy documentation and licenses
    cp README.md "$dist_dir/" 2>/dev/null || echo "README.md not found for Rust package"
    cp LICENSE "$dist_dir/" 2>/dev/null || cp ../../LICENSE "$dist_dir/" 2>/dev/null || echo "No LICENSE found"

    # Create install script
    create_install_script "$dist_dir" "$binary_name" "$platform"

    # Package binary
    cd "$BUILD_DIR"
    if [ "$archive_ext" = "zip" ]; then
        zip -r "esm-cli-${VERSION}-${platform}.zip" "esm-cli-${VERSION}-${platform}/"
    else
        tar -czf "esm-cli-${VERSION}-${platform}.tar.gz" "esm-cli-${VERSION}-${platform}/"
    fi

    # Generate checksums
    if [ "$archive_ext" = "zip" ]; then
        sha256sum "esm-cli-${VERSION}-${platform}.zip" >> "checksums.txt"
    else
        sha256sum "esm-cli-${VERSION}-${platform}.tar.gz" >> "checksums.txt"
    fi

    echo "✓ Built $platform binary"
    cd "$PROJECT_ROOT"
}

# Function to create platform-specific install scripts
create_install_script() {
    local dist_dir=$1
    local binary_name=$2
    local platform=$3

    case $platform in
        "linux-x64"|"macos-x64"|"macos-arm64")
            cat > "$dist_dir/install.sh" << 'EOF'
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
EOF
            chmod +x "$dist_dir/install.sh"
            ;;
        "windows-x64")
            cat > "$dist_dir/install.bat" << 'EOF'
@echo off
setlocal enabledelayedexpansion

echo Installing ESM CLI...

rem Create install directory
set "INSTALL_DIR=%USERPROFILE%\.local\bin"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

rem Copy binary
copy esm.exe "%INSTALL_DIR%\" >nul

rem Check if directory is in PATH
echo %PATH% | findstr /C:"%INSTALL_DIR%" >nul
if errorlevel 1 (
    echo Adding %INSTALL_DIR% to PATH...
    setx PATH "%PATH%;%INSTALL_DIR%"
    echo Please restart your command prompt.
) else (
    echo %INSTALL_DIR% is already in PATH.
)

echo ESM CLI installed successfully!
echo Run 'esm --help' to get started.
pause
EOF
            ;;
    esac
}

# Function to build Python wheel (if setup.py exists)
build_python_wheel() {
    echo "Building Python wheel..."

    cd "${PROJECT_ROOT}/packages/esm_format"

    if [ -f "pyproject.toml" ]; then
        python -m build --wheel --outdir "${BUILD_DIR}/"
        echo "✓ Built Python wheel"
    else
        echo "⚠ No pyproject.toml found, skipping Python wheel build"
    fi

    cd "$PROJECT_ROOT"
}

# Function to build TypeScript package
build_typescript_package() {
    echo "Building TypeScript package..."

    cd "${PROJECT_ROOT}/packages/esm-format"

    if [ -f "package.json" ]; then
        npm ci
        npm run build
        npm pack --pack-destination="${BUILD_DIR}/"
        echo "✓ Built TypeScript package"
    else
        echo "⚠ No package.json found, skipping TypeScript build"
    fi

    cd "$PROJECT_ROOT"
}

# Create update mechanism script
create_update_script() {
    echo "Creating update mechanism..."

    cat > "${BUILD_DIR}/update.sh" << 'EOF'
#!/bin/bash
set -euo pipefail

# ESM CLI Update Script
# Automatically detects platform and downloads the latest version

REPO="ctessum/EarthSciSerialization"
INSTALL_DIR="${HOME}/.local/bin"

# Detect platform
detect_platform() {
    local os="$(uname -s)"
    local arch="$(uname -m)"

    case "$os" in
        "Linux")
            case "$arch" in
                "x86_64") echo "linux-x64" ;;
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
            echo "windows-x64"
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

main() {
    local platform="$(detect_platform)"
    if [ "$platform" = "unsupported" ]; then
        echo "❌ Unsupported platform: $(uname -s) $(uname -m)"
        exit 1
    fi

    echo "Detected platform: $platform"

    local latest_version="$(get_latest_release)"
    if [ -z "$latest_version" ]; then
        echo "❌ Failed to get latest version"
        exit 1
    fi

    echo "Latest version: $latest_version"

    # Check if already up to date
    if command -v esm &> /dev/null; then
        local current_version="$(esm --version 2>/dev/null | grep -o 'v[0-9.]*' || echo 'unknown')"
        if [ "$current_version" = "$latest_version" ]; then
            echo "✓ Already up to date ($current_version)"
            exit 0
        fi
        echo "Updating from $current_version to $latest_version"
    fi

    # Download and install
    local download_url="https://github.com/$REPO/releases/download/$latest_version/esm-cli-${latest_version#v}-$platform.tar.gz"
    local temp_dir="$(mktemp -d)"

    echo "Downloading from $download_url..."

    cd "$temp_dir"
    curl -L -o "esm-cli.tar.gz" "$download_url"
    tar -xzf "esm-cli.tar.gz"

    # Install
    mkdir -p "$INSTALL_DIR"
    cp esm-cli-*/esm "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/esm"

    # Cleanup
    rm -rf "$temp_dir"

    echo "✓ ESM CLI updated to $latest_version"
}

main "$@"
EOF

    chmod +x "${BUILD_DIR}/update.sh"
}

# Create platform detection helper
create_platform_detector() {
    echo "Creating platform detection utilities..."

    cat > "${BUILD_DIR}/detect-platform.sh" << 'EOF'
#!/bin/bash
# Platform detection utility for ESM CLI

detect_platform() {
    local os="$(uname -s)"
    local arch="$(uname -m)"

    case "$os" in
        "Linux")
            case "$arch" in
                "x86_64"|"amd64") echo "linux-x64" ;;
                "aarch64"|"arm64") echo "linux-arm64" ;;
                *) echo "linux-unknown" ;;
            esac
            ;;
        "Darwin")
            case "$arch" in
                "x86_64") echo "macos-x64" ;;
                "arm64") echo "macos-arm64" ;;
                *) echo "macos-unknown" ;;
            esac
            ;;
        "CYGWIN"*|"MINGW"*|"MSYS"*)
            case "$arch" in
                "x86_64"|"amd64") echo "windows-x64" ;;
                *) echo "windows-unknown" ;;
            esac
            ;;
        *)
            echo "unknown-$os-$arch"
            ;;
    esac
}

if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    # Script is being run directly
    detect_platform
fi
EOF

    chmod +x "${BUILD_DIR}/detect-platform.sh"
}

# Main build process
main() {
    echo "Starting cross-platform build process..."

    # Initialize build directory
    mkdir -p "${BUILD_DIR}"
    echo "# Checksums for EarthSciSerialization v${VERSION}" > "${BUILD_DIR}/checksums.txt"

    # Build binaries for each platform
    for platform in $PLATFORMS; do
        echo "Processing platform: $platform"
        build_rust_binary "$platform"
    done

    # Build other packages
    build_python_wheel
    build_typescript_package

    # Create utility scripts
    create_update_script
    create_platform_detector

    # Create release notes
    cat > "${BUILD_DIR}/RELEASE_NOTES.md" << EOF
# EarthSciSerialization v${VERSION}

## Binary Downloads

### ESM CLI Tool
- **Linux x64**: [esm-cli-${VERSION}-linux-x64.tar.gz](esm-cli-${VERSION}-linux-x64.tar.gz)
- **macOS x64**: [esm-cli-${VERSION}-macos-x64.tar.gz](esm-cli-${VERSION}-macos-x64.tar.gz)
- **macOS ARM64**: [esm-cli-${VERSION}-macos-arm64.tar.gz](esm-cli-${VERSION}-macos-arm64.tar.gz)
- **Windows x64**: [esm-cli-${VERSION}-windows-x64.zip](esm-cli-${VERSION}-windows-x64.zip)

### Quick Install
\`\`\`bash
# Auto-detect platform and install latest version
curl -sSL https://github.com/ctessum/EarthSciSerialization/releases/latest/download/update.sh | bash
\`\`\`

### Library Packages
- **Python**: \`pip install esm-format\`
- **TypeScript/JavaScript**: \`npm install esm-format\`
- **Julia**: \`using Pkg; Pkg.add("ESMFormat")\`
- **Rust**: Add \`earthsci-toolkit = "${VERSION}"\` to Cargo.toml

### Verification
Download [checksums.txt](checksums.txt) to verify package integrity:
\`\`\`bash
sha256sum -c checksums.txt
\`\`\`

## Features
- Cross-platform native executables
- Automatic updates with \`update.sh\`
- Platform detection and appropriate installer generation
- Comprehensive CLI tools for ESM file manipulation
- Multi-language library support

## Installation
Each binary package includes platform-specific install scripts:
- Linux/macOS: \`./install.sh\`
- Windows: \`install.bat\`
EOF

    echo "Build summary:"
    echo "=============="
    ls -la "${BUILD_DIR}"

    echo
    echo "✓ Cross-platform binary distribution build complete!"
    echo "Built packages are in: ${BUILD_DIR}"
    echo "Upload these to GitHub releases for distribution."
}

# Run main function if script is executed directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi