# Coupling Resolution Algorithm Verification Tests

This directory contains comprehensive test fixtures for verifying the ESM scoped reference resolution algorithm described in Section 4.3 of the ESM format specification.

## Algorithm Overview

The scoped reference resolution algorithm handles hierarchical dot notation like `"AtmosphereModel.Chemistry.FastReactions.k1"`:

1. **Split on dots**: `"A.B.C.var"` → `["A", "B", "C", "var"]`
2. **Identify components**:
   - Final segment (`var`) is the variable/species/parameter name
   - Preceding segments (`["A", "B", "C"]`) form the system path
3. **Walk hierarchy**:
   - `A` must match a key in top-level `models`, `reaction_systems`, `data_loaders`, or `operators`
   - `B` must match a key in `A`'s `subsystems` map
   - `C` must match a key in `B`'s `subsystems` map
   - Continue until reaching the parent system of the variable
4. **Resolve variable**: Find `var` in the final system's `variables`/`species`/`parameters`

## Test Structure

### Success Cases (`coupling_resolution_algorithm.esm`)

This file provides positive test cases that verify each step of the algorithm works correctly:

| Test Case | Reference | Algorithm Steps Verified |
|-----------|-----------|-------------------------|
| Case 1 | `AtmosphereModel.Chemistry` | 2-level system resolution |
| Case 2 | `MeteorologicalData.temperature` | Data loader variable resolution |
| Case 3 | `AtmosphereModel.Chemistry.temperature` | 3-level hierarchy walking |
| Case 4 | `AtmosphereModel.Chemistry.FastReactions.k1` | 4-level deep nesting |
| Case 5 | `AtmosphereModel.Transport.Advection.u_wind` | Alternative branch navigation |
| Case 6 | `MeteorologicalData.QualityControl.data_quality_flag` | Data loader subsystem |
| Case 7 | `BiogenicEmissions.TemperatureDependence.beta` | Operator subsystem |
| Case 8 | References in `couple2` expressions | Scoped refs within expressions |

### Error Cases (`../invalid/coupling_resolution_errors.esm`)

This file provides negative test cases for each failure point in the algorithm:

| Error Type | Test Reference | Expected Error Code | Failure Point |
|------------|----------------|-------------------|--------------|
| Invalid top-level system | `NonExistentModel.valid_var` | `undefined_system` | Algorithm Step 4 |
| Invalid subsystem | `ValidModel.NonExistentSub.var` | `unresolved_scoped_ref` | Algorithm Step 5 |
| Invalid variable | `ValidModel.ValidSub.nonexistent_var` | `undefined_variable` | Algorithm Step 6 |
| Type error | `ValidModel.valid_var.invalid_access` | `unresolved_scoped_ref` | Type checking |

## Verification Points

### For Libraries Implementing Resolution

Libraries should verify they correctly implement each step:

1. **String Parsing**:
   ```javascript
   function splitScopedReference(ref) {
     const segments = ref.split('.');
     if (segments.length < 2) throw new Error("Invalid scoped reference");
     const variable = segments.pop();
     const systemPath = segments;
     return { systemPath, variable };
   }
   ```

2. **Top-Level Lookup**:
   ```javascript
   function findTopLevelSystem(systemName, esmFile) {
     return esmFile.models?.[systemName] ||
            esmFile.reaction_systems?.[systemName] ||
            esmFile.data_loaders?.[systemName] ||
            esmFile.operators?.[systemName];
   }
   ```

3. **Hierarchy Walking**:
   ```javascript
   function walkSubsystemPath(system, path) {
     let current = system;
     for (const segment of path) {
       if (!current.subsystems?.[segment]) {
         throw new Error(`Subsystem '${segment}' not found`);
       }
       current = current.subsystems[segment];
     }
     return current;
   }
   ```

4. **Variable Resolution**:
   ```javascript
   function resolveVariable(system, variableName) {
     return system.variables?.[variableName] ||
            system.species?.[variableName] ||
            system.parameters?.[variableName];
   }
   ```

### For Validators

Validation libraries should check that all scoped references in `coupling` entries resolve successfully using this algorithm.

### Test Data Hierarchy

The test files create this hierarchy to exercise all resolution paths:

```
AtmosphereModel (model)
├── pressure (variable)
├── temperature (variable)
├── Chemistry (subsystem)
│   ├── O3 (variable)
│   ├── temperature (variable)
│   ├── FastReactions (subsystem)
│   │   ├── k1 (variable) ← 4-level deep
│   │   └── k2 (variable)
│   └── SlowReactions (subsystem)
│       └── k_slow (variable)
└── Transport (subsystem)
    ├── wind_speed (variable)
    └── Advection (subsystem)
        ├── u_wind (variable) ← Alternative branch
        └── v_wind (variable)

MeteorologicalData (data_loader)
├── temperature (provided variable)
└── QualityControl (subsystem)
    └── data_quality_flag (variable) ← Data loader subsystem

BiogenicEmissions (operator)
└── TemperatureDependence (subsystem)
    └── beta (variable) ← Operator subsystem
```

## Usage

### For Test Runners

1. Load `coupling_resolution_algorithm.esm` and verify all coupling references resolve successfully
2. Load `coupling_resolution_errors.esm` and verify each coupling reference produces the expected error
3. Check that the step-by-step algorithm produces the same results as documented in the `_test_verification` section

### For Implementation Verification

Use these test cases to verify your resolution algorithm implementation:

```python
# Example verification
def test_resolution_algorithm():
    esm = load("coupling_resolution_algorithm.esm")

    # Test case: "AtmosphereModel.Chemistry.FastReactions.k1"
    ref = "AtmosphereModel.Chemistry.FastReactions.k1"

    # Step 1: Split
    segments = ref.split('.')  # ["AtmosphereModel", "Chemistry", "FastReactions", "k1"]
    variable_name = segments[-1]  # "k1"
    system_path = segments[:-1]  # ["AtmosphereModel", "Chemistry", "FastReactions"]

    # Step 2: Find top-level system
    top_system = esm.models["AtmosphereModel"]  # Should succeed

    # Step 3: Walk subsystem path
    current = top_system
    current = current.subsystems["Chemistry"]  # Should succeed
    current = current.subsystems["FastReactions"]  # Should succeed

    # Step 4: Resolve variable
    variable = current.variables["k1"]  # Should succeed

    assert variable.type == "parameter"
    assert variable.units == "1/s"
```

This comprehensive test suite ensures that any library implementing the ESM format correctly handles the hierarchical scoped reference resolution algorithm as specified in Section 4.3.