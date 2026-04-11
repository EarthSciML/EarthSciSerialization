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

    /// Named spatial/temporal domain specifications
    #[serde(skip_serializing_if = "Option::is_none")]
    pub domains: Option<HashMap<String, Domain>>,

    /// Geometric interfaces between domains
    #[serde(skip_serializing_if = "Option::is_none")]
    pub interfaces: Option<HashMap<String, serde_json::Value>>,
}

/// Academic citation or data source reference
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Reference {
    /// DOI identifier
    #[serde(skip_serializing_if = "Option::is_none")]
    pub doi: Option<String>,

    /// Full citation text
    #[serde(skip_serializing_if = "Option::is_none")]
    pub citation: Option<String>,

    /// URL reference
    #[serde(skip_serializing_if = "Option::is_none")]
    pub url: Option<String>,

    /// Additional notes
    #[serde(skip_serializing_if = "Option::is_none")]
    pub notes: Option<String>,
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

    /// License information
    #[serde(skip_serializing_if = "Option::is_none")]
    pub license: Option<String>,

    /// Creation timestamp (ISO 8601)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub created: Option<String>,

    /// Last modification timestamp (ISO 8601)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub modified: Option<String>,

    /// Tags for categorization
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tags: Option<Vec<String>>,

    /// Academic citations and references
    #[serde(skip_serializing_if = "Option::is_none")]
    pub references: Option<Vec<Reference>>,
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

    /// Name of a domain from the `domains` section (or null for 0D models)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub domain: Option<String>,

    /// Coupling type label
    #[serde(skip_serializing_if = "Option::is_none")]
    pub coupletype: Option<String>,

    /// Academic citation or data source reference
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reference: Option<Reference>,

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

    /// Named child models (subsystems), keyed by unique identifier
    #[serde(skip_serializing_if = "Option::is_none")]
    pub subsystems: Option<HashMap<String, serde_json::Value>>,

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

    /// Functional affect specification
    #[serde(skip_serializing_if = "Option::is_none")]
    pub functional_affect: Option<FunctionalAffect>,

    /// Parameters modified by this event
    #[serde(skip_serializing_if = "Option::is_none")]
    pub discrete_parameters: Option<Vec<String>>,

    /// Whether to reinitialize the system after the event
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reinitialize: Option<bool>,

    /// Brief description
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
}

/// Trigger condition for discrete events
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum DiscreteEventTrigger {
    /// Fires when boolean condition is true
    Condition { expression: Expr },
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

    /// Condition expressions (zero-crossing detection)
    pub conditions: Vec<Expr>,

    /// What happens when the event fires on positive-going zero crossings
    pub affects: Vec<AffectEquation>,

    /// Separate affects for negative-going zero crossings
    #[serde(skip_serializing_if = "Option::is_none")]
    pub affect_neg: Option<Vec<AffectEquation>>,

    /// Root finding direction
    #[serde(skip_serializing_if = "Option::is_none")]
    pub root_find: Option<RootFindDirection>,

    /// Whether to reinitialize the system after the event
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reinitialize: Option<bool>,

    /// Parameters modified by this event
    #[serde(skip_serializing_if = "Option::is_none")]
    pub discrete_parameters: Option<Vec<String>>,

    /// Event priority (lower number = higher priority)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub priority: Option<u32>,

    /// Brief description
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
}

/// Functional affect specification for events
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FunctionalAffect {
    /// Registered identifier for the affect implementation
    pub handler_id: String,

    /// State variables accessed by the handler
    pub read_vars: Vec<String>,

    /// Parameters accessed by the handler
    pub read_params: Vec<String>,

    /// Parameters modified by the handler
    #[serde(skip_serializing_if = "Option::is_none")]
    pub modified_params: Option<Vec<String>>,

    /// Handler-specific configuration
    #[serde(skip_serializing_if = "Option::is_none")]
    pub config: Option<serde_json::Value>,
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
    /// Domain name (key in EsmFile.domains)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub domain: Option<String>,

    /// Coupling type label
    #[serde(skip_serializing_if = "Option::is_none")]
    pub coupletype: Option<String>,

    /// Academic citation or data source reference
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reference: Option<Reference>,

    /// Chemical species, keyed by species name
    pub species: HashMap<String, Species>,

    /// Named parameters (rate constants, temperature, photolysis rates, etc.)
    pub parameters: HashMap<String, Parameter>,

    /// Chemical reactions
    pub reactions: Vec<Reaction>,

    /// Additional algebraic or ODE constraints
    #[serde(skip_serializing_if = "Option::is_none")]
    pub constraint_equations: Option<Vec<Equation>>,

    /// Discrete events
    #[serde(skip_serializing_if = "Option::is_none")]
    pub discrete_events: Option<Vec<DiscreteEvent>>,

    /// Continuous events
    #[serde(skip_serializing_if = "Option::is_none")]
    pub continuous_events: Option<Vec<ContinuousEvent>>,

    /// Named child reaction systems (subsystems), keyed by unique identifier
    #[serde(skip_serializing_if = "Option::is_none")]
    pub subsystems: Option<HashMap<String, serde_json::Value>>,
}

/// Chemical species in a reaction system. Keyed by name in the parent map.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct Species {
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
    /// Unique reaction identifier
    #[serde(skip_serializing_if = "Option::is_none")]
    pub id: Option<String>,

    /// Human-readable reaction name
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,

    /// Reactant species and stoichiometry. May be null for source reactions (∅ → X).
    /// Schema requires this field to be present (possibly null).
    #[serde(default)]
    pub substrates: Option<Vec<StoichiometricEntry>>,

    /// Product species and stoichiometry. May be null for sink reactions (X → ∅).
    /// Schema requires this field to be present (possibly null).
    #[serde(default)]
    pub products: Option<Vec<StoichiometricEntry>>,

    /// Rate law expression
    pub rate: Expr,

    /// Academic citation or data source reference
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reference: Option<Reference>,
}

/// Species with stoichiometric coefficient
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StoichiometricEntry {
    /// Species name
    pub species: String,

    /// Stoichiometric coefficient (integer ≥ 1 per schema; serialized as `stoichiometry`)
    #[serde(rename = "stoichiometry", default = "default_stoichiometry")]
    pub coefficient: u32,
}

fn default_stoichiometry() -> u32 {
    1
}

/// External data loader reference
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataLoader {
    /// Data loader type identifier
    #[serde(rename = "type")]
    pub loader_type: String,

    /// Registered identifier the runtime uses to find the implementation
    pub loader_id: String,

    /// Configuration parameters
    #[serde(skip_serializing_if = "Option::is_none")]
    pub config: Option<serde_json::Value>,

    /// Academic citation or data source reference
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reference: Option<Reference>,

    /// Variables this loader makes available, keyed by name
    pub provides: HashMap<String, DataLoaderProvides>,

    /// ISO 8601 duration (e.g., "PT3H")
    #[serde(skip_serializing_if = "Option::is_none")]
    pub temporal_resolution: Option<String>,

    /// Grid spacing per dimension
    #[serde(skip_serializing_if = "Option::is_none")]
    pub spatial_resolution: Option<HashMap<String, f64>>,

    /// Interpolation method (linear, nearest, cubic)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub interpolation: Option<String>,
}

/// A variable provided by a data loader
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataLoaderProvides {
    /// Physical units
    #[serde(skip_serializing_if = "Option::is_none")]
    pub units: Option<String>,

    /// Brief description
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
}

/// Runtime operator reference
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Operator {
    /// Registered identifier the runtime uses to find the implementation
    pub operator_id: String,

    /// Variables required by the operator
    pub needed_vars: Vec<String>,

    /// Variables the operator modifies
    #[serde(skip_serializing_if = "Option::is_none")]
    pub modifies: Option<Vec<String>>,

    /// Academic citation or data source reference
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reference: Option<Reference>,

    /// Implementation-specific configuration
    #[serde(skip_serializing_if = "Option::is_none")]
    pub config: Option<serde_json::Value>,

    /// Brief description
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
}

/// Coupling entry with discriminated union based on type field
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
#[allow(clippy::large_enum_variant)]
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
    /// Bi-directional coupling via explicit ConnectorSystem equations
    Couple {
        /// The two systems involved in coupling
        systems: Vec<String>,
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
        /// Optional description
        #[serde(skip_serializing_if = "Option::is_none")]
        description: Option<String>,
    },
    /// Callback coupling
    Callback {
        /// Registered identifier for the callback
        callback_id: String,
        /// Configuration parameters
        #[serde(skip_serializing_if = "Option::is_none")]
        config: Option<serde_json::Value>,
        /// Optional description
        #[serde(skip_serializing_if = "Option::is_none")]
        description: Option<String>,
    },
    /// Event-based coupling
    Event {
        /// Whether this is a continuous or discrete event
        event_type: String,
        /// Human-readable identifier
        #[serde(skip_serializing_if = "Option::is_none")]
        name: Option<String>,
        /// Condition expressions (zero-crossing for continuous, boolean for discrete)
        #[serde(skip_serializing_if = "Option::is_none")]
        conditions: Option<Vec<Expr>>,
        /// Trigger specification (for discrete events)
        #[serde(skip_serializing_if = "Option::is_none")]
        trigger: Option<DiscreteEventTrigger>,
        /// Affect equations
        #[serde(skip_serializing_if = "Option::is_none")]
        affects: Option<Vec<AffectEquation>>,
        /// Functional affect handler
        #[serde(skip_serializing_if = "Option::is_none")]
        functional_affect: Option<FunctionalAffect>,
        /// Separate affects for negative-going zero crossings
        #[serde(skip_serializing_if = "Option::is_none")]
        affect_neg: Option<Vec<AffectEquation>>,
        /// Parameters modified by this event
        #[serde(skip_serializing_if = "Option::is_none")]
        discrete_parameters: Option<Vec<String>>,
        /// Root finding direction
        #[serde(skip_serializing_if = "Option::is_none")]
        root_find: Option<RootFindDirection>,
        /// Whether to reinitialize the system after the event
        #[serde(skip_serializing_if = "Option::is_none")]
        reinitialize: Option<bool>,
        /// Brief description
        #[serde(skip_serializing_if = "Option::is_none")]
        description: Option<String>,
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
    /// Name of the independent (time) variable
    #[serde(skip_serializing_if = "Option::is_none")]
    pub independent_variable: Option<String>,

    /// Temporal domain
    #[serde(skip_serializing_if = "Option::is_none")]
    pub temporal: Option<serde_json::Value>,

    /// Spatial dimensions, keyed by name
    #[serde(skip_serializing_if = "Option::is_none")]
    pub spatial: Option<serde_json::Value>,

    /// Coordinate transforms
    #[serde(skip_serializing_if = "Option::is_none")]
    pub coordinate_transforms: Option<serde_json::Value>,

    /// Coordinate reference system
    #[serde(skip_serializing_if = "Option::is_none")]
    pub spatial_ref: Option<String>,

    /// Initial conditions specification
    #[serde(skip_serializing_if = "Option::is_none")]
    pub initial_conditions: Option<serde_json::Value>,

    /// Boundary conditions
    #[serde(skip_serializing_if = "Option::is_none")]
    pub boundary_conditions: Option<serde_json::Value>,

    /// Floating point precision
    #[serde(skip_serializing_if = "Option::is_none")]
    pub element_type: Option<String>,

    /// Array backend identifier
    #[serde(skip_serializing_if = "Option::is_none")]
    pub array_type: Option<String>,
}
