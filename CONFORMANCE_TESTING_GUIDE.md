# Conformance Testing Quick Start Guide

This guide provides practical instructions for using the cross-language conformance testing infrastructure for ESM Format implementations.

## Current Status

The conformance testing infrastructure is **fully implemented** and includes:

- ✅ Cross-language test runner scripts
- ✅ Comparison and analysis tools
- ✅ HTML report generation
- ✅ Test fixture structure (validation, display, substitution, graphs)
- ✅ Inline simulation tests (`tests[]` and `examples[]` on each `Model` / `ReactionSystem` — see `esm-spec.md` §6.6–6.7)
- ✅ Comprehensive documentation

However, individual language implementations currently have issues that prevent full conformance testing:

- ⚠️ Julia: Test suite issues with MTK integration
- ⚠️ TypeScript: Test failures
- ⚠️ Python: Test failures
- ⚠️ Rust: Compilation errors

## Usage

### 1. Run Full Conformance Tests (when implementations are working)

```bash
./scripts/test-conformance.sh
```

### 2. Check Individual Language Status

```bash
# Julia
cd packages/EarthSciSerialization.jl
julia --project=. -e 'using Pkg; Pkg.test()'

# TypeScript
cd packages/earthsci-toolkit
npm test -- --run

# Python
cd packages/earthsci_toolkit
python3 -m pytest tests/ -v

# Rust
cd packages/earthsci-toolkit-rs
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

2. **Run Full Conformance Tests**
   ```bash
   ./scripts/test-conformance.sh
   ```

3. **Review Results**
   - Check console output for overall status
   - Review HTML report in `conformance-results/reports/`
   - Examine `analysis.json` for detailed comparison data

## Files and Scripts

| File | Purpose |
|------|---------|
| `scripts/test-conformance.sh` | Main conformance test runner |
| `scripts/run-julia-conformance.jl` | Julia-specific test runner |
| `scripts/run-typescript-conformance.js` | TypeScript-specific test runner |
| `scripts/run-python-conformance.py` | Python-specific test runner |
| `scripts/compare-conformance-outputs.py` | Cross-language comparison |
| `scripts/generate-conformance-report.py` | HTML report generation |
| `CONFORMANCE_SPEC.md` | Authoritative fixture format spec and execution protocol |

## Advanced Usage

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

### Customizing Thresholds

Edit the status thresholds in `compare-conformance-outputs.py`:

```python
"status": "PASS" if consistency_score >= 0.9 else "WARN" if consistency_score >= 0.7 else "FAIL"
```

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
- Check individual language test outputs for specific debugging information