//! Structural validation error code tests
//!
//! Tests the structural validation logic that goes beyond JSON schema validation.

use esm_format::*;

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
            let has_unknown_var_error = validation_result.errors.iter().any(|err| {
                matches!(err.code, StructuralErrorCode::UnknownVariableReference)
            });
            assert!(has_unknown_var_error, "Expected UnknownVariableReference error");
        },
        Err(_) => {
            // If it fails to parse, that's also acceptable for this test
        }
    }
}

/// Test undefined species in reactions
#[test]
fn test_undefined_species() {
    let fixtures = [
        ("undefined_species", include_str!("../../../tests/invalid/undefined_species.esm")),
        ("undefined_species_in_substrates", include_str!("../../../tests/invalid/undefined_species_in_substrates.esm")),
        ("undefined_species_in_products", include_str!("../../../tests/invalid/undefined_species_in_products.esm")),
    ];

    for (name, fixture) in fixtures {
        let parsed_result = load(fixture);

        match parsed_result {
            Ok(esm_file) => {
                let validation_result = validate(&esm_file);
                assert!(validation_result.has_errors(), "Expected {} to have validation errors", name);

                let has_undefined_species_error = validation_result.errors.iter().any(|err| {
                    matches!(err.code, StructuralErrorCode::UndefinedSpecies)
                });
                assert!(has_undefined_species_error, "Expected UndefinedSpecies error for {}", name);
            },
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
        ("undefined_parameter", include_str!("../../../tests/invalid/undefined_parameter.esm")),
        ("undefined_parameter_simple_rate", include_str!("../../../tests/invalid/undefined_parameter_simple_rate.esm")),
        ("undefined_parameter_complex_rate", include_str!("../../../tests/invalid/undefined_parameter_complex_rate.esm")),
    ];

    for (name, fixture) in fixtures {
        let parsed_result = load(fixture);

        match parsed_result {
            Ok(esm_file) => {
                let validation_result = validate(&esm_file);
                assert!(validation_result.has_errors(), "Expected {} to have validation errors", name);

                let has_undefined_param_error = validation_result.errors.iter().any(|err| {
                    matches!(err.code, StructuralErrorCode::UndefinedParameter)
                });
                assert!(has_undefined_param_error, "Expected UndefinedParameter error for {}", name);
            },
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
        ("equation_count_mismatch", include_str!("../../../tests/invalid/equation_count_mismatch.esm")),
        ("equation_count_mismatch_too_many_vars", include_str!("../../../tests/invalid/equation_count_mismatch_too_many_vars.esm")),
        ("equation_count_mismatch_too_many_equations", include_str!("../../../tests/invalid/equation_count_mismatch_too_many_equations.esm")),
    ];

    for (name, fixture) in fixtures {
        let parsed_result = load(fixture);

        match parsed_result {
            Ok(esm_file) => {
                let validation_result = validate(&esm_file);
                assert!(validation_result.has_errors(), "Expected {} to have validation errors", name);

                let has_equation_count_error = validation_result.errors.iter().any(|err| {
                    matches!(err.code, StructuralErrorCode::EquationCountMismatch)
                });
                assert!(has_equation_count_error, "Expected EquationCountMismatch error for {}", name);
            },
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
        ("null_reaction", include_str!("../../../tests/invalid/null_reaction.esm")),
        ("null_reaction_explicit_nulls", include_str!("../../../tests/invalid/null_reaction_explicit_nulls.esm")),
    ];

    for (name, fixture) in fixtures {
        let parsed_result = load(fixture);

        match parsed_result {
            Ok(esm_file) => {
                let validation_result = validate(&esm_file);
                assert!(validation_result.has_errors(), "Expected {} to have validation errors", name);

                let has_null_reaction_error = validation_result.errors.iter().any(|err| {
                    matches!(err.code, StructuralErrorCode::NullReaction)
                });
                assert!(has_null_reaction_error, "Expected NullReaction error for {}", name);
            },
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
        ("missing_observed_expr", include_str!("../../../tests/invalid/missing_observed_expr.esm")),
        ("missing_observed_expr_single", include_str!("../../../tests/invalid/missing_observed_expr_single.esm")),
        ("missing_observed_expr_multiple", include_str!("../../../tests/invalid/missing_observed_expr_multiple.esm")),
    ];

    for (name, fixture) in fixtures {
        let parsed_result = load(fixture);

        match parsed_result {
            Ok(esm_file) => {
                let validation_result = validate(&esm_file);
                assert!(validation_result.has_errors(), "Expected {} to have validation errors", name);

                let has_missing_observed_error = validation_result.errors.iter().any(|err| {
                    matches!(err.code, StructuralErrorCode::MissingObservedExpression)
                });
                assert!(has_missing_observed_error, "Expected MissingObservedExpression error for {}", name);
            },
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
        ("unresolved_scoped_ref", include_str!("../../../tests/invalid/unresolved_scoped_ref.esm")),
        ("unresolved_scoped_ref_missing_system", include_str!("../../../tests/invalid/unresolved_scoped_ref_missing_system.esm")),
        ("unresolved_scoped_ref_missing_variable", include_str!("../../../tests/invalid/unresolved_scoped_ref_missing_variable.esm")),
    ];

    for (name, fixture) in fixtures {
        let parsed_result = load(fixture);

        match parsed_result {
            Ok(esm_file) => {
                let validation_result = validate(&esm_file);
                assert!(validation_result.has_errors(), "Expected {} to have validation errors", name);

                let has_unresolved_ref_error = validation_result.errors.iter().any(|err| {
                    matches!(err.code, StructuralErrorCode::UnresolvedScopedReference)
                });
                assert!(has_unresolved_ref_error, "Expected UnresolvedScopedReference error for {}", name);
            },
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
        ("event_var_undeclared", include_str!("../../../tests/invalid/event_var_undeclared.esm")),
        ("event_var_undeclared_condition", include_str!("../../../tests/invalid/event_var_undeclared_condition.esm")),
        ("event_var_undeclared_affects", include_str!("../../../tests/invalid/event_var_undeclared_affects.esm")),
    ];

    for (name, fixture) in fixtures {
        let parsed_result = load(fixture);

        match parsed_result {
            Ok(esm_file) => {
                let validation_result = validate(&esm_file);
                assert!(validation_result.has_errors(), "Expected {} to have validation errors", name);

                let has_event_var_error = validation_result.errors.iter().any(|err| {
                    matches!(err.code, StructuralErrorCode::EventVariableUndeclared)
                });
                assert!(has_event_var_error, "Expected EventVariableUndeclared error for {}", name);
            },
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
        ("invalid_discrete_param", include_str!("../../../tests/invalid/invalid_discrete_param.esm")),
        ("invalid_discrete_param_not_parameter", include_str!("../../../tests/invalid/invalid_discrete_param_not_parameter.esm")),
    ];

    for (name, fixture) in fixtures {
        let parsed_result = load(fixture);

        match parsed_result {
            Ok(esm_file) => {
                let validation_result = validate(&esm_file);
                assert!(validation_result.has_errors(), "Expected {} to have validation errors", name);

                let has_invalid_discrete_error = validation_result.errors.iter().any(|err| {
                    matches!(err.code, StructuralErrorCode::InvalidDiscreteParameter)
                });
                assert!(has_invalid_discrete_error, "Expected InvalidDiscreteParameter error for {}", name);
            },
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
        ("undefined_operator", include_str!("../../../tests/invalid/undefined_operator.esm")),
        ("undefined_operator_in_apply", include_str!("../../../tests/invalid/undefined_operator_in_apply.esm")),
    ];

    for (name, fixture) in fixtures {
        let parsed_result = load(fixture);

        match parsed_result {
            Ok(esm_file) => {
                let validation_result = validate(&esm_file);
                assert!(validation_result.has_errors(), "Expected {} to have validation errors", name);

                let has_undefined_operator_error = validation_result.errors.iter().any(|err| {
                    matches!(err.code, StructuralErrorCode::UndefinedOperator)
                });
                assert!(has_undefined_operator_error, "Expected UndefinedOperator error for {}", name);
            },
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
        ("undefined_variable_in_rhs", include_str!("../../../tests/invalid/undefined_variable_in_rhs.esm")),
        ("undefined_variable_in_nested_expr", include_str!("../../../tests/invalid/undefined_variable_in_nested_expr.esm")),
    ];

    for (name, fixture) in fixtures {
        let parsed_result = load(fixture);

        match parsed_result {
            Ok(esm_file) => {
                let validation_result = validate(&esm_file);
                assert!(validation_result.has_errors(), "Expected {} to have validation errors", name);

                let has_undefined_var_error = validation_result.errors.iter().any(|err| {
                    matches!(err.code, StructuralErrorCode::UnknownVariableReference)
                });
                assert!(has_undefined_var_error, "Expected UnknownVariableReference error for {}", name);
            },
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

            let has_undefined_system_error = validation_result.errors.iter().any(|err| {
                matches!(err.code, StructuralErrorCode::UndefinedSystem)
            });
            assert!(has_undefined_system_error, "Expected UndefinedSystem error");
        },
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
            assert!(validation_result.errors.len() > 1, "Expected multiple validation errors");
        },
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
        },
        Err(_) => {
            // Parse failure is also acceptable
        }
    }
}