#!/bin/bash

# Minimal test of conformance infrastructure
# This version validates that the structure works without running full tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="$PROJECT_ROOT/conformance-results-test"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

main() {
    log "Testing conformance infrastructure..."

    # Clean and setup output directories
    rm -rf "$OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR"/{julia,typescript,python,rust,comparison,reports}

    # Create minimal test results for each language
    cat > "$OUTPUT_DIR/julia/results.json" << 'EOF'
{
  "language": "julia",
  "timestamp": "2024-01-01T00:00:00Z",
  "validation_results": {
    "valid": {
      "test.esm": {
        "is_valid": true,
        "schema_errors": [],
        "structural_errors": [],
        "parsed_successfully": true
      }
    },
    "invalid": {
      "bad.esm": {
        "is_valid": false,
        "schema_errors": ["missing_field"],
        "structural_errors": [],
        "parsed_successfully": true
      }
    }
  },
  "display_results": {},
  "substitution_results": {},
  "graph_results": {},
  "errors": []
}
EOF

    cat > "$OUTPUT_DIR/typescript/results.json" << 'EOF'
{
  "language": "typescript",
  "timestamp": "2024-01-01T00:00:00Z",
  "validation_results": {
    "valid": {
      "test.esm": {
        "is_valid": true,
        "schema_errors": [],
        "structural_errors": [],
        "parsed_successfully": true
      }
    },
    "invalid": {
      "bad.esm": {
        "is_valid": false,
        "schema_errors": ["missing_field"],
        "structural_errors": [],
        "parsed_successfully": true
      }
    }
  },
  "display_results": {},
  "substitution_results": {},
  "graph_results": {},
  "errors": []
}
EOF

    log "Testing comparison script..."
    python3 "$SCRIPT_DIR/compare-conformance-outputs.py" \
        --output-dir "$OUTPUT_DIR" \
        --languages julia typescript \
        --comparison-output "$OUTPUT_DIR/comparison/analysis.json"

    success "Comparison completed successfully"

    log "Testing HTML report generation..."
    python3 "$SCRIPT_DIR/generate-conformance-report.py" \
        --analysis-file "$OUTPUT_DIR/comparison/analysis.json" \
        --output-file "$OUTPUT_DIR/reports/test-report.html"

    success "HTML report generated successfully"

    # Verify the analysis results
    if [ -f "$OUTPUT_DIR/comparison/analysis.json" ]; then
        OVERALL_STATUS=$(python3 -c "import json; data=json.load(open('$OUTPUT_DIR/comparison/analysis.json')); print(data.get('overall_status', 'UNKNOWN'))")
        log "Overall status: $OVERALL_STATUS"
    fi

    success "Conformance infrastructure test completed!"
    log "Results available in: $OUTPUT_DIR"

    # Cleanup test results
    rm -rf "$OUTPUT_DIR"
}

main "$@"