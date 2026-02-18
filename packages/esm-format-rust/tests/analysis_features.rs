use esm_format::*;

#[test]
fn test_analysis_features_integration() {
    // Use a simpler test that bypasses schema validation
    use std::collections::HashMap;

    let metadata = crate::types::Metadata {
        name: Some("test_model".to_string()),
        description: None,
        authors: None,
        created: None,
        modified: None,
        version: None,
    };

    let mut variables = HashMap::new();
    variables.insert("x".to_string(), ModelVariable {
        var_type: VariableType::State,
        units: None,
        default: Some(1.0),
        description: None,
    });
    variables.insert("k".to_string(), ModelVariable {
        var_type: VariableType::Parameter,
        units: None,
        default: Some(0.1),
        description: None,
    });

    let model = Model {
        name: Some("Simple Model".to_string()),
        variables,
        equations: vec![Equation {
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
        }],
        discrete_events: None,
        continuous_events: None,
        description: None,
    };

    let mut models = HashMap::new();
    models.insert("simple".to_string(), model);

    // Create reaction system
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
                    Expr::Variable("k".to_string()),
                    Expr::Variable("A".to_string()),
                ],
                wrt: None,
                dim: None,
            }),
            description: None,
        }
    ];

    let rs = ReactionSystem {
        name: Some("Simple RS".to_string()),
        species,
        reactions,
        description: None,
    };

    let mut reaction_systems = HashMap::new();
    reaction_systems.insert("simple_rs".to_string(), rs);

    let esm_file = EsmFile {
        esm: "0.1.0".to_string(),
        metadata,
        models: Some(models),
        reaction_systems: Some(reaction_systems),
        data_loaders: None,
        operators: None,
        coupling: None,
        domain: None,
        solver: None,
    };

    // Test component graph
    let comp_graph = component_graph(&esm_file);
    assert_eq!(comp_graph.nodes.len(), 2); // 1 model + 1 reaction system

    // Test export formats
    let dot_export = comp_graph.to_dot();
    assert!(!dot_export.is_empty());
    assert!(dot_export.contains("digraph ComponentGraph"));

    let mermaid_export = comp_graph.to_mermaid();
    assert!(!mermaid_export.is_empty());
    assert!(mermaid_export.contains("graph LR"));

    let json_export = comp_graph.to_json_graph();
    assert!(!json_export.is_empty());

    // Test expression graph for model
    if let Some(ref models) = esm_file.models {
        if let Some(model) = models.get("simple") {
            let expr_graph = expression_graph(model);
            assert!(!expr_graph.nodes.is_empty());

            let expr_dot = expr_graph.to_dot();
            assert!(!expr_dot.is_empty());
            assert!(expr_dot.contains("digraph ExpressionGraph"));
        }
    }

    // Test reaction system analysis
    if let Some(ref reaction_systems) = esm_file.reaction_systems {
        if let Some(rs) = reaction_systems.get("simple_rs") {
            // Test stoichiometric matrix
            let matrix = stoichiometric_matrix(rs);
            assert_eq!(matrix.len(), 2); // 2 species
            assert_eq!(matrix[0].len(), 1); // 1 reaction
            assert_eq!(matrix[0][0], -1.0); // A consumed
            assert_eq!(matrix[1][0], 1.0); // B produced

            // Test ODE derivation
            let ode_model = derive_odes(rs).expect("Should derive ODEs successfully");
            assert_eq!(ode_model.variables.len(), 2); // A and B
            assert_eq!(ode_model.equations.len(), 2); // d[A]/dt and d[B]/dt

            // Test expression graph for reaction system
            let rs_expr_graph = expression_graph(rs);
            assert!(!rs_expr_graph.nodes.is_empty());
        }
    }
}

#[test]
fn test_units_functionality() {
    // Test unit parsing
    let m_per_s = parse_unit("m/s").expect("Failed to parse m/s");
    let mol_per_l = parse_unit("mol/L").expect("Failed to parse mol/L");

    // Test dimensional consistency (should fail)
    let consistency_check = check_dimensional_consistency(&m_per_s, &mol_per_l);
    assert!(consistency_check.is_err(), "Should detect dimensional inconsistency");

    // Test unit conversion
    let m_unit = parse_unit("m").expect("Failed to parse m");
    let cm_unit = parse_unit("cm").expect("Failed to parse cm");
    let conversion = convert_units(1.0, &m_unit, &cm_unit).expect("Failed to convert units");
    assert!((conversion - 100.0).abs() < 1e-10, "1 m should equal 100 cm");
}

#[test]
fn test_editing_operations() {
    use std::collections::HashMap;

    // Create a simple model
    let model = Model {
        name: Some("Test Model".to_string()),
        variables: HashMap::new(),
        equations: vec![],
        discrete_events: None,
        continuous_events: None,
        description: None,
    };

    // Test adding variables
    let new_var = ModelVariable {
        var_type: VariableType::Parameter,
        units: Some("s^-1".to_string()),
        default: Some(0.1),
        description: Some("Test rate constant".to_string()),
    };

    let updated_model = add_variable(&model, "test_k", new_var).expect("Failed to add variable");
    assert!(updated_model.variables.contains_key("test_k"));
    assert_eq!(updated_model.variables.len(), 1);

    // Test adding equations
    let new_eq = Equation {
        lhs: Expr::Variable("test_var".to_string()),
        rhs: Expr::Number(42.0),
    };

    let model_with_eq = add_equation(&updated_model, new_eq).expect("Failed to add equation");
    assert_eq!(model_with_eq.equations.len(), 1);

    // Test variable substitution
    let expr = Expr::Operator(ExpressionNode {
        op: "+".to_string(),
        args: vec![
            Expr::Variable("x".to_string()),
            Expr::Number(1.0),
        ],
        wrt: None,
        dim: None,
    });

    let mut substitutions = HashMap::new();
    substitutions.insert("x".to_string(), Expr::Number(5.0));

    let result = substitute_in_expression(&expr, &substitutions);

    if let Expr::Operator(node) = result {
        assert_eq!(node.op, "+");
        if let Expr::Number(val) = &node.args[0] {
            assert_eq!(*val, 5.0);
        } else {
            panic!("Expected substituted value");
        }
    } else {
        panic!("Expected operator expression");
    }
}