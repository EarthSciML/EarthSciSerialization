//! Core type definitions for the ESM format
//!
//! This module provides Rust types that correspond to the ESM JSON Schema.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Top-level ESM file structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EsmFile {
    /// Format version string (semver)
    pub esm: String,

    /// Authorship, provenance, description
    pub metadata: Metadata,

    /// ODE-based model components, keyed by unique identifier
    #[serde(skip_serializing_if = "Option::is_none")]
    pub models: Option<HashMap<String, Model>>,

    /// Reaction network components, keyed by unique identifier
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reaction_systems: Option<HashMap<String, ReactionSystem>>,

    /// External data source registrations (by reference)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data_loaders: Option<HashMap<String, DataLoader>>,

    /// Registered runtime operators (by reference)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub operators: Option<HashMap<String, Operator>>,

    /// Composition and coupling rules
    #[serde(skip_serializing_if = "Option::is_none")]
    pub coupling: Option<Vec<CouplingEntry>>,

    /// Spatial/temporal domain specification
    #[serde(skip_serializing_if = "Option::is_none")]
    pub domain: Option<Domain>,

    /// Solver strategy and configuration
    #[serde(skip_serializing_if = "Option::is_none")]
    pub solver: Option<Solver>,
}

/// Metadata section
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Metadata {
    /// Human-readable model name
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,

    /// Brief description
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,

    /// Authors/contributors
    #[serde(skip_serializing_if = "Option::is_none")]
    pub authors: Option<Vec<String>>,

    /// Creation timestamp (ISO 8601)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub created: Option<String>,

    /// Last modification timestamp (ISO 8601)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub modified: Option<String>,

    /// Version of this model
    #[serde(skip_serializing_if = "Option::is_none")]
    pub version: Option<String>,
}

/// Mathematical expression: a number literal, variable reference, or operator node
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum Expr {
    /// Number literal
    Number(f64),

    /// Variable or parameter reference string
    Variable(String),

    /// Operator node with children
    Operator(ExpressionNode),
}

/// Expression node representing an operator with operands
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ExpressionNode {
    /// Operator name (e.g., "+", "-", "*", "/", "sin", "cos", etc.)
    pub op: String,

    /// Operand expressions
    pub args: Vec<Expr>,

    /// Differentiation variable (for derivatives)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub wrt: Option<String>,

    /// Dimensional analysis hint
    #[serde(skip_serializing_if = "Option::is_none")]
    pub dim: Option<String>,
}

/// ODE-based model component
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Model {
    /// Human-readable model name
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,

    /// State variables, parameters, and observed quantities (keyed by name)
    pub variables: HashMap<String, ModelVariable>,

    /// Differential equations
    pub equations: Vec<Equation>,

    /// Discrete events
    #[serde(skip_serializing_if = "Option::is_none")]
    pub discrete_events: Option<Vec<DiscreteEvent>>,

    /// Continuous events
    #[serde(skip_serializing_if = "Option::is_none")]
    pub continuous_events: Option<Vec<ContinuousEvent>>,

    /// Brief description
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
}

/// Variable within a model
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelVariable {
    /// Variable type
    #[serde(rename = "type")]
    pub var_type: VariableType,

    /// Physical units
    #[serde(skip_serializing_if = "Option::is_none")]
    pub units: Option<String>,

    /// Default/initial value
    #[serde(skip_serializing_if = "Option::is_none")]
    pub default: Option<f64>,

    /// Brief description
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,

    /// Defining expression for observed variables
    #[serde(skip_serializing_if = "Option::is_none")]
    pub expression: Option<Expr>,
}

/// Type of model variable
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum VariableType {
    /// State variable (appears in d/dt equations)
    State,
    /// Parameter (constant)
    Parameter,
    /// Observed quantity (computed from state/parameters)
    Observed,
}

/// Differential equation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Equation {
    /// Left-hand side expression
    pub lhs: Expr,

    /// Right-hand side expression
    pub rhs: Expr,
}

/// Discrete event that can modify the system
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiscreteEvent {
    /// Human-readable identifier
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,

    /// When the event fires
    pub trigger: DiscreteEventTrigger,

    /// What happens when the event fires
    #[serde(skip_serializing_if = "Option::is_none")]
    pub affects: Option<Vec<AffectEquation>>,

    /// Brief description
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
}

/// Trigger condition for discrete events
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum DiscreteEventTrigger {
    /// Fires when boolean condition is true
    Condition {
        expression: Expr,
    },
    /// Fires at regular intervals
    Periodic {
        /// Interval in simulation time units
        interval: f64,
        /// Offset from t=0 for first firing
        #[serde(skip_serializing_if = "Option::is_none")]
        initial_offset: Option<f64>,
    },
    /// Fires at preset times
    PresetTimes {
        /// Array of simulation times at which to fire
        times: Vec<f64>,
    },
}

/// Equation that modifies state/parameters when event fires
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AffectEquation {
    /// Left-hand side (variable to modify)
    pub lhs: String,

    /// Right-hand side (new value expression)
    pub rhs: Expr,
}

/// Continuous event that fires on zero-crossings
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContinuousEvent {
    /// Human-readable identifier
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,

    /// Condition expression (zero-crossing detection)
    pub condition: Expr,

    /// What happens when the event fires
    #[serde(skip_serializing_if = "Option::is_none")]
    pub affects: Option<Vec<AffectEquation>>,

    /// Functional affect specification
    #[serde(skip_serializing_if = "Option::is_none")]
    pub functional_affect: Option<FunctionalAffect>,

    /// Root finding direction
    #[serde(skip_serializing_if = "Option::is_none")]
    pub root_find: Option<RootFindDirection>,

    /// Brief description
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
}

/// Functional affect specification for events
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FunctionalAffect {
    /// Function name or code
    pub function: String,

    /// Function parameters
    #[serde(skip_serializing_if = "Option::is_none")]
    pub params: Option<serde_json::Value>,
}

/// Root finding direction for continuous events
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RootFindDirection {
    /// Detect positive-going zero crossings
    Left,
    /// Detect negative-going zero crossings
    Right,
    /// Detect all zero crossings
    All,
}

/// Reaction network component
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReactionSystem {
    /// Human-readable name
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,

    /// Chemical species
    pub species: Vec<Species>,

    /// Named parameters (rate constants, temperature, photolysis rates, etc.)
    pub parameters: HashMap<String, Parameter>,

    /// Chemical reactions
    pub reactions: Vec<Reaction>,

    /// Brief description
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
}

/// Chemical species in a reaction system
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Species {
    /// Species name (unique within reaction system)
    pub name: String,

    /// Physical units
    #[serde(skip_serializing_if = "Option::is_none")]
    pub units: Option<String>,

    /// Default/initial concentration
    #[serde(skip_serializing_if = "Option::is_none")]
    pub default: Option<f64>,

    /// Brief description
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
}

/// Parameter in a reaction system
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Parameter {
    /// Physical units
    #[serde(skip_serializing_if = "Option::is_none")]
    pub units: Option<String>,

    /// Default/initial value
    #[serde(skip_serializing_if = "Option::is_none")]
    pub default: Option<f64>,

    /// Brief description
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
}

/// Chemical reaction
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Reaction {
    /// Human-readable reaction name
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,

    /// Reactant species and stoichiometry
    pub substrates: Vec<StoichiometricEntry>,

    /// Product species and stoichiometry
    pub products: Vec<StoichiometricEntry>,

    /// Rate law expression
    pub rate: Expr,

    /// Brief description
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
}

/// Species with stoichiometric coefficient
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StoichiometricEntry {
    /// Species name
    pub species: String,

    /// Stoichiometric coefficient (default: 1.0)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub coefficient: Option<f64>,
}

/// External data loader reference
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataLoader {
    /// Data loader type identifier
    #[serde(rename = "type")]
    pub loader_type: String,

    /// Configuration parameters
    #[serde(skip_serializing_if = "Option::is_none")]
    pub config: Option<serde_json::Value>,

    /// Brief description
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
}

/// Runtime operator reference
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Operator {
    /// Operator type identifier
    #[serde(rename = "type")]
    pub op_type: String,

    /// Configuration parameters
    #[serde(skip_serializing_if = "Option::is_none")]
    pub config: Option<serde_json::Value>,

    /// Brief description
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
}

/// Coupling entry with discriminated union based on type field
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum CouplingEntry {
    /// Operator composition coupling
    OperatorCompose {
        /// The two systems to compose
        systems: Vec<String>,
        /// Variable mappings when LHS variables don't have matching names
        #[serde(skip_serializing_if = "Option::is_none")]
        translate: Option<serde_json::Value>,
        /// Optional description
        #[serde(skip_serializing_if = "Option::is_none")]
        description: Option<String>,
    },
    /// Two-way coupling between systems
    Couple2 {
        /// The two systems involved in coupling
        systems: Vec<String>,
        /// The coupletype names for each system
        coupletype_pair: Vec<String>,
        /// Connector definition with equations
        connector: serde_json::Value,
        /// Optional description
        #[serde(skip_serializing_if = "Option::is_none")]
        description: Option<String>,
    },
    /// Variable mapping between systems
    VariableMap {
        /// Source variable (scoped reference)
        from: String,
        /// Target parameter (scoped reference)
        to: String,
        /// How the mapping is applied
        transform: String,
        /// Conversion factor (for conversion_factor transform)
        #[serde(skip_serializing_if = "Option::is_none")]
        factor: Option<f64>,
        /// Optional description
        #[serde(skip_serializing_if = "Option::is_none")]
        description: Option<String>,
    },
    /// Apply operator to system
    OperatorApply {
        /// Operator reference
        operator: String,
        /// Target system reference
        target: String,
        /// Application parameters
        #[serde(skip_serializing_if = "Option::is_none")]
        config: Option<serde_json::Value>,
    },
    /// Callback coupling
    Callback {
        /// Callback function reference
        callback: String,
        /// Source system reference
        source: String,
        /// Target system reference
        target: String,
    },
    /// Event-based coupling
    Event {
        /// Event reference
        event: String,
        /// Systems involved
        systems: Vec<String>,
        /// Event configuration
        #[serde(skip_serializing_if = "Option::is_none")]
        config: Option<serde_json::Value>,
    },
}

/// Variable mapping between systems
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VariableMapping {
    /// Source variable name
    pub source_var: String,
    /// Target variable name
    pub target_var: String,
    /// Optional scaling factor
    #[serde(skip_serializing_if = "Option::is_none")]
    pub factor: Option<f64>,
}

/// Spatial/temporal domain specification
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Domain {
    /// Spatial dimensions
    #[serde(skip_serializing_if = "Option::is_none")]
    pub spatial: Option<serde_json::Value>,

    /// Temporal domain
    #[serde(skip_serializing_if = "Option::is_none")]
    pub temporal: Option<serde_json::Value>,
}

/// Solver configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Solver {
    /// Solver algorithm
    #[serde(skip_serializing_if = "Option::is_none")]
    pub algorithm: Option<String>,

    /// Solver-specific parameters
    #[serde(skip_serializing_if = "Option::is_none")]
    pub config: Option<serde_json::Value>,
}