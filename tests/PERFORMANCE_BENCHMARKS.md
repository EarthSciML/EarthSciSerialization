# Performance Benchmarks for Security and Robustness Tests

This document defines the performance requirements and expected benchmarks for all security and robustness test fixtures.

## Benchmark Categories

### Memory Usage Benchmarks

#### Small Files (< 1MB)
- **Target**: < 50MB RAM during parsing
- **Maximum**: < 100MB RAM
- **Test Files**: Most security fixtures, basic robustness tests

#### Medium Files (1-10MB)
- **Target**: < 200MB RAM during parsing
- **Maximum**: < 500MB RAM
- **Test Files**: `resource_exhaustion.esm`, `deep_equation_chains.esm`

#### Large Files (10-100MB)
- **Target**: < 1GB RAM during parsing
- **Maximum**: < 2GB RAM
- **Test Files**: `mega_payload_attack.esm`, `memory_exhaustion_variables.esm`

#### Massive Files (>100MB)
- **Target**: < 4GB RAM during parsing
- **Maximum**: < 8GB RAM
- **Test Files**: `mega_reaction_system.esm`, `massive_coupling_graph.esm`

### Parsing Time Benchmarks

#### Security Tests (Failure Cases)
- **Target**: < 1 second to detect and report errors
- **Maximum**: < 5 seconds
- **Rationale**: Security validation should be fast to prevent DoS

#### Robustness Tests (Success Cases)
- **Small Files**: < 5 seconds
- **Medium Files**: < 15 seconds
- **Large Files**: < 30 seconds
- **Massive Files**: < 120 seconds

### Validation Time Benchmarks

#### Schema Validation
- **Target**: < 10% of parsing time
- **Maximum**: < 50% of parsing time

#### Structural Validation
- **Dependency Analysis**: < 30 seconds for any file
- **Circular Reference Detection**: < 10 seconds for any file
- **Coupling Graph Analysis**: < 60 seconds for massive graphs

## Specific File Benchmarks

### Security Test Performance

| File | Size Limit | Parse Time | Memory | Notes |
|------|------------|------------|---------|-------|
| `malformed_json_syntax.esm` | < 1KB | < 0.1s | < 10MB | Should fail fast |
| `deeply_nested_json.esm` | < 100KB | < 2s | < 50MB | Depth limit check |
| `mega_payload_attack.esm` | > 50MB | < 30s | < 2GB | Memory bomb test |
| `excessive_nesting_bomb.esm` | < 10KB | < 1s | < 20MB | Should reject quickly |
| `billion_laughs_json.esm` | < 5KB | < 0.5s | < 15MB | Expansion bomb |
| `unicode_normalization_attack.esm` | < 5KB | < 1s | < 10MB | Character validation |

### Robustness Test Performance

| File | Size Limit | Parse Time | Memory | Validation Time |
|------|------------|------------|---------|------------------|
| `memory_exhaustion_variables.esm` | > 20MB | < 30s | < 2GB | < 60s |
| `mega_reaction_system.esm` | > 100MB | < 45s | < 4GB | < 90s |
| `massive_coupling_graph.esm` | > 50MB | < 120s | < 8GB | < 180s |
| `deep_equation_chains.esm` | > 10MB | < 15s | < 1GB | < 30s |
| `numerical_edge_cases.esm` | < 1MB | < 5s | < 50MB | < 10s |
| `circular_coupling_dependencies.esm` | < 100KB | < 2s | < 20MB | < 5s |

## Platform Requirements

### Minimum Hardware
- **CPU**: 2 cores, 2.0 GHz
- **RAM**: 8GB available
- **Storage**: SSD preferred for I/O intensive tests

### Target Hardware
- **CPU**: 4+ cores, 3.0+ GHz
- **RAM**: 16GB available
- **Storage**: NVMe SSD

### Performance Scaling

#### CPU Scaling
- Parsing should utilize multiple cores where possible
- Validation can be parallelized for independent checks
- Expression evaluation should be vectorizable

#### Memory Scaling
- Memory usage should scale sub-linearly with file size
- Streaming parsing recommended for files > 50MB
- Garbage collection should be efficient

## Testing Methodology

### Automated Benchmarking

```bash
# Example benchmark script
for test_file in tests/{security,robustness}/*.esm; do
    echo "Benchmarking: $test_file"

    # Measure parsing time
    start_time=$(date +%s.%N)
    result=$(parse_esm_file "$test_file")
    end_time=$(date +%s.%N)
    parse_time=$(echo "$end_time - $start_time" | bc)

    # Measure peak memory usage
    /usr/bin/time -v parse_esm_file "$test_file" 2>&1 | \
        grep "Maximum resident set size"

    echo "Parse time: ${parse_time}s"
    echo "---"
done
```

### Memory Profiling

1. Use platform-specific memory profilers:
   - **Linux**: `valgrind --tool=massif`
   - **macOS**: `leaks` and Activity Monitor
   - **Windows**: Application Verifier

2. Monitor for:
   - Peak memory usage
   - Memory leaks
   - Fragmentation patterns
   - GC pressure

### Performance Regression Detection

- Benchmark results should be tracked over time
- Alert on > 20% performance regression
- Consider hardware variations in CI/CD
- Test on multiple platforms and architectures

## Expected Failure Modes

### Graceful Degradation
- **Memory Exhaustion**: Should report error, not crash
- **Time Limits**: Should timeout gracefully with partial results
- **Stack Overflow**: Should detect and report recursion depth

### Performance Boundaries
- **File Size**: Reject files > 1GB with clear error message
- **Variable Count**: Warn when > 100,000 variables
- **Nesting Depth**: Reject expressions > 1000 levels deep
- **Parse Time**: Timeout after 5 minutes with progress report

## Implementation Guidelines

### Parser Optimization
- Use streaming JSON parsers for large files
- Implement lazy loading for optional sections
- Cache frequently accessed schema validations
- Minimize memory copying during parsing

### Memory Management
- Use memory pools for small, frequent allocations
- Implement reference counting for shared objects
- Clear intermediate data structures promptly
- Monitor and limit total memory consumption

### Error Handling
- Provide progress callbacks for long operations
- Include memory usage in error messages
- Implement circuit breakers for resource limits
- Log performance metrics for debugging

---

*These benchmarks are guidelines for implementation. Actual performance may vary based on hardware, platform, and specific implementation choices.*