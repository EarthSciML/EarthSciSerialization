//! Basic functionality tests
//!
//! Tests basic parsing, serialization, and core functionality with simple valid examples.

use esm_format::*;
use std::collections::HashMap;

/// Test basic round-trip with simple valid data
#[test]
fn test_basic_round_trip() {
    let json = r#"
    {
      "esm": "0.1.0",
      "metadata": {
        "name": "test_model"
      },
      "models": {
        "simple": {
          "variables": {},
          "equations": []
        }
      }
    }
    "#;

    let parsed: EsmFile = load(json).expect("Failed to parse basic JSON");
    let serialized = save(&parsed).expect("Failed to serialize back to JSON");
    let reparsed: EsmFile = load(&serialized).expect("Failed to reparse serialized output");

    assert_eq!(parsed.esm, reparsed.esm);
    assert_eq!(parsed.metadata.name, reparsed.metadata.name);
}

/// Test schema validation with missing esm version
#[test]
fn test_missing_esm_version() {
    let json = r#"
    {
      "metadata": {
        "name": "test_model"
      }
    }
    "#;

    let result = load(json);
    assert!(result.is_err(), "Expected parsing to fail for missing ESM version");

    if let Err(EsmError::SchemaValidation(error)) = result {
        assert!(error.contains("esm") || error.to_lowercase().contains("required"));
    } else {
        panic!("Expected schema validation error");
    }
}

/// Test schema validation with wrong data types
#[test]
fn test_wrong_data_types() {
    let json = r#"
    {
      "esm": 123,
      "metadata": {
        "name": "test_model"
      }
    }
    "#;

    let result = load(json);
    assert!(result.is_err(), "Expected parsing to fail for wrong data type");
}

/// Test structural validation
#[test]
fn test_structural_validation() {
    // Create a model with equations but no variables (should fail structural validation)
    let variables = HashMap::new();
    let model = Model {
        name: Some("Test Model".to_string()),
        variables,
        equations: vec![
            Equation {
                lhs: Expr::Variable("x".to_string()),
                rhs: Expr::Number(1.0),
            }
        ],
        events: None,
        description: None,
    };

    let mut models = HashMap::new();
    models.insert("test".to_string(), model);

    let esm_file = EsmFile {
        esm: "0.1.0".to_string(),
        metadata: Metadata {
            name: Some("Test".to_string()),
            description: None,
            authors: None,
            created: None,
            modified: None,
            version: None,
        },
        models: Some(models),
        reaction_systems: None,
        data_loaders: None,
        operators: None,
        coupling: None,
        domain: None,
        solver: None,
    };

    let validation_result = validate(&esm_file);
    assert!(!validation_result.structural_errors.is_empty(), "Expected structural validation to find errors");
}

/// Test expression operations
#[test]
fn test_expression_operations() {
    let expr = Expr::Operator(ExpressionNode {
        op: "+".to_string(),
        args: vec![
            Expr::Variable("x".to_string()),
            Expr::Number(5.0),
        ],
        wrt: None,
        dim: None,
    });

    // Test free variables
    let vars = free_variables(&expr);
    assert!(vars.contains("x"));
    assert_eq!(vars.len(), 1);

    // Test evaluation
    let mut context = HashMap::new();
    context.insert("x".to_string(), 10.0);

    let result = evaluate(&expr, &context).expect("Failed to evaluate expression");
    assert_eq!(result, 15.0);

    // Test substitution
    let mut substitutions = HashMap::new();
    substitutions.insert("x".to_string(), Expr::Number(20.0));

    let substituted = substitute_in_expression(&expr, &substitutions);
    if let Expr::Operator(node) = substituted {
        if let Expr::Number(val) = &node.args[0] {
            assert_eq!(*val, 20.0);
        }
    }
}

/// Test stoichiometric matrix generation
#[test]
fn test_stoichiometric_matrix() {
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
            rate: Expr::Variable("k".to_string()),
            description: None,
        }
    ];

    let rs = ReactionSystem {
        name: Some("Test RS".to_string()),
        species,
        reactions,
        description: None,
    };

    let matrix = stoichiometric_matrix(&rs);
    assert_eq!(matrix.len(), 2);
    assert_eq!(matrix[0].len(), 1);
    assert_eq!(matrix[0][0], -1.0); // A consumed
    assert_eq!(matrix[1][0], 1.0);  // B produced
}

/// Test component graph generation
#[test]
fn test_component_graph() {
    let metadata = Metadata {
        name: Some("Test".to_string()),
        description: None,
        authors: None,
        created: None,
        modified: None,
        version: None,
    };

    let model = Model {
        name: Some("TestModel".to_string()),
        variables: HashMap::new(),
        equations: vec![],
        events: None,
        description: None,
    };

    let mut models = HashMap::new();
    models.insert("test_model".to_string(), model);

    let esm_file = EsmFile {
        esm: "0.1.0".to_string(),
        metadata,
        models: Some(models),
        reaction_systems: None,
        data_loaders: None,
        operators: None,
        coupling: None,
        domain: None,
        solver: None,
    };

    let graph = component_graph(&esm_file);
    assert_eq!(graph.nodes.len(), 1);

    // Test exports
    let dot_output = graph.to_dot();
    assert!(!dot_output.is_empty());
    assert!(dot_output.contains("digraph ComponentGraph"));

    let mermaid_output = graph.to_mermaid();
    assert!(!mermaid_output.is_empty());
}

/// Test pretty printing
#[test]
fn test_pretty_printing() {
    let test_strings = ["H2O", "CO2", "CH4", "NO2", "D", "*", "+"];

    for input in &test_strings {
        // Create simple expressions to test display functions
        let expr = Expr::Variable(input.to_string());

        let unicode_result = to_unicode(&expr);
        let latex_result = to_latex(&expr);
        let ascii_result = to_ascii(&expr);

        assert!(!unicode_result.is_empty());
        assert!(!latex_result.is_empty());
        assert!(!ascii_result.is_empty());
    }
}

/// Test units functionality
#[test]
fn test_units() {
    let m_per_s = parse_unit("m/s").expect("Failed to parse m/s");
    let mol_per_l = parse_unit("mol/L").expect("Failed to parse mol/L");

    // Test dimensional consistency (should fail)
    let consistency_check = check_dimensional_consistency(&m_per_s, &mol_per_l);
    assert!(consistency_check.is_err());

    // Test unit conversion
    let m_unit = parse_unit("m").expect("Failed to parse m");
    let cm_unit = parse_unit("cm").expect("Failed to parse cm");
    let conversion = convert_units(1.0, &m_unit, &cm_unit).expect("Failed to convert units");
    assert!((conversion - 100.0).abs() < 1e-10);
}

/// Test editing operations
#[test]
fn test_editing() {
    let model = Model {
        name: Some("Test Model".to_string()),
        variables: HashMap::new(),
        equations: vec![],
        events: None,
        description: None,
    };

    // Test adding variables
    let new_var = ModelVariable {
        var_type: VariableType::Parameter,
        units: Some("s^-1".to_string()),
        default: Some(0.1),
        description: Some("Test rate constant".to_string()),
    };

    let updated_model = add_variable(&model, "k", new_var).expect("Failed to add variable");
    assert!(updated_model.variables.contains_key("k"));
    assert_eq!(updated_model.variables.len(), 1);
}