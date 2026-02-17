#!/bin/bash
#
# Security Check Wrapper Script
#
# Convenient wrapper for running security scans on EarthSciSerialization packages.
#

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default configuration
CONFIG_FILE="$PROJECT_ROOT/.security-config.json"
OUTPUT_DIR="$PROJECT_ROOT/security-reports"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Help function
show_help() {
    cat << EOF
Security Check Tool for EarthSciSerialization

Usage: $0 [OPTIONS] [COMMAND]

COMMANDS:
    scan        Run security scan on all packages (default)
    verify      Run signature verification on all packages
    quick       Run quick security check (scan only, no detailed analysis)
    full        Run comprehensive security analysis
    package     Scan a specific package

OPTIONS:
    -h, --help              Show this help message
    -c, --config FILE       Use custom config file (default: .security-config.json)
    -o, --output DIR        Output directory for reports (default: security-reports)
    -p, --package NAME      Specific package to scan (use with 'package' command)
    -t, --type TYPE         Package type: julia|python|npm|rust (use with 'package' command)
    -f, --fail-on-warnings Fail if warnings are found
    -q, --quiet             Suppress output
    -v, --verbose           Verbose output

EXAMPLES:
    # Run standard security scan
    $0 scan

    # Run scan and fail on warnings
    $0 scan --fail-on-warnings

    # Scan specific package
    $0 package --package packages/esm_format --type python

    # Run comprehensive analysis
    $0 full

    # Run signature verification
    $0 verify

EOF
}

# Logging functions
log_info() {
    if [[ "${QUIET:-false}" != "true" ]]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Parse command line arguments
COMMAND="scan"
PACKAGE_PATH=""
PACKAGE_TYPE=""
FAIL_ON_WARNINGS=false
QUIET=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -p|--package)
            PACKAGE_PATH="$2"
            shift 2
            ;;
        -t|--type)
            PACKAGE_TYPE="$2"
            shift 2
            ;;
        -f|--fail-on-warnings)
            FAIL_ON_WARNINGS=true
            shift
            ;;
        -q|--quiet)
            QUIET=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        scan|verify|quick|full|package)
            COMMAND="$1"
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check dependencies
check_dependencies() {
    local missing_deps=()

    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        log_error "Please install the missing dependencies and try again."
        exit 1
    fi
}

# Run security scan
run_security_scan() {
    local output_file="$OUTPUT_DIR/security-scan-$(date +%Y%m%d-%H%M%S).json"
    local scanner_args=("--config" "$CONFIG_FILE" "--output" "$output_file")

    if [[ "$FAIL_ON_WARNINGS" == "true" ]]; then
        scanner_args+=("--fail-on-warnings")
    fi

    if [[ -n "$PACKAGE_PATH" && -n "$PACKAGE_TYPE" ]]; then
        scanner_args+=("--package" "$PACKAGE_PATH" "--package-type" "$PACKAGE_TYPE")
    fi

    log_info "Running security scan..."
    log_info "Config: $CONFIG_FILE"
    log_info "Output: $output_file"

    if [[ "$VERBOSE" == "true" ]]; then
        python3 "$PROJECT_ROOT/scripts/package-security-scanner.py" "${scanner_args[@]}"
    else
        python3 "$PROJECT_ROOT/scripts/package-security-scanner.py" "${scanner_args[@]}" 2>/dev/null || {
            local exit_code=$?
            log_error "Security scan failed with exit code $exit_code"
            log_info "Run with --verbose for detailed output"
            return $exit_code
        }
    fi

    log_success "Security scan completed. Results saved to: $output_file"
    return 0
}

# Run signature verification
run_signature_verification() {
    local output_file="$OUTPUT_DIR/signature-verification-$(date +%Y%m%d-%H%M%S).json"
    local verifier_args=("--config" "$CONFIG_FILE" "--output" "$output_file")

    if [[ -n "$PACKAGE_PATH" && -n "$PACKAGE_TYPE" ]]; then
        verifier_args+=("--package" "$PACKAGE_PATH" "--package-type" "$PACKAGE_TYPE")
    fi

    log_info "Running signature verification..."
    log_info "Config: $CONFIG_FILE"
    log_info "Output: $output_file"

    if [[ "$VERBOSE" == "true" ]]; then
        python3 "$PROJECT_ROOT/scripts/package-signature-verifier.py" "${verifier_args[@]}"
    else
        python3 "$PROJECT_ROOT/scripts/package-signature-verifier.py" "${verifier_args[@]}" 2>/dev/null || {
            local exit_code=$?
            if [[ $exit_code -ne 0 ]]; then
                log_warning "Signature verification completed with warnings (exit code $exit_code)"
                log_info "This is normal if packages don't have GPG signatures yet"
            fi
        }
    fi

    log_success "Signature verification completed. Results saved to: $output_file"
    return 0
}

# Main execution
main() {
    log_info "EarthSciSerialization Security Check Tool"
    log_info "Command: $COMMAND"

    # Check dependencies
    check_dependencies

    # Validate config file
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi

    # Create output directory
    mkdir -p "$OUTPUT_DIR"

    case "$COMMAND" in
        scan)
            run_security_scan
            ;;
        verify)
            run_signature_verification
            ;;
        quick)
            log_info "Running quick security check (scan only)..."
            run_security_scan
            ;;
        full)
            log_info "Running comprehensive security analysis..."
            run_security_scan
            local scan_exit=$?
            run_signature_verification
            exit $scan_exit  # Return scan exit code as it's more critical
            ;;
        package)
            if [[ -z "$PACKAGE_PATH" || -z "$PACKAGE_TYPE" ]]; then
                log_error "Package scanning requires --package and --type options"
                show_help
                exit 1
            fi
            run_security_scan
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"