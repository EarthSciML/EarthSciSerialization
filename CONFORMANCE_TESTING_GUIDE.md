# Conformance Testing Quick Start Guide

This guide provides practical instructions for using the cross-language conformance testing infrastructure for ESM Format implementations.

## Current Status

The conformance testing infrastructure is **fully implemented** and includes:

- ✅ Cross-language test runner scripts
- ✅ Comparison and analysis tools
- ✅ HTML report generation
- ✅ Test fixture structure
- ✅ Comprehensive documentation

However, individual language implementations currently have issues that prevent full conformance testing:

- ⚠️ Julia: Test suite issues with MTK integration
- ⚠️ TypeScript: Test failures
- ⚠️ Python: Test failures
- ⚠️ Rust: Compilation errors

## Quick Verification

To verify the conformance infrastructure works:

```bash
# Test the infrastructure with minimal test data
./scripts/test-conformance-minimal.sh
```

This creates mock results and tests the comparison/reporting pipeline.

## Usage

### 1. Test Infrastructure Only

```bash
./scripts/test-conformance-minimal.sh
```

### 2. Run Full Conformance Tests (when implementations are working)

```bash
./scripts/test-conformance.sh
```

### 3. Check Individual Language Status

```bash
# Julia
cd packages/EarthSciSerialization.jl
julia --project=. -e 'using Pkg; Pkg.test()'

# TypeScript
cd packages/esm-format
npm test -- --run

# Python
cd packages/esm_format
python3 -m pytest tests/ -v

# Rust
cd packages/esm-format-rust
cargo test
```

## Understanding the Output

### Success Case
When conformance tests succeed:
- `conformance-results/` directory contains language-specific results
- `conformance-results/comparison/analysis.json` shows cross-language comparison
- `conformance-results/reports/conformance_report_*.html` provides detailed HTML report
- Overall status: PASS/WARN/FAIL with consistency scores

### Current Failure Case
When language implementations fail their individual tests:
- Each language reports test failures
- Conformance comparison cannot run (requires ≥2 passing languages)
- Error message: "Need at least 2 successful language implementations to perform comparison"

## Debugging Individual Languages

### Julia Issues
Common problems:
- MTK/Catalyst integration errors
- Missing dependencies
- Version compatibility issues

### TypeScript Issues
Common problems:
- Node.js version compatibility
- Missing npm dependencies
- Type definition errors

### Python Issues
Common problems:
- Virtual environment not activated
- Missing pip dependencies
- Import errors

### Rust Issues
Common problems:
- Compilation errors in migration.rs
- Type mismatches
- Missing dependencies

## Development Workflow

1. **Fix Individual Language Issues First**
   - Get at least 2 language implementations passing their test suites
   - This is a prerequisite for conformance testing

2. **Test Infrastructure**
   ```bash
   ./scripts/test-conformance-minimal.sh
   ```

3. **Run Full Conformance Tests**
   ```bash
   ./scripts/test-conformance.sh
   ```

4. **Review Results**
   - Check console output for overall status
   - Review HTML report in `conformance-results/reports/`
   - Examine `analysis.json` for detailed comparison data

## Files and Scripts

| File | Purpose |
|------|---------|
| `scripts/test-conformance.sh` | Main conformance test runner |
| `scripts/test-conformance-minimal.sh` | Infrastructure testing only |
| `scripts/run-julia-conformance.jl` | Julia-specific test runner |
| `scripts/run-typescript-conformance.js` | TypeScript-specific test runner |
| `scripts/run-python-conformance.py` | Python-specific test runner |
| `scripts/compare-conformance-outputs.py` | Cross-language comparison |
| `scripts/generate-conformance-report.py` | HTML report generation |
| `CONFORMANCE_TESTING.md` | Detailed technical documentation |

## Next Steps for Full Conformance Testing

To enable full cross-language conformance testing:

1. **Priority**: Fix individual language test suite failures
2. **Verify**: Run individual language tests successfully
3. **Test**: Run `./scripts/test-conformance.sh`
4. **Analyze**: Review generated HTML reports for consistency

The conformance testing infrastructure is ready to use once the underlying language implementations are working properly.

## Support

- The conformance infrastructure itself is working correctly
- Issues are primarily with individual language implementation test suites
- Use `./scripts/test-conformance-minimal.sh` to verify infrastructure health
- Check individual language test outputs for specific debugging information