# EarthSciSerialization Cross-Platform Binary Distribution

This directory contains the cross-platform binary distribution system for EarthSciSerialization, providing native executables and installation tools for multiple platforms.

## Quick Install

### One-Command Install (Recommended)
```bash
curl -sSL https://raw.githubusercontent.com/ctessum/EarthSciSerialization/main/dist/update.sh | bash
```

### Or download from GitHub Releases
Visit [GitHub Releases](https://github.com/ctessum/EarthSciSerialization/releases/latest) and download the appropriate binary for your platform.

## Available Platforms

| Platform | Binary Package | Status |
|----------|----------------|--------|
| Linux x64 | `esm-cli-VERSION-linux-x64.tar.gz` | ✅ Supported |
| macOS x64 (Intel) | `esm-cli-VERSION-macos-x64.tar.gz` | ✅ Supported |
| macOS ARM64 (Apple Silicon) | `esm-cli-VERSION-macos-arm64.tar.gz` | ✅ Supported |
| Windows x64 | `esm-cli-VERSION-windows-x64.zip` | ✅ Supported |

## Installation Methods

### Method 1: Universal Installer (Recommended)
The universal installer automatically detects your platform and installs the latest version:

```bash
# Download and run
curl -sSL https://raw.githubusercontent.com/ctessum/EarthSciSerialization/main/dist/update.sh | bash

# Or download first, then run
wget https://raw.githubusercontent.com/ctessum/EarthSciSerialization/main/dist/update.sh
chmod +x update.sh
./update.sh
```

### Method 2: Manual Installation

1. **Detect your platform:**
   ```bash
   curl -sSL https://raw.githubusercontent.com/ctessum/EarthSciSerialization/main/dist/detect-platform.sh | bash
   ```

2. **Download the appropriate binary:**
   ```bash
   # Replace VERSION and PLATFORM with appropriate values
   curl -L -o esm-cli.tar.gz \
     "https://github.com/ctessum/EarthSciSerialization/releases/download/vVERSION/esm-cli-VERSION-PLATFORM.tar.gz"
   ```

3. **Extract and install:**
   ```bash
   # Linux/macOS
   tar -xzf esm-cli.tar.gz
   cd esm-cli-*/
   ./install.sh

   # Windows (use PowerShell or Command Prompt)
   # Expand-Archive esm-cli.zip
   # cd esm-cli-*/
   # install.bat
   ```

## Tools Included

### ESM CLI Tool (`esm`)
A comprehensive command-line interface for working with EarthSciML Serialization Format files.

**Features:**
- File validation and pretty-printing
- Format conversion and analysis
- Mathematical expression processing
- System graph generation
- Performance profiling and optimization

**Usage:**
```bash
esm --help                    # Show all available commands
esm validate file.esm         # Validate an ESM file
esm pretty file.esm           # Pretty-print expressions
esm convert file.esm --to json # Convert formats
esm analyze file.esm          # System analysis
```

### Update Mechanism
Keep your installation up to date:

```bash
# The universal installer also works as an updater
curl -sSL https://raw.githubusercontent.com/ctessum/EarthSciSerialization/main/dist/update.sh | bash
```

### Platform Detection
Utility to detect your current platform and suggest appropriate downloads:

```bash
curl -sSL https://raw.githubusercontent.com/ctessum/EarthSciSerialization/main/dist/detect-platform.sh | bash --info
```

## Build System

### Build Scripts

- **`scripts/build-binaries.sh`**: Main cross-platform build script
- **`.github/workflows/binary-release.yml`**: GitHub Actions for automated builds

### Building Locally

To build binaries locally:

```bash
# Build for current platform only
ESM_PLATFORMS="linux-x64" ./scripts/build-binaries.sh

# Build for all platforms (requires cross-compilation setup)
./scripts/build-binaries.sh
```

### GitHub Actions Integration

The binary release workflow automatically:

1. **Detects version** from git tags or manual input
2. **Cross-compiles** for all supported platforms
3. **Packages binaries** with installers and documentation
4. **Creates GitHub releases** with all artifacts
5. **Generates checksums** for integrity verification

Trigger a release:

```bash
# Create and push a version tag
git tag v1.0.0
git push origin v1.0.0

# Or use GitHub's workflow dispatch for custom builds
```

## Directory Structure

```
dist/
├── README.md                           # This file
├── update.sh                          # Universal installer/updater
├── detect-platform.sh                # Platform detection utility
├── checksums.txt                     # SHA256 checksums
├── esm-cli-VERSION-PLATFORM.tar.gz   # Binary packages
└── esm-cli-VERSION-PLATFORM/         # Extracted packages
    ├── esm                           # Binary executable
    ├── LICENSE                       # License file
    └── install.sh                    # Platform-specific installer
```

## Security

### Checksum Verification
All packages include SHA256 checksums for integrity verification:

```bash
# Download checksums
curl -L -o checksums.txt \
  "https://github.com/ctessum/EarthSciSerialization/releases/download/vVERSION/checksums.txt"

# Verify package integrity
sha256sum -c checksums.txt
```

### Signature Verification
Future releases will include GPG signatures for enhanced security.

## Library Integration

While this distribution focuses on native executables, EarthSciSerialization is also available as libraries:

- **Python**: `pip install earthsci-toolkit`
- **TypeScript/JavaScript**: `npm install esm-format`
- **Julia**: `using Pkg; Pkg.add("EarthSciSerialization")`
- **Rust**: Add `esm-format = "VERSION"` to Cargo.toml

## Troubleshooting

### Common Issues

**Platform not supported:**
```bash
# Check supported platforms
./detect-platform.sh --info
```

**Binary not in PATH:**
```bash
# Add to current session
export PATH="$HOME/.local/bin:$PATH"

# Add permanently (restart shell after)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc  # or ~/.zshrc
```

**Download fails:**
- Check internet connection
- Verify the release exists on GitHub
- Try manual download from the web interface

**Permission denied:**
```bash
chmod +x ~/.local/bin/esm
```

### Getting Help

- **Issues**: https://github.com/ctessum/EarthSciSerialization/issues
- **Documentation**: https://github.com/ctessum/EarthSciSerialization#readme
- **CLI Help**: `esm --help` and `esm COMMAND --help`

## License

EarthSciSerialization is released under the MIT License. See LICENSE file for details.