//! Structural validation error code tests
//!
//! Tests the structural validation logic that goes beyond JSON schema validation.

use earthsci_toolkit::*;

/// Test unknown variable reference error
#[test]
fn test_unknown_variable_reference() {
    let fixture = include_str!("../../../tests/invalid/unknown_variable_ref.esm");

    let parsed_result = load(fixture);

    match parsed_result {
        Ok(esm_file) => {
            // File parsed successfully, now test structural validation
            let validation_result = validate(&esm_file);
            assert!(validation_result.has_errors());

            // Check for unknown variable reference error
            let has_unknown_var_error = validation_result
                .errors()
                .iter()
                .any(|err| matches!(err.code, StructuralErrorCode::UndefinedVariable));
            assert!(has_unknown_var_error, "Expected UndefinedVariable error");
        }
        Err(_) => {
            // If it fails to parse, that's also acceptable for this test
        }
    }
}

/// Test undefined species in reactions
#[test]
fn test_undefined_species() {
    let fixtures = [
        (
            "undefined_species",
            include_str!("../../../tests/invalid/undefined_species.esm"),
        ),
        (
            "undefined_species_in_substrates",
            include_str!("../../../tests/invalid/undefined_species_in_substrates.esm"),
        ),
        (
            "undefined_species_in_products",
            include_str!("../../../tests/invalid/undefined_species_in_products.esm"),
        ),
    ];

    for (name, fixture) in fixtures {
        let parsed_result = load(fixture);

        match parsed_result {
            Ok(esm_file) => {
                let validation_result = validate(&esm_file);
                assert!(
                    validation_result.has_errors(),
                    "Expected {} to have validation errors",
                    name
                );

                let has_undefined_species_error = validation_result
                    .errors()
                    .iter()
                    .any(|err| matches!(err.code, StructuralErrorCode::UndefinedSpecies));
                assert!(
                    has_undefined_species_error,
                    "Expected UndefinedSpecies error for {}",
                    name
                );
            }
            Err(_) => {
                // Parse failure is also acceptable
            }
        }
    }
}

/// Test undefined parameter errors
#[test]
fn test_undefined_parameter() {
    let fixtures = [
        (
            "undefined_parameter",
            include_str!("../../../tests/invalid/undefined_parameter.esm"),
        ),
        (
            "undefined_parameter_simple_rate",
            include_str!("../../../tests/invalid/undefined_parameter_simple_rate.esm"),
        ),
        (
            "undefined_parameter_complex_rate",
            include_str!("../../../tests/invalid/undefined_parameter_complex_rate.esm"),
        ),
    ];

    for (name, fixture) in fixtures {
        let parsed_result = load(fixture);

        match parsed_result {
            Ok(esm_file) => {
                let validation_result = validate(&esm_file);
                assert!(
                    validation_result.has_errors(),
                    "Expected {} to have validation errors",
                    name
                );

                let has_undefined_param_error = validation_result
                    .errors()
                    .iter()
                    .any(|err| matches!(err.code, StructuralErrorCode::UndefinedParameter));
                assert!(
                    has_undefined_param_error,
                    "Expected UndefinedParameter error for {}",
                    name
                );
            }
            Err(_) => {
                // Parse failure is also acceptable
            }
        }
    }
}

/// Test equation count mismatch
#[test]
fn test_equation_count_mismatch() {
    let fixtures = [
        (
            "equation_count_mismatch",
            include_str!("../../../tests/invalid/equation_count_mismatch.esm"),
        ),
        (
            "equation_count_mismatch_too_many_vars",
            include_str!("../../../tests/invalid/equation_count_mismatch_too_many_vars.esm"),
        ),
        (
            "equation_count_mismatch_too_many_equations",
            include_str!("../../../tests/invalid/equation_count_mismatch_too_many_equations.esm"),
        ),
    ];

    for (name, fixture) in fixtures {
        let parsed_result = load(fixture);

        match parsed_result {
            Ok(esm_file) => {
                let validation_result = validate(&esm_file);
                assert!(
                    validation_result.has_errors(),
                    "Expected {} to have validation errors",
                    name
                );

                let has_equation_count_error = validation_result
                    .errors()
                    .iter()
                    .any(|err| matches!(err.code, StructuralErrorCode::EquationCountMismatch));
                assert!(
                    has_equation_count_error,
                    "Expected EquationCountMismatch error for {}",
                    name
                );
            }
            Err(_) => {
                // Parse failure is also acceptable
            }
        }
    }
}

/// Test null reaction validation
#[test]
fn test_null_reaction() {
    let fixtures = [
        (
            "null_reaction",
            include_str!("../../../tests/invalid/null_reaction.esm"),
        ),
        (
            "null_reaction_explicit_nulls",
            include_str!("../../../tests/invalid/null_reaction_explicit_nulls.esm"),
        ),
    ];

    for (name, fixture) in fixtures {
        let parsed_result = load(fixture);

        match parsed_result {
            Ok(esm_file) => {
                let validation_result = validate(&esm_file);
                assert!(
                    validation_result.has_errors(),
                    "Expected {} to have validation errors",
                    name
                );

                let has_null_reaction_error = validation_result
                    .errors()
                    .iter()
                    .any(|err| matches!(err.code, StructuralErrorCode::NullReaction));
                assert!(
                    has_null_reaction_error,
                    "Expected NullReaction error for {}",
                    name
                );
            }
            Err(_) => {
                // Parse failure is also acceptable
            }
        }
    }
}

/// Test missing observed expression
#[test]
fn test_missing_observed_expression() {
    let fixtures = [
        (
            "missing_observed_expr",
            include_str!("../../../tests/invalid/missing_observed_expr.esm"),
        ),
        (
            "missing_observed_expr_single",
            include_str!("../../../tests/invalid/missing_observed_expr_single.esm"),
        ),
        (
            "missing_observed_expr_multiple",
            include_str!("../../../tests/invalid/missing_observed_expr_multiple.esm"),
        ),
    ];

    for (name, fixture) in fixtures {
        let parsed_result = load(fixture);

        match parsed_result {
            Ok(esm_file) => {
                let validation_result = validate(&esm_file);
                assert!(
                    validation_result.has_errors(),
                    "Expected {} to have validation errors",
                    name
                );

                let has_missing_observed_error = validation_result
                    .errors()
                    .iter()
                    .any(|err| matches!(err.code, StructuralErrorCode::MissingObservedExpr));
                assert!(
                    has_missing_observed_error,
                    "Expected MissingObservedExpr error for {}",
                    name
                );
            }
            Err(_) => {
                // Parse failure is also acceptable
            }
        }
    }
}

/// Test unresolved scoped references
#[test]
fn test_unresolved_scoped_reference() {
    let fixtures = [
        (
            "unresolved_scoped_ref",
            include_str!("../../../tests/invalid/unresolved_scoped_ref.esm"),
        ),
        (
            "unresolved_scoped_ref_missing_system",
            include_str!("../../../tests/invalid/unresolved_scoped_ref_missing_system.esm"),
        ),
        (
            "unresolved_scoped_ref_missing_variable",
            include_str!("../../../tests/invalid/unresolved_scoped_ref_missing_variable.esm"),
        ),
    ];

    for (name, fixture) in fixtures {
        let parsed_result = load(fixture);

        match parsed_result {
            Ok(esm_file) => {
                let validation_result = validate(&esm_file);
                assert!(
                    validation_result.has_errors(),
                    "Expected {} to have validation errors",
                    name
                );

                let has_unresolved_ref_error = validation_result
                    .errors()
                    .iter()
                    .any(|err| matches!(err.code, StructuralErrorCode::UnresolvedScopedRef));
                assert!(
                    has_unresolved_ref_error,
                    "Expected UnresolvedScopedRef error for {}",
                    name
                );
            }
            Err(_) => {
                // Parse failure is also acceptable
            }
        }
    }
}

/// Test event variable undeclared errors
#[test]
fn test_event_variable_undeclared() {
    let fixtures = [
        (
            "event_var_undeclared",
            include_str!("../../../tests/invalid/event_var_undeclared.esm"),
        ),
        (
            "event_var_undeclared_condition",
            include_str!("../../../tests/invalid/event_var_undeclared_condition.esm"),
        ),
        (
            "event_var_undeclared_affects",
            include_str!("../../../tests/invalid/event_var_undeclared_affects.esm"),
        ),
    ];

    for (name, fixture) in fixtures {
        let parsed_result = load(fixture);

        match parsed_result {
            Ok(esm_file) => {
                let validation_result = validate(&esm_file);
                assert!(
                    validation_result.has_errors(),
                    "Expected {} to have validation errors",
                    name
                );

                let has_event_var_error = validation_result
                    .errors()
                    .iter()
                    .any(|err| matches!(err.code, StructuralErrorCode::EventVarUndeclared));
                assert!(
                    has_event_var_error,
                    "Expected EventVarUndeclared error for {}",
                    name
                );
            }
            Err(_) => {
                // Parse failure is also acceptable
            }
        }
    }
}

/// Test invalid discrete parameter
#[test]
fn test_invalid_discrete_parameter() {
    let fixtures = [
        (
            "invalid_discrete_param",
            include_str!("../../../tests/invalid/invalid_discrete_param.esm"),
        ),
        (
            "invalid_discrete_param_not_parameter",
            include_str!("../../../tests/invalid/invalid_discrete_param_not_parameter.esm"),
        ),
    ];

    for (name, fixture) in fixtures {
        let parsed_result = load(fixture);

        match parsed_result {
            Ok(esm_file) => {
                let validation_result = validate(&esm_file);
                assert!(
                    validation_result.has_errors(),
                    "Expected {} to have validation errors",
                    name
                );

                let has_invalid_discrete_error = validation_result
                    .errors()
                    .iter()
                    .any(|err| matches!(err.code, StructuralErrorCode::InvalidDiscreteParam));
                assert!(
                    has_invalid_discrete_error,
                    "Expected InvalidDiscreteParam error for {}",
                    name
                );
            }
            Err(_) => {
                // Parse failure is also acceptable
            }
        }
    }
}

/// Test undefined operator errors
#[test]
fn test_undefined_operator() {
    let fixtures = [
        (
            "undefined_operator",
            include_str!("../../../tests/invalid/undefined_operator.esm"),
        ),
        (
            "undefined_operator_in_apply",
            include_str!("../../../tests/invalid/undefined_operator_in_apply.esm"),
        ),
    ];

    for (name, fixture) in fixtures {
        let parsed_result = load(fixture);

        match parsed_result {
            Ok(esm_file) => {
                let validation_result = validate(&esm_file);
                assert!(
                    validation_result.has_errors(),
                    "Expected {} to have validation errors",
                    name
                );

                let has_undefined_operator_error = validation_result
                    .errors()
                    .iter()
                    .any(|err| matches!(err.code, StructuralErrorCode::UndefinedOperator));
                assert!(
                    has_undefined_operator_error,
                    "Expected UndefinedOperator error for {}",
                    name
                );
            }
            Err(_) => {
                // Parse failure is also acceptable
            }
        }
    }
}

/// Test undefined variable in various contexts
#[test]
fn test_undefined_variable_contexts() {
    let fixtures = [
        (
            "undefined_variable_in_rhs",
            include_str!("../../../tests/invalid/undefined_variable_in_rhs.esm"),
        ),
        (
            "undefined_variable_in_nested_expr",
            include_str!("../../../tests/invalid/undefined_variable_in_nested_expr.esm"),
        ),
    ];

    for (name, fixture) in fixtures {
        let parsed_result = load(fixture);

        match parsed_result {
            Ok(esm_file) => {
                let validation_result = validate(&esm_file);
                assert!(
                    validation_result.has_errors(),
                    "Expected {} to have validation errors",
                    name
                );

                let has_undefined_var_error = validation_result
                    .errors()
                    .iter()
                    .any(|err| matches!(err.code, StructuralErrorCode::UndefinedVariable));
                assert!(
                    has_undefined_var_error,
                    "Expected UndefinedVariable error for {}",
                    name
                );
            }
            Err(_) => {
                // Parse failure is also acceptable
            }
        }
    }
}

/// Test undefined system reference
#[test]
fn test_undefined_system() {
    let fixture = include_str!("../../../tests/invalid/undefined_system.esm");

    let parsed_result = load(fixture);

    match parsed_result {
        Ok(esm_file) => {
            let validation_result = validate(&esm_file);
            assert!(validation_result.has_errors());

            let has_undefined_system_error = validation_result
                .errors()
                .iter()
                .any(|err| matches!(err.code, StructuralErrorCode::UndefinedSystem));
            assert!(has_undefined_system_error, "Expected UndefinedSystem error");
        }
        Err(_) => {
            // Parse failure is also acceptable
        }
    }
}

/// Test multiple errors combined
#[test]
fn test_multiple_errors_combined() {
    let fixture = include_str!("../../../tests/invalid/multiple_errors_combined.esm");

    let parsed_result = load(fixture);

    match parsed_result {
        Ok(esm_file) => {
            let validation_result = validate(&esm_file);
            assert!(validation_result.has_errors());

            // Should have multiple different error types
            assert!(
                validation_result.errors().len() > 1,
                "Expected multiple validation errors"
            );
        }
        Err(_) => {
            // Parse failure is also acceptable for a severely malformed file
        }
    }
}

/// Test event error conditions
#[test]
fn test_event_error_conditions() {
    let fixture = include_str!("../../../tests/invalid/event_error_conditions.esm");

    let parsed_result = load(fixture);

    match parsed_result {
        Ok(esm_file) => {
            let validation_result = validate(&esm_file);
            assert!(validation_result.has_errors());
        }
        Err(_) => {
            // Parse failure is also acceptable
        }
    }
}

/// Test circular dependency detection.
///
/// Accepts either outcome: `load()` may reject the fixture at parse time
/// (the current behavior after cross-language conformance tightening in
/// gt-sac), or `load()` may succeed and the `validate()` pass must find a
/// `CircularDependency` structural error. Both paths are valid realizations
/// of the spec §3.2 rule; the stricter parse-time rejection matches Julia
/// and Python.
#[test]
fn test_circular_dependency_detection() {
    let fixture = include_str!("../../../tests/invalid/circular_coupling.esm");

    match load(fixture) {
        Ok(esm_file) => {
            let validation_result = validate(&esm_file);
            assert!(
                validation_result.has_errors(),
                "Expected circular coupling to have validation errors"
            );

            let has_circular_dependency_error = validation_result
                .errors()
                .iter()
                .any(|err| matches!(err.code, StructuralErrorCode::CircularDependency));
            assert!(
                has_circular_dependency_error,
                "Expected CircularDependency error"
            );

            let errors = validation_result.errors();
            let circular_error = errors
                .iter()
                .find(|err| matches!(err.code, StructuralErrorCode::CircularDependency))
                .expect("CircularDependency error should exist");

            assert!(
                circular_error
                    .message
                    .contains("Circular dependency detected")
            );
            assert!(circular_error.message.contains("ModelA"));
            assert!(circular_error.message.contains("ModelB"));
        }
        Err(e) => {
            let msg = e.to_string();
            assert!(
                msg.contains("cycle") || msg.contains("circular"),
                "Expected load() failure to mention a cycle, got: {msg}"
            );
            assert!(
                msg.contains("ModelA") && msg.contains("ModelB"),
                "Expected load() failure to name both models, got: {msg}"
            );
        }
    }
}

/// Test that valid cross-model references (non-circular) pass validation
#[test]
fn test_valid_cross_model_references() {
    // Test a valid model with cross-references but no circular dependencies
    let json_str = r#"{
        "esm": "0.1.0",
        "metadata": {
            "name": "ValidCrossModelTest",
            "description": "Test file with valid cross-model references (no cycles)"
        },
        "models": {
            "SourceModel": {
                "variables": {
                    "source_var": {
                        "type": "state",
                        "units": "mol/mol",
                        "default": 1.0
                    }
                },
                "equations": [
                    {
                        "lhs": { "op": "D", "args": ["source_var"], "wrt": "t" },
                        "rhs": { "op": "*", "args": [-0.1, "source_var"] }
                    }
                ]
            },
            "SinkModel": {
                "variables": {
                    "sink_var": {
                        "type": "state",
                        "units": "mol/mol",
                        "default": 0.0
                    }
                },
                "equations": [
                    {
                        "lhs": { "op": "D", "args": ["sink_var"], "wrt": "t" },
                        "rhs": { "op": "*", "args": [0.1, "SourceModel.source_var"] }
                    }
                ]
            }
        }
    }"#;

    let parsed_result = load(json_str);

    match parsed_result {
        Ok(esm_file) => {
            let validation_result = validate(&esm_file);

            // Should not have circular dependency errors
            let has_circular_dependency_error = validation_result
                .errors()
                .iter()
                .any(|err| matches!(err.code, StructuralErrorCode::CircularDependency));
            assert!(
                !has_circular_dependency_error,
                "Valid cross-model references should not trigger CircularDependency error"
            );

            // Should not have unresolved scoped reference errors for valid references
            let has_unresolved_ref_error = validation_result
                .errors()
                .iter()
                .any(|err| matches!(err.code, StructuralErrorCode::UnresolvedScopedRef));
            assert!(
                !has_unresolved_ref_error,
                "Valid scoped references should not trigger UnresolvedScopedRef error"
            );
        }
        Err(e) => {
            panic!(
                "Valid cross-model reference file should parse successfully, but got error: {}",
                e
            );
        }
    }
}

/// units_reaction_rate_mismatch.esm declares a 2nd-order reaction A + B -> C
/// with species in mol/L and rate parameter k in 1/s (should be L/(mol*s)).
/// Must be rejected as a structural error across all bindings (gt-zs9o).
#[test]
fn test_reaction_rate_units_mismatch_fixture_rejected() {
    let fixture = include_str!("../../../tests/invalid/units_reaction_rate_mismatch.esm");
    let esm_file = load(fixture).expect("fixture should parse and schema-validate");
    let result = validate(&esm_file);
    let err = result
        .errors()
        .into_iter()
        .find(|e| matches!(e.code, StructuralErrorCode::UnitInconsistency))
        .unwrap_or_else(|| {
            panic!(
                "expected UnitInconsistency error for units_reaction_rate_mismatch.esm, got: {:?}",
                result.errors()
            )
        });
    // Match the contract in tests/invalid/expected_errors.json.
    assert_eq!(
        err.message,
        "Reaction rate expression has incompatible units for reaction stoichiometry"
    );
    assert_eq!(err.details["reaction_id"], "R1");
    assert_eq!(err.details["rate_units"], "1/s");
    assert_eq!(err.details["expected_rate_units"], "L/(mol*s)");
    assert_eq!(err.details["reaction_order"], 2);
}

/// units_dimensional_constant_error.esm declares the ideal gas constant `R`
/// with units `kcal/mol` — missing the temperature dimension (canonical is
/// `J/(mol*K)`). Must be rejected as a structural unit_inconsistency error
/// across all bindings, reported at the usage site `gas_law_calculation`
/// (mirrors Python's `_check_physical_constant_units`, gt-3tgv).
#[test]
fn test_physical_constant_dimensional_error_fixture_rejected() {
    let fixture = include_str!("../../../tests/invalid/units_dimensional_constant_error.esm");
    let esm_file = load(fixture).expect("fixture should parse and schema-validate");
    let result = validate(&esm_file);
    let err = result
        .errors()
        .into_iter()
        .find(|e| {
            matches!(e.code, StructuralErrorCode::UnitInconsistency)
                && e.message == "Physical constant used with incorrect dimensional analysis"
        })
        .unwrap_or_else(|| {
            panic!(
                "expected UnitInconsistency (physical constant) for units_dimensional_constant_error.esm, got: {:?}",
                result.errors()
            )
        });
    assert_eq!(
        err.path,
        "/models/ConstantUnitsModel/variables/gas_law_calculation"
    );
    assert_eq!(err.details["constant_name"], "R");
    assert_eq!(err.details["constant_description"], "ideal gas constant");
    assert_eq!(err.details["declared_units"], "kcal/mol");
    assert_eq!(err.details["canonical_units"], "J/(mol*K)");
}

/// units_gradient_operator_mismatch.esm applies `grad` over a spatial
/// coordinate `x` that is declared in the domain without units. A validator
/// that models grad/div/laplacian cannot infer the result's dimension and must
/// emit a structured `unit_inconsistency` error at the equation site, rather
/// than silently assuming metres. Mirrors the TypeScript binding's behaviour
/// and the Julia binding's `_check_gradient_ops` (gt-sosg, gt-ui96).
#[test]
fn test_gradient_operator_spatial_units_mismatch_rejected() {
    let fixture = include_str!("../../../tests/invalid/units_gradient_operator_mismatch.esm");
    let esm_file = load(fixture).expect("fixture should parse and schema-validate");
    let result = validate(&esm_file);
    let err = result
        .errors()
        .into_iter()
        .find(|e| {
            matches!(e.code, StructuralErrorCode::UnitInconsistency)
                && e.message
                    == "Gradient operator applied to variable with incompatible spatial units"
        })
        .unwrap_or_else(|| {
            panic!(
                "expected UnitInconsistency (gradient) for units_gradient_operator_mismatch.esm, got: {:?}",
                result.errors()
            )
        });
    assert_eq!(err.path, "/models/SpatialModel/equations/0");
    assert_eq!(err.details["operator"], "grad");
    assert_eq!(err.details["variable"], "c");
    assert_eq!(err.details["variable_units"], "mol/m^3");
    assert_eq!(err.details["dim"], "x");
    assert!(err.details["coordinate_units"].is_null());
    assert_eq!(err.details["equation_index"], 0);
    assert!(!result.is_valid);
}
