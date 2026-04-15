# Robustness Test Fixtures

This directory contains test fixtures designed to test the robustness and fault tolerance of ESM format implementations under extreme conditions and edge cases.

## Test Categories

### Memory and Resource Management
- **memory_exhaustion_variables.esm**: Tests with >100,000 variables to stress memory allocation
- **mega_reaction_system.esm**: Tests with >50,000 species and >10,000 reactions
- **deep_equation_chains.esm**: Tests with very long equation dependency chains
- **massive_coupling_graph.esm**: Tests with complex inter-model coupling scenarios

### Numerical Robustness
- **numerical_edge_cases.esm**: Tests overflow, underflow, NaN, Inf handling
- **platform_precision_differences.esm**: Tests floating-point precision across platforms
- **catastrophic_cancellation.esm**: Tests numerical stability in edge cases
- **denormal_number_handling.esm**: Tests very small number representations

### Recursion and Circular Dependencies
- **circular_coupling_dependencies.esm**: Tests circular model coupling detection
- **infinite_recursion_expressions.esm**: Tests infinite recursion detection
- **stack_overflow_substitutions.esm**: Tests deep substitution chain handling
- **self_referential_systems.esm**: Tests variables that reference themselves

### Performance and Scalability
- **parser_performance_stress.esm**: Tests parser performance with large files
- **expression_evaluation_stress.esm**: Tests complex expression evaluation
- **memory_fragmentation_test.esm**: Tests memory fragmentation scenarios
- **concurrent_access_simulation.esm**: Tests thread-safety scenarios

### Error Recovery and Graceful Degradation
- **partial_corruption_recovery.esm**: Tests recovery from partially corrupted files
- **schema_evolution_stress.esm**: Tests handling of mixed schema versions
- **malformed_expression_recovery.esm**: Tests recovery from expression errors
- **missing_dependency_handling.esm**: Tests handling of missing variable references

## Performance Requirements

Each implementation must:

1. **Memory Limits**: Handle files up to 1GB without excessive memory usage (max 4x file size)
2. **Time Limits**: Parse any valid file within 30 seconds on standard hardware
3. **Error Recovery**: Gracefully handle and report errors without crashing
4. **Resource Cleanup**: Properly release resources even when parsing fails

## Expected Behavior

### Memory Management
- ✅ Efficient memory allocation for large variable counts
- ✅ Proper cleanup on parsing failures
- ✅ Reasonable memory usage scaling
- ❌ Memory leaks or excessive allocation

### Error Handling
- ✅ Clear error messages for invalid content
- ✅ Partial parsing where possible
- ✅ Graceful degradation on resource limits
- ❌ Crashes or silent failures

### Performance
- ✅ Sub-linear scaling for most operations
- ✅ Streaming or chunked processing for large files
- ✅ Bounded resource consumption
- ❌ Exponential time/memory complexity

## Testing Guidelines

1. Run tests in isolated environments with resource limits
2. Monitor memory usage during parsing
3. Set reasonable timeouts (30 seconds for parsing)
4. Test on multiple platforms and architectures
5. Verify error messages are helpful and actionable

See individual test files for specific expected behaviors and performance benchmarks.