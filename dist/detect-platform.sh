#!/bin/bash
# Platform detection utility for ESM CLI
# This utility detects the current platform and suggests the appropriate binary

detect_platform() {
    local os="$(uname -s)"
    local arch="$(uname -m)"
    local platform=""

    case "$os" in
        "Linux")
            case "$arch" in
                "x86_64"|"amd64") platform="linux-x64" ;;
                "aarch64"|"arm64") platform="linux-arm64" ;;
                "i386"|"i686") platform="linux-x32" ;;
                *) platform="linux-unknown" ;;
            esac
            ;;
        "Darwin")
            case "$arch" in
                "x86_64") platform="macos-x64" ;;
                "arm64") platform="macos-arm64" ;;
                *) platform="macos-unknown" ;;
            esac
            ;;
        "CYGWIN"*|"MINGW"*|"MSYS"*)
            case "$arch" in
                "x86_64"|"amd64") platform="windows-x64" ;;
                "i386"|"i686") platform="windows-x32" ;;
                *) platform="windows-unknown" ;;
            esac
            ;;
        "FreeBSD")
            platform="freebsd-${arch}"
            ;;
        "OpenBSD")
            platform="openbsd-${arch}"
            ;;
        "NetBSD")
            platform="netbsd-${arch}"
            ;;
        *)
            platform="unknown-${os,,}-${arch}"
            ;;
    esac

    echo "$platform"
}

get_platform_info() {
    local platform="$1"
    local supported="no"
    local archive_ext="tar.gz"
    local binary_name="esm"

    case "$platform" in
        "linux-x64"|"macos-x64"|"macos-arm64")
            supported="yes"
            ;;
        "windows-x64")
            supported="yes"
            archive_ext="zip"
            binary_name="esm.exe"
            ;;
    esac

    echo "Platform: $platform"
    echo "Supported: $supported"
    echo "Archive format: $archive_ext"
    echo "Binary name: $binary_name"

    if [ "$supported" = "yes" ]; then
        echo "Download pattern: esm-cli-VERSION-${platform}.${archive_ext}"
    else
        echo "This platform is not currently supported."
        echo "Supported platforms: linux-x64, macos-x64, macos-arm64, windows-x64"
    fi
}

show_system_info() {
    echo "System Information:"
    echo "==================="
    echo "OS: $(uname -s)"
    echo "Architecture: $(uname -m)"
    echo "Kernel: $(uname -r)"
    if command -v lsb_release &> /dev/null; then
        echo "Distribution: $(lsb_release -d -s 2>/dev/null || echo 'Unknown')"
    elif [ -f /etc/os-release ]; then
        echo "Distribution: $(. /etc/os-release && echo "$PRETTY_NAME")"
    fi
    echo ""
}

main() {
    local show_info=false
    local show_help=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -i|--info)
                show_info=true
                shift
                ;;
            -h|--help)
                show_help=true
                shift
                ;;
            *)
                echo "Unknown option: $1"
                show_help=true
                shift
                ;;
        esac
    done

    if [ "$show_help" = true ]; then
        echo "Platform Detection Utility for ESM CLI"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  -i, --info     Show detailed system information"
        echo "  -h, --help     Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0             # Detect platform"
        echo "  $0 --info      # Show detailed system info"
        return 0
    fi

    if [ "$show_info" = true ]; then
        show_system_info
    fi

    local platform="$(detect_platform)"
    get_platform_info "$platform"
}

# If script is run directly (not sourced), execute main
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi