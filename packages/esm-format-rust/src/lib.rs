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

#[cfg(feature = "wasm")]
pub mod wasm;

// Re-export main types
pub use types::{
    EsmFile, Model, ReactionSystem, Expr, Species, Reaction,
    Metadata, ModelVariable, VariableType, Equation, ExpressionNode,
    DiscreteEvent, DiscreteEventTrigger, AffectEquation,
    StoichiometricEntry, DataLoader, Operator, CouplingEntry,
    Domain, Solver
};
pub use parse::{load, ParseError, SchemaValidationError};
pub use serialize::save;
pub use validate::{validate, ValidationResult, StructuralError, StructuralErrorCode, SchemaError};
pub use substitute::{substitute_in_model, substitute_in_reaction_system};
pub use display::{to_unicode, to_latex, to_ascii};
pub use expression::{free_variables, free_parameters, contains, evaluate, simplify, substitute};
pub use graph::{component_graph, component_exists, get_component_type, ComponentGraph, ComponentNode, CouplingEdge, ComponentType};
pub use error::EsmError;

/// Package version
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
/// ESM schema version supported by this implementation
pub const SCHEMA_VERSION: &str = "0.1.0";