//! # ESM Format - Rust Implementation
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
//! use esm_format::{EsmFile, load, save};
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


pub mod types;
pub mod parse;
pub mod serialize;
pub mod validate;
pub mod substitute;
pub mod pretty_print;
pub mod display;
pub mod expression;
pub mod graph;
pub mod error;
pub mod reactions;
pub mod units;
pub mod edit;

#[cfg(feature = "wasm")]
pub mod wasm;

pub mod performance;

// Re-export main types
pub use types::{
    EsmFile, Model, ReactionSystem, Expr, Species, Reaction,
    Metadata, ModelVariable, VariableType, Equation, ExpressionNode,
    DiscreteEvent, DiscreteEventTrigger, AffectEquation,
    StoichiometricEntry, DataLoader, Operator, CouplingEntry,
    Domain, Solver
};
pub use parse::{load, ParseError, SchemaValidationError};
pub use serialize::{save, save_compact};
pub use validate::{validate, ValidationResult, StructuralError, StructuralErrorCode, SchemaError};
pub use substitute::{substitute_in_model, substitute_in_reaction_system};
pub use display::{to_unicode, to_latex, to_ascii};
pub use expression::{free_variables, free_parameters, contains, evaluate, simplify, substitute};
pub use graph::{
    component_graph, component_exists, get_component_type, expression_graph,
    ComponentGraph, ComponentNode, CouplingEdge, ComponentType,
    ExpressionGraph, VariableNode, VariableKind, DependencyEdge, DependencyRelationship,
    ExpressionGraphInput
};
pub use reactions::{derive_odes, stoichiometric_matrix, DeriveError};
pub use units::{parse_unit, check_dimensional_consistency, convert_units, Unit, Dimension, UnitError};
pub use edit::{
    add_model, remove_model, add_variable, remove_variable, add_equation, remove_equation,
    replace_equation, add_reaction_system, add_species, remove_species, add_reaction,
    remove_reaction, update_model_metadata, substitute_in_expression, EditError
};
pub use error::EsmError;
pub use performance::{PerformanceError, CompactExpr};

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
            CouplingEntry::Couple2 { systems, coupletype_pair, .. } => {
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
            CouplingEntry::VariableMap { from, to, transform, .. } => {
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