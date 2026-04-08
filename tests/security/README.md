# Security and Robustness Test Fixtures

This directory contains test fixtures designed to ensure ESM format implementations are robust against malicious or malformed inputs and handle edge cases securely.

## Test Categories

### JSON Parsing Security
- **malformed_json_syntax.esm**: Tests malformed JSON with trailing commas, unclosed brackets
- **malformed_json_quotes.esm**: Tests unescaped quotes and control characters in JSON
- **deeply_nested_json.esm**: Tests parser bombing with deeply nested structures (30+ levels)

### Numerical Security
- **large_numbers_overflow.esm**: Tests very large numbers that may cause floating-point overflow
- **resource_exhaustion.esm**: Tests memory exhaustion with very long strings and many fields

### Expression Security
- **circular_expression_refs.esm**: Tests circular reference detection in observed variable expressions
- **expression_injection.esm**: Tests input sanitization for unsafe operators and function calls

### Character Encoding Security
- **null_byte_injection.esm**: Tests null byte injection and control character handling
- **unicode_attacks.esm**: Tests Unicode normalization attacks, homograph attacks, and zero-width characters

## Security Requirements

All ESM format implementations must:

1. **Parse safely**: Handle malformed JSON gracefully without crashing
2. **Prevent resource exhaustion**: Set reasonable limits on:
   - Maximum nesting depth (recommended: 100 levels)
   - Maximum string length (recommended: 1MB)
   - Maximum number of fields (recommended: 10,000)
   - Parsing time limits (recommended: 5 seconds)

3. **Detect circular references**: Identify and reject circular dependencies in:
   - Expression variable references
   - Coupling system references
   - Observed variable expression chains

4. **Sanitize input**: Reject or escape:
   - Null bytes and control characters in identifiers
   - Unicode homograph attacks (mixing scripts)
   - Zero-width characters that could hide malicious content
   - Unsafe operators in expressions

5. **Handle large numbers**: Gracefully process:
   - Very large floating-point numbers
   - Numbers that exceed representation limits
   - Prevent infinite or NaN values from propagating

## Implementation Notes

- These tests should be run in isolated environments
- Libraries should never execute arbitrary code from expressions
- All user input should be validated against allowed operators/functions
- Consider implementing sandboxing for expression evaluation
- Log security violations for monitoring

## Expected Behavior

Libraries should:
- ✅ Parse valid complex structures efficiently
- ✅ Reject malformed JSON with clear error messages
- ✅ Detect and report circular dependencies
- ✅ Sanitize dangerous input characters
- ❌ Never execute arbitrary code
- ❌ Never crash on malformed input
- ❌ Never consume excessive system resources

See `expected_errors.json` for detailed expected validation results.