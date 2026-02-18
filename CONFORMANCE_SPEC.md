# ESM Format Conformance Test Specification

**Version 1.0 — Test Fixture Format and Execution Protocol**

This document specifies the structure, format, and execution model for ESM Format conformance test fixtures. It defines how test cases are organized, what outputs are expected, and how cross-language consistency is verified.

## 1. Overview

The ESM Format conformance testing system ensures that Julia, TypeScript, Python, and Rust implementations produce consistent results when processing the same ESM files. This specification defines:

- **Test fixture organization** and directory structure
- **Test case formats** for validation, display, substitution, and graph generation
- **Expected output formats** that all implementations must produce
- **Execution protocols** for running conformance tests
- **Error reporting standards** for validation failures

## 2. Test Fixture Organization

### 2.1 Directory Structure

Test fixtures are organized by test category under the `tests/` directory:

```
tests/
├── valid/                    # ESM files that should parse and validate successfully
├── invalid/                  # ESM files that should fail validation with specific errors
├── display/                  # Display formatting test cases (Unicode, LaTeX, ASCII)
├── substitution/             # Expression substitution test cases
├── graphs/                   # Graph generation test cases and expected outputs
├── simulation/               # Simulation test cases with expected trajectories
├── version_compatibility/    # Version migration and compatibility tests
├── conformance/              # Cross-language comparison results and analysis
└── [other categories]/       # Additional test categories as needed
```

### 2.2 Test Categories

#### 2.2.1 Validation Tests (`tests/valid/` and `tests/invalid/`)

**Purpose:** Verify schema and structural validation consistency across implementations.

**Structure:**
- **`tests/valid/`**: ESM files that should parse successfully and pass all validation checks
- **`tests/invalid/`**: ESM files that should fail validation with documented error codes

**File naming convention:**
```
<category>_<description>.esm
```

Examples:
- `minimal_chemistry.esm` - Baseline valid file exercising core features
- `events_all_types.esm` - Comprehensive event type coverage
- `circular_coupling.esm` - Invalid file with circular dependency
- `equation_count_mismatch.esm` - Invalid file with state/equation imbalance

#### 2.2.2 Display Format Tests (`tests/display/`)

**Purpose:** Verify consistent pretty-printing across implementations.

**File format:** JSON arrays with test case objects:

```json
[
  {
    "input": "O3",
    "unicode": "O₃",
    "latex": "\\mathrm{O_3}",
    "reasoning": "O is oxygen, 3 becomes subscript"
  },
  {
    "input": {"op": "D", "args": ["O3"], "wrt": "t"},
    "unicode": "∂O₃/∂t",
    "latex": "\\frac{\\partial \\mathrm{O_3}}{\\partial t}",
    "reasoning": "Partial derivative with respect to time"
  }
]
```

**Test case structure:**
- `input`: The expression to format (string for variables, object for AST nodes)
- `unicode`: Expected Unicode mathematical output
- `latex`: Expected LaTeX output
- `ascii`: Expected ASCII output (optional)
- `reasoning`: Human-readable explanation of formatting rules applied

#### 2.2.3 Substitution Tests (`tests/substitution/`)

**Purpose:** Verify expression substitution behavior across implementations.

**File format:** JSON arrays with substitution test cases:

```json
[
  {
    "input": {"op": "+", "args": ["T", {"op": "*", "args": ["k", "A"]}]},
    "substitutions": {"T": 298.15, "k": 1.5e-3},
    "expected": {"op": "+", "args": [298.15, {"op": "*", "args": [1.5e-3, "A"]}]},
    "description": "Simple parameter substitution"
  },
  {
    "input": {"op": "D", "args": ["_var"], "wrt": "t"},
    "substitutions": {"_var": "O3"},
    "expected": {"op": "D", "args": ["O3"], "wrt": "t"},
    "description": "Placeholder variable substitution"
  }
]
```

**Test case structure:**
- `input`: Expression AST to modify
- `substitutions`: Variable/parameter bindings to apply
- `expected`: Expected result after substitution
- `description`: Test case explanation

#### 2.2.4 Graph Generation Tests (`tests/graphs/`)

**Purpose:** Verify system and expression graph generation consistency.

**Structure:**
- `*.json` files with graph generation test cases
- `expected_dot/`, `expected_mermaid/`, `expected_graphml/` subdirectories with reference outputs

**Graph test case format:**
```json
{
  "file": "path/to/test.esm",
  "graph_type": "system|expression",
  "options": {
    "merge_coupled": true,
    "include_parameters": false
  },
  "expected_nodes": [
    {"id": "SimpleOzone", "type": "reaction_system", "metadata": {...}},
    {"id": "Advection", "type": "model", "metadata": {...}}
  ],
  "expected_edges": [
    {
      "source": "SimpleOzone",
      "target": "Advection",
      "type": "operator_compose",
      "label": "composition",
      "metadata": {...}
    }
  ]
}
```

#### 2.2.5 Simulation Tests (`tests/simulation/`)

**Purpose:** Verify numerical simulation consistency (Julia and Python only).

**Structure:**
- `*.esm` files with simulation test cases
- `expected/` subdirectory with reference solution CSV files

**Expected CSV format:**
```csv
t,O3,NO,NO2
0.0,4.0e-08,1.0e-10,1.0e-09
3600.0,3.95e-08,1.02e-10,1.05e-09
7200.0,3.91e-08,1.04e-10,1.09e-09
```

### 2.3 Test Fixture Metadata

Each test category may include a `README.md` file documenting:
- Test case descriptions and rationale
- Known limitations or implementation differences
- Tolerance thresholds for numerical comparisons
- Category-specific validation rules

## 3. Expected Output Formats

### 3.1 Validation Results

All implementations must produce validation results in this standard format:

```json
{
  "language": "julia|typescript|python|rust",
  "timestamp": "2026-02-18T10:30:00Z",
  "file_path": "tests/valid/minimal_chemistry.esm",
  "validation_result": {
    "is_valid": true,
    "schema_errors": [],
    "structural_errors": [],
    "unit_warnings": [
      {
        "path": "/reaction_systems/SimpleOzone/reactions/0/rate",
        "message": "Unit consistency check failed",
        "lhs_units": "mol/mol/s",
        "rhs_units": "cm^3/molec/s"
      }
    ]
  }
}
```

### 3.2 Display Results

Display formatting tests expect this output structure:

```json
{
  "language": "julia|typescript|python|rust",
  "timestamp": "2026-02-18T10:30:00Z",
  "test_file": "tests/display/chemical_subscripts.json",
  "results": [
    {
      "input": "O3",
      "output_unicode": "O₃",
      "output_latex": "\\mathrm{O_3}",
      "output_ascii": "O3",
      "success": true,
      "error": null
    },
    {
      "input": {"op": "D", "args": ["O3"], "wrt": "t"},
      "output_unicode": "∂O₃/∂t",
      "output_latex": "\\frac{\\partial \\mathrm{O_3}}{\\partial t}",
      "output_ascii": "d(O3)/dt",
      "success": true,
      "error": null
    }
  ],
  "summary": {
    "total_tests": 15,
    "passed": 14,
    "failed": 1
  }
}
```

### 3.3 Substitution Results

```json
{
  "language": "julia|typescript|python|rust",
  "timestamp": "2026-02-18T10:30:00Z",
  "test_file": "tests/substitution/simple_var_replace.json",
  "results": [
    {
      "input": {"op": "+", "args": ["T", "k"]},
      "substitutions": {"T": 298.15},
      "expected": {"op": "+", "args": [298.15, "k"]},
      "actual": {"op": "+", "args": [298.15, "k"]},
      "success": true,
      "error": null
    }
  ],
  "summary": {
    "total_tests": 8,
    "passed": 8,
    "failed": 0
  }
}
```

### 3.4 Graph Results

```json
{
  "language": "julia|typescript|python|rust",
  "timestamp": "2026-02-18T10:30:00Z",
  "test_file": "tests/graphs/system_graph.json",
  "results": [
    {
      "input_file": "tests/valid/minimal_chemistry.esm",
      "graph_type": "system",
      "nodes": [
        {"id": "SimpleOzone", "type": "reaction_system", "properties": {...}},
        {"id": "Advection", "type": "model", "properties": {...}},
        {"id": "GEOSFP", "type": "data_loader", "properties": {...}}
      ],
      "edges": [
        {
          "source": "SimpleOzone",
          "target": "Advection",
          "type": "operator_compose",
          "properties": {...}
        }
      ],
      "formats": {
        "dot": "digraph G { ... }",
        "json": "{\"nodes\": [...], \"edges\": [...]}",
        "mermaid": "graph TD\n  A[SimpleOzone] --> B[Advection]"
      },
      "success": true,
      "error": null
    }
  ]
}
```

## 4. Test Execution Protocol

### 4.1 Language-Specific Test Runners

Each language implementation provides a test runner script that:

1. **Discovers test fixtures** in the appropriate directories
2. **Executes tests** using the language's native ESM library
3. **Produces standardized output** in the formats specified above
4. **Writes results** to designated output directories
5. **Returns appropriate exit codes** (0 = success, non-zero = failure)

### 4.2 Test Runner Interface

All test runners must support this command-line interface:

```bash
# Run all conformance tests
<runner> --output-dir <path> [--categories <list>] [--verbose]

# Run specific test categories
<runner> --output-dir <path> --categories validation,display

# Run tests on specific files
<runner> --output-dir <path> --files tests/valid/minimal_chemistry.esm
```

**Parameters:**
- `--output-dir`: Directory to write test results (JSON files)
- `--categories`: Comma-separated list of test categories to run
- `--files`: Specific test files to process (overrides category-based discovery)
- `--verbose`: Include debug output and timing information

### 4.3 Test Execution Sequence

1. **Pre-validation**: Verify the language implementation passes its native test suite
2. **Fixture Discovery**: Scan test directories for applicable fixtures
3. **Individual Tests**: Process each test case and capture results
4. **Output Generation**: Write standardized JSON results to output directory
5. **Summary Report**: Generate test execution summary and statistics

### 4.4 Result File Naming

Test runners write results using this naming convention:

```
<output-dir>/
├── <language>_validation_results.json      # Validation test results
├── <language>_display_results.json         # Display formatting results
├── <language>_substitution_results.json    # Substitution test results
├── <language>_graph_results.json           # Graph generation results
├── <language>_simulation_results.json      # Simulation results (Julia/Python)
└── <language>_summary.json                 # Overall test summary
```

## 5. Cross-Language Comparison

### 5.1 Comparison Protocol

After individual language test runners complete, a comparison script analyzes results for consistency:

1. **Load results** from all language implementations
2. **Compare outputs** for identical test cases
3. **Identify divergences** and categorize their severity
4. **Generate compatibility report** with detailed analysis
5. **Determine pass/fail status** based on consistency thresholds

### 5.2 Consistency Thresholds

| Test Category | Pass Threshold | Description |
|---|---|---|
| **Validation** | 100% | All implementations must agree on valid/invalid status and error codes |
| **Display Unicode** | 98% | Minor differences in number formatting acceptable |
| **Display LaTeX** | 95% | Syntax variations acceptable if mathematically equivalent |
| **Substitution** | 100% | Expression substitution must be deterministic |
| **Graph Structure** | 95% | Node/edge sets must match; property differences acceptable |
| **Simulation** | 90% | Numerical tolerance for ODE solutions |

### 5.3 Divergence Analysis

The comparison system categorizes divergences as:

- **Critical**: Different validation results, expression structure changes
- **Major**: Significant display formatting differences, graph topology changes
- **Minor**: Cosmetic differences in formatting, property metadata
- **Acceptable**: Known implementation limitations or language-specific constraints

### 5.4 Compatibility Report Format

```json
{
  "analysis_timestamp": "2026-02-18T10:45:00Z",
  "languages_compared": ["julia", "typescript", "python", "rust"],
  "test_categories": {
    "validation": {
      "total_tests": 45,
      "consistent_results": 45,
      "consistency_score": 1.0,
      "status": "PASS",
      "divergences": []
    },
    "display": {
      "total_tests": 120,
      "consistent_results": 118,
      "consistency_score": 0.983,
      "status": "PASS",
      "divergences": [
        {
          "test_case": "scientific_notation_formatting",
          "severity": "minor",
          "description": "Julia uses × symbol, others use x",
          "affected_languages": ["julia"]
        }
      ]
    }
  },
  "overall_status": "PASS|WARN|FAIL",
  "overall_score": 0.976,
  "recommendations": [
    "Review scientific notation formatting standards",
    "Consider harmonizing LaTeX fraction spacing"
  ]
}
```

## 6. Error Handling and Reporting

### 6.1 Standard Error Codes

Validation tests must use these standardized error codes:

| Code | Category | Description |
|---|---|---|
| `schema_validation_failed` | Schema | JSON Schema validation error |
| `equation_count_mismatch` | Structural | State variables vs ODE equations mismatch |
| `undefined_variable` | Structural | Equation references undeclared variable |
| `undefined_species` | Structural | Reaction references undeclared species |
| `undefined_parameter` | Structural | Rate expression references undeclared parameter |
| `undefined_system` | Structural | Coupling references nonexistent system |
| `unresolved_scoped_ref` | Structural | Invalid scoped reference path |
| `null_reaction` | Structural | Reaction with both null substrates and products |
| `missing_observed_expr` | Structural | Observed variable missing expression |
| `event_var_undeclared` | Structural | Event affects undeclared variable |
| `unit_dimension_mismatch` | Units | Dimensional analysis failure |
| `unit_parse_error` | Units | Unrecognized unit string |

### 6.2 Error Message Format

```json
{
  "code": "undefined_variable",
  "path": "/models/SuperFast/equations/0/rhs",
  "message": "Variable 'O4' referenced in equation but not declared in variables",
  "details": {
    "variable_name": "O4",
    "equation_index": 0,
    "available_variables": ["O3", "NO", "NO2"]
  }
}
```

### 6.3 Test Failure Reporting

When a test case fails, implementations must report:

- **Input**: The test case that caused the failure
- **Expected**: What output was expected
- **Actual**: What output was produced
- **Error**: Exception message or error description
- **Context**: Additional debugging information

## 7. Test Fixture Authoring Guidelines

### 7.1 Fixture Creation Process

1. **Design test case** targeting specific functionality or edge case
2. **Author baseline fixture** in appropriate category directory
3. **Generate reference outputs** using a designated reference implementation
4. **Review outputs** for correctness and cross-language applicability
5. **Document rationale** in fixture metadata or README
6. **Commit to repository** after peer review

### 7.2 Fixture Quality Standards

- **Minimal**: Each fixture should test one specific aspect or behavior
- **Comprehensive**: Edge cases and boundary conditions should be covered
- **Documented**: Include reasoning for expected outputs
- **Reproducible**: Results should be deterministic across implementations
- **Maintainable**: Fixtures should be easy to update when specifications change

### 7.3 Version Control

- Test fixtures are version-controlled alongside the ESM schema
- Changes to expected outputs require review and approval
- Breaking changes must be coordinated across all language implementations
- Deprecated fixtures should be marked but preserved for historical testing

## 8. Implementation Requirements

### 8.1 Minimum Conformance

To claim conformance with this specification, an implementation must:

1. **Pass all validation tests** in `tests/valid/` and `tests/invalid/`
2. **Achieve 95% consistency** on display formatting tests
3. **Pass all substitution tests** with 100% accuracy
4. **Generate correct graph structures** for system and expression graphs
5. **Produce standardized output formats** as specified in Section 3

### 8.2 Test Coverage Requirements

Implementations must provide test coverage for:

- All ESM format sections (models, reaction_systems, coupling, domain, etc.)
- All expression operators and functions
- All validation error codes
- All coupling types and transformations
- All event types (continuous, discrete, functional)

### 8.3 Performance Guidelines

While not strictly required for conformance, implementations should:

- Complete the full test suite in under 60 seconds on standard hardware
- Handle large ESM files (1000+ equations) without excessive memory usage
- Provide progress reporting for long-running test operations

## 9. Future Extensions

### 9.1 Planned Additions

- **MathML output format** tests for web/academic publishing
- **Code generation tests** for Julia/Python output quality verification
- **Migration tests** for ESM format version compatibility
- **Performance benchmarks** with standardized timing measurements
- **Fuzzing test cases** for robustness testing

### 9.2 Extensibility

The test fixture format is designed to accommodate:

- New test categories via additional subdirectories
- Extended output formats through additional fields in result objects
- Custom validation rules through metadata in test fixture files
- Language-specific test extensions while maintaining core compatibility

## 10. Reference Implementation

The Julia `ESMFormat.jl` library serves as the reference implementation for conformance test development. When adding new test fixtures:

1. Verify behavior using `ESMFormat.jl`
2. Generate expected outputs using Julia implementation
3. Validate that other implementations produce equivalent results
4. Document any acceptable implementation differences

New conformance tests should be developed iteratively with input from all language implementation maintainers to ensure realistic and achievable standards.

---

This specification establishes the foundation for rigorous cross-language testing of ESM Format implementations. By following these protocols, we ensure that ESM files can be processed consistently across Julia, TypeScript, Python, and Rust, enabling reliable interoperability in the EarthSciML ecosystem.