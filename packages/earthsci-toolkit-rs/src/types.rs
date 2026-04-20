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

    /// Registry of named pure functions invoked inside expressions via the
    /// `call` op (esm-spec §9.2).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub registered_functions: Option<HashMap<String, RegisteredFunction>>,

    /// Composition and coupling rules
    #[serde(skip_serializing_if = "Option::is_none")]
    pub coupling: Option<Vec<CouplingEntry>>,

    /// Named spatial/temporal domain specifications
    #[serde(skip_serializing_if = "Option::is_none")]
    pub domains: Option<HashMap<String, Domain>>,

    /// Geometric interfaces between domains
    #[serde(skip_serializing_if = "Option::is_none")]
    pub interfaces: Option<HashMap<String, serde_json::Value>>,

    /// Named discretization grids (v0.2.0). Each entry declares a
    /// cartesian/unstructured/cubed_sphere topology per docs/rfcs/discretization.md §6.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub grids: Option<HashMap<String, Grid>>,
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

    /// System classification stamped by `discretize()` per RFC §12:
    /// `"ode"` if no algebraic equations remain after discretization,
    /// `"dae"` if any algebraic equations remain. Absent on undiscretized
    /// inputs.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub system_class: Option<String>,

    /// DAE classification details stamped by `discretize()` per RFC §12.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub dae_info: Option<DaeInfo>,

    /// Provenance stamp: the `metadata.name` of the input ESM that
    /// `discretize()` was called on. Absent on undiscretized inputs.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub discretized_from: Option<String>,
}

/// Summary of DAE classification stamped onto `metadata.dae_info` by
/// `discretize()` per RFC §12.
///
/// `algebraic_equation_count` is the post-`discretize()` total across all
/// models; `per_model` breaks it down by model name. `factored_equation_count`
/// is rust-binding-specific — it reports the number of trivially
/// substitutable algebraic equations the preprocessor eliminated before
/// classification (see `docs/rfcs/dae-binding-strategies.md`). `0` on
/// bindings that do not perform trivial factoring.
#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct DaeInfo {
    /// Total algebraic equations remaining after `discretize()` completes.
    pub algebraic_equation_count: usize,

    /// Per-model count, keyed by model name.
    pub per_model: HashMap<String, usize>,

    /// rust-binding-specific: number of trivially substitutable algebraic
    /// equations factored into the ODE system by the preprocessor. `None`
    /// on bindings that do not factor.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub factored_equation_count: Option<usize>,
}

/// Mathematical expression: a number literal, variable reference, or operator node.
///
/// Per discretization RFC §5.4.1, integer and float literals are distinct AST
/// node kinds. On the wire (§5.4.6 round-trip parse rule), a JSON-number
/// token containing `.`, `e`, or `E` deserializes to [`Expr::Number`]; a token
/// matching the integer grammar `-?(0|[1-9][0-9]*)` deserializes to
/// [`Expr::Integer`]. `#[serde(untagged)]` tries variants in order; `Integer`
/// appears before `Number` so that the strict integer JSON tokens bind to
/// `Integer` and float tokens fall through to `Number`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(untagged)]
#[allow(clippy::large_enum_variant)]
pub enum Expr {
    /// Integer literal (JSON integer token, no `.`, no `e`/`E`).
    Integer(i64),

    /// Float literal (JSON number token with `.`, `e`, or `E`).
    Number(f64),

    /// Variable or parameter reference string
    Variable(String),

    /// Operator node with children
    Operator(ExpressionNode),
}

/// Expression node representing an operator with operands
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
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

    /// Body expression for `arrayop` nodes (the scalar body evaluated for
    /// each tuple of loop-index values). Out-of-band from `args` because the
    /// serialized schema uses a sidecar `expr` field.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub expr: Option<Box<Expr>>,

    /// Output index names for `arrayop` (e.g. `["i", "j"]`).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub output_idx: Option<Vec<String>>,

    /// Per-index inclusive ranges `{name: [lo, hi]}` for `arrayop`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub ranges: Option<HashMap<String, [i64; 2]>>,

    /// Reduction operator (`"+"`, `"*"`, `"max"`, `"min"`) for `arrayop`
    /// contractions over indices appearing in `expr` but not `output_idx`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub reduce: Option<String>,

    /// Per-region per-dimension inclusive range lists for `makearray`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub regions: Option<Vec<Vec<[i64; 2]>>>,

    /// Per-region value expressions for `makearray`. Later regions overwrite
    /// earlier regions at overlapping positions.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub values: Option<Vec<Expr>>,

    /// Target shape for `reshape`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub shape: Option<Vec<i64>>,

    /// Permutation for `transpose` (defaults to reverse-axis for 2-D).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub perm: Option<Vec<i64>>,

    /// Concatenation axis for `concat` (0-indexed).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub axis: Option<i64>,

    /// Elementwise operator name for `broadcast` (serialized as `fn`).
    #[serde(default, rename = "fn", skip_serializing_if = "Option::is_none")]
    pub broadcast_fn: Option<String>,

    /// For `call`: id of a registered function (esm-spec §4.4 / §9.2).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub handler_id: Option<String>,
}

/// Numerical comparison tolerance used by inline model tests.
///
/// Either or both of `abs` / `rel` may be set. An assertion passes when any
/// set bound is satisfied:
/// `|actual - expected| <= abs`  OR
/// `|actual - expected| / max(|expected|, epsilon) <= rel`.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Tolerance {
    /// Absolute tolerance bound.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub abs: Option<f64>,

    /// Relative tolerance bound.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub rel: Option<f64>,
}

/// Simulation time interval used by inline model tests.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TimeSpan {
    /// Start of the simulation window (in the component's time units).
    pub start: f64,

    /// End of the simulation window (in the component's time units).
    pub end: f64,
}

/// A single scalar `(variable, time, expected)` check inside a [`ModelTest`].
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ModelTestAssertion {
    /// Name of the variable or species to check.
    pub variable: String,

    /// Simulation time at which to evaluate the assertion.
    pub time: f64,

    /// Expected scalar value of the variable at the given time.
    pub expected: f64,

    /// Per-assertion tolerance override. Takes precedence over test-level
    /// and model-level defaults when present.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tolerance: Option<Tolerance>,
}

/// Inline validation test for a [`Model`] (schema gt-cc1).
///
/// Defines the run configuration — initial conditions, parameter overrides,
/// simulation time span — and a list of scalar assertions that must hold.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ModelTest {
    /// Identifier unique within this component's `tests` array.
    pub id: String,

    /// Human-readable description of what this test verifies.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,

    /// Initial-value overrides for state variables, keyed by variable name.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub initial_conditions: Option<HashMap<String, f64>>,

    /// Parameter overrides, keyed by parameter name.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub parameter_overrides: Option<HashMap<String, f64>>,

    /// Simulation time interval for this test.
    pub time_span: TimeSpan,

    /// Test-level default tolerance applied to assertions that do not
    /// override it.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tolerance: Option<Tolerance>,

    /// Scalar `(variable, time)` checks that define the pass/fail criterion.
    pub assertions: Vec<ModelTestAssertion>,
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

    /// Model-level default numerical tolerance for inline tests.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tolerance: Option<Tolerance>,

    /// Inline validation tests that exercise this model in isolation.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tests: Option<Vec<ModelTest>>,

    /// Model-level boundary conditions, keyed by user-supplied id. New in ESM
    /// v0.2.0 (breaking change per docs/rfcs/discretization.md §9 / §10.1).
    /// Held as a raw JSON map pending downstream consumers; downstream code
    /// may deserialize each entry into a typed BC struct as needed.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub boundary_conditions: Option<HashMap<String, serde_json::Value>>,

    /// Equations that hold only at t=0 (initialization-only, not time-stepped).
    /// Introduced for aerosol equilibrium / plume-rise style models (gt-ebuq).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub initialization_equations: Option<Vec<Equation>>,

    /// Initial-guess seeds for nonlinear solvers during initialization, keyed
    /// by variable name. Values may be numeric literals or Expression graphs.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub guesses: Option<HashMap<String, serde_json::Value>>,

    /// MTK system-kind discriminator: "ode" (default), "nonlinear", "sde", "pde".
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub system_kind: Option<String>,
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

    /// Arrayed-variable shape: ordered dimension names drawn from the
    /// enclosing model's domain.spatial. `None` means scalar.
    /// See discretization RFC §10.2.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub shape: Option<Vec<String>>,

    /// Staggered-grid location tag (e.g., "cell_center", "edge_normal",
    /// "vertex"). `None` means no explicit staggering.
    /// See discretization RFC §10.2.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub location: Option<String>,

    /// Brownian-only: kind of stochastic process. Currently only "wiener".
    #[serde(skip_serializing_if = "Option::is_none")]
    pub noise_kind: Option<String>,

    /// Brownian-only: opaque tag grouping correlated noise sources.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub correlation_group: Option<String>,
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
    /// Brownian noise source (Wiener process). The presence of any brownian
    /// variable promotes the enclosing model from an ODE system to an SDE
    /// system. Maps to MTK `@brownians` and an `SDESystem`.
    Brownian,
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
#[allow(clippy::large_enum_variant)]
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

    /// Reservoir species: participates in reactions but held fixed (no ODE).
    /// Maps to Catalyst's `isconstantspecies=true`.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub constant: Option<bool>,
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

/// Species with stoichiometric coefficient.
///
/// v0.2.x permits fractional coefficients (e.g. `0.87 CH2O` in atmospheric
/// chemistry) in addition to the historical integer case. The coefficient
/// MUST be positive and finite — NaN / ±∞ are rejected at parse time by
/// [`validate_stoichiometries`](crate::parse::validate_stoichiometries).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StoichiometricEntry {
    /// Species name
    pub species: String,

    /// Stoichiometric coefficient (positive finite number; serialized as `stoichiometry`)
    #[serde(rename = "stoichiometry", default = "default_stoichiometry")]
    pub coefficient: f64,
}

fn default_stoichiometry() -> f64 {
    1.0
}

/// Generic, runtime-agnostic description of an external data source.
///
/// Carries enough structural information to locate files, map timestamps to
/// files, describe spatial/variable semantics, and regrid — rather than
/// pointing at a runtime handler. Authentication and algorithm-specific
/// tuning are runtime-only and not part of the schema.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataLoader {
    /// Structural kind of the dataset. Scientific role (emissions,
    /// meteorology, elevation, ...) is not schema-validated and belongs in
    /// `metadata.tags`.
    pub kind: DataLoaderKind,

    /// File discovery configuration.
    pub source: DataLoaderSource,

    /// Temporal coverage and record layout.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub temporal: Option<DataLoaderTemporal>,

    /// Spatial grid description.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub spatial: Option<DataLoaderSpatial>,

    /// Variables exposed by this loader, keyed by schema-level variable name.
    pub variables: HashMap<String, DataLoaderVariable>,

    /// Structural regridding configuration.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub regridding: Option<DataLoaderRegridding>,

    /// Academic citation or data source reference.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reference: Option<Reference>,

    /// Free-form metadata about the data source. Tags convey scientific role.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metadata: Option<DataLoaderMetadata>,
}

/// Structural kind of a data loader dataset.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DataLoaderKind {
    /// Gridded dataset.
    Grid,
    /// Point / observational dataset.
    Points,
    /// Static dataset (no time dimension).
    Static,
}

/// File discovery configuration. Describes how to locate data files at
/// runtime via URL templates with date/variable substitutions.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataLoaderSource {
    /// Jinja-style URL template with substitutions. Supported:
    /// `{date:<strftime>}` (e.g. `{date:%Y%m%d}`), `{var}`, `{sector}`,
    /// `{species}`. Custom substitutions are allowed and must be passed
    /// through by the runtime.
    pub url_template: String,

    /// Ordered fallback URL templates. Runtime tries each in order.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub mirrors: Option<Vec<String>>,
}

/// Temporal coverage and record layout for a data source.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct DataLoaderTemporal {
    /// ISO 8601 datetime — first timestamp available from this source.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub start: Option<String>,

    /// ISO 8601 datetime — last timestamp available from this source.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub end: Option<String>,

    /// ISO 8601 duration describing how much time one file covers.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub file_period: Option<String>,

    /// ISO 8601 duration describing spacing between samples within a file.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub frequency: Option<String>,

    /// Number of time records per file. `"auto"` means read from file at
    /// runtime.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub records_per_file: Option<RecordsPerFile>,

    /// Name of the time coordinate variable in the file. Used when
    /// `records_per_file` is absent or `"auto"`.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub time_variable: Option<String>,
}

/// Number of records per file — an integer, or the literal `"auto"`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum RecordsPerFile {
    /// Fixed count (`>= 1`).
    Count(u32),
    /// `"auto"` — read from file at runtime.
    Auto(AutoRecords),
}

/// Carrier for the `"auto"` literal in [`RecordsPerFile`].
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum AutoRecords {
    /// Runtime discovers the record count from file metadata.
    Auto,
}

/// Per-dimension grid staggering (centered or edge-aligned).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum StaggeringMode {
    /// Cell-centered.
    Center,
    /// Edge-aligned.
    Edge,
}

/// Spatial grid description for a data source.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataLoaderSpatial {
    /// Coordinate reference system as a PROJ string or EPSG code.
    pub crs: String,

    /// Structural grid family.
    pub grid_type: GridType,

    /// Per-dimension staggering.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub staggering: Option<HashMap<String, StaggeringMode>>,

    /// Per-dimension resolution in native CRS units.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub resolution: Option<HashMap<String, f64>>,

    /// Per-dimension `[min, max]` extent in native CRS units.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub extent: Option<HashMap<String, [f64; 2]>>,
}

/// Structural grid family for a data loader.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum GridType {
    /// Latitude/longitude grid.
    Latlon,
    /// Lambert conformal conic.
    LambertConformal,
    /// Mercator projection.
    Mercator,
    /// Polar stereographic projection.
    PolarStereographic,
    /// Rotated-pole projection.
    RotatedPole,
    /// Unstructured mesh / point dataset.
    Unstructured,
}

/// A variable exposed by a data loader, mapped from a source-file variable.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataLoaderVariable {
    /// Name of the variable inside the source file. May differ from the
    /// schema-level variable name.
    pub file_variable: String,

    /// Units of the variable as exposed to the schema.
    pub units: String,

    /// Optional multiplicative factor or Expression AST applied to convert
    /// source-file values to the declared units.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub unit_conversion: Option<UnitConversion>,

    /// Brief description.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,

    /// Academic citation or data source reference.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reference: Option<Reference>,
}

/// Multiplicative factor (number) or Expression AST used to convert source-
/// file values to the declared units.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
#[allow(clippy::large_enum_variant)]
pub enum UnitConversion {
    /// Simple multiplicative factor.
    Factor(f64),
    /// Expression AST applied to the source value.
    Expression(Expr),
}

/// Structural regridding configuration. Algorithm-specific tuning parameters
/// are runtime-side and not in the schema.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct DataLoaderRegridding {
    /// Value to assign to cells with no source data.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub fill_value: Option<f64>,

    /// Behavior when regridding targets fall outside the source extent.
    /// Defaults to `clamp`.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub extrapolation: Option<ExtrapolationMode>,
}

/// Behavior when regridding targets fall outside the source extent.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ExtrapolationMode {
    /// Clamp to nearest in-range value.
    Clamp,
    /// Return NaN.
    Nan,
    /// Periodic wrap-around.
    Periodic,
}

/// Free-form metadata about a data loader.
///
/// The `tags` field is conventional for expressing scientific role
/// (e.g. `"emissions"`, `"reanalysis"`) and is not schema-validated.
/// Additional fields are preserved as raw JSON via `extra`.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct DataLoaderMetadata {
    /// Scientific role tags (freeform).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tags: Option<Vec<String>>,

    /// Additional, loader-specific metadata fields.
    #[serde(flatten)]
    pub extra: HashMap<String, serde_json::Value>,
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

/// Calling convention for a [`RegisteredFunction`] (esm-spec §9.2).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RegisteredFunctionSignature {
    /// Number of positional arguments the handler expects.
    pub arg_count: i64,

    /// Optional per-argument type hints.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub arg_types: Option<Vec<String>>,

    /// Optional return-type hint (`"scalar"` or `"array"`).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub return_type: Option<String>,
}

/// A named pure function invoked inside an expression via the `call` op
/// (esm-spec §9.2). The serialized entry declares the calling contract only;
/// the concrete implementation is supplied by the runtime through a handler
/// registry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RegisteredFunction {
    /// Registered identifier; must match the map key and `call.handler_id`.
    pub id: String,

    /// Calling convention.
    pub signature: RegisteredFunctionSignature,

    /// Optional output units string.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub units: Option<String>,

    /// Optional per-argument units hints; length must equal `signature.arg_count`.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub arg_units: Option<Vec<Option<String>>>,

    /// Human-readable description.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,

    /// Academic citations.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub references: Option<Vec<Reference>>,

    /// Implementation-specific configuration passed to the handler at bind time.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub config: Option<serde_json::Value>,
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

    /// DEPRECATED v0.1.0 domain-level boundary conditions. Retained as a
    /// transitional shim (RFC §10.1 + gt-2fvs mayor decision); loaders emit
    /// E_DEPRECATED_DOMAIN_BC when this field is present. Model-level BCs
    /// (Model::boundary_conditions) are the canonical v0.2.0 form.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub boundary_conditions: Option<serde_json::Value>,

    /// Floating point precision
    #[serde(skip_serializing_if = "Option::is_none")]
    pub element_type: Option<String>,

    /// Array backend identifier
    #[serde(skip_serializing_if = "Option::is_none")]
    pub array_type: Option<String>,
}

/// Generator for a grid metric array (§6.5). Exactly one of the three kinds
/// applies:
/// * `expression`: analytic expression, with `expr` set.
/// * `loader`: pulled from a `data_loaders` entry; `loader` + `field` set.
/// * `builtin`: closed set (currently `gnomonic_c6_neighbors`,
///   `gnomonic_c6_d4_action`) selected by `name`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GridMetricGenerator {
    /// One of `"expression"`, `"loader"`, `"builtin"`.
    pub kind: String,

    /// For `kind = "expression"`: the expression tree / literal / variable ref.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub expr: Option<Expr>,

    /// For `kind = "loader"`: name of a `data_loaders` entry.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub loader: Option<String>,

    /// For `kind = "loader"`: named field within the loader's output.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub field: Option<String>,

    /// For `kind = "builtin"`: canonical builtin name (closed set per §6.4).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
}

/// A named metric array declared on a grid (e.g., dx, dcEdge, areaCell). See §6.5.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GridMetricArray {
    /// Tensor rank of the array: 0 = scalar, 1 = along a single dim, 2+ = multi.
    pub rank: u32,

    /// For `rank = 1`: the dimension the array is indexed by.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub dim: Option<String>,

    /// For `rank >= 2`: ordered list of dimensions the array is indexed by.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub dims: Option<Vec<String>>,

    /// Optional declared shape (parameter names or integer literals per dim).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub shape: Option<Vec<serde_json::Value>>,

    /// The generator that produces this array.
    pub generator: GridMetricGenerator,
}

/// Unstructured / cubed-sphere connectivity table (§6.3, §6.4). Either
/// `loader` + `field` are set (data-loader-backed) or `generator` is set
/// (builtin / expression).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GridConnectivity {
    /// Ordered list of dimension sizes (parameter names or integer literals).
    pub shape: Vec<serde_json::Value>,

    /// Tensor rank (>= 1).
    pub rank: u32,

    /// Name of a `data_loaders` entry that supplies this table.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub loader: Option<String>,

    /// Named field within the referenced loader's output.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub field: Option<String>,

    /// Alternative to loader/field: generator-backed connectivity (e.g.,
    /// cubed-sphere `panel_connectivity` via `kind = "builtin"`).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub generator: Option<GridMetricGenerator>,
}

/// Per-dimension extent for cartesian or cubed_sphere grids. `n` is either
/// an integer literal or a parameter-name string; `spacing` is `"uniform"`
/// or `"nonuniform"` for cartesian.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GridExtent {
    /// Integer literal or parameter-name string naming the dimension count.
    pub n: serde_json::Value,

    /// Cartesian spacing: `"uniform"` or `"nonuniform"`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub spacing: Option<String>,
}

/// A named discretization grid (§6.1-§6.5). The `family` field selects one of
/// three topologies: `"cartesian"`, `"unstructured"`, or `"cubed_sphere"`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Grid {
    /// One of `"cartesian"`, `"unstructured"`, `"cubed_sphere"`.
    pub family: String,

    /// Human-readable description.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,

    /// Ordered list of logical dimension names.
    pub dimensions: Vec<String>,

    /// Declared stagger locations used by variables on this grid (see §11).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub locations: Option<Vec<String>>,

    /// Metric array declarations, keyed by array name.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub metric_arrays: Option<HashMap<String, GridMetricArray>>,

    /// Grid-level parameters. Reuses the ordinary ESM Parameter schema.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub parameters: Option<HashMap<String, Parameter>>,

    /// Optional name of the `domains` entry this grid refines.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub domain: Option<String>,

    /// Per-dimension extents (required for `"cartesian"` and `"cubed_sphere"`).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub extents: Option<HashMap<String, GridExtent>>,

    /// Unstructured-family connectivity tables (e.g. `cellsOnEdge`).
    /// Required for `family = "unstructured"`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub connectivity: Option<HashMap<String, GridConnectivity>>,

    /// Cubed-sphere panel connectivity (e.g. `neighbors`, `axis_flip`).
    /// Required for `family = "cubed_sphere"`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub panel_connectivity: Option<HashMap<String, GridConnectivity>>,
}
