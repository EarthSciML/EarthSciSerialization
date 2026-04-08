# Performance and Scalability Test Fixtures

This directory contains comprehensive performance benchmarking and scalability testing tools for the ESM format libraries across all supported languages (Python, Julia, TypeScript, Rust).

## Overview

The performance test suite provides:

1. **Automated Benchmarking**: Cross-language performance comparison
2. **Memory Profiling**: Detailed memory usage analysis and leak detection
3. **Scalability Testing**: Performance characteristics under varying load
4. **CI/CD Integration**: Automated performance regression detection
5. **Baseline Management**: Performance expectations and limits documentation

## Quick Start

```bash
# Run comprehensive benchmarks across all languages
./benchmark.sh

# Run Python-only benchmarks
./benchmark.sh --python-only

# Run memory profiling on medium-sized test data
python3 memory_profiler.py --size medium --iterations 100

# View performance baselines and expectations
less performance_baselines.json
```

## Test Categories

### 1. Parse Time Benchmarks

Tests ESM file parsing performance across different file sizes:

- **Tiny Files** (< 1KB): Basic syntax parsing
- **Small Files** (1-100KB): Typical research models
- **Medium Files** (100KB-10MB): Regional-scale models
- **Large Files** (10-100MB): Global Earth system models
- **Massive Files** (100MB-1GB): High-resolution or ensemble models

### 2. Memory Usage Benchmarks

Comprehensive memory profiling including:

- **Peak Memory Usage**: Maximum RAM during operations
- **Memory Scaling**: How memory usage grows with file size
- **Memory Leaks**: Detection of unreleased memory
- **Garbage Collection**: Efficiency of memory cleanup
- **Memory Per Operation**: Cost of individual parse/serialize operations

### 3. Scalability Benchmarks

Tests performance scaling characteristics:

- **Variable Count**: 10³ to 10⁶ variables
- **Reaction Networks**: 10² to 10⁴ reactions
- **Expression Complexity**: Simple to deeply nested expressions
- **Coupling Networks**: Sparse to densely connected systems
- **Hierarchy Depth**: Flat to deeply nested subsystems

### 4. Validation Performance

Measures validation overhead:

- **Schema Validation**: JSON schema compliance checking
- **Structural Validation**: Cross-reference and dependency validation
- **Domain Validation**: Physical units and scientific consistency
- **Performance Impact**: Validation time as percentage of parse time

## File Structure

```
tests/performance/
├── README.md                    # This file
├── benchmark.sh                 # Main benchmarking script
├── memory_profiler.py          # Memory profiling and leak detection
├── performance_baselines.json  # Performance expectations by language
├── ci_benchmark.yml            # GitHub Actions CI/CD configuration
├── SCALABILITY_LIMITS.md       # Detailed scalability documentation
├── results/                    # Benchmark results (generated)
│   ├── benchmark_results_*.json
│   ├── memory_profiles_*.json
│   └── regression_analysis_*.json
└── data/                       # Test data (generated)
    ├── small_test.esm
    ├── medium_test.esm
    └── large_test.esm
```

## Tools and Scripts

### `benchmark.sh`

Comprehensive cross-language benchmarking script.

**Features:**
- Runs benchmarks for Python, Julia, TypeScript implementations
- Measures parse time, serialize time, memory usage, file sizes
- Generates structured JSON results for analysis
- Includes system information and hardware context
- Supports single-language testing for focused analysis

**Usage:**
```bash
# Full benchmark suite
./benchmark.sh

# Language-specific benchmarks
./benchmark.sh --python-only
./benchmark.sh --julia-only
./benchmark.sh --ts-only

# View help
./benchmark.sh --help
```

**Output:**
- Structured JSON results in `results/benchmark_results_TIMESTAMP.json`
- Individual language result files
- System metrics and monitoring data
- Performance summary to console

### `memory_profiler.py`

Advanced memory profiling with leak detection.

**Features:**
- Detailed memory usage tracking (RSS, VMS, Python heap)
- Memory leak detection with configurable thresholds
- Repeated operation testing to amplify memory effects
- Garbage collection efficiency analysis
- Memory usage per operation calculations

**Usage:**
```bash
# Basic memory profiling
python3 memory_profiler.py

# Large test data with many iterations
python3 memory_profiler.py --size large --iterations 200

# Memory leak testing only
python3 memory_profiler.py --leak-test-only

# Save results to custom file
python3 memory_profiler.py --output custom_memory_results.json
```

**Output:**
- JSON report with memory usage statistics
- Leak detection results and recommendations
- Memory efficiency metrics
- Raw memory snapshots for detailed analysis

### `performance_baselines.json`

Comprehensive performance expectations and baselines.

**Contains:**
- Target performance metrics for each language
- File size categories and expected performance
- Memory usage baselines and scaling factors
- Validation overhead expectations
- Platform-specific performance variations
- Regression detection thresholds

### `ci_benchmark.yml`

GitHub Actions workflow for automated performance testing.

**Features:**
- Runs on every PR and main branch push
- Nightly comprehensive benchmarking
- Performance regression detection
- Cross-language consistency checking
- Artifact collection and retention
- PR comment notifications

## Performance Expectations

### Parse Time Targets (Medium Files, 1-10MB)

| Language   | Target Time | Max Time | Memory Usage |
|------------|-------------|----------|--------------|
| Python     | 1.0s        | 2.0s     | 200MB        |
| Julia      | 0.5s        | 1.0s     | 100MB        |
| TypeScript | 1.5s        | 3.0s     | 300MB        |
| Rust       | 0.25s       | 0.5s     | 50MB         |

### Scalability Characteristics

| Metric | Linear Range | Sublinear Range | Practical Limit |
|--------|--------------|-----------------|-----------------|
| Variables | 0-10K | 10K-100K | 1M |
| Reactions | 0-1K | 1K-10K | 100K |
| Expression Terms | 0-100 | 100-1K | 10K |
| Coupling Density | 0-10% | 10-30% | 60% |

## Running Performance Tests

### Prerequisites

**Python:**
```bash
cd packages/esm_format
pip install -e .[test]
pip install psutil pytest-benchmark memory-profiler
```

**Julia:**
```bash
cd packages/ESMFormat.jl
julia --project=. -e 'using Pkg; Pkg.instantiate()'
julia --project=. -e 'using Pkg; Pkg.add(["BenchmarkTools", "JSON3"])'
```

**TypeScript:**
```bash
cd packages/esm-format
npm install
npm run build
```

**System Tools:**
```bash
# Linux
sudo apt-get install jq htop sysstat

# macOS
brew install jq htop

# Verify tools
jq --version
```

### Basic Performance Testing

1. **Quick Smoke Test**:
   ```bash
   cd tests/performance
   ./benchmark.sh --python-only
   ```

2. **Memory Analysis**:
   ```bash
   python3 memory_profiler.py --size medium --iterations 50
   ```

3. **Full Benchmark Suite**:
   ```bash
   ./benchmark.sh
   ```

### Advanced Performance Analysis

1. **Memory Leak Detection**:
   ```bash
   python3 memory_profiler.py --leak-test-only --iterations 1000
   ```

2. **Scalability Testing**:
   ```bash
   # Test with existing Python fixtures
   cd packages/esm_format
   python3 -m pytest tests/test_performance_scalability_fixtures.py -v
   ```

3. **Cross-Language Comparison**:
   ```bash
   ./benchmark.sh > full_results.log 2>&1
   grep "RESULT|" full_results.log | column -t -s '|'
   ```

## Interpreting Results

### Benchmark Output Structure

```json
{
  "timestamp": "2026-02-15T16:42:00Z",
  "system_info": {
    "cpu_info": "Intel Core i7-8700K @ 3.70GHz",
    "memory_gb": 16,
    "os": "Linux"
  },
  "benchmarks": {
    "python": {
      "small_model": {
        "parse_time_s": 0.045,
        "serialize_time_s": 0.032,
        "memory_delta_mb": 12.5,
        "file_size_mb": 0.002,
        "success": true
      }
    }
  }
}
```

### Key Metrics to Monitor

1. **Parse Time**: Should scale linearly with file size
2. **Memory Delta**: Memory used beyond baseline
3. **Memory Per Operation**: Efficiency of individual operations
4. **Cross-Language Ratio**: Performance consistency between languages
5. **Memory Leaks**: Should be < 1MB per 1000 operations

### Warning Signs

- **Parse time** increasing faster than file size (non-linear scaling)
- **Memory leaks** detected in repeated operation tests
- **Cross-language performance** differences > 10x
- **Memory usage** growing faster than O(n) with file size
- **Validation overhead** > 50% of parse time

## CI/CD Integration

### GitHub Actions Workflow

The included `ci_benchmark.yml` provides:

- **Automated Testing**: Runs on every PR and push to main
- **Performance Regression Detection**: Compares against baselines
- **Cross-Platform Testing**: Linux, macOS, Windows support
- **Artifact Collection**: Saves detailed results for analysis
- **PR Comments**: Performance summary directly in PRs

### Setting Up CI

1. Copy `ci_benchmark.yml` to `.github/workflows/`
2. Ensure all language environments are available in CI
3. Configure notification settings (Slack, email, etc.)
4. Set up performance baseline database

### Performance Gates

The CI system will fail if:
- Parse time regresses > 20%
- Memory usage increases > 15%
- Memory leaks detected
- Any test times out (30 minutes default)

## Troubleshooting

### Common Issues

1. **"ESM format not available"**:
   - Install the Python package: `pip install -e packages/esm_format[test]`
   - Or run from the package directory

2. **"pytest not found"**:
   - Install pytest: `pip install pytest`
   - Or use Python test runner: `python -m unittest`

3. **Julia package errors**:
   - Update packages: `julia --project=. -e 'using Pkg; Pkg.update()'`
   - Rebuild: `julia --project=. -e 'using Pkg; Pkg.build()'`

4. **Memory profiler crashes**:
   - Install psutil: `pip install psutil`
   - Reduce iterations: `--iterations 10`

5. **Benchmark script permissions**:
   - Make executable: `chmod +x benchmark.sh`
   - Check path: `ls -la benchmark.sh`

### Performance Debugging

1. **Slow parsing**:
   - Check file size vs. parse time scaling
   - Profile JSON parsing specifically
   - Look for quadratic algorithms in validation

2. **High memory usage**:
   - Run memory profiler with detailed snapshots
   - Check for retention of large intermediate objects
   - Profile garbage collection efficiency

3. **Memory leaks**:
   - Run leak detection with high iteration counts
   - Check object cleanup in language-specific code
   - Monitor system memory during long runs

4. **Cross-language inconsistencies**:
   - Compare identical test files across languages
   - Check for different validation implementations
   - Profile JSON parsing vs. ESM-specific processing

## Contributing

### Adding New Performance Tests

1. **Create test fixture** in appropriate language package
2. **Add benchmark case** to `benchmark.sh`
3. **Update baselines** in `performance_baselines.json`
4. **Document expectations** in `SCALABILITY_LIMITS.md`

### Updating Performance Baselines

1. Run comprehensive benchmarks on reference hardware
2. Update target and maximum values in `performance_baselines.json`
3. Adjust CI thresholds if needed
4. Document rationale for changes

### Adding New Language Support

1. **Implement benchmark runner** for new language
2. **Add to benchmark.sh** script
3. **Define performance baselines** in configuration
4. **Update CI workflow** to include new language
5. **Add platform-specific considerations**

## References

- [Performance Baselines Configuration](performance_baselines.json)
- [Detailed Scalability Analysis](SCALABILITY_LIMITS.md)
- [CI/CD Workflow Configuration](ci_benchmark.yml)
- [Python Implementation Tests](../packages/esm_format/tests/test_performance_scalability_fixtures.py)
- [Project Performance Benchmarks](PERFORMANCE_BENCHMARKS.md)

---

*For questions or issues with performance testing, please open an issue in the main repository.*