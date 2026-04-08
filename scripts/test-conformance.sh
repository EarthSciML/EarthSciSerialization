#!/bin/bash

# Cross-language conformance testing script for ESM Format implementations
# Tests Julia, TypeScript, Python, and Rust implementations against the same test fixtures
# Generates comparable outputs and detects divergence across languages

set -e  # Exit on any error

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TESTS_DIR="$PROJECT_ROOT/tests"
OUTPUT_DIR="$PROJECT_ROOT/conformance-results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Language implementation directories
JULIA_DIR="$PROJECT_ROOT/packages/ESMFormat.jl"
TYPESCRIPT_DIR="$PROJECT_ROOT/packages/esm-format"
PYTHON_DIR="$PROJECT_ROOT/packages/esm_format"
RUST_DIR="$PROJECT_ROOT/packages/esm-format-rust"

# Test categories
VALID_TESTS_DIR="$TESTS_DIR/valid"
INVALID_TESTS_DIR="$TESTS_DIR/invalid"
DISPLAY_TESTS_DIR="$TESTS_DIR/display"
SUBSTITUTION_TESTS_DIR="$TESTS_DIR/substitution"
GRAPHS_TESTS_DIR="$TESTS_DIR/graphs"

# Output directories for each language
JULIA_OUTPUT="$OUTPUT_DIR/julia"
TYPESCRIPT_OUTPUT="$OUTPUT_DIR/typescript"
PYTHON_OUTPUT="$OUTPUT_DIR/python"
RUST_OUTPUT="$OUTPUT_DIR/rust"

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Clean and setup output directories
setup_output_dirs() {
    log "Setting up output directories..."
    rm -rf "$OUTPUT_DIR"
    mkdir -p "$JULIA_OUTPUT" "$TYPESCRIPT_OUTPUT" "$PYTHON_OUTPUT" "$RUST_OUTPUT"
    mkdir -p "$OUTPUT_DIR/comparison" "$OUTPUT_DIR/reports"
}

# Check if language implementation exists and can be tested
check_language_availability() {
    local language=$1
    local dir=$2

    case $language in
        "julia")
            if [ -d "$dir" ] && [ -f "$dir/Project.toml" ]; then
                if command -v julia &> /dev/null; then
                    return 0
                else
                    warning "Julia command not found, skipping Julia tests"
                    return 1
                fi
            fi
            ;;
        "typescript")
            if [ -d "$dir" ] && [ -f "$dir/package.json" ]; then
                if command -v npm &> /dev/null; then
                    return 0
                else
                    warning "npm command not found, skipping TypeScript tests"
                    return 1
                fi
            fi
            ;;
        "python")
            if [ -d "$dir" ] && [ -f "$dir/pyproject.toml" ]; then
                if command -v python3 &> /dev/null; then
                    return 0
                else
                    warning "python3 command not found, skipping Python tests"
                    return 1
                fi
            fi
            ;;
        "rust")
            if [ -d "$dir" ] && [ -f "$dir/Cargo.toml" ]; then
                if command -v cargo &> /dev/null; then
                    return 0
                else
                    warning "cargo command not found, skipping Rust tests"
                    return 1
                fi
            fi
            ;;
    esac
    return 1
}

# Run Julia tests and generate conformance outputs
run_julia_tests() {
    log "Running Julia conformance tests..."

    if ! check_language_availability "julia" "$JULIA_DIR"; then
        warning "Julia implementation not available, skipping"
        return 1
    fi

    cd "$JULIA_DIR"

    # First run the basic tests to ensure everything works
    log "Running Julia test suite..."
    if julia --project=. -e 'using Pkg; Pkg.test()'; then
        success "Julia tests passed"
    else
        error "Julia tests failed"
        return 1
    fi

    # Generate conformance test outputs
    log "Generating Julia conformance outputs..."
    julia --project=. "$SCRIPT_DIR/run-julia-conformance.jl" "$JULIA_OUTPUT"

    return $?
}

# Run TypeScript tests and generate conformance outputs
run_typescript_tests() {
    log "Running TypeScript conformance tests..."

    if ! check_language_availability "typescript" "$TYPESCRIPT_DIR"; then
        warning "TypeScript implementation not available, skipping"
        return 1
    fi

    cd "$TYPESCRIPT_DIR"

    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        log "Installing TypeScript dependencies..."
        npm install
    fi

    # Run the test suite
    log "Running TypeScript test suite..."
    if npm test -- --run; then
        success "TypeScript tests passed"
    else
        error "TypeScript tests failed"
        return 1
    fi

    # Generate conformance outputs
    log "Generating TypeScript conformance outputs..."
    node "$SCRIPT_DIR/run-typescript-conformance.js" "$TYPESCRIPT_OUTPUT"

    return $?
}

# Run Python tests and generate conformance outputs
run_python_tests() {
    log "Running Python conformance tests..."

    if ! check_language_availability "python" "$PYTHON_DIR"; then
        warning "Python implementation not available, skipping"
        return 1
    fi

    cd "$PYTHON_DIR"

    # Run pytest to verify implementation
    log "Running Python test suite..."
    if python3 -m pytest tests/ -v; then
        success "Python tests passed"
    else
        error "Python tests failed"
        return 1
    fi

    # Generate conformance outputs
    log "Generating Python conformance outputs..."
    python3 "$SCRIPT_DIR/run-python-conformance.py" "$PYTHON_OUTPUT"

    return $?
}

# Run Rust tests and generate conformance outputs
run_rust_tests() {
    log "Running Rust conformance tests..."

    if ! check_language_availability "rust" "$RUST_DIR"; then
        warning "Rust implementation not available, skipping"
        return 1
    fi

    cd "$RUST_DIR"

    # Run cargo test
    log "Running Rust test suite..."
    if cargo test; then
        success "Rust tests passed"
    else
        error "Rust tests failed"
        return 1
    fi

    # Generate conformance outputs
    log "Generating Rust conformance outputs..."
    cargo run --bin esm -- conformance-test "$RUST_OUTPUT"

    return $?
}

# Compare outputs between languages and detect divergence
compare_outputs() {
    log "Comparing cross-language outputs..."

    python3 "$SCRIPT_DIR/compare-conformance-outputs.py" \
        --output-dir "$OUTPUT_DIR" \
        --languages julia typescript python rust \
        --comparison-output "$OUTPUT_DIR/comparison/analysis.json"

    return $?
}

# Generate HTML conformance report
generate_report() {
    log "Generating conformance report..."

    python3 "$SCRIPT_DIR/generate-conformance-report.py" \
        --analysis-file "$OUTPUT_DIR/comparison/analysis.json" \
        --output-file "$OUTPUT_DIR/reports/conformance_report_${TIMESTAMP}.html"

    success "Conformance report generated: $OUTPUT_DIR/reports/conformance_report_${TIMESTAMP}.html"
}

# Main execution
main() {
    log "Starting cross-language conformance testing..."
    log "Project root: $PROJECT_ROOT"

    setup_output_dirs

    # Track which languages succeeded
    declare -a successful_languages=()
    declare -a failed_languages=()

    # Run tests for each language
    if run_julia_tests; then
        successful_languages+=("julia")
    else
        failed_languages+=("julia")
    fi

    if run_typescript_tests; then
        successful_languages+=("typescript")
    else
        failed_languages+=("typescript")
    fi

    if run_python_tests; then
        successful_languages+=("python")
    else
        failed_languages+=("python")
    fi

    if run_rust_tests; then
        successful_languages+=("rust")
    else
        failed_languages+=("rust")
    fi

    # Report summary
    log "Test execution summary:"
    if [ ${#successful_languages[@]} -gt 0 ]; then
        success "Successful languages: ${successful_languages[*]}"
    fi
    if [ ${#failed_languages[@]} -gt 0 ]; then
        error "Failed languages: ${failed_languages[*]}"
    fi

    # Only proceed with comparison if we have at least 2 successful languages
    if [ ${#successful_languages[@]} -ge 2 ]; then
        log "Proceeding with cross-language comparison..."

        if compare_outputs; then
            success "Cross-language comparison completed"
        else
            error "Cross-language comparison failed"
            exit 1
        fi

        if generate_report; then
            success "Conformance report generated successfully"
        else
            error "Report generation failed"
            exit 1
        fi

        success "Cross-language conformance testing completed successfully!"
        log "Results available in: $OUTPUT_DIR"

    else
        error "Need at least 2 successful language implementations to perform comparison"
        exit 1
    fi
}

# Check if script is being run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi