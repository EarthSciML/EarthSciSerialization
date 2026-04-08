# Coupling Resolution Algorithm Test Fixtures

This directory contains comprehensive test fixtures for verifying the coupling resolution algorithms described in Section 4.7 of the ESM format specification.

## Overview

Coupling resolution is the process of combining individual models, reaction systems, data loaders, and operators into a single system according to the coupling rules. These test fixtures ensure deterministic coupling resolution across all implementations.

## Test Fixture Files

### 1. `operator_compose_resolution_fixtures.esm`
Tests the `operator_compose` algorithm (Section 4.7.1) that merges ODE systems by matching time derivatives and adding RHS terms.

**Key Test Cases:**
- Basic placeholder expansion (`_var` → all state variables)
- Translation mappings between systems
- Conversion factors in translation
- Mixing different equation types

**Verification Points:**
- Dependent variable extraction from equation LHS
- Placeholder expansion with state variable matching
- Translation map application with conversion factors
- RHS combination (`rhs_A + factor * rhs_B`)

### 2. `couple2_resolution_fixtures.esm`
Tests the `couple2` algorithm (Section 4.7.2) that provides bidirectional coupling via ConnectorSystem equations.

**Key Test Cases:**
- Additive transforms (source added to target equation RHS)
- Multiplicative transforms (target RHS multiplied by source)
- Replacement transforms (target RHS completely replaced)
- Multi-directional coupling scenarios

**Verification Points:**
- Connector equation resolution
- Transform type application
- Shared variable creation across systems
- Bidirectional coupling semantics

### 3. `variable_map_resolution_fixtures.esm`
Tests the `variable_map` algorithm (Section 4.7.3) that replaces parameters with variables from other systems.

**Key Test Cases:**
- `param_to_var`: Parameter promoted to time-varying variable
- `identity`: Direct assignment without type change
- `additive`: Source value added to target equation RHS
- `multiplicative`: Target equation RHS multiplied by source
- `conversion_factor`: Parameter promotion with unit conversion

**Verification Points:**
- Scoped reference resolution
- Transform type semantics
- Parameter/variable list updates
- Cross-system variable sharing

### 4. `multi_step_coupling_chains_fixtures.esm`
Tests complex multi-step coupling scenarios combining multiple algorithms in sequence.

**Key Test Cases:**
- 10-step coupling chain using all coupling types
- Order-independent coupling verification
- Cross-system dependency chains
- Mixed data loader, operator, and model coupling

**Verification Points:**
- Coupling commutativity (order independence)
- Multi-algorithm interaction
- Complex dependency resolution
- Final merged system structure

### 5. `coupling_resolution_edge_cases.esm`
Tests edge cases and boundary conditions that coupling algorithms must handle correctly.

**Key Test Cases:**
- Empty systems and empty equations
- Self-coupling (system coupled to itself)
- Variable name conflicts and disambiguation
- Placeholder expansion with no state variables
- Mixed equation types (ODE, algebraic, discrete)

**Verification Points:**
- Edge case handling
- Error-free composition of empty systems
- Conflict resolution strategies
- Type compatibility checks

### 6. `comprehensive_coupling_resolution_errors.esm` (in `tests/invalid/`)
Tests error conditions that coupling resolution algorithms must detect and report.

**Key Test Cases:**
- Invalid scoped references
- Type mismatches in variable mappings
- Invalid transform types
- Missing required fields
- Circular dependencies
- Invalid operator/callback references

**Verification Points:**
- Deterministic error reporting
- Consistent error codes across implementations
- Early validation and error detection
- Proper error message content

## Algorithm Verification

### `operator_compose` Algorithm Steps
1. Extract dependent variables from equation LHS
2. Apply translation mappings between systems
3. Match equations by dependent variables or placeholder expansion
4. Combine matched equations by adding RHS terms
5. Preserve unmatched equations unchanged

### `couple2` Algorithm Steps
1. Read connector.equations array
2. Resolve 'from' and 'to' scoped references
3. Apply coupling based on transform type
4. Create shared variables across systems

### `variable_map` Algorithm Steps
1. Resolve 'from' scoped reference to source system and variable
2. Resolve 'to' scoped reference to target system and parameter
3. Apply transform based on type
4. Update merged system's variable/parameter lists

## Expected Test Results

### Success Cases
All fixtures except those in `tests/invalid/` should load successfully and produce the documented coupling results in the `_test_verification` sections.

### Error Cases
Files in `tests/invalid/` should produce the specific error codes and messages documented in their `_expected_error` fields.

### Cross-Implementation Consistency
All library implementations must produce:
- Identical final coupled systems for success cases
- Identical error codes and messages for error cases
- Deterministic results regardless of coupling order

## Usage in Test Suites

### For Library Implementers
1. Load each fixture file
2. Execute coupling resolution algorithm
3. Compare results with documented expected outcomes
4. Verify error handling for invalid fixtures

### For Validation Libraries
1. Parse coupling entries and validate references
2. Check algorithm compliance with documented steps
3. Verify deterministic error reporting

### For Integration Testing
1. Test round-trip coupling resolution
2. Verify cross-system variable sharing
3. Test complex multi-step scenarios

## Implementation Notes

### Order Independence
Coupling rules are commutative - the same mathematical system must be produced regardless of the order in which coupling rules are applied. Test files include verification that different processing orders yield identical results.

### Error Handling
- Errors should be deterministic and reproducible
- Error codes must be consistent across implementations
- Libraries should continue processing other coupling entries after encountering errors
- Multiple errors should be collected and reported together

### Performance Considerations
- Implementations should process coupling entries efficiently
- Circular dependency detection should be optimized
- Large coupling chains should scale appropriately

This comprehensive test suite ensures that all coupling resolution algorithms work correctly and consistently across different ESM format library implementations.