//! # EarthSci Toolkit - Rust Implementation
//!
//! This crate provides Rust types and utilities for the EarthSciML Serialization Format (ESM).
//!
//! ## Features
//!
//! - **Core**: Parse, serialize, pretty-print, substitute, validate schema
//! - **Analysis**: Unit checking, equation counting, structural validation
//! - **CLI Tool**: Command-line interface for validation and conversion
//! - **WASM**: WebAssembly compilation for web use
//!
//! ## Example
//!
//! ```rust
//! use earthsci_toolkit::{EsmFile, load, save};
//!
//! // Load an ESM file
//! let esm_data = r#"
//! {
//!   "esm": "0.1.0",
//!   "metadata": {
//!     "name": "test_model"
//!   },
//!   "models": {
//!     "simple": {
//!       "variables": {},
//!       "equations": []
//!     }
//!   }
//! }
//! "#;
//! let esm_file: EsmFile = load(esm_data)?;
//!
//! // Save back to JSON
//! let json = save(&esm_file)?;
//! # Ok::<(), Box<dyn std::error::Error>>(())
//! ```

pub mod display;
pub mod edit;
pub mod error;
pub mod expression;
pub mod graph;
pub mod migration;
pub mod parse;
pub mod reactions;
pub mod serialize;
pub mod substitute;
pub mod types;
pub mod units;
pub mod validate;

#[cfg(feature = "wasm")]
pub mod wasm;

pub mod performance;

// Re-export main types
pub use display::{to_ascii, to_latex, to_unicode};
pub use expression::{contains, evaluate, free_parameters, free_variables, simplify};
pub use graph::{
    component_exists, component_graph, expression_graph, get_component_type, ComponentGraph,
    ComponentNode, ComponentType, CouplingEdge, DependencyEdge, DependencyRelationship,
    ExpressionGraph, ExpressionGraphInput, VariableKind, VariableNode,
};
pub use parse::{load, ParseError, SchemaValidationError};
pub use reactions::{
    derive_odes, detect_conservation_violations, stoichiometric_matrix, ConservationAnalysis,
    ConservationLawType, ConservationViolation, DeriveError, LinearInvariant,
};
pub use serialize::{save, save_compact};
pub use substitute::{
    substitute, substitute_in_model, substitute_in_model_with_context,
    substitute_in_reaction_system, substitute_in_reaction_system_with_context,
    substitute_with_context, ScopedContext,
};
pub use types::{
    AffectEquation, ContinuousEvent, CouplingEntry, DataLoader, DiscreteEvent,
    DiscreteEventTrigger, Domain, Equation, EsmFile, Expr, ExpressionNode, FunctionalAffect,
    Metadata, Model, ModelVariable, Operator, Reaction, ReactionSystem, Solver, Species,
    StoichiometricEntry, VariableType,
};
pub use validate::{
    validate, validate_complete, SchemaError, StructuralError, StructuralErrorCode,
    ValidationResult,
};

pub use edit::{
    add_coupling, add_equation, add_model, add_reaction, add_reaction_system, add_species,
    add_variable, remove_coupling, remove_equation, remove_model, remove_reaction, remove_species,
    remove_variable, replace_coupling, replace_equation, substitute_in_expression,
    update_model_metadata, EditError,
};
pub use error::EsmError;
pub use migration::{can_migrate, get_supported_migration_targets, migrate, MigrationError};
pub use performance::{CompactExpr, PerformanceError};
#[cfg(feature = "simd")]
pub use reactions::compute_conservation_weights_simd;
#[cfg(feature = "parallel")]
pub use reactions::stoichiometric_matrix_parallel;
pub use units::{
    check_dimensional_consistency, convert_units, parse_unit, Dimension, Unit, UnitError,
};

#[cfg(feature = "parallel")]
pub use performance::ParallelEvaluator;

#[cfg(feature = "custom_alloc")]
pub use performance::ModelAllocator;

/// Package version
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
/// ESM schema version supported by this implementation
pub const SCHEMA_VERSION: &str = "0.1.0";

#[cfg(test)]
mod coupling_field_tests {
    use super::*;
    use serde_json;

    #[test]
    fn test_operator_compose_new_fields() {
        // Test OperatorCompose with new systems field
        let json = r#"{
            "type": "operator_compose",
            "systems": ["system1", "system2"]
        }"#;

        let entry: CouplingEntry = serde_json::from_str(json).unwrap();
        match entry {
            CouplingEntry::OperatorCompose { systems, .. } => {
                assert_eq!(systems, vec!["system1", "system2"]);
            }
            _ => panic!("Expected OperatorCompose variant"),
        }
    }

    #[test]
    fn test_couple2_new_fields() {
        // Test Couple2 with new systems field
        let json = r#"{
            "type": "couple2",
            "systems": ["system1", "system2"],
            "coupletype_pair": ["type1", "type2"],
            "connector": {
                "equations": []
            }
        }"#;

        let entry: CouplingEntry = serde_json::from_str(json).unwrap();
        match entry {
            CouplingEntry::Couple2 {
                systems,
                coupletype_pair,
                ..
            } => {
                assert_eq!(systems, vec!["system1", "system2"]);
                assert_eq!(coupletype_pair, vec!["type1", "type2"]);
            }
            _ => panic!("Expected Couple2 variant"),
        }
    }

    #[test]
    fn test_variable_map_new_fields() {
        // Test VariableMap with new from/to fields
        let json = r#"{
            "type": "variable_map",
            "from": "source.var",
            "to": "target.param",
            "transform": "identity"
        }"#;

        let entry: CouplingEntry = serde_json::from_str(json).unwrap();
        match entry {
            CouplingEntry::VariableMap {
                from,
                to,
                transform,
                ..
            } => {
                assert_eq!(from, "source.var");
                assert_eq!(to, "target.param");
                assert_eq!(transform, "identity");
            }
            _ => panic!("Expected VariableMap variant"),
        }
    }

    #[test]
    fn test_coupling_serialization_round_trip() {
        // Test serialization round-trip
        let coupling = CouplingEntry::OperatorCompose {
            systems: vec!["sys1".to_string(), "sys2".to_string()],
            translate: None,
            description: None,
        };

        let serialized = serde_json::to_string(&coupling).unwrap();
        let deserialized: CouplingEntry = serde_json::from_str(&serialized).unwrap();

        match deserialized {
            CouplingEntry::OperatorCompose { systems, .. } => {
                assert_eq!(systems, vec!["sys1", "sys2"]);
            }
            _ => panic!("Round-trip failed"),
        }
    }
}

#[cfg(test)]
mod discrete_event_test {
    use super::*;
    use serde_json;

    #[test]
    fn test_discrete_event_fields_present() {
        // Test that we can create a DiscreteEvent with discrete_parameters and reinitialize
        let event = DiscreteEvent {
            name: Some("test_event".to_string()),
            trigger: DiscreteEventTrigger::Condition {
                expression: Expr::Number(1.0),
            },
            affects: None,
            functional_affect: None,
            discrete_parameters: Some(vec!["param1".to_string(), "param2".to_string()]),
            reinitialize: Some(true),
            description: Some("Test event".to_string()),
        };

        // Test serialization
        let json = serde_json::to_string(&event).expect("Serialization should work");
        assert!(
            json.contains("discrete_parameters"),
            "JSON should contain discrete_parameters field"
        );
        assert!(
            json.contains("reinitialize"),
            "JSON should contain reinitialize field"
        );
        assert!(
            json.contains("param1"),
            "JSON should contain the parameter values"
        );

        // Test deserialization
        let deserialized: DiscreteEvent =
            serde_json::from_str(&json).expect("Deserialization should work");

        assert_eq!(
            deserialized.discrete_parameters,
            Some(vec!["param1".to_string(), "param2".to_string()])
        );
        assert_eq!(deserialized.reinitialize, Some(true));
    }

    #[test]
    fn test_discrete_event_json_parsing() {
        let json = r#"
        {
            "trigger": {
                "type": "condition",
                "expression": 1.0
            },
            "discrete_parameters": ["param1", "param2"],
            "reinitialize": true
        }
        "#;

        let event: DiscreteEvent = serde_json::from_str(json)
            .expect("Should parse JSON with discrete_parameters and reinitialize");

        assert_eq!(
            event.discrete_parameters,
            Some(vec!["param1".to_string(), "param2".to_string()])
        );
        assert_eq!(event.reinitialize, Some(true));
    }
}
