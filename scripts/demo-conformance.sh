#!/bin/bash

# Demonstration of conformance testing infrastructure
# Shows the system working with realistic test scenarios

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="$PROJECT_ROOT/conformance-demo-results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[DEMO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[DEMO]${NC} $1"
}

main() {
    log "ESM Format Conformance Testing Demonstration"
    log "This demo shows the cross-language testing infrastructure working"
    echo

    # Clean and setup output directories
    log "Setting up demo output directories..."
    rm -rf "$OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR"/{julia,typescript,python,rust,comparison,reports}

    # Scenario 1: Perfect consistency
    log "=== Scenario 1: Perfect Cross-Language Consistency ==="

    # Create consistent results for all languages
    for lang in julia typescript python rust; do
        cat > "$OUTPUT_DIR/$lang/results.json" << EOF
{
  "language": "$lang",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "validation_results": {
    "valid": {
      "simple_model.esm": {
        "is_valid": true,
        "schema_errors": [],
        "structural_errors": [],
        "parsed_successfully": true
      },
      "chemistry_model.esm": {
        "is_valid": true,
        "schema_errors": [],
        "structural_errors": [],
        "parsed_successfully": true
      }
    },
    "invalid": {
      "missing_variables.esm": {
        "is_valid": false,
        "schema_errors": [],
        "structural_errors": ["undefined_variable"],
        "parsed_successfully": true
      },
      "malformed.esm": {
        "is_valid": false,
        "schema_errors": ["missing_required_field"],
        "structural_errors": [],
        "parsed_successfully": false
      }
    }
  },
  "display_results": {
    "chemical_formulas": [
      {
        "input": "CO2",
        "output_unicode": "CO₂",
        "output_latex": "CO_2",
        "success": true
      },
      {
        "input": "H2SO4",
        "output_unicode": "H₂SO₄",
        "output_latex": "H_2SO_4",
        "success": true
      }
    ],
    "mathematical_expressions": [
      {
        "input": "d(O3)/dt",
        "output_unicode": "d(O₃)/dt",
        "output_latex": "\\frac{d(O_3)}{dt}",
        "success": true
      }
    ]
  },
  "substitution_results": {
    "basic_substitution": [
      {
        "expression": "k1 * CO2",
        "substitutions": {"k1": "2.5e-3"},
        "result": "2.5e-3 * CO2",
        "success": true
      }
    ]
  },
  "graph_results": {
    "system_coupling": {
      "nodes": ["atmosphere", "chemistry"],
      "edges": [{"from": "atmosphere", "to": "chemistry", "type": "coupling"}],
      "export_formats": {
        "dot": "digraph { atmosphere -> chemistry; }",
        "json_summary": "2 nodes, 1 edge"
      }
    }
  },
  "errors": []
}
EOF
    done

    # Run comparison
    log "Running cross-language comparison..."
    python3 "$SCRIPT_DIR/compare-conformance-outputs.py" \
        --output-dir "$OUTPUT_DIR" \
        --languages julia typescript python rust \
        --comparison-output "$OUTPUT_DIR/comparison/perfect_analysis.json"

    # Generate report
    log "Generating HTML report for perfect consistency..."
    python3 "$SCRIPT_DIR/generate-conformance-report.py" \
        --analysis-file "$OUTPUT_DIR/comparison/perfect_analysis.json" \
        --output-file "$OUTPUT_DIR/reports/perfect_consistency_${TIMESTAMP}.html"

    success "Perfect consistency scenario completed"
    echo

    # Scenario 2: Minor divergences
    log "=== Scenario 2: Minor Implementation Divergences ==="

    # Create results with small differences
    # Julia and TypeScript agree, Python has minor display difference, Rust missing feature
    for lang in julia typescript; do
        cat > "$OUTPUT_DIR/$lang/results.json" << EOF
{
  "language": "$lang",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "validation_results": {
    "valid": {
      "test_model.esm": {
        "is_valid": true,
        "schema_errors": [],
        "structural_errors": [],
        "parsed_successfully": true
      }
    },
    "invalid": {
      "bad_model.esm": {
        "is_valid": false,
        "schema_errors": [],
        "structural_errors": ["equation_count_mismatch"],
        "parsed_successfully": true
      }
    }
  },
  "display_results": {
    "expressions": [
      {
        "input": "sqrt(x)",
        "output_unicode": "√x",
        "output_latex": "\\sqrt{x}",
        "success": true
      }
    ]
  },
  "substitution_results": {},
  "graph_results": {},
  "errors": []
}
EOF
    done

    # Python has different display output
    cat > "$OUTPUT_DIR/python/results.json" << 'EOF'
{
  "language": "python",
  "timestamp": "2024-01-01T12:00:00Z",
  "validation_results": {
    "valid": {
      "test_model.esm": {
        "is_valid": true,
        "schema_errors": [],
        "structural_errors": [],
        "parsed_successfully": true
      }
    },
    "invalid": {
      "bad_model.esm": {
        "is_valid": false,
        "schema_errors": [],
        "structural_errors": ["equation_count_mismatch"],
        "parsed_successfully": true
      }
    }
  },
  "display_results": {
    "expressions": [
      {
        "input": "sqrt(x)",
        "output_unicode": "sqrt(x)",
        "output_latex": "\\sqrt{x}",
        "success": true
      }
    ]
  },
  "substitution_results": {},
  "graph_results": {},
  "errors": []
}
EOF

    # Rust missing some features
    cat > "$OUTPUT_DIR/rust/results.json" << 'EOF'
{
  "language": "rust",
  "timestamp": "2024-01-01T12:00:00Z",
  "validation_results": {
    "valid": {
      "test_model.esm": {
        "is_valid": true,
        "schema_errors": [],
        "structural_errors": [],
        "parsed_successfully": true
      }
    },
    "invalid": {
      "bad_model.esm": {
        "is_valid": false,
        "schema_errors": [],
        "structural_errors": ["equation_count_mismatch"],
        "parsed_successfully": true
      }
    }
  },
  "display_results": {},
  "substitution_results": {},
  "graph_results": {},
  "errors": ["Display formatting not implemented", "Graph export not implemented"]
}
EOF

    # Run comparison for divergent scenario
    log "Running comparison with divergences..."
    python3 "$SCRIPT_DIR/compare-conformance-outputs.py" \
        --output-dir "$OUTPUT_DIR" \
        --languages julia typescript python rust \
        --comparison-output "$OUTPUT_DIR/comparison/divergent_analysis.json"

    # Generate report
    log "Generating HTML report for divergent scenario..."
    python3 "$SCRIPT_DIR/generate-conformance-report.py" \
        --analysis-file "$OUTPUT_DIR/comparison/divergent_analysis.json" \
        --output-file "$OUTPUT_DIR/reports/divergent_implementations_${TIMESTAMP}.html"

    success "Divergent scenario completed"
    echo

    # Scenario 3: Two-language comparison
    log "=== Scenario 3: Two-Language Comparison (Realistic) ==="

    # Only create Julia and TypeScript results (most realistic scenario)
    rm -rf "$OUTPUT_DIR"/{python,rust}
    mkdir -p "$OUTPUT_DIR"/{julia,typescript,comparison,reports}

    cat > "$OUTPUT_DIR/julia/results.json" << 'EOF'
{
  "language": "julia",
  "timestamp": "2024-01-01T12:00:00Z",
  "validation_results": {
    "valid": {
      "atmospheric_chemistry.esm": {
        "is_valid": true,
        "schema_errors": [],
        "structural_errors": [],
        "parsed_successfully": true
      },
      "coupled_system.esm": {
        "is_valid": true,
        "schema_errors": [],
        "structural_errors": [],
        "parsed_successfully": true
      }
    },
    "invalid": {
      "undefined_species.esm": {
        "is_valid": false,
        "schema_errors": [],
        "structural_errors": ["undefined_species"],
        "parsed_successfully": true
      },
      "missing_equations.esm": {
        "is_valid": false,
        "schema_errors": [],
        "structural_errors": ["equation_count_mismatch"],
        "parsed_successfully": true
      }
    }
  },
  "display_results": {
    "chemical_formulas": [
      {
        "input": "NO2",
        "output_unicode": "NO₂",
        "output_latex": "NO_2",
        "success": true
      },
      {
        "input": "C6H6",
        "output_unicode": "C₆H₆",
        "output_latex": "C_6H_6",
        "success": true
      }
    ]
  },
  "substitution_results": {
    "variable_substitution": [
      {
        "expression": "k_photo * O3",
        "substitutions": {"k_photo": "1.2e-4"},
        "result": "1.2e-4 * O3",
        "success": true
      }
    ]
  },
  "graph_results": {
    "coupling_graph": {
      "nodes": ["atmosphere", "ocean", "land"],
      "edges": [
        {"from": "atmosphere", "to": "ocean", "type": "mass_transfer"},
        {"from": "atmosphere", "to": "land", "type": "deposition"}
      ]
    }
  },
  "errors": []
}
EOF

    cat > "$OUTPUT_DIR/typescript/results.json" << 'EOF'
{
  "language": "typescript",
  "timestamp": "2024-01-01T12:00:00Z",
  "validation_results": {
    "valid": {
      "atmospheric_chemistry.esm": {
        "is_valid": true,
        "schema_errors": [],
        "structural_errors": [],
        "parsed_successfully": true
      },
      "coupled_system.esm": {
        "is_valid": true,
        "schema_errors": [],
        "structural_errors": [],
        "parsed_successfully": true
      }
    },
    "invalid": {
      "undefined_species.esm": {
        "is_valid": false,
        "schema_errors": [],
        "structural_errors": ["undefined_species"],
        "parsed_successfully": true
      },
      "missing_equations.esm": {
        "is_valid": false,
        "schema_errors": [],
        "structural_errors": ["equation_count_mismatch"],
        "parsed_successfully": true
      }
    }
  },
  "display_results": {
    "chemical_formulas": [
      {
        "input": "NO2",
        "output_unicode": "NO₂",
        "output_latex": "NO_2",
        "success": true
      },
      {
        "input": "C6H6",
        "output_unicode": "C₆H₆",
        "output_latex": "C_6H_6",
        "success": true
      }
    ]
  },
  "substitution_results": {
    "variable_substitution": [
      {
        "expression": "k_photo * O3",
        "substitutions": {"k_photo": "1.2e-4"},
        "result": "1.2e-4 * O3",
        "success": true
      }
    ]
  },
  "graph_results": {
    "coupling_graph": {
      "nodes": ["atmosphere", "ocean", "land"],
      "edges": [
        {"from": "atmosphere", "to": "ocean", "type": "mass_transfer"},
        {"from": "atmosphere", "to": "land", "type": "deposition"}
      ]
    }
  },
  "errors": []
}
EOF

    # Run two-language comparison
    log "Running two-language comparison..."
    python3 "$SCRIPT_DIR/compare-conformance-outputs.py" \
        --output-dir "$OUTPUT_DIR" \
        --languages julia typescript \
        --comparison-output "$OUTPUT_DIR/comparison/two_lang_analysis.json"

    # Generate report
    log "Generating HTML report for two-language comparison..."
    python3 "$SCRIPT_DIR/generate-conformance-report.py" \
        --analysis-file "$OUTPUT_DIR/comparison/two_lang_analysis.json" \
        --output-file "$OUTPUT_DIR/reports/two_language_${TIMESTAMP}.html"

    success "Two-language comparison completed"
    echo

    # Summary
    success "=== Conformance Testing Demonstration Complete ==="
    log "Generated reports:"
    ls -la "$OUTPUT_DIR/reports/"*.html | sed 's/^/  /'
    echo
    log "Analysis files:"
    ls -la "$OUTPUT_DIR/comparison/"*.json | sed 's/^/  /'
    echo
    log "Key takeaways:"
    echo "  • Conformance testing infrastructure is fully functional"
    echo "  • Can handle perfect consistency, divergences, and partial implementations"
    echo "  • Generates detailed HTML reports for analysis"
    echo "  • Works with any combination of 2+ language implementations"
    echo
    warning "To run real conformance tests, fix individual language test suites first"
    log "Demo results available in: $OUTPUT_DIR"
}

main "$@"