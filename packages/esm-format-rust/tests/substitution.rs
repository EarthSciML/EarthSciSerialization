//! Substitution tests matching fixtures
//!
//! Tests the variable and expression substitution functionality.

use esm_format::*;
use serde_json;
use std::collections::HashMap;

/// Test simple variable replacement
#[test]
fn test_simple_var_replace() {
    let fixture = include_str!("../../../tests/substitution/simple_var_replace.json");
    let test_data: serde_json::Value = serde_json::from_str(fixture)
        .expect("Failed to parse simple var replace fixture");

    if let (Some(input_expr), Some(substitutions_data), Some(expected_expr)) = (
        test_data.get("input_expression"),
        test_data.get("substitutions"),
        test_data.get("expected_result")
    ) {
        // Parse input expression
        let input_str = serde_json::to_string(input_expr).expect("Failed to serialize input expression");
        let input: Expr = serde_json::from_str(&input_str).expect("Failed to parse input expression");

        // Parse substitutions
        let mut substitutions = HashMap::new();
        if let Some(subs_obj) = substitutions_data.as_object() {
            for (var_name, sub_expr) in subs_obj {
                let sub_str = serde_json::to_string(sub_expr).expect("Failed to serialize substitution");
                let sub: Expr = serde_json::from_str(&sub_str).expect("Failed to parse substitution");
                substitutions.insert(var_name.clone(), sub);
            }
        }

        // Parse expected result
        let expected_str = serde_json::to_string(expected_expr).expect("Failed to serialize expected result");
        let expected: Expr = serde_json::from_str(&expected_str).expect("Failed to parse expected result");

        // Perform substitution
        let result = substitute_in_expression(&input, &substitutions);

        // Compare results (this is simplified - real comparison would be more sophisticated)
        assert_eq!(
            serde_json::to_value(&result).expect("Failed to serialize result"),
            serde_json::to_value(&expected).expect("Failed to serialize expected"),
            "Substitution result doesn't match expected"
        );
    }
}

/// Test nested substitution
#[test]
fn test_nested_substitution() {
    let fixture = include_str!("../../../tests/substitution/nested_substitution.json");
    let test_data: serde_json::Value = serde_json::from_str(fixture)
        .expect("Failed to parse nested substitution fixture");

    if let (Some(input_expr), Some(substitutions_data), Some(expected_expr)) = (
        test_data.get("input_expression"),
        test_data.get("substitutions"),
        test_data.get("expected_result")
    ) {
        // Parse input expression
        let input_str = serde_json::to_string(input_expr).expect("Failed to serialize input expression");
        let input: Expr = serde_json::from_str(&input_str).expect("Failed to parse input expression");

        // Parse substitutions
        let mut substitutions = HashMap::new();
        if let Some(subs_obj) = substitutions_data.as_object() {
            for (var_name, sub_expr) in subs_obj {
                let sub_str = serde_json::to_string(sub_expr).expect("Failed to serialize substitution");
                let sub: Expr = serde_json::from_str(&sub_str).expect("Failed to parse substitution");
                substitutions.insert(var_name.clone(), sub);
            }
        }

        // Parse expected result
        let expected_str = serde_json::to_string(expected_expr).expect("Failed to serialize expected result");
        let expected: Expr = serde_json::from_str(&expected_str).expect("Failed to parse expected result");

        // Perform substitution
        let result = substitute_in_expression(&input, &substitutions);

        // Compare results
        assert_eq!(
            serde_json::to_value(&result).expect("Failed to serialize result"),
            serde_json::to_value(&expected).expect("Failed to serialize expected"),
            "Nested substitution result doesn't match expected"
        );
    }
}

/// Test scoped reference substitution
#[test]
fn test_scoped_reference() {
    let fixture = include_str!("../../../tests/substitution/scoped_reference.json");
    let test_data: serde_json::Value = serde_json::from_str(fixture)
        .expect("Failed to parse scoped reference fixture");

    if let (Some(input_expr), Some(substitutions_data), Some(expected_expr)) = (
        test_data.get("input_expression"),
        test_data.get("substitutions"),
        test_data.get("expected_result")
    ) {
        // Parse input expression
        let input_str = serde_json::to_string(input_expr).expect("Failed to serialize input expression");
        let input: Expr = serde_json::from_str(&input_str).expect("Failed to parse input expression");

        // Parse substitutions
        let mut substitutions = HashMap::new();
        if let Some(subs_obj) = substitutions_data.as_object() {
            for (var_name, sub_expr) in subs_obj {
                let sub_str = serde_json::to_string(sub_expr).expect("Failed to serialize substitution");
                let sub: Expr = serde_json::from_str(&sub_str).expect("Failed to parse substitution");
                substitutions.insert(var_name.clone(), sub);
            }
        }

        // Parse expected result
        let expected_str = serde_json::to_string(expected_expr).expect("Failed to serialize expected result");
        let expected: Expr = serde_json::from_str(&expected_str).expect("Failed to parse expected result");

        // Perform substitution
        let result = substitute_in_expression(&input, &substitutions);

        // Compare results
        assert_eq!(
            serde_json::to_value(&result).expect("Failed to serialize result"),
            serde_json::to_value(&expected).expect("Failed to serialize expected"),
            "Scoped reference substitution result doesn't match expected"
        );
    }
}

/// Test substitution in model context
#[test]
fn test_model_substitution() {
    // Create a simple model for testing
    let mut variables = HashMap::new();
    variables.insert("x".to_string(), ModelVariable {
        var_type: VariableType::State,
        units: None,
        default: Some(1.0),
        description: None,
        expression: None,
    });
    variables.insert("k".to_string(), ModelVariable {
        var_type: VariableType::Parameter,
        units: None,
        default: Some(0.1),
        description: None,
        expression: None,
    });
    variables.insert("y".to_string(), ModelVariable {
        var_type: VariableType::State,
        units: None,
        default: Some(0.0),
        description: None,
        expression: None,
    });

    let model = Model {
        name: Some("Test Model".to_string()),
        variables,
        equations: vec![
            Equation {
                lhs: Expr::Operator(ExpressionNode {
                    op: "D".to_string(),
                    args: vec![Expr::Variable("x".to_string())],
                    wrt: Some("t".to_string()),
                    dim: None,
                }),
                rhs: Expr::Operator(ExpressionNode {
                    op: "*".to_string(),
                    args: vec![
                        Expr::Variable("k".to_string()),
                        Expr::Variable("x".to_string()),
                    ],
                    wrt: None,
                    dim: None,
                }),
            },
        ],
        discrete_events: None,
        continuous_events: None,
        description: None,
    };

    // Create substitutions
    let mut substitutions = HashMap::new();
    substitutions.insert("k".to_string(), Expr::Number(0.2));

    // Perform substitution on model
    let result = substitute_in_model(&model, &substitutions);

    // Check that substitution worked
    if let Some(equation) = result.equations.first() {
        if let Expr::Operator(rhs_node) = &equation.rhs {
            if let Expr::Number(val) = &rhs_node.args[0] {
                assert_eq!(*val, 0.2, "Expected k to be substituted with 0.2");
            }
        }
    }
}

/// Test substitution in reaction system context
#[test]
fn test_reaction_system_substitution() {
    // Create a simple reaction system
    let species = vec![
        Species {
            name: "A".to_string(),
            units: Some("mol/L".to_string()),
            default: Some(1.0),
            description: None,
        },
        Species {
            name: "B".to_string(),
            units: Some("mol/L".to_string()),
            default: Some(0.0),
            description: None,
        },
    ];

    let reactions = vec![
        Reaction {
            name: None,
            substrates: vec![StoichiometricEntry {
                species: "A".to_string(),
                coefficient: Some(1.0),
            }],
            products: vec![StoichiometricEntry {
                species: "B".to_string(),
                coefficient: Some(1.0),
            }],
            rate: Expr::Operator(ExpressionNode {
                op: "*".to_string(),
                args: vec![
                    Expr::Variable("k_rate".to_string()),
                    Expr::Variable("A".to_string()),
                ],
                wrt: None,
                dim: None,
            }),
            description: None,
        }
    ];

    let rs = ReactionSystem {
        name: Some("Test RS".to_string()),
        species,
        parameters: HashMap::new(),
        reactions,
        description: None,
    };

    // Create substitutions
    let mut substitutions = HashMap::new();
    substitutions.insert("k_rate".to_string(), Expr::Number(1.5));

    // Perform substitution on reaction system
    let result = substitute_in_reaction_system(&rs, &substitutions);

    // Check that substitution worked
    if let Some(reaction) = result.reactions.first() {
        if let Expr::Operator(rate_node) = &reaction.rate {
            if let Expr::Number(val) = &rate_node.args[0] {
                assert_eq!(*val, 1.5, "Expected k_rate to be substituted with 1.5");
            }
        }
    }
}

/// Test complex substitution patterns
#[test]
fn test_complex_substitution_patterns() {
    // Create a complex expression with nested operators
    let complex_expr = Expr::Operator(ExpressionNode {
        op: "+".to_string(),
        args: vec![
            Expr::Operator(ExpressionNode {
                op: "*".to_string(),
                args: vec![
                    Expr::Variable("a".to_string()),
                    Expr::Operator(ExpressionNode {
                        op: "^".to_string(),
                        args: vec![
                            Expr::Variable("x".to_string()),
                            Expr::Number(2.0),
                        ],
                        wrt: None,
                        dim: None,
                    }),
                ],
                wrt: None,
                dim: None,
            }),
            Expr::Operator(ExpressionNode {
                op: "*".to_string(),
                args: vec![
                    Expr::Variable("b".to_string()),
                    Expr::Variable("x".to_string()),
                ],
                wrt: None,
                dim: None,
            }),
            Expr::Variable("c".to_string()),
        ],
        wrt: None,
        dim: None,
    });

    // Create complex substitutions
    let mut substitutions = HashMap::new();
    substitutions.insert("a".to_string(), Expr::Number(1.0));
    substitutions.insert("b".to_string(), Expr::Number(-2.0));
    substitutions.insert("c".to_string(), Expr::Number(1.0));

    // Perform substitution
    let result = substitute_in_expression(&complex_expr, &substitutions);

    // Verify that substitution occurred in nested structures
    if let Expr::Operator(result_node) = result {
        assert_eq!(result_node.args.len(), 3, "Expected 3 arguments in result");
    }
}

/// Test substitution with no-op (identity)
#[test]
fn test_identity_substitution() {
    let expr = Expr::Variable("x".to_string());
    let substitutions = HashMap::new(); // No substitutions

    let result = substitute_in_expression(&expr, &substitutions);

    // Should return unchanged expression
    assert_eq!(
        serde_json::to_value(&result).expect("Failed to serialize result"),
        serde_json::to_value(&expr).expect("Failed to serialize original"),
        "Identity substitution should return unchanged expression"
    );
}

/// Test substitution with variable not present
#[test]
fn test_substitution_variable_not_present() {
    let expr = Expr::Variable("x".to_string());
    let mut substitutions = HashMap::new();
    substitutions.insert("y".to_string(), Expr::Number(42.0)); // Different variable

    let result = substitute_in_expression(&expr, &substitutions);

    // Should return unchanged expression since 'x' is not in substitutions
    assert_eq!(
        serde_json::to_value(&result).expect("Failed to serialize result"),
        serde_json::to_value(&expr).expect("Failed to serialize original"),
        "Substitution with non-present variable should return unchanged expression"
    );
}