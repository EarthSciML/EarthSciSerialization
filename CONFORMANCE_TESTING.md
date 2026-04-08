# Cross-Language Conformance Testing Infrastructure

This document describes the cross-language conformance testing infrastructure for ESM Format implementations. The system ensures that Julia, TypeScript, Python, and Rust implementations maintain compatibility and produce consistent results.

## Overview

The conformance testing system:

1. **Runs standardized tests** across all language implementations
2. **Compares outputs** to detect divergence between implementations
3. **Generates reports** showing consistency scores and divergence details
4. **Integrates with CI** to prevent breaking changes from being merged
5. **Provides HTML reports** for easy review and debugging

## Quick Start

### Run All Conformance Tests

```bash
./scripts/test-conformance.sh
```

This will:
- Run tests for each available language implementation
- Compare outputs across languages
- Generate an HTML conformance report
- Output results to `conformance-results/`

### Test Infrastructure Only

To test the conformance infrastructure without running full tests:

```bash
./scripts/test-conformance-minimal.sh
```

## Architecture

### Test Categories

The conformance testing covers four main categories:

1. **Validation Tests** (`tests/valid/` and `tests/invalid/`)
   - Schema validation consistency
   - Structural validation error codes
   - Parse success/failure consistency

2. **Display Format Tests** (`tests/display/`)
   - Unicode mathematical notation
   - LaTeX formatting
   - Chemical formula rendering
   - Expression pretty-printing

3. **Substitution Tests** (`tests/substitution/`)
   - Variable substitution in expressions
   - Scoped reference resolution
   - Nested substitution handling

4. **Graph Generation Tests** (`tests/graphs/`)
   - System-level coupling graphs
   - Variable dependency graphs
   - DOT/Mermaid/JSON export formats

### Scripts and Components

```
scripts/
├── test-conformance.sh              # Main test runner
├── run-julia-conformance.jl         # Julia-specific test runner
├── run-typescript-conformance.js    # TypeScript-specific test runner
├── run-python-conformance.py        # Python-specific test runner
├── compare-conformance-outputs.py   # Cross-language comparison
└── generate-conformance-report.py   # HTML report generator
```

## Language Implementation Requirements

Each language implementation must provide:

### 1. Core Functions

- `load(filepath)` - Load and parse ESM files
- `validate(esm_data)` - Schema and structural validation
- `save(filepath, esm_data)` - Serialize ESM data
- `parse_expression(expr_string)` - Parse expression strings
- `pretty_print(expr, format)` - Format expressions (unicode/latex/ascii)
- `substitute(expr, substitutions)` - Variable substitution
- `render_chemical_formula(formula)` - Chemical formula formatting
- `generate_system_graph(esm_data)` - System coupling graph
- `export_dot(graph)` - Export graph as DOT format
- `export_json(graph)` - Export graph as JSON

### 2. Validation Results Format

```json
{
  "is_valid": boolean,
  "schema_errors": ["error_code1", "error_code2", ...],
  "structural_errors": ["error_code1", "error_code2", ...],
  "parsed_successfully": boolean
}
```

### 3. Expected Error Codes

According to ESM specification Section 3.4:

- `equation_count_mismatch` - State variables vs ODE equations mismatch
- `undefined_variable` - Equation references undeclared variable
- `undefined_species` - Reaction references undeclared species
- `undefined_parameter` - Rate expression references undeclared parameter
- `undefined_system` - Coupling references nonexistent system
- `unresolved_scoped_ref` - Invalid scoped reference path
- `null_reaction` - Reaction with both null substrates and products
- `missing_observed_expr` - Observed variable missing expression
- `event_var_undeclared` - Event affects undeclared variable

### 4. Test Runner Integration

Each language provides a test runner script that:

1. Runs the language's native test suite first
2. Generates conformance outputs in standard JSON format
3. Outputs results to the specified directory
4. Returns appropriate exit codes (0 = success, 1 = failure)

## Output Format

### Results Structure

Each language generates a `results.json` file:

```json
{
  "language": "python|julia|typescript|rust",
  "timestamp": "ISO-8601-timestamp",
  "validation_results": {
    "valid": { "filename.esm": { "is_valid": true, ... } },
    "invalid": { "filename.esm": { "is_valid": false, ... } }
  },
  "display_results": {
    "test_file.json": [
      {
        "input": "CO2",
        "output_unicode": "CO₂",
        "output_latex": "CO_2",
        "success": true
      }
    ]
  },
  "substitution_results": { ... },
  "graph_results": { ... },
  "errors": ["error messages if any"]
}
```

### Analysis Output

The comparison produces `analysis.json`:

```json
{
  "languages_tested": ["julia", "typescript", "python", "rust"],
  "validation_analysis": { ... },
  "display_analysis": { ... },
  "substitution_analysis": { ... },
  "graph_analysis": { ... },
  "divergence_summary": {
    "overall_score": 0.95,
    "critical_divergences": [],
    "categories": {
      "validation": {
        "consistency_score": 0.98,
        "status": "PASS"
      }
    }
  },
  "overall_status": "PASS|WARN|FAIL"
}
```

## Status Levels

### Overall Status

- **PASS**: ≥90% consistency across all categories
- **WARN**: ≥70% consistency (minor divergences)
- **FAIL**: <70% consistency (critical divergences)

### Category Status

- **PASS**: ≥90% of tests consistent across languages
- **WARN**: ≥70% of tests consistent
- **FAIL**: <70% of tests consistent

## CI Integration

### GitHub Actions Workflow

The `.github/workflows/conformance-testing.yml` workflow:

1. **Individual Tests**: Runs each language's test suite independently
2. **Conformance Tests**: Cross-language comparison (only if individual tests pass)
3. **Results Upload**: Stores conformance results as artifacts
4. **PR Comments**: Posts conformance status on pull requests
5. **Failure Detection**: Fails if critical divergences detected

### Triggering

Conformance tests run automatically on:
- Pushes to `main` or `develop` branches
- Pull requests affecting `packages/`, `tests/`, or `scripts/`
- Manual workflow dispatch

### Workflow Dependencies

```yaml
conformance-testing:
  needs: [julia-tests, typescript-tests, python-tests, rust-tests]
```

Only runs cross-language tests if individual language tests pass.

## Local Development

### Prerequisites

Ensure you have all required languages installed:

```bash
# Julia
julia --version

# Node.js/TypeScript
npm --version

# Python
python3 --version

# Rust
cargo --version
```

### Running Individual Language Tests

```bash
# Julia
cd packages/ESMFormat.jl
julia --project=. -e 'using Pkg; Pkg.test()'

# TypeScript
cd packages/esm-format
npm test -- --run

# Python
cd packages/esm_format
python -m pytest tests/ -v

# Rust
cd packages/esm-format-rust
cargo test
```

### Development Workflow

1. **Make changes** to implementation or tests
2. **Run individual tests** to ensure basic functionality
3. **Run conformance tests** to check cross-language consistency:
   ```bash
   ./scripts/test-conformance.sh
   ```
4. **Review HTML report** at `conformance-results/reports/conformance_report_*.html`
5. **Fix any divergences** identified in the report
6. **Commit and push** - CI will validate automatically

## Troubleshooting

### Common Issues

1. **"Language implementation not available"**
   - Ensure the language runtime is installed
   - Check that package directories exist and have correct structure

2. **"Tests failed before conformance"**
   - Fix individual language test failures first
   - Conformance tests only run if basic tests pass

3. **"No results generated"**
   - Check that language test runners are executable
   - Verify output directories are writable

4. **"Critical divergences detected"**
   - Review HTML report for specific divergence details
   - Check that implementations follow the same specification
   - Verify test fixtures are correct

### Debug Mode

Run scripts with debug output:

```bash
bash -x ./scripts/test-conformance.sh
```

### Manual Comparison

Run comparison on existing results:

```bash
python3 scripts/compare-conformance-outputs.py \
  --output-dir conformance-results \
  --languages julia typescript python \
  --comparison-output analysis.json
```

## Extending the System

### Adding New Test Categories

1. **Create test fixtures** in `tests/new_category/`
2. **Update language runners** to handle new category
3. **Extend comparison logic** in `compare-conformance-outputs.py`
4. **Update report generator** in `generate-conformance-report.py`

### Adding New Language Implementation

1. **Create package directory** under `packages/`
2. **Implement required functions** (see Requirements section)
3. **Create test runner script** following existing patterns
4. **Update main script** to include new language
5. **Update CI workflow** to test new language

### Customizing Thresholds

Edit the status thresholds in `compare-conformance-outputs.py`:

```python
"status": "PASS" if consistency_score >= 0.9 else "WARN" if consistency_score >= 0.7 else "FAIL"
```

## Best Practices

1. **Run conformance tests locally** before pushing changes
2. **Keep test fixtures comprehensive** but focused
3. **Document divergences** when they're intentional
4. **Update tests** when specification changes
5. **Monitor consistency scores** over time
6. **Review HTML reports** for detailed divergence analysis

## Support

For issues with conformance testing:

1. Check this documentation first
2. Review existing GitHub issues
3. Run minimal test to verify infrastructure: `./scripts/test-conformance-minimal.sh`
4. Create issue with full error output and system information