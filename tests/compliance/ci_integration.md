# CI Integration for ESM Format Compliance Matrix

This document describes how to integrate the ESM format compliance matrix verification into your CI/CD pipeline.

## Overview

The compliance matrix verification ensures that:
1. All specification requirements have corresponding test fixtures
2. Test fixtures exist on disk and are valid
3. The matrix remains consistent as requirements evolve
4. No regression in test coverage occurs

## GitHub Actions Integration

Add this step to your GitHub Actions workflow:

```yaml
name: Compliance Matrix Verification

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  compliance-check:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Verify Compliance Matrix
      run: |
        cd tests/compliance
        python3 verify_coverage.py --check-fixtures --report

    - name: Upload Coverage Report
      if: always()
      uses: actions/upload-artifact@v4
      with:
        name: compliance-coverage-report
        path: tests/compliance/
```

## Pre-commit Hook Integration

Add to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: compliance-matrix-check
        name: Verify ESM Compliance Matrix
        entry: python3 tests/compliance/verify_coverage.py
        language: system
        files: '^(tests/compliance/|esm-spec\.md|esm-libraries-spec\.md)'
        pass_filenames: false
```

## Make Target

Add to your `Makefile`:

```makefile
.PHONY: check-compliance
check-compliance:
	@echo "Verifying ESM format compliance matrix..."
	@cd tests/compliance && python3 verify_coverage.py --check-fixtures --report

.PHONY: compliance-report
compliance-report:
	@cd tests/compliance && python3 verify_coverage.py --report > compliance_report.txt
	@echo "Compliance report generated: tests/compliance/compliance_report.txt"
```

## Integration Points

### When to Run Verification

1. **On every commit**: Basic matrix consistency check
2. **On pull requests**: Full verification with fixture existence check
3. **Nightly builds**: Full compliance report generation
4. **Before releases**: Mandatory compliance verification

### Failure Conditions

The verification will fail if:
- Test fixtures referenced in the matrix don't exist
- Requirements are missing test coverage
- Matrix has inconsistent category counts
- Spec references are malformed

### Reporting

Generate reports using:
```bash
python3 verify_coverage.py --report --check-fixtures > compliance_report.txt
```

### Integration with Other Tools

The compliance matrix can be integrated with:
- Test runners (pytest, jest, cargo test, etc.)
- Coverage tools (to ensure test fixtures are actually executed)
- Documentation generators (to create requirement traceability matrices)
- Static analysis tools (to validate test fixture content)

## Maintenance

### Adding New Requirements

1. Update the relevant specification file (esm-spec.md or esm-libraries-spec.md)
2. Add the requirement to compliance_matrix.json with proper categorization
3. Create corresponding test fixtures
4. Update test_fixture_mapping in the matrix
5. Run verification to ensure consistency

### Updating Test Fixtures

When modifying test fixtures:
1. Ensure they still cover the intended requirements
2. Update the compliance matrix if fixture paths change
3. Verify no requirements become uncovered

### Matrix Schema Evolution

If the matrix schema evolves:
1. Update the schema_version in compliance_matrix.json
2. Update verify_coverage.py to handle new schema features
3. Migrate existing entries to new schema format
4. Update this documentation

## Troubleshooting

### Common Issues

**Missing test fixtures**: Run with `--check-fixtures` to identify which files need to be created.

**Requirement coverage gaps**: Check the matrix for requirements without corresponding test_fixtures entries.

**Category mismatches**: Ensure requirement category fields match the category defined in requirement IDs.

**Invalid spec references**: Verify spec_ref fields point to valid sections in specification files.