//! Native array runtime for `arrayop`, `makearray`, `index`, `reshape`,
//! `transpose`, `concat`, and `broadcast` expression nodes (gt-oxr).
//!
//! This module sits alongside [`crate::simulate`] and handles the subset of
//! ESM models that use array-shaped state variables and the array-op AST
//! nodes introduced in gt-t5c. It is invoked from [`crate::simulate`] when
//! the top-level dispatcher detects array-op nodes in the file; pure-scalar
//! models continue to go through the existing scalar interpreter.
//!
//! ## Approach
//!
//! The flat state vector that diffsol consumes is a contiguous
//! concatenation of per-variable blocks. Each array variable occupies a
//! column-major-ordered block sized by its inferred shape; scalar
//! variables occupy a single slot. Shape inference walks every `index`
//! call and every `arrayop` `ranges` dict to compute per-variable, per-
//! dimension bounds.
//!
//! At RHS evaluation time the interpreter wraps the flat state slice into
//! [`ndarray::ArrayD`] views (one per variable), binds `arrayop` loop
//! indices into a context, and evaluates each equation's body expression
//! into a [`Value`] — either `Scalar(f64)` or `Array(ArrayD<f64>)`. For
//! array-producing operators (`reshape`, `transpose`, `concat`,
//! `broadcast`, `makearray`) the whole array is materialised as an
//! intermediate so downstream `index` extractions can select any element.
//!
//! Column-major ordering is the convention used by the Julia sibling and
//! reflected in the cross-language conformance fixtures (e.g.
//! `arrayop_11_reshape_roundtrip.esm`).

#![cfg(not(target_arch = "wasm32"))]
#![allow(
    clippy::too_many_arguments,
    clippy::type_complexity,
    clippy::collapsible_if,
    clippy::needless_range_loop,
    clippy::large_enum_variant
)]

use crate::aggregate::{
    ReduceKind, effective_reduce_kind, is_aggregate_op, resolve_aggregate_ranges,
};
use crate::simulate::{CompileError, SimulateError, SimulateOptions, SolutionMetadata};
use crate::simulate::{SimulateOptions as _SimOpts, Solution, SolverChoice};
use crate::types::{EsmFile, Expr, ExpressionNode, Model, ModelVariable, RangeSpec, VariableType};
use indexmap::IndexMap;
use ndarray::{ArrayD, IxDyn};
use std::collections::{HashMap, HashSet};

use diffsol::{
    Bdf, FaerLU, FaerMat, NewtonNonlinearSolver, OdeBuilder, OdeSolverMethod, Sdirk, VectorHost,
};

// `SimulateOptions` re-export alias silences unused-import warnings from the
// alternate import path above while keeping a single source of truth for the
// public option type.
#[allow(dead_code)]
type _OptsAlias = _SimOpts;

// ============================================================================
// Value type: scalar or dynamic-rank ndarray.
// ============================================================================

/// A runtime value carried through the array-aware interpreter.
///
/// Scalars and whole arrays are first-class so operators like `reshape`,
/// `transpose`, `concat`, and `broadcast` can produce array-typed
/// intermediates that later `index` calls sample from.
#[derive(Debug, Clone)]
pub enum Value {
    Scalar(f64),
    Array(ArrayD<f64>),
}

impl Value {
    fn as_scalar(&self) -> Option<f64> {
        match self {
            Value::Scalar(v) => Some(*v),
            Value::Array(a) if a.ndim() == 0 => Some(a[IxDyn(&[])]),
            _ => None,
        }
    }
}

// ============================================================================
// Array model: shape information per variable + compiled RHS rules.
// ============================================================================

/// Per-variable shape/origin description.
#[derive(Debug, Clone)]
pub struct VarShape {
    /// Dimension extents. Empty vec means scalar.
    pub shape: Vec<usize>,
    /// Per-dimension origin (1-based indices per schema convention).
    pub origin: Vec<i64>,
    /// Flat offset in the state vector.
    pub flat_offset: usize,
}

/// One contracted (reduction) index's loop bound in an `aggregate`/`arrayop`
/// einsum. Either a static inclusive interval, or a **ragged** bound whose
/// upper limit `offsets[of…]` is gathered per output tuple at eval time
/// (RFC `semiring-faq-unified-ir` §5.2 — variable-valence / unstructured-mesh
/// reductions). The lower bound of a ragged dim is implicitly `1`.
#[derive(Debug, Clone)]
enum ContractDim {
    /// Static inclusive `[lo, hi]` (interval / categorical index sets).
    Static(i64, i64),
    /// Ragged `[1, offsets[of…]]` — `offsets` names the per-parent length
    /// factor; `of` names the parent index variables that address it.
    Ragged { offsets: String, of: Vec<String> },
}

impl ContractDim {
    /// Build a contracted dim from a resolved range spec: a [`RangeSpec::RaggedDyn`]
    /// becomes [`ContractDim::Ragged`]; anything else falls back to its static
    /// `[lo, hi]` bounds (`[0, 0]` — an empty reduction — if unresolved).
    fn from_range(spec: &RangeSpec) -> Self {
        match spec.ragged() {
            Some((offsets, of)) => ContractDim::Ragged {
                offsets: offsets.to_string(),
                of: of.to_vec(),
            },
            None => {
                let r = spec.bounds().unwrap_or([0, 0]);
                ContractDim::Static(r[0], r[1])
            }
        }
    }

    /// Resolve to a concrete inclusive `(lo, hi)` range under the current loop
    /// binds. A ragged dim gathers its parent index value(s) from `ctx` and
    /// reads `offsets[parent…]`; an empty bound (`lo > hi`, e.g. an isolated
    /// cell with zero neighbours) yields no contraction tuples, so the
    /// reduction returns the semiring's additive identity 0̄.
    fn concrete(&self, ctx: &EvalCtx) -> (i64, i64) {
        match self {
            ContractDim::Static(lo, hi) => (*lo, *hi),
            ContractDim::Ragged { offsets, of } => (1, ragged_upper_bound(offsets, of, ctx)),
        }
    }
}

/// An equation rule compiled for runtime RHS evaluation.
#[derive(Debug, Clone)]
enum RhsRule {
    /// Scalar derivative `D(var) = body` — `var` is a 0-D state variable.
    Scalar { slot: usize, body: Box<Expr> },
    /// Indexed scalar derivative `D(var[i1, i2, ...]) = body` with all
    /// indices concrete. Writes to a single flat slot.
    IndexedScalar { slot: usize, body: Box<Expr> },
    /// Array-op derivative. The body expression is evaluated once per tuple
    /// of `output_idx` values (the tuple drawn from `output_ranges`) and the
    /// resulting scalar is written into `var_name[idx...]`.
    /// If `contract_names` is non-empty the body also contains contracted
    /// (reduction) indices that are unrolled at eval time and combined via the
    /// semiring's ⊕ (`reduce`), resolved once at build time.
    ArrayLoop {
        var_name: String,
        output_idx_names: Vec<String>,
        output_ranges: Vec<(i64, i64)>,
        lhs_idx_exprs: Vec<Expr>,
        body: Box<Expr>,
        contract_names: Vec<String>,
        /// Per-contracted-index loop bounds. A [`ContractDim::Ragged`] dim is
        /// expanded to its dynamic `[1, offsets[of…]]` extent per output tuple.
        contract_dims: Vec<ContractDim>,
        reduce: ReduceKind,
        /// Optional `filter` predicate (§5.3): combinations for which it is
        /// false contribute the additive identity 0̄. `None` ⇒ no gating.
        filter: Option<Box<Expr>>,
    },
}

/// Eliminated algebraic-variable definition. Evaluated once per RHS call
/// into a transient ndarray (or scalar) that the `observed_values` map
/// exposes to downstream expressions.
#[derive(Debug, Clone)]
enum AlgebraicRule {
    /// `var := body` — pure scalar algebraic.
    Scalar { var: String, body: Box<Expr> },
    /// `var[i...] := body` — array algebraic defined via an arrayop over
    /// the full shape of `var`.
    ArrayLoop {
        var: String,
        output_idx_names: Vec<String>,
        output_ranges: Vec<(i64, i64)>,
        body: Box<Expr>,
    },
}

/// Compiled, parameter-sweep-ready ODE model for array-op models.
pub struct ArrayCompiled {
    var_shapes: IndexMap<String, VarShape>,
    /// Names of every scalar slot (`"u[1]"`, `"u[2,3]"`, `"s"`, etc.),
    /// parallel to the flat state vector.
    scalar_state_names: Vec<String>,
    /// Name → flat slot lookup.
    scalar_state_index: HashMap<String, usize>,
    /// Per-slot default value (from variable.default or None).
    state_defaults: Vec<Option<f64>>,
    param_names: Vec<String>,
    param_index: HashMap<String, usize>,
    param_defaults: Vec<Option<f64>>,
    /// Algebraic variables eliminated from the state vector. Stored as
    /// observed definitions evaluated at each RHS call in order (no cross-
    /// dependency support for v1 — fixtures don't need it).
    observed_rules: Vec<AlgebraicRule>,
    /// Observed-variable shapes (matches key set of observed_rules).
    observed_shapes: HashMap<String, VarShape>,
    /// Per-state RHS rules.
    rhs_rules: Vec<RhsRule>,
    /// Number of flat state slots.
    n_states: usize,
}

// ============================================================================
// Detection: does the file contain array-op expressions anywhere?
// ============================================================================

/// Names of the array-op sidecar operators introduced in gt-t5c. `arrayop`
/// and `makearray` are the composition primitives; the rest are shape /
/// extraction helpers that are only meaningful when operating on array
/// intermediates.
const ARRAY_OP_NAMES: &[&str] = &[
    "arrayop",
    "aggregate", // canonical alias of `arrayop` (RFC semiring-faq-unified-ir §5.6)
    "makearray",
    "reshape",
    "transpose",
    "concat",
    "broadcast",
];

/// Return true if any expression in the file uses a gt-t5c array op.
pub fn file_has_array_ops(file: &EsmFile) -> bool {
    let Some(models) = &file.models else {
        return false;
    };
    for model in models.values() {
        if model_has_array_ops(model) {
            return true;
        }
    }
    false
}

/// Return true if the file has spatial structure: top-level grid declarations
/// or any model with array-shaped state variables (`shape` field non-empty).
///
/// Used by [`crate::simulate::simulate`] to route discretized-PDE files to the
/// ArrayOp runtime even when the equations do not yet contain explicit
/// `arrayop`/`index` nodes (e.g. a spatial model whose equations were rewritten
/// using indexed-scalar D(u[i])=... form rather than the `arrayop` wrapper).
pub fn file_has_spatial_model(file: &EsmFile) -> bool {
    if file.grids.is_some() {
        return true;
    }
    let Some(models) = &file.models else {
        return false;
    };
    for model in models.values() {
        for var in model.variables.values() {
            if let Some(shape) = &var.shape {
                if !shape.is_empty() {
                    return true;
                }
            }
        }
    }
    false
}

fn model_has_array_ops(model: &Model) -> bool {
    for eq in &model.equations {
        if expr_has_array_op(&eq.lhs) || expr_has_array_op(&eq.rhs) {
            return true;
        }
    }
    // Also detect by the presence of bracketed initial conditions in the
    // variable definitions — not strictly an AST signal but a strong hint.
    for name in model.variables.keys() {
        if name.contains('[') {
            return true;
        }
    }
    false
}

fn expr_has_array_op(expr: &Expr) -> bool {
    match expr {
        Expr::Number(_) | Expr::Integer(_) | Expr::Variable(_) => false,
        Expr::Operator(node) => {
            if ARRAY_OP_NAMES.contains(&node.op.as_str()) {
                return true;
            }
            if node.op == "index" {
                // `index` is only meaningful when there is an array to index
                // into — always recognise it as an array-op signal.
                return true;
            }
            if let Some(inner) = &node.expr
                && expr_has_array_op(inner)
            {
                return true;
            }
            if let Some(vals) = &node.values {
                for v in vals {
                    if expr_has_array_op(v) {
                        return true;
                    }
                }
            }
            for a in &node.args {
                if expr_has_array_op(a) {
                    return true;
                }
            }
            false
        }
    }
}

/// Walk an expression and reject any spatial differential operator
/// (`grad`/`div`/`laplacian`). Per the canonical pipeline contract, ESD
/// discretization rules MUST rewrite these into `arrayop` AST before
/// reaching any binding's simulator. Encountering one here means
/// `discretize` was skipped or did not rewrite the node — silently
/// substituting zeros (the previous behaviour) would mask the broken
/// pipeline. (esm-i7b)
fn check_no_spatial_ops(expr: &Expr) -> Result<(), CompileError> {
    match expr {
        Expr::Number(_) | Expr::Integer(_) | Expr::Variable(_) => Ok(()),
        Expr::Operator(node) => {
            if matches!(node.op.as_str(), "grad" | "div" | "laplacian") {
                return Err(CompileError::UnreachableSpatialOperatorError {
                    op: node.op.clone(),
                });
            }
            if let Some(inner) = &node.expr {
                check_no_spatial_ops(inner)?;
            }
            if let Some(vals) = &node.values {
                for v in vals {
                    check_no_spatial_ops(v)?;
                }
            }
            for a in &node.args {
                check_no_spatial_ops(a)?;
            }
            Ok(())
        }
    }
}

// ============================================================================
// Compile path: model → ArrayCompiled.
// ============================================================================

impl ArrayCompiled {
    pub fn from_file(file: &EsmFile) -> Result<Self, CompileError> {
        let Some(models) = &file.models else {
            return Err(CompileError::InterpreterBuildError {
                details: "File has no models to simulate".to_string(),
            });
        };
        if models.len() != 1 {
            return Err(CompileError::InterpreterBuildError {
                details: "Array-op path currently only supports a single model file (no coupling)"
                    .to_string(),
            });
        }
        let (_model_name, model) = models.iter().next().unwrap();
        Self::from_model(model)
    }

    pub fn from_model(model: &Model) -> Result<Self, CompileError> {
        // Resolve `{ "from": <index set> }` range references (RFC
        // semiring-faq-unified-ir §5.2) into concrete `[lo, hi]` intervals
        // before any shape inference or rule building. Operates on an owned
        // clone so the caller's model — and its serialized form — is untouched;
        // every downstream consumer then sees only dense interval ranges.
        let mut model_owned = model.clone();
        // Resolve `join.on` value-equality clauses (RFC §5.3) FIRST, while each
        // aggregate range still carries its `{ "from": <index set> }` linkage so
        // the join key columns' member values can be read. A join whose key
        // columns resolve to the same loop symbol is the degenerate positional
        // no-op (byte-identical to the no-join form); a join over two distinct
        // loop symbols is the data-derived value-equality case and is lowered
        // into a member-equality `filter` over the contraction; a join over a
        // genuine (non-loop) data column is rejected rather than mis-combined.
        crate::join::resolve_aggregate_joins(&mut model_owned)?;
        // Then rewrite every `{ "from": <index set> }` range reference (§5.2)
        // into a concrete `[lo, hi]` interval before shape inference / rule
        // building, so every downstream consumer sees only dense intervals.
        resolve_aggregate_ranges(&mut model_owned)?;
        let model = &model_owned;

        // (0) Reject spatial differential operators anywhere in the model's
        // equations or observed-variable expressions — the canonical
        // pipeline contract requires `grad`/`div`/`laplacian` to be
        // rewritten by ESD discretization before reaching the simulator
        // (esm-i7b).
        for eq in &model.equations {
            check_no_spatial_ops(&eq.lhs)?;
            check_no_spatial_ops(&eq.rhs)?;
        }
        for var in model.variables.values() {
            if let Some(expr) = &var.expression {
                check_no_spatial_ops(expr)?;
            }
        }

        // (1) Collect state / parameter / observed variables.
        let mut state_vars: Vec<&String> = Vec::new();
        let mut param_vars: Vec<&String> = Vec::new();
        let mut observed_vars: Vec<(&String, &ModelVariable)> = Vec::new();

        let mut var_keys: Vec<&String> = model.variables.keys().collect();
        var_keys.sort();
        for name in var_keys {
            let var = &model.variables[name];
            match var.var_type {
                VariableType::State => state_vars.push(name),
                VariableType::Parameter => param_vars.push(name),
                VariableType::Observed => observed_vars.push((name, var)),
                VariableType::Brownian => {
                    return Err(CompileError::UnsupportedFeatureError {
                        feature: "brownian".to_string(),
                        message: format!(
                            "Rust simulation backend does not support SDE (brownian) models; variable '{name}' is brownian"
                        ),
                    });
                }
            }
        }

        // (2) Infer shapes for state variables from all equation usages.
        let shape_map = infer_shapes(&state_vars, &model.equations)?;

        // (3) Partition state variables: those with D equations stay as
        //     states, those defined only by algebraic arrayop equations
        //     migrate to observed.
        let derivative_targets = collect_derivative_targets(&model.equations);

        let mut final_states: Vec<String> = Vec::new();
        let mut eliminated: HashSet<String> = HashSet::new();
        for name in &state_vars {
            if derivative_targets.contains(*name) {
                final_states.push((*name).clone());
            } else {
                // No D equation — this is algebraic.
                eliminated.insert((*name).clone());
            }
        }

        // (4) Build flat offset and scalar-slot names per state variable.
        let mut var_shapes: IndexMap<String, VarShape> = IndexMap::new();
        let mut scalar_state_names: Vec<String> = Vec::new();
        let mut scalar_state_index: HashMap<String, usize> = HashMap::new();
        let mut state_defaults: Vec<Option<f64>> = Vec::new();
        let mut flat_offset: usize = 0;

        for name in &final_states {
            let shape = shape_map.get(name).cloned().unwrap_or_default();
            let origin: Vec<i64> = if shape.is_empty() {
                Vec::new()
            } else {
                vec![1i64; shape.len()]
            };
            let default = model.variables.get(name).and_then(|v| v.default);
            let total = shape.iter().copied().product::<usize>().max(1);
            if shape.is_empty() {
                scalar_state_names.push(name.clone());
                scalar_state_index.insert(name.clone(), flat_offset);
                state_defaults.push(default);
            } else {
                // Generate per-element names in column-major order.
                for flat in 0..total {
                    let multi = flat_to_multi_col_major(flat, &shape);
                    let idx_str = multi
                        .iter()
                        .zip(origin.iter())
                        .map(|(v, o)| (v + *o as usize).to_string())
                        .collect::<Vec<_>>()
                        .join(",");
                    let slot_name = format!("{name}[{idx_str}]");
                    scalar_state_names.push(slot_name.clone());
                    scalar_state_index.insert(slot_name, flat_offset + flat);
                    state_defaults.push(default);
                }
            }
            var_shapes.insert(
                name.clone(),
                VarShape {
                    shape,
                    origin,
                    flat_offset,
                },
            );
            flat_offset += total;
        }

        let n_states = flat_offset;

        // (5) Build the param tables.
        let param_names: Vec<String> = param_vars.iter().map(|s| (*s).clone()).collect();
        let param_index: HashMap<String, usize> = param_names
            .iter()
            .enumerate()
            .map(|(i, n)| (n.clone(), i))
            .collect();
        let param_defaults: Vec<Option<f64>> = param_vars
            .iter()
            .map(|n| model.variables.get(*n).and_then(|v| v.default))
            .collect();

        // (6) Build observed algebraic rules from eliminated variables AND
        //     from declared observed variables that define an expression.
        let mut observed_rules: Vec<AlgebraicRule> = Vec::new();
        let mut observed_shapes: HashMap<String, VarShape> = HashMap::new();

        // Declared observed variables with an `expression` field.
        for (name, var) in &observed_vars {
            if let Some(expr) = &var.expression {
                observed_rules.push(AlgebraicRule::Scalar {
                    var: (*name).clone(),
                    body: Box::new(expr.clone()),
                });
                observed_shapes.insert(
                    (*name).clone(),
                    VarShape {
                        shape: Vec::new(),
                        origin: Vec::new(),
                        flat_offset: 0,
                    },
                );
            }
        }

        // Algebraic arrayop equations for eliminated state variables.
        for eq in &model.equations {
            if let Some((var, idx_names, ranges, body)) =
                extract_algebraic_arrayop(&eq.lhs, &eq.rhs)
                && eliminated.contains(&var)
            {
                // Infer the shape from ranges.
                let shape: Vec<usize> = ranges
                    .iter()
                    .map(|(lo, hi)| (hi - lo + 1) as usize)
                    .collect();
                let origin: Vec<i64> = ranges.iter().map(|(lo, _)| *lo).collect();
                observed_shapes.insert(
                    var.clone(),
                    VarShape {
                        shape: shape.clone(),
                        origin,
                        flat_offset: 0,
                    },
                );
                observed_rules.push(AlgebraicRule::ArrayLoop {
                    var,
                    output_idx_names: idx_names,
                    output_ranges: ranges,
                    body: Box::new(body),
                });
                continue;
            }
            // Also handle scalar algebraic: `var = rhs` (plain Variable LHS).
            if let Expr::Variable(name) = &eq.lhs
                && eliminated.contains(name)
            {
                observed_rules.push(AlgebraicRule::Scalar {
                    var: name.clone(),
                    body: Box::new(eq.rhs.clone()),
                });
                observed_shapes.insert(
                    name.clone(),
                    VarShape {
                        shape: Vec::new(),
                        origin: Vec::new(),
                        flat_offset: 0,
                    },
                );
            }
        }

        // (7) Build RHS rules. Each equation with a derivative LHS produces
        //     either a scalar slot write, an indexed scalar slot write, or
        //     an array loop.
        let mut rhs_rules: Vec<RhsRule> = Vec::new();
        let mut covered_slots: HashSet<usize> = HashSet::new();

        for eq in &model.equations {
            if let Some((
                var,
                idx_names,
                ranges,
                lhs_idx_exprs,
                body,
                contract_names,
                contract_dims,
                reduce,
                filter,
            )) = extract_derivative_arrayop(&eq.lhs, &eq.rhs)
            {
                // Array-op derivative over (idx_names, ranges).
                if !var_shapes.contains_key(&var) {
                    return Err(CompileError::InterpreterBuildError {
                        details: format!(
                            "Array-op derivative targets unknown state variable '{var}'"
                        ),
                    });
                }
                // Mark the covered slots.
                let shape = &var_shapes[&var];
                for tuple in cartesian_range(&ranges) {
                    // Map to column-major flat offset using actual LHS index expressions.
                    let binds: HashMap<String, i64> = idx_names
                        .iter()
                        .zip(tuple.iter())
                        .map(|(n, v)| (n.clone(), *v))
                        .collect();
                    let actual_multi: Vec<i64> = lhs_idx_exprs
                        .iter()
                        .map(|e| eval_simple_index(e, &binds))
                        .collect();
                    let flat = multi_to_flat_col_major(&actual_multi, &shape.shape, &shape.origin);
                    covered_slots.insert(shape.flat_offset + flat);
                }
                rhs_rules.push(RhsRule::ArrayLoop {
                    var_name: var,
                    output_idx_names: idx_names,
                    output_ranges: ranges,
                    lhs_idx_exprs,
                    body: Box::new(body),
                    contract_names,
                    contract_dims,
                    reduce,
                    filter,
                });
                continue;
            }
            // Scalar D(var, t) = rhs.
            if let Some((var, idx_opt)) = extract_derivative_scalar(&eq.lhs) {
                if let Some(indices) = idx_opt {
                    // Indexed: find slot.
                    let shape = var_shapes.get(&var).ok_or_else(|| {
                        CompileError::InterpreterBuildError {
                            details: format!(
                                "Scalar derivative targets unknown state variable '{var}'"
                            ),
                        }
                    })?;
                    let flat = multi_to_flat_col_major(&indices, &shape.shape, &shape.origin);
                    let slot = shape.flat_offset + flat;
                    covered_slots.insert(slot);
                    rhs_rules.push(RhsRule::IndexedScalar {
                        slot,
                        body: Box::new(eq.rhs.clone()),
                    });
                    continue;
                } else {
                    // Plain scalar D(var, t) = rhs.
                    let shape = var_shapes.get(&var).ok_or_else(|| {
                        CompileError::InterpreterBuildError {
                            details: format!(
                                "Scalar derivative targets unknown state variable '{var}'"
                            ),
                        }
                    })?;
                    if !shape.shape.is_empty() {
                        return Err(CompileError::InterpreterBuildError {
                            details: format!(
                                "Scalar derivative for non-scalar variable '{var}' (shape {:?})",
                                shape.shape
                            ),
                        });
                    }
                    let slot = shape.flat_offset;
                    covered_slots.insert(slot);
                    rhs_rules.push(RhsRule::Scalar {
                        slot,
                        body: Box::new(eq.rhs.clone()),
                    });
                    continue;
                }
            }
            // Otherwise: algebraic equation (or something we don't support).
            // If the LHS is algebraic for an eliminated variable it was
            // already consumed above; ignore here.
        }

        // (8) Every state slot must have a defining equation.
        for (i, name) in scalar_state_names.iter().enumerate() {
            if !covered_slots.contains(&i) {
                return Err(CompileError::InterpreterBuildError {
                    details: format!("State slot '{name}' has no defining derivative equation."),
                });
            }
        }

        Ok(ArrayCompiled {
            var_shapes,
            scalar_state_names,
            scalar_state_index,
            state_defaults,
            param_names,
            param_index,
            param_defaults,
            observed_rules,
            observed_shapes,
            rhs_rules,
            n_states,
        })
    }

    pub fn state_variable_names(&self) -> &[String] {
        &self.scalar_state_names
    }
    pub fn parameter_names(&self) -> &[String] {
        &self.param_names
    }

    /// Run the simulation.
    pub fn simulate(
        &self,
        tspan: (f64, f64),
        params: &HashMap<String, f64>,
        initial_conditions: &HashMap<String, f64>,
        opts: &SimulateOptions,
    ) -> Result<Solution, SimulateError> {
        let (t0, t_end) = tspan;
        let n_states = self.n_states;
        let n_params = self.param_names.len();

        // Validate param names and build the param vec.
        for key in params.keys() {
            if !self.param_index.contains_key(key) {
                return Err(SimulateError::InvalidParameter { name: key.clone() });
            }
        }
        let mut param_vec = vec![0.0f64; n_params];
        for (i, name) in self.param_names.iter().enumerate() {
            if let Some(&v) = params.get(name) {
                param_vec[i] = v;
            } else if let Some(d) = self.param_defaults[i] {
                param_vec[i] = d;
            } else {
                return Err(SimulateError::InvalidParameter { name: name.clone() });
            }
        }

        // Validate IC names and build the initial state vector.
        for key in initial_conditions.keys() {
            if !self.scalar_state_index.contains_key(key) {
                return Err(SimulateError::InvalidInitialCondition { name: key.clone() });
            }
        }
        let mut ic_vec = vec![0.0f64; n_states];
        for (i, name) in self.scalar_state_names.iter().enumerate() {
            if let Some(&v) = initial_conditions.get(name) {
                ic_vec[i] = v;
            } else if let Some(d) = self.state_defaults[i] {
                ic_vec[i] = d;
            } else {
                return Err(SimulateError::InvalidInitialCondition { name: name.clone() });
            }
        }

        let rhs_rules = self.rhs_rules.clone();
        let observed_rules = self.observed_rules.clone();
        let observed_shapes = self.observed_shapes.clone();
        let var_shapes = self.var_shapes.clone();
        let param_names = self.param_names.clone();

        let rhs_rules_jac = rhs_rules.clone();
        let observed_rules_jac = observed_rules.clone();
        let observed_shapes_jac = observed_shapes.clone();
        let var_shapes_jac = var_shapes.clone();
        let param_names_jac = param_names.clone();

        let rhs_closure = move |y: &diffsol::FaerVec<f64>,
                                p: &diffsol::FaerVec<f64>,
                                t: f64,
                                dy: &mut diffsol::FaerVec<f64>| {
            let y_s = y.as_slice();
            let p_s = p.as_slice();
            let dy_s = dy.as_mut_slice();
            for slot in dy_s.iter_mut() {
                *slot = 0.0;
            }
            evaluate_rhs(
                &rhs_rules,
                &observed_rules,
                &observed_shapes,
                &var_shapes,
                &param_names,
                y_s,
                p_s,
                t,
                dy_s,
            );
        };

        let jac_closure = move |y: &diffsol::FaerVec<f64>,
                                p: &diffsol::FaerVec<f64>,
                                t: f64,
                                v: &diffsol::FaerVec<f64>,
                                jv: &mut diffsol::FaerVec<f64>| {
            let n = y.as_slice().len();
            let v_s = v.as_slice();
            let p_s = p.as_slice();
            let y_s = y.as_slice();
            let mut y_norm = 0.0f64;
            for &yi in y_s {
                y_norm += yi * yi;
            }
            let y_norm = y_norm.sqrt().max(1.0);
            let eps = f64::EPSILON.sqrt() * y_norm;

            let mut y_perturbed = vec![0.0f64; n];
            for i in 0..n {
                y_perturbed[i] = y_s[i] + eps * v_s[i];
            }

            let mut f_y = vec![0.0f64; n];
            let mut f_yp = vec![0.0f64; n];
            evaluate_rhs(
                &rhs_rules_jac,
                &observed_rules_jac,
                &observed_shapes_jac,
                &var_shapes_jac,
                &param_names_jac,
                y_s,
                p_s,
                t,
                &mut f_y,
            );
            evaluate_rhs(
                &rhs_rules_jac,
                &observed_rules_jac,
                &observed_shapes_jac,
                &var_shapes_jac,
                &param_names_jac,
                &y_perturbed,
                p_s,
                t,
                &mut f_yp,
            );
            let jv_s = jv.as_mut_slice();
            for i in 0..n {
                jv_s[i] = (f_yp[i] - f_y[i]) / eps;
            }
        };

        let abstol = opts.abstol;
        let reltol = opts.reltol;
        let ic_for_init = ic_vec.clone();

        let builder = OdeBuilder::<FaerMat<f64>>::new()
            .t0(t0)
            .rtol(reltol)
            .atol(vec![abstol; n_states])
            .p(param_vec.clone())
            .rhs_implicit(rhs_closure, jac_closure)
            .init(
                move |_p: &diffsol::FaerVec<f64>, _t: f64, y: &mut diffsol::FaerVec<f64>| {
                    let y_s = y.as_mut_slice();
                    for (i, &v) in ic_for_init.iter().enumerate() {
                        y_s[i] = v;
                    }
                },
                n_states,
            );

        let problem = builder.build().map_err(|e| SimulateError::DiffsolError {
            details: e.to_string(),
        })?;

        let solver_name = match opts.solver {
            SolverChoice::Bdf => "Bdf",
            SolverChoice::Sdirk => "Sdirk",
            SolverChoice::Erk => "Erk",
        };

        let (time, state) = match opts.solver {
            SolverChoice::Bdf => {
                let mut solver: Bdf<'_, _, NewtonNonlinearSolver<_, FaerLU<f64>, _>> = problem
                    .bdf::<FaerLU<f64>>()
                    .map_err(|e| SimulateError::DiffsolError {
                        details: e.to_string(),
                    })?;
                run_solver(&mut solver, t_end, opts)?
            }
            SolverChoice::Sdirk => {
                let mut solver: Sdirk<'_, _, FaerLU<f64>> = problem
                    .tr_bdf2::<FaerLU<f64>>()
                    .map_err(|e| SimulateError::DiffsolError {
                        details: e.to_string(),
                    })?;
                run_solver(&mut solver, t_end, opts)?
            }
            SolverChoice::Erk => {
                let mut solver = problem.tsit45().map_err(|e| SimulateError::DiffsolError {
                    details: e.to_string(),
                })?;
                run_solver(&mut solver, t_end, opts)?
            }
        };

        Ok(Solution {
            time,
            state,
            state_variable_names: self.scalar_state_names.clone(),
            metadata: SolutionMetadata {
                solver: solver_name.to_string(),
                ..Default::default()
            },
        })
    }
}

// ============================================================================
// Runtime: evaluate one RHS call.
// ============================================================================

fn evaluate_rhs(
    rhs_rules: &[RhsRule],
    observed_rules: &[AlgebraicRule],
    observed_shapes: &HashMap<String, VarShape>,
    var_shapes: &IndexMap<String, VarShape>,
    param_names: &[String],
    state: &[f64],
    params: &[f64],
    t: f64,
    dy: &mut [f64],
) {
    // (a) Build state ndarray views (owned copies — fast enough at fixture
    //     sizes).
    let mut state_arrays: HashMap<String, ArrayD<f64>> = HashMap::new();
    for (name, vs) in var_shapes {
        let total = vs.shape.iter().copied().product::<usize>().max(1);
        let block = &state[vs.flat_offset..vs.flat_offset + total];
        if vs.shape.is_empty() {
            state_arrays.insert(name.clone(), ArrayD::from_elem(IxDyn(&[]), block[0]));
        } else {
            // The flat block is column-major over vs.shape.
            state_arrays.insert(name.clone(), col_major_to_arrayd(block, &vs.shape));
        }
    }

    // (b) Evaluate observed algebraic rules in order into observed_arrays.
    let mut observed_arrays: HashMap<String, ArrayD<f64>> = HashMap::new();
    for rule in observed_rules {
        match rule {
            AlgebraicRule::Scalar { var, body } => {
                let mut ctx = EvalCtx {
                    state_arrays: &state_arrays,
                    observed_arrays: &observed_arrays,
                    params,
                    param_names,
                    loop_binds: HashMap::new(),
                    t,
                };
                let v = eval(body, &mut ctx);
                let arr = ArrayD::from_elem(IxDyn(&[]), v.as_scalar().unwrap_or(f64::NAN));
                observed_arrays.insert(var.clone(), arr);
            }
            AlgebraicRule::ArrayLoop {
                var,
                output_idx_names,
                output_ranges,
                body,
            } => {
                // Size the storage as 1-based (origin 1) with max_index
                // extent per dimension so downstream `index(v, k)` always
                // computes offset `k - 1` regardless of the range's lo.
                // Positions below the defined range are left at 0.
                let padded_shape: Vec<usize> =
                    output_ranges.iter().map(|(_, hi)| *hi as usize).collect();
                let padded_origin: Vec<i64> = vec![1i64; padded_shape.len()];
                let total = padded_shape.iter().copied().product::<usize>().max(1);
                let mut buf = vec![0.0f64; total];
                for tuple in cartesian_range(output_ranges) {
                    let mut ctx = EvalCtx {
                        state_arrays: &state_arrays,
                        observed_arrays: &observed_arrays,
                        params,
                        param_names,
                        loop_binds: HashMap::new(),
                        t,
                    };
                    for (name, val) in output_idx_names.iter().zip(tuple.iter()) {
                        ctx.loop_binds.insert(name.clone(), *val);
                    }
                    let v = eval(body, &mut ctx).as_scalar().unwrap_or(f64::NAN);
                    let flat = multi_to_flat_col_major(&tuple, &padded_shape, &padded_origin);
                    if flat < buf.len() {
                        buf[flat] = v;
                    }
                }
                let arr = col_major_to_arrayd(&buf, &padded_shape);
                observed_arrays.insert(var.clone(), arr);
            }
        }
    }

    // Emit observed shapes we need for downstream variable lookups.
    let _ = observed_shapes; // kept for future consistency checks

    // (c) Evaluate each RHS rule and write into dy.
    for rule in rhs_rules {
        match rule {
            RhsRule::Scalar { slot, body } => {
                let mut ctx = EvalCtx {
                    state_arrays: &state_arrays,
                    observed_arrays: &observed_arrays,
                    params,
                    param_names,
                    loop_binds: HashMap::new(),
                    t,
                };
                let v = eval(body, &mut ctx).as_scalar().unwrap_or(f64::NAN);
                dy[*slot] = v;
            }
            RhsRule::IndexedScalar { slot, body } => {
                let mut ctx = EvalCtx {
                    state_arrays: &state_arrays,
                    observed_arrays: &observed_arrays,
                    params,
                    param_names,
                    loop_binds: HashMap::new(),
                    t,
                };
                let v = eval(body, &mut ctx).as_scalar().unwrap_or(f64::NAN);
                dy[*slot] = v;
            }
            RhsRule::ArrayLoop {
                var_name,
                output_idx_names,
                output_ranges,
                lhs_idx_exprs,
                body,
                contract_names,
                contract_dims,
                reduce,
                filter,
            } => {
                let vs = &var_shapes[var_name];
                let filter = filter.as_deref();
                for tuple in cartesian_range(output_ranges) {
                    let mut ctx = EvalCtx {
                        state_arrays: &state_arrays,
                        observed_arrays: &observed_arrays,
                        params,
                        param_names,
                        loop_binds: HashMap::new(),
                        t,
                    };
                    for (name, val) in output_idx_names.iter().zip(tuple.iter()) {
                        ctx.loop_binds.insert(name.clone(), *val);
                    }
                    // Generalized einsum: contracted indices (incl. ragged
                    // per-cell dynamic bounds) are unrolled and ⊕-combined here.
                    let v = reduce_contraction(
                        contract_names,
                        contract_dims,
                        body,
                        *reduce,
                        filter,
                        &mut ctx,
                    );
                    let actual_multi: Vec<i64> = lhs_idx_exprs
                        .iter()
                        .map(|e| eval_simple_index(e, &ctx.loop_binds))
                        .collect();
                    let flat = multi_to_flat_col_major(&actual_multi, &vs.shape, &vs.origin);
                    dy[vs.flat_offset + flat] = v;
                }
            }
        }
    }
}

// ============================================================================
// Interpreter.
// ============================================================================

struct EvalCtx<'a> {
    state_arrays: &'a HashMap<String, ArrayD<f64>>,
    observed_arrays: &'a HashMap<String, ArrayD<f64>>,
    params: &'a [f64],
    param_names: &'a [String],
    loop_binds: HashMap<String, i64>,
    t: f64,
}

fn eval(expr: &Expr, ctx: &mut EvalCtx) -> Value {
    match expr {
        Expr::Number(n) => Value::Scalar(*n),
        Expr::Integer(n) => Value::Scalar(*n as f64),
        Expr::Variable(name) => lookup_variable(name, ctx),
        Expr::Operator(node) => eval_op(node, ctx),
    }
}

fn lookup_variable(name: &str, ctx: &EvalCtx) -> Value {
    if name == "t" {
        return Value::Scalar(ctx.t);
    }
    if let Some(v) = ctx.loop_binds.get(name) {
        return Value::Scalar(*v as f64);
    }
    if let Some(a) = ctx.state_arrays.get(name) {
        return if a.ndim() == 0 {
            Value::Scalar(a[IxDyn(&[])])
        } else {
            Value::Array(a.clone())
        };
    }
    if let Some(a) = ctx.observed_arrays.get(name) {
        return if a.ndim() == 0 {
            Value::Scalar(a[IxDyn(&[])])
        } else {
            Value::Array(a.clone())
        };
    }
    if let Some(i) = ctx.param_names.iter().position(|p| p == name) {
        return Value::Scalar(ctx.params[i]);
    }
    Value::Scalar(f64::NAN)
}

fn eval_op(node: &ExpressionNode, ctx: &mut EvalCtx) -> Value {
    match node.op.as_str() {
        // Elementwise / scalar arithmetic. If any operand is an array,
        // return an array (with ndarray broadcasting).
        "+" | "-" | "*" | "/" | "^" => eval_arith(&node.op, &node.args, ctx),

        // Unary / scalar transcendentals.
        "exp" | "log" | "ln" | "log10" | "sqrt" | "abs" | "sign" | "floor" | "ceil" | "sin"
        | "cos" | "tan" | "asin" | "acos" | "atan" | "sinh" | "cosh" | "tanh" => {
            eval_unary(&node.op, &node.args, ctx)
        }

        "atan2" => eval_binary(&node.op, &node.args, ctx),

        // n-ary min/max (esm-spec §4.2 — arity ≥ 2). Reuse the n-ary
        // arithmetic combiner so array operands broadcast through the same
        // ndarray path as `+`/`*`.
        "min" | "max" => eval_arith(&node.op, &node.args, ctx),

        // Scalar comparison operators — return 1.0 (true) or 0.0 (false).
        "==" | "!=" | "<" | "<=" | ">" | ">=" => {
            if node.args.len() != 2 {
                return Value::Scalar(f64::NAN);
            }
            let a = eval(&node.args[0], ctx).as_scalar().unwrap_or(f64::NAN);
            let b = eval(&node.args[1], ctx).as_scalar().unwrap_or(f64::NAN);
            Value::Scalar(match node.op.as_str() {
                "==" => {
                    if (a - b).abs() == 0.0 {
                        1.0
                    } else {
                        0.0
                    }
                }
                "!=" => {
                    if (a - b).abs() != 0.0 {
                        1.0
                    } else {
                        0.0
                    }
                }
                "<" => {
                    if a < b {
                        1.0
                    } else {
                        0.0
                    }
                }
                "<=" => {
                    if a <= b {
                        1.0
                    } else {
                        0.0
                    }
                }
                ">" => {
                    if a > b {
                        1.0
                    } else {
                        0.0
                    }
                }
                ">=" => {
                    if a >= b {
                        1.0
                    } else {
                        0.0
                    }
                }
                _ => f64::NAN,
            })
        }

        "ifelse" => {
            let c = eval(&node.args[0], ctx).as_scalar().unwrap_or(0.0);
            if c != 0.0 {
                eval(&node.args[1], ctx)
            } else {
                eval(&node.args[2], ctx)
            }
        }

        // Derivative operator: only meaningful on LHS. On RHS we treat
        // D(anything) = 0 for parity with the scalar interpreter.
        "D" => Value::Scalar(0.0),

        // Spatial differential operators must be rewritten by ESD
        // discretization rules before reaching the simulator (esm-i7b).
        // The compile-time `check_no_spatial_ops` walk in `from_model`
        // catches these; panicking here is defense-in-depth in case the
        // build path is bypassed.
        "grad" | "div" | "laplacian" => panic!(
            "UnreachableSpatialOperatorError: encountered '{}' node in simulation evaluation. \
             Spatial operators must be rewritten by ESD discretization rules before reaching \
             the simulator. Pipeline contract violated.",
            node.op
        ),

        "Pre" => eval(&node.args[0], ctx),

        // Array ops.
        "index" => eval_index(node, ctx),
        "arrayop" | "aggregate" => eval_arrayop(node, ctx),
        // Conservative-regridding geometry kernel (RFC §8.1): clip two lon/lat
        // polygon rings on the node's `manifold`, producing the overlap ring as
        // an `[N, 2]` array. `polygon_area` over it is an ordinary `aggregate`.
        "intersect_polygon" => eval_intersect_polygon(node, ctx),
        "makearray" => eval_makearray(node, ctx),
        "reshape" => eval_reshape(node, ctx),
        "transpose" => eval_transpose(node, ctx),
        "concat" => eval_concat(node, ctx),
        "broadcast" => eval_broadcast(node, ctx),

        _ => Value::Scalar(f64::NAN),
    }
}

fn eval_arith(op: &str, args: &[Expr], ctx: &mut EvalCtx) -> Value {
    let mut values: Vec<Value> = args.iter().map(|a| eval(a, ctx)).collect();

    // Unary minus: 1 arg.
    if op == "-" && values.len() == 1 {
        return negate(values.remove(0));
    }

    // Scalar fast path — if all operands are scalars, compute scalar.
    if values.iter().all(|v| matches!(v, Value::Scalar(_))) {
        let scalars: Vec<f64> = values
            .iter()
            .map(|v| match v {
                Value::Scalar(s) => *s,
                _ => unreachable!(),
            })
            .collect();
        return Value::Scalar(fold_scalar(op, &scalars));
    }

    // Array path: reduce left-to-right with broadcasting.
    let mut acc = values.remove(0);
    for v in values {
        acc = combine(op, acc, v);
    }
    acc
}

fn fold_scalar(op: &str, vs: &[f64]) -> f64 {
    match op {
        "+" => vs.iter().sum(),
        "*" => vs.iter().product(),
        "-" => {
            if vs.len() == 2 {
                vs[0] - vs[1]
            } else {
                f64::NAN
            }
        }
        "/" => {
            if vs.len() == 2 {
                vs[0] / vs[1]
            } else {
                f64::NAN
            }
        }
        "^" => {
            if vs.len() == 2 {
                vs[0].powf(vs[1])
            } else {
                f64::NAN
            }
        }
        "min" => {
            if vs.len() < 2 {
                f64::NAN
            } else {
                vs.iter().copied().fold(f64::INFINITY, f64::min)
            }
        }
        "max" => {
            if vs.len() < 2 {
                f64::NAN
            } else {
                vs.iter().copied().fold(f64::NEG_INFINITY, f64::max)
            }
        }
        _ => f64::NAN,
    }
}

fn negate(v: Value) -> Value {
    match v {
        Value::Scalar(s) => Value::Scalar(-s),
        Value::Array(a) => Value::Array(a.mapv(|x| -x)),
    }
}

fn combine(op: &str, a: Value, b: Value) -> Value {
    match (a, b) {
        (Value::Scalar(x), Value::Scalar(y)) => Value::Scalar(apply_binary(op, x, y)),
        (Value::Scalar(x), Value::Array(ya)) => Value::Array(ya.mapv(|y| apply_binary(op, x, y))),
        (Value::Array(xa), Value::Scalar(y)) => Value::Array(xa.mapv(|x| apply_binary(op, x, y))),
        (Value::Array(xa), Value::Array(ya)) => {
            // Use ndarray broadcasting.
            Value::Array(broadcast_binary(op, &xa, &ya))
        }
    }
}

fn apply_binary(op: &str, x: f64, y: f64) -> f64 {
    match op {
        "+" => x + y,
        "-" => x - y,
        "*" => x * y,
        "/" => x / y,
        "^" => x.powf(y),
        "atan2" => x.atan2(y),
        "min" => x.min(y),
        "max" => x.max(y),
        _ => f64::NAN,
    }
}

fn broadcast_binary(op: &str, a: &ArrayD<f64>, b: &ArrayD<f64>) -> ArrayD<f64> {
    // Julia-style left-align: pad the lower-rank operand with trailing
    // singletons before broadcasting.
    let max_rank = a.ndim().max(b.ndim());
    let a_padded = pad_trailing(a, max_rank);
    let b_padded = pad_trailing(b, max_rank);
    let target_shape = broadcast_shape(a_padded.shape(), b_padded.shape());
    let av = a_padded
        .broadcast(IxDyn(&target_shape))
        .expect("broadcast failed");
    let bv = b_padded
        .broadcast(IxDyn(&target_shape))
        .expect("broadcast failed");
    let mut out = ArrayD::<f64>::zeros(IxDyn(&target_shape));
    ndarray::Zip::from(&mut out)
        .and(&av)
        .and(&bv)
        .for_each(|o, &x, &y| {
            *o = apply_binary(op, x, y);
        });
    out
}

/// Julia-style broadcast shape alignment: pad the lower-rank shape with
/// *trailing* singleton dimensions so `(3,) + (1,3) → (3,3)`. This differs
/// from NumPy's right-alignment convention; the fixtures were authored in
/// Julia and expect this behavior (see
/// `fixtures/arrayop/14_broadcast_elementwise.esm`).
fn broadcast_shape(a: &[usize], b: &[usize]) -> Vec<usize> {
    let n = a.len().max(b.len());
    let mut out = vec![1usize; n];
    for i in 0..n {
        let ai = if i < a.len() { a[i] } else { 1 };
        let bi = if i < b.len() { b[i] } else { 1 };
        let dim = if ai == bi {
            ai
        } else if ai == 1 {
            bi
        } else if bi == 1 {
            ai
        } else {
            0
        };
        out[i] = dim;
    }
    out
}

/// Pad an ndarray with trailing singleton dimensions to reach `target_rank`.
fn pad_trailing(arr: &ArrayD<f64>, target_rank: usize) -> ArrayD<f64> {
    if arr.ndim() >= target_rank {
        return arr.clone();
    }
    let mut shape = arr.shape().to_vec();
    while shape.len() < target_rank {
        shape.push(1);
    }
    arr.clone()
        .into_shape_with_order(IxDyn(&shape))
        .expect("pad_trailing reshape")
}

fn eval_unary(op: &str, args: &[Expr], ctx: &mut EvalCtx) -> Value {
    let v = eval(&args[0], ctx);
    match v {
        Value::Scalar(s) => Value::Scalar(apply_unary(op, s)),
        Value::Array(a) => Value::Array(a.mapv(|x| apply_unary(op, x))),
    }
}

fn apply_unary(op: &str, x: f64) -> f64 {
    match op {
        "exp" => x.exp(),
        "log" | "ln" => x.ln(),
        "log10" => x.log10(),
        "sqrt" => x.sqrt(),
        "abs" => x.abs(),
        "sign" => {
            if x > 0.0 {
                1.0
            } else if x < 0.0 {
                -1.0
            } else {
                0.0
            }
        }
        "floor" => x.floor(),
        "ceil" => x.ceil(),
        "sin" => x.sin(),
        "cos" => x.cos(),
        "tan" => x.tan(),
        "asin" => x.asin(),
        "acos" => x.acos(),
        "atan" => x.atan(),
        "sinh" => x.sinh(),
        "cosh" => x.cosh(),
        "tanh" => x.tanh(),
        _ => f64::NAN,
    }
}

fn eval_binary(op: &str, args: &[Expr], ctx: &mut EvalCtx) -> Value {
    let a = eval(&args[0], ctx);
    let b = eval(&args[1], ctx);
    combine(op, a, b)
}

// --- Array ops ---

fn eval_index(node: &ExpressionNode, ctx: &mut EvalCtx) -> Value {
    // First arg is the array-valued expression; remaining args are indices.
    if node.args.is_empty() {
        return Value::Scalar(f64::NAN);
    }
    let array_val = eval(&node.args[0], ctx);
    let arr = match array_val {
        Value::Array(a) => a,
        Value::Scalar(s) if node.args.len() == 1 => return Value::Scalar(s),
        Value::Scalar(_) => return Value::Scalar(f64::NAN),
    };
    // Evaluate index expressions into integer indices (1-based).
    // Out-of-bounds accesses return 0.0 — this implements homogeneous Dirichlet
    // ghost-cell semantics: a discretized PDE's stencil can reference u[i-1]
    // when i=1 (ghost cell at i=0) and the boundary condition is u=0.
    let mut in_bounds = true;
    let indices: Vec<usize> = node.args[1..]
        .iter()
        .enumerate()
        .map(|(d, a)| {
            let v = eval(a, ctx);
            let one_based = match v.as_scalar() {
                Some(f) => f.round() as i64,
                None => {
                    in_bounds = false;
                    return 0;
                }
            };
            let dim_size = arr.shape().get(d).copied().unwrap_or(0) as i64;
            if one_based < 1 || one_based > dim_size {
                in_bounds = false;
            }
            (one_based - 1).max(0) as usize
        })
        .collect();
    if !in_bounds {
        return Value::Scalar(0.0);
    }
    if indices.len() != arr.ndim() {
        return Value::Scalar(f64::NAN);
    }
    let ix = IxDyn(&indices);
    if let Some(v) = arr.get(ix) {
        Value::Scalar(*v)
    } else {
        Value::Scalar(0.0)
    }
}

/// Evaluate the `intersect_polygon` leaf op (RFC `semiring-faq-unified-ir` §8.1):
/// clip the two polygon operands on the node's declared `manifold` and return
/// the overlap ring as an `[N, 2]` array of `(lon, lat)` rows. `N` is
/// data-dependent; a disjoint / edge-touching clip yields a `[0, 2]` array.
/// Spherical/geodesic clips dispatch to `s2geometry` via [`crate::geometry`];
/// planar clips use a pure-Rust Sutherland–Hodgman intersection.
fn eval_intersect_polygon(node: &ExpressionNode, ctx: &mut EvalCtx) -> Value {
    // Strict binary clip (schema-enforced; defense-in-depth here).
    if node.args.len() != 2 {
        return Value::Scalar(f64::NAN);
    }
    // The `manifold` flag is required and part of the op's contract (§5.8.4);
    // a missing or out-of-enum value is not evaluable.
    let manifold = match node
        .manifold
        .as_deref()
        .and_then(crate::geometry::Manifold::from_flag)
    {
        Some(m) => m,
        None => return Value::Scalar(f64::NAN),
    };
    let poly_a = match eval(&node.args[0], ctx) {
        Value::Array(a) => a,
        _ => return Value::Scalar(f64::NAN),
    };
    let poly_b = match eval(&node.args[1], ctx) {
        Value::Array(a) => a,
        _ => return Value::Scalar(f64::NAN),
    };
    let (va, vb) = match (arrayd_to_lonlat(&poly_a), arrayd_to_lonlat(&poly_b)) {
        (Some(a), Some(b)) => (a, b),
        _ => return Value::Scalar(f64::NAN),
    };
    match crate::geometry::intersect_polygon(&va, &vb, manifold) {
        Ok(ring) => Value::Array(lonlat_to_arrayd(&ring)),
        // A degenerate input ring or unavailable backend surfaces as NaN, the
        // same not-a-value sentinel the evaluator uses for unevaluable nodes.
        Err(_) => Value::Scalar(f64::NAN),
    }
}

/// Read a `[V, 2]` lon/lat coordinate array into a `Vec<(lon, lat)>`. Returns
/// `None` unless the array is 2-D with a trailing coordinate axis of length 2.
fn arrayd_to_lonlat(arr: &ArrayD<f64>) -> Option<Vec<(f64, f64)>> {
    if arr.ndim() != 2 || arr.shape()[1] != 2 {
        return None;
    }
    let nv = arr.shape()[0];
    let mut out = Vec::with_capacity(nv);
    for v in 0..nv {
        out.push((arr[IxDyn(&[v, 0])], arr[IxDyn(&[v, 1])]));
    }
    Some(out)
}

/// Build a row-major `[N, 2]` lon/lat array from a ring of `(lon, lat)` pairs.
/// An empty ring yields a `[0, 2]` array so downstream `index(clip, v, c)` reads
/// return the 0 ghost value and a `sum_product` FAQ over the empty `clip_ring`
/// range reduces to the additive identity `0̄`.
fn lonlat_to_arrayd(ring: &[(f64, f64)]) -> ArrayD<f64> {
    let n = ring.len();
    let mut flat = Vec::with_capacity(n * 2);
    for &(lon, lat) in ring {
        flat.push(lon);
        flat.push(lat);
    }
    ArrayD::from_shape_vec(IxDyn(&[n, 2]), flat).expect("ring [N,2] shape is consistent")
}

/// Evaluate a standalone expression against a set of named array inputs, reusing
/// the array evaluator — in particular the M1 `aggregate` machinery in
/// [`eval_arrayop`]. This is the entry point for computing a `polygon_area`
/// `sum_product` FAQ over an `intersect_polygon` ring (RFC §8.1): supply the
/// clipped ring (and any companion arrays the integrand references) in `inputs`
/// with the aggregate's `clip_ring` range already resolved to a concrete
/// `[1, N]` interval, and the body is reduced exactly as any other `aggregate`.
///
/// Returns [`Value::Scalar`] for a scalar FAQ output (`output_idx: []`),
/// [`Value::Array`] otherwise.
pub fn eval_expression(
    expr: &Expr,
    inputs: &HashMap<String, ArrayD<f64>>,
    params: &[f64],
    param_names: &[String],
    t: f64,
) -> Value {
    let empty: HashMap<String, ArrayD<f64>> = HashMap::new();
    let mut ctx = EvalCtx {
        state_arrays: &empty,
        observed_arrays: inputs,
        params,
        param_names,
        loop_binds: HashMap::new(),
        t,
    };
    eval(expr, &mut ctx)
}

/// Evaluate an `aggregate`/`arrayop` `filter` predicate under the current loop
/// binds and report whether the combination is **excluded** (§5.3): excluded
/// iff a filter is present and evaluates to false (a zero scalar). With no
/// filter this is always `false`, so the reduction is byte-identical to the
/// no-filter form.
fn filter_excludes(filter: Option<&Expr>, ctx: &mut EvalCtx) -> bool {
    match filter {
        Some(f) => eval(f, ctx).as_scalar().unwrap_or(0.0) == 0.0,
        None => false,
    }
}

/// Evaluate one output cell's value: the pointwise body when there are no
/// contracted indices, otherwise the semiring ⊕-reduction of the body over the
/// Cartesian product of the contracted dims. Each dim is resolved to its
/// concrete bound *under the current output tuple*, so a [`ContractDim::Ragged`]
/// dim uses this cell's dynamic per-parent extent (an empty extent reduces to
/// the additive identity 0̄). `ctx.loop_binds` must already hold the output-index
/// tuple; the contracted indices are bound here. This is the single contraction
/// kernel shared by the standalone-aggregate ([`eval_arrayop`]) and compiled
/// array-op-derivative ([`RhsRule::ArrayLoop`]) paths, mirroring the Julia
/// `_expand_int_range_dyn` einsum loop and the Python `_expand_ragged` gather.
fn reduce_contraction(
    contract_names: &[String],
    contract_dims: &[ContractDim],
    body: &Expr,
    reduce: ReduceKind,
    filter: Option<&Expr>,
    ctx: &mut EvalCtx,
) -> f64 {
    if contract_names.is_empty() {
        // Pointwise: a filtered-out cell contributes the additive identity 0̄.
        return if filter_excludes(filter, ctx) {
            reduce.identity()
        } else {
            eval(body, ctx).as_scalar().unwrap_or(f64::NAN)
        };
    }
    // Resolve each contracted dim to a concrete (lo, hi) under the current
    // output tuple — ragged dims read their per-parent length here.
    let ranges: Vec<(i64, i64)> = contract_dims.iter().map(|d| d.concrete(ctx)).collect();
    let mut acc: f64 = reduce.identity();
    for k_tuple in cartesian_range(&ranges) {
        for (kn, kv) in contract_names.iter().zip(k_tuple.iter()) {
            ctx.loop_binds.insert(kn.clone(), *kv);
        }
        // A filtered-out combination contributes 0̄ (acc ⊕ 0̄ = acc) (§5.3).
        if filter_excludes(filter, ctx) {
            continue;
        }
        let term = eval(body, ctx).as_scalar().unwrap_or(f64::NAN);
        acc = reduce.combine(acc, term);
    }
    acc
}

/// Gather the ragged per-parent length `offsets[of…]` for the current output
/// tuple: read each parent index variable from `ctx.loop_binds`, address the
/// `offsets` factor array (1-based → 0-based), and round to an integer count.
/// A scalar/0-D `offsets` factor is a constant valence for every parent. A
/// missing/unbound parent, a rank mismatch, or an out-of-bounds gather yields
/// `0` — an empty reduction (the additive identity 0̄), matching the evaluator's
/// homogeneous-ghost convention for out-of-bounds reads.
fn ragged_upper_bound(offsets: &str, of: &[String], ctx: &EvalCtx) -> i64 {
    let arr = match lookup_variable(offsets, ctx) {
        Value::Scalar(s) => return s.round() as i64,
        Value::Array(a) => a,
    };
    if of.len() != arr.ndim() {
        return 0;
    }
    let mut idx = Vec::with_capacity(of.len());
    for p in of {
        match ctx.loop_binds.get(p) {
            Some(pv) if *pv >= 1 => idx.push((*pv - 1) as usize),
            _ => return 0,
        }
    }
    arr.get(IxDyn(&idx)).map(|v| v.round() as i64).unwrap_or(0)
}

fn eval_arrayop(node: &ExpressionNode, ctx: &mut EvalCtx) -> Value {
    // Standalone arrayop (embedded as an expression, not as the top-level
    // of an equation LHS/RHS). Build the output array by iterating
    // ranges, binding loop indices, evaluating the body.
    //
    // Supports generalized einsum: indices present in `ranges` but absent
    // from `output_idx` are contracted (summed/reduced) per `reduce`.
    let idx_names = node.output_idx.clone().unwrap_or_default();
    let ranges_map = node.ranges.clone().unwrap_or_default();
    let body = match &node.expr {
        Some(b) => b.as_ref().clone(),
        None => return Value::Scalar(f64::NAN),
    };
    let ranges: Vec<(i64, i64)> = idx_names
        .iter()
        .map(|n| {
            let r = ranges_map.get(n).and_then(|s| s.bounds()).unwrap_or([0, 0]);
            (r[0], r[1])
        })
        .collect();

    // Contracted indices: in ranges_map but not in output_idx.
    let output_idx_set: std::collections::HashSet<&String> = idx_names.iter().collect();
    let mut sorted_contract_keys: Vec<&String> = ranges_map
        .keys()
        .filter(|k| !output_idx_set.contains(k))
        .collect();
    sorted_contract_keys.sort();
    let contract_names: Vec<String> = sorted_contract_keys.iter().map(|k| (*k).clone()).collect();
    let contract_dims: Vec<ContractDim> = sorted_contract_keys
        .iter()
        .map(|k| ContractDim::from_range(&ranges_map[*k]))
        .collect();
    let reduce = effective_reduce_kind(node.semiring.as_deref(), node.reduce.as_deref());
    // §5.3 filter: a boolean predicate gating which index combinations
    // contribute a ⊗-term. Absent ⇒ every combination contributes (byte-
    // identical to the no-filter form).
    let filter = node.filter.as_deref();

    let shape: Vec<usize> = ranges
        .iter()
        .map(|(lo, hi)| (hi - lo + 1) as usize)
        .collect();
    let origin: Vec<i64> = ranges.iter().map(|(lo, _)| *lo).collect();
    let total = shape.iter().copied().product::<usize>().max(1);
    let mut buf = vec![0.0f64; total];
    let saved_binds: Vec<(String, Option<i64>)> = idx_names
        .iter()
        .chain(contract_names.iter())
        .map(|n| (n.clone(), ctx.loop_binds.get(n).copied()))
        .collect();
    for tuple in cartesian_range(&ranges) {
        for (name, val) in idx_names.iter().zip(tuple.iter()) {
            ctx.loop_binds.insert(name.clone(), *val);
        }
        let v = reduce_contraction(&contract_names, &contract_dims, &body, reduce, filter, ctx);
        let flat = multi_to_flat_col_major(&tuple, &shape, &origin);
        buf[flat] = v;
    }
    for (name, saved) in saved_binds {
        match saved {
            Some(v) => {
                ctx.loop_binds.insert(name, v);
            }
            None => {
                ctx.loop_binds.remove(&name);
            }
        }
    }
    if shape.is_empty() {
        Value::Scalar(buf[0])
    } else {
        Value::Array(col_major_to_arrayd(&buf, &shape))
    }
}

fn eval_makearray(node: &ExpressionNode, ctx: &mut EvalCtx) -> Value {
    let regions = node.regions.clone().unwrap_or_default();
    let values = node.values.clone().unwrap_or_default();
    if regions.is_empty() || values.len() != regions.len() {
        return Value::Scalar(f64::NAN);
    }
    // Compute the bounding box.
    let ndim = regions[0].len();
    let mut lo = vec![i64::MAX; ndim];
    let mut hi = vec![i64::MIN; ndim];
    for region in &regions {
        for (d, r) in region.iter().enumerate() {
            lo[d] = lo[d].min(r[0]);
            hi[d] = hi[d].max(r[1]);
        }
    }
    let shape: Vec<usize> = (0..ndim).map(|d| (hi[d] - lo[d] + 1) as usize).collect();
    let origin = lo.clone();
    let mut arr = ArrayD::<f64>::zeros(IxDyn(&shape));
    for (region, value_expr) in regions.iter().zip(values.iter()) {
        let v = eval(value_expr, ctx);
        // Iterate the region's index tuples.
        let ranges: Vec<(i64, i64)> = region.iter().map(|r| (r[0], r[1])).collect();
        for tuple in cartesian_range(&ranges) {
            let indices: Vec<usize> = tuple
                .iter()
                .enumerate()
                .map(|(d, x)| (x - origin[d]) as usize)
                .collect();
            let ix = IxDyn(&indices);
            let scalar = match &v {
                Value::Scalar(s) => *s,
                Value::Array(a) if a.ndim() == 0 => a[IxDyn(&[])],
                _ => continue,
            };
            arr[ix] = scalar;
        }
    }
    Value::Array(arr)
}

fn eval_reshape(node: &ExpressionNode, ctx: &mut EvalCtx) -> Value {
    let v = eval(&node.args[0], ctx);
    let arr = match v {
        Value::Array(a) => a,
        Value::Scalar(s) => ArrayD::from_elem(IxDyn(&[]), s),
    };
    let target: Vec<usize> = node
        .shape
        .clone()
        .unwrap_or_default()
        .iter()
        .map(|&d| d as usize)
        .collect();
    // Column-major reshape: flatten in column-major order, reinterpret
    // under the new shape in column-major order.
    let flat = arrayd_to_col_major(&arr);
    Value::Array(col_major_to_arrayd(&flat, &target))
}

fn eval_transpose(node: &ExpressionNode, ctx: &mut EvalCtx) -> Value {
    let v = eval(&node.args[0], ctx);
    let arr = match v {
        Value::Array(a) => a,
        Value::Scalar(s) => return Value::Scalar(s),
    };
    let perm: Vec<usize> = if let Some(p) = &node.perm {
        p.iter().map(|&x| x as usize).collect()
    } else {
        // Default: reverse axes.
        (0..arr.ndim()).rev().collect()
    };
    Value::Array(arr.permuted_axes(perm).as_standard_layout().into_owned())
}

fn eval_concat(node: &ExpressionNode, ctx: &mut EvalCtx) -> Value {
    let axis = node.axis.unwrap_or(0) as usize;
    let parts: Vec<ArrayD<f64>> = node
        .args
        .iter()
        .map(|a| match eval(a, ctx) {
            Value::Array(arr) => arr,
            Value::Scalar(s) => ArrayD::from_elem(IxDyn(&[1]), s),
        })
        .collect();
    let views: Vec<_> = parts.iter().map(|a| a.view()).collect();
    let joined = ndarray::concatenate(ndarray::Axis(axis), &views)
        .unwrap_or_else(|_| ArrayD::zeros(IxDyn(&[0])));
    Value::Array(joined)
}

fn eval_broadcast(node: &ExpressionNode, ctx: &mut EvalCtx) -> Value {
    let fn_name = node.broadcast_fn.clone().unwrap_or_else(|| "+".to_string());
    let vs: Vec<Value> = node.args.iter().map(|a| eval(a, ctx)).collect();
    if vs.is_empty() {
        return Value::Scalar(f64::NAN);
    }
    let mut acc = vs.into_iter();
    let first = acc.next().unwrap();
    let mut out = first;
    for next in acc {
        out = combine(&fn_name, out, next);
    }
    out
}

// ============================================================================
// Shape inference + LHS parsing helpers.
// ============================================================================

/// Collect every state variable that receives a `D(..., t) = ...` definition
/// somewhere in the equation list.
fn collect_derivative_targets(equations: &[crate::types::Equation]) -> HashSet<String> {
    let mut out = HashSet::new();
    for eq in equations {
        if let Some((name, _)) = extract_derivative_scalar(&eq.lhs) {
            out.insert(name);
        }
        if let Some((name, _, _, _, _, _, _, _, _)) = extract_derivative_arrayop(&eq.lhs, &eq.rhs) {
            out.insert(name);
        }
    }
    out
}

/// If `lhs` is `D(var, t)` or `D(index(var, i1, ...), t)`, return
/// `(var_name, Some(indices))` for the indexed form (with all concrete
/// integer indices), `(var_name, None)` for the plain form. `None` result
/// means this LHS is neither.
fn extract_derivative_scalar(lhs: &Expr) -> Option<(String, Option<Vec<i64>>)> {
    let Expr::Operator(node) = lhs else {
        return None;
    };
    if node.op != "D" {
        return None;
    }
    if node.args.len() != 1 {
        return None;
    }
    match &node.args[0] {
        Expr::Variable(name) => Some((name.clone(), None)),
        Expr::Operator(inner) if inner.op == "index" => {
            let name = match inner.args.first()? {
                Expr::Variable(v) => v.clone(),
                _ => return None,
            };
            let indices: Vec<i64> = inner
                .args
                .iter()
                .skip(1)
                .map(|a| match a {
                    Expr::Number(n) => Some(*n as i64),
                    Expr::Integer(n) => Some(*n),
                    _ => None,
                })
                .collect::<Option<Vec<_>>>()?;
            Some((name, Some(indices)))
        }
        _ => None,
    }
}

/// If `lhs` is `arrayop(expr=D(index(var, idx...)), ...)`, extract
/// `(var_name, output_idx_names, output_ranges, lhs_idx_exprs, rhs_body,
///  contract_names, contract_ranges, reduce)`.
/// `contract_names`/`contract_ranges` are indices present in the RHS ranges
/// but absent from `output_idx` (generalized-einsum contracted indices).
/// `reduce` is the semiring ⊕ resolved from the RHS node's `semiring`/`reduce`
/// (defaulting to `Sum` per the ESM spec).
fn extract_derivative_arrayop(
    lhs: &Expr,
    rhs: &Expr,
) -> Option<(
    String,
    Vec<String>,
    Vec<(i64, i64)>,
    Vec<Expr>,
    Expr,
    Vec<String>,
    Vec<ContractDim>,
    ReduceKind,
    Option<Box<Expr>>,
)> {
    let Expr::Operator(node) = lhs else {
        return None;
    };
    if !is_aggregate_op(&node.op) {
        return None;
    }
    let body = node.expr.as_ref()?.as_ref();
    let idx_names = node.output_idx.clone()?;
    let ranges_map = node.ranges.clone()?;
    // Body must be D(index(var, ...)).
    let Expr::Operator(d_node) = body else {
        return None;
    };
    if d_node.op != "D" {
        return None;
    }
    let Expr::Operator(inner) = d_node.args.first()? else {
        return None;
    };
    if inner.op != "index" {
        return None;
    }
    let var_name = match inner.args.first()? {
        Expr::Variable(v) => v.clone(),
        _ => return None,
    };
    let lhs_idx_exprs: Vec<Expr> = inner.args.iter().skip(1).cloned().collect();
    // Map idx_names → ranges in order.
    let ranges: Vec<(i64, i64)> = idx_names
        .iter()
        .map(|n| {
            let r = ranges_map.get(n).and_then(|s| s.bounds()).unwrap_or([0, 0]);
            (r[0], r[1])
        })
        .collect();
    // RHS body: assume rhs is also arrayop with body, or pass through as
    // scalar-valued expr that evaluates at each tuple.
    // Also extract contracted (reduction) indices and the semiring ⊕ reducer.
    let (rhs_body, contract_names, contract_dims, reduce, filter) = match rhs {
        Expr::Operator(rnode) if is_aggregate_op(&rnode.op) => {
            let b = rnode.expr.as_ref().map(|b| b.as_ref().clone())?;
            let rop = effective_reduce_kind(rnode.semiring.as_deref(), rnode.reduce.as_deref());
            let mut c_names: Vec<String> = Vec::new();
            let mut c_dims: Vec<ContractDim> = Vec::new();
            if let Some(rhs_ranges) = &rnode.ranges {
                let mut sorted_keys: Vec<&String> = rhs_ranges.keys().collect();
                sorted_keys.sort();
                for n in sorted_keys {
                    if !idx_names.contains(n) {
                        // A ragged contracted index keeps its dynamic bound; all
                        // others collapse to a static interval here.
                        c_names.push(n.clone());
                        c_dims.push(ContractDim::from_range(&rhs_ranges[n]));
                    }
                }
            }
            // §5.3 filter rides on the RHS aggregate; carry it into the rule so
            // the contraction gates on it (otherwise it would be silently lost).
            (b, c_names, c_dims, rop, rnode.filter.clone())
        }
        other => (other.clone(), Vec::new(), Vec::new(), ReduceKind::Sum, None),
    };
    Some((
        var_name,
        idx_names,
        ranges,
        lhs_idx_exprs,
        rhs_body,
        contract_names,
        contract_dims,
        reduce,
        filter,
    ))
}

/// Extract an algebraic `arrayop(expr=index(var, idx...)) = arrayop(...)`
/// definition. Matches fixtures 02 and 04 where an algebraic variable is
/// defined through an arrayop whose body is just `index(v, i...)`.
fn extract_algebraic_arrayop(
    lhs: &Expr,
    rhs: &Expr,
) -> Option<(String, Vec<String>, Vec<(i64, i64)>, Expr)> {
    let Expr::Operator(node) = lhs else {
        return None;
    };
    if !is_aggregate_op(&node.op) {
        return None;
    }
    let body = node.expr.as_ref()?.as_ref();
    let idx_names = node.output_idx.clone()?;
    let ranges_map = node.ranges.clone()?;
    // Body must be index(var, idx...) with idx symbols matching idx_names in order.
    let Expr::Operator(inner) = body else {
        return None;
    };
    if inner.op != "index" {
        return None;
    }
    let var_name = match inner.args.first()? {
        Expr::Variable(v) => v.clone(),
        _ => return None,
    };
    // Indices must be exactly the output_idx names in order (v1 constraint).
    let idx_args: Vec<&Expr> = inner.args.iter().skip(1).collect();
    if idx_args.len() != idx_names.len() {
        return None;
    }
    for (a, want) in idx_args.iter().zip(idx_names.iter()) {
        match a {
            Expr::Variable(v) if v == want => {}
            _ => return None,
        }
    }
    let ranges: Vec<(i64, i64)> = idx_names
        .iter()
        .map(|n| {
            let r = ranges_map.get(n).and_then(|s| s.bounds()).unwrap_or([0, 0]);
            (r[0], r[1])
        })
        .collect();
    let rhs_body = match rhs {
        Expr::Operator(rnode) if is_aggregate_op(&rnode.op) => {
            // This elementwise (non-contracting) fast path does not apply a
            // `filter`. Bail rather than silently drop it — a filtered
            // definition must be compiled by a path that honors §5.3.
            if rnode.filter.is_some() {
                return None;
            }
            rnode.expr.as_ref().map(|b| b.as_ref().clone())?
        }
        other => other.clone(),
    };
    Some((var_name, idx_names, ranges, rhs_body))
}

/// Shape inference: per state variable, infer its shape from every
/// `index(var, ...)` reference, `D(index(var, ...))` reference, and
/// `arrayop` over its elements. Returns a map var_name → shape (empty Vec
/// means scalar). Origins are assumed 1-based.
///
/// Two-pass design: LHS equations pin the authoritative state extent; RHS
/// index references (which may include stencil offsets like `i-1` or `i+1`)
/// are only used for variables not already shaped by the LHS. This prevents
/// neighbor references in PDE stencils from bloating the inferred shape.
fn infer_shapes(
    state_vars: &[&String],
    equations: &[crate::types::Equation],
) -> Result<HashMap<String, Vec<usize>>, CompileError> {
    let state_set: HashSet<&str> = state_vars.iter().map(|s| s.as_str()).collect();

    // Pass 1: LHS only — these are the authoritative (pinned) shapes.
    let mut per_var_min: HashMap<String, Vec<i64>> = HashMap::new();
    let mut per_var_max: HashMap<String, Vec<i64>> = HashMap::new();
    let mut seen_indexed: HashSet<String> = HashSet::new();
    let skip_none: HashSet<String> = HashSet::new();
    for eq in equations {
        walk_for_shapes(
            &eq.lhs,
            &state_set,
            &mut per_var_min,
            &mut per_var_max,
            &mut seen_indexed,
            &HashMap::new(),
            &skip_none,
        );
    }

    // Pass 2: RHS — skip variables already pinned by LHS to prevent stencil
    // offsets (e.g. index(u, i-1)) from expanding the state's extent.
    let lhs_pinned = seen_indexed.clone();
    for eq in equations {
        walk_for_shapes(
            &eq.rhs,
            &state_set,
            &mut per_var_min,
            &mut per_var_max,
            &mut seen_indexed,
            &HashMap::new(),
            &lhs_pinned,
        );
    }

    let mut out: HashMap<String, Vec<usize>> = HashMap::new();
    for name in state_vars {
        let name_s = (*name).clone();
        if !seen_indexed.contains(&name_s) {
            out.insert(name_s, Vec::new());
            continue;
        }
        let mins = per_var_min.get(&name_s).cloned().unwrap_or_default();
        let maxes = per_var_max.get(&name_s).cloned().unwrap_or_default();
        if mins.len() != maxes.len() {
            return Err(CompileError::InterpreterBuildError {
                details: format!("Inconsistent index rank for variable '{name_s}'"),
            });
        }
        let shape: Vec<usize> = mins
            .iter()
            .zip(maxes.iter())
            .map(|(lo, hi)| (hi - lo + 1).max(1) as usize)
            .collect();
        out.insert(name_s, shape);
    }
    Ok(out)
}

/// Walk an expression tree collecting per-variable index bounds for shape
/// inference. `skip_shape_update` lists variables whose shapes are already
/// pinned (by a prior LHS pass); their bounds are not updated here, though
/// they are still marked as seen.
fn walk_for_shapes(
    expr: &Expr,
    states: &HashSet<&str>,
    per_var_min: &mut HashMap<String, Vec<i64>>,
    per_var_max: &mut HashMap<String, Vec<i64>>,
    seen_indexed: &mut HashSet<String>,
    loop_ranges: &HashMap<String, (i64, i64)>,
    skip_shape_update: &HashSet<String>,
) {
    match expr {
        Expr::Number(_) | Expr::Integer(_) | Expr::Variable(_) => {}
        Expr::Operator(node) => {
            if node.op == "index" {
                if let Some(Expr::Variable(var)) = node.args.first()
                    && states.contains(var.as_str())
                {
                    seen_indexed.insert(var.clone());
                    if !skip_shape_update.contains(var) {
                        let mut dim_min: Vec<i64> = Vec::new();
                        let mut dim_max: Vec<i64> = Vec::new();
                        for idx_expr in node.args.iter().skip(1) {
                            let (lo, hi) = evaluate_index_range(idx_expr, loop_ranges);
                            dim_min.push(lo);
                            dim_max.push(hi);
                        }
                        let cur_min = per_var_min.entry(var.clone()).or_default();
                        let cur_max = per_var_max.entry(var.clone()).or_default();
                        if cur_min.len() < dim_min.len() {
                            cur_min.resize(dim_min.len(), i64::MAX);
                        }
                        if cur_max.len() < dim_max.len() {
                            cur_max.resize(dim_max.len(), i64::MIN);
                        }
                        for (d, v) in dim_min.iter().enumerate() {
                            cur_min[d] = cur_min[d].min(*v);
                        }
                        for (d, v) in dim_max.iter().enumerate() {
                            cur_max[d] = cur_max[d].max(*v);
                        }
                    }
                }
            }
            if is_aggregate_op(&node.op) {
                // Build loop range map from the arrayop's ranges. Ranges have
                // already been resolved to concrete intervals (RFC §5.2) by
                // `resolve_aggregate_ranges` at the top of `from_model`.
                let mut inner = loop_ranges.clone();
                if let Some(ranges) = &node.ranges {
                    for (k, v) in ranges {
                        if let Some(b) = v.bounds() {
                            inner.insert(k.clone(), (b[0], b[1]));
                        }
                    }
                }
                if let Some(inner_expr) = &node.expr {
                    walk_for_shapes(
                        inner_expr,
                        states,
                        per_var_min,
                        per_var_max,
                        seen_indexed,
                        &inner,
                        skip_shape_update,
                    );
                }
                for a in &node.args {
                    walk_for_shapes(
                        a,
                        states,
                        per_var_min,
                        per_var_max,
                        seen_indexed,
                        &inner,
                        skip_shape_update,
                    );
                }
                if let Some(vs) = &node.values {
                    for v in vs {
                        walk_for_shapes(
                            v,
                            states,
                            per_var_min,
                            per_var_max,
                            seen_indexed,
                            &inner,
                            skip_shape_update,
                        );
                    }
                }
                return;
            }
            if let Some(inner) = &node.expr {
                walk_for_shapes(
                    inner,
                    states,
                    per_var_min,
                    per_var_max,
                    seen_indexed,
                    loop_ranges,
                    skip_shape_update,
                );
            }
            if let Some(vs) = &node.values {
                for v in vs {
                    walk_for_shapes(
                        v,
                        states,
                        per_var_min,
                        per_var_max,
                        seen_indexed,
                        loop_ranges,
                        skip_shape_update,
                    );
                }
            }
            for a in &node.args {
                walk_for_shapes(
                    a,
                    states,
                    per_var_min,
                    per_var_max,
                    seen_indexed,
                    loop_ranges,
                    skip_shape_update,
                );
            }
        }
    }
}

/// Evaluate a simple index expression given concrete loop variable bindings.
/// Supports integer literals, bare variable lookups, and `a + b` / `a - b`.
fn eval_simple_index(expr: &Expr, binds: &HashMap<String, i64>) -> i64 {
    match expr {
        Expr::Integer(n) => *n,
        Expr::Number(n) => *n as i64,
        Expr::Variable(name) => binds.get(name).copied().unwrap_or(0),
        Expr::Operator(node) if (node.op == "+" || node.op == "-") && node.args.len() == 2 => {
            let a = eval_simple_index(&node.args[0], binds);
            let b = eval_simple_index(&node.args[1], binds);
            if node.op == "+" { a + b } else { a - b }
        }
        _ => 0,
    }
}

/// Evaluate the integer range of an index expression given the currently
/// active loop variable ranges. Supports: integer literals, a bare symbol
/// bound to a loop, and `(i + k)` / `(i - k)` / `(k + i)` arithmetic.
fn evaluate_index_range(expr: &Expr, loop_ranges: &HashMap<String, (i64, i64)>) -> (i64, i64) {
    match expr {
        Expr::Integer(n) => (*n, *n),
        Expr::Number(n) => {
            let v = *n as i64;
            (v, v)
        }
        Expr::Variable(name) => {
            if let Some((lo, hi)) = loop_ranges.get(name) {
                (*lo, *hi)
            } else {
                (0, 0)
            }
        }
        Expr::Operator(node) => match node.op.as_str() {
            "+" | "-" => {
                if node.args.len() != 2 {
                    return (0, 0);
                }
                let a = evaluate_index_range(&node.args[0], loop_ranges);
                let b = evaluate_index_range(&node.args[1], loop_ranges);
                if node.op == "+" {
                    (a.0 + b.0, a.1 + b.1)
                } else {
                    (a.0 - b.1, a.1 - b.0)
                }
            }
            _ => (0, 0),
        },
    }
}

// ============================================================================
// Layout helpers (column-major).
// ============================================================================

fn multi_to_flat_col_major(multi: &[i64], shape: &[usize], origin: &[i64]) -> usize {
    if shape.is_empty() {
        return 0;
    }
    let mut flat: usize = 0;
    let mut stride: usize = 1;
    for d in 0..shape.len() {
        let off = (multi[d] - origin[d]).max(0) as usize;
        flat += off * stride;
        stride *= shape[d];
    }
    flat
}

fn flat_to_multi_col_major(flat: usize, shape: &[usize]) -> Vec<usize> {
    let mut out = vec![0usize; shape.len()];
    let mut rem = flat;
    for d in 0..shape.len() {
        out[d] = rem % shape[d];
        rem /= shape[d];
    }
    out
}

/// Build a column-major ndarray from a flat slice. ndarray uses row-major
/// strides natively, so we construct via `from_shape_vec` with a reversed
/// shape and then `permuted_axes` to get the column-major view.
fn col_major_to_arrayd(flat: &[f64], shape: &[usize]) -> ArrayD<f64> {
    if shape.is_empty() {
        return ArrayD::from_elem(IxDyn(&[]), flat[0]);
    }
    // Build row-major array with reversed shape, then reverse axes. The
    // element order in `flat` is column-major, which equals row-major of
    // the reversed-shape array.
    let rev_shape: Vec<usize> = shape.iter().rev().copied().collect();
    let arr = ArrayD::from_shape_vec(IxDyn(&rev_shape), flat.to_vec())
        .expect("col_major_to_arrayd shape mismatch");
    let perm: Vec<usize> = (0..shape.len()).rev().collect();
    arr.permuted_axes(perm).as_standard_layout().into_owned()
}

/// Flatten an ndarray into column-major order.
fn arrayd_to_col_major(arr: &ArrayD<f64>) -> Vec<f64> {
    if arr.ndim() == 0 {
        return vec![arr[IxDyn(&[])]];
    }
    let shape: Vec<usize> = arr.shape().to_vec();
    let total: usize = shape.iter().product();
    let mut out = vec![0.0f64; total];
    for flat in 0..total {
        let multi = flat_to_multi_col_major(flat, &shape);
        out[flat] = arr[IxDyn(&multi)];
    }
    out
}

/// Generate every index tuple in the Cartesian product of the given
/// (lo, hi) inclusive ranges. Ordering is lexicographic on dim0 outermost.
fn cartesian_range(ranges: &[(i64, i64)]) -> Vec<Vec<i64>> {
    let mut out = vec![Vec::new()];
    for &(lo, hi) in ranges {
        let mut next: Vec<Vec<i64>> = Vec::new();
        for partial in &out {
            for v in lo..=hi {
                let mut p = partial.clone();
                p.push(v);
                next.push(p);
            }
        }
        out = next;
    }
    out
}

// ============================================================================
// Solver loop (duplicated from simulate.rs — small enough to inline).
// ============================================================================

fn run_solver<'a, S, Eqn>(
    solver: &mut S,
    t_end: f64,
    opts: &SimulateOptions,
) -> Result<(Vec<f64>, Vec<Vec<f64>>), SimulateError>
where
    S: OdeSolverMethod<'a, Eqn>,
    Eqn: diffsol::OdeEquations<T = f64, V = diffsol::FaerVec<f64>>,
    Eqn: 'a,
{
    use diffsol::OdeSolverStopReason;

    let t0 = solver.state().t;
    let n_states = solver.state().y.as_slice().len();
    let initial_state: Vec<f64> = solver.state().y.as_slice().to_vec();

    let mut times: Vec<f64> = Vec::new();
    let mut state_rows: Vec<Vec<f64>> = vec![Vec::new(); n_states];

    let push_state = |times: &mut Vec<f64>, state_rows: &mut [Vec<f64>], t: f64, y: &[f64]| {
        times.push(t);
        for (i, &v) in y.iter().enumerate() {
            state_rows[i].push(v);
        }
    };

    solver
        .set_stop_time(t_end)
        .map_err(|e| SimulateError::DiffsolError {
            details: e.to_string(),
        })?;

    let mut step_count: usize = 0;

    if let Some(t_eval) = &opts.output_times {
        let mut next_idx: usize = 0;
        while next_idx < t_eval.len() && t_eval[next_idx] <= t0 {
            push_state(
                &mut times,
                &mut state_rows,
                t_eval[next_idx],
                &initial_state,
            );
            next_idx += 1;
        }
        let mut t_prev = t0;
        loop {
            if next_idx >= t_eval.len() {
                break;
            }
            if step_count >= opts.max_steps {
                return Err(SimulateError::MaxStepsExceeded {
                    max_steps: opts.max_steps,
                });
            }
            let stop = solver.step().map_err(|e| SimulateError::DiffsolError {
                details: e.to_string(),
            })?;
            step_count += 1;
            let t_curr = solver.state().t;
            while next_idx < t_eval.len() && t_eval[next_idx] <= t_curr {
                let t = t_eval[next_idx];
                let y = solver
                    .interpolate(t)
                    .map_err(|e| SimulateError::DiffsolError {
                        details: e.to_string(),
                    })?;
                let y_s = y.as_slice();
                push_state(&mut times, &mut state_rows, t, y_s);
                next_idx += 1;
            }
            t_prev = t_curr;
            if matches!(stop, OdeSolverStopReason::TstopReached) {
                break;
            }
        }
        while next_idx < t_eval.len() {
            let t = t_eval[next_idx];
            let y = solver
                .interpolate(t)
                .map_err(|e| SimulateError::DiffsolError {
                    details: e.to_string(),
                })?;
            push_state(&mut times, &mut state_rows, t, y.as_slice());
            next_idx += 1;
        }
        let _ = t_prev;
    } else {
        push_state(&mut times, &mut state_rows, t0, &initial_state);
        loop {
            if step_count >= opts.max_steps {
                return Err(SimulateError::MaxStepsExceeded {
                    max_steps: opts.max_steps,
                });
            }
            let stop = solver.step().map_err(|e| SimulateError::DiffsolError {
                details: e.to_string(),
            })?;
            step_count += 1;
            let t_curr = solver.state().t;
            let y_owned: Vec<f64> = solver.state().y.as_slice().to_vec();
            push_state(&mut times, &mut state_rows, t_curr, &y_owned);
            if matches!(stop, OdeSolverStopReason::TstopReached) {
                break;
            }
        }
    }

    Ok((times, state_rows))
}

#[cfg(test)]
mod geometry_eval_tests {
    //! End-to-end evaluation of the M4 geometry kernel through the *real* array
    //! evaluator (bead ess-my4.4.11; RFC `semiring-faq-unified-ir` §8.1): the
    //! `intersect_polygon` leaf is dispatched by [`eval_op`] (spherical →
    //! s2geometry via the `s2bindings` crate, planar → Sutherland–Hodgman), and
    //! `polygon_area` is computed as an ordinary `sum_product` aggregate over the
    //! clipped ring, reduced by the M1 machinery in [`eval_arrayop`]. This is the
    //! Rust binding actually clipping and integrating, not just schema-validating.
    use super::*;
    use serde_json::json;

    /// Build an `[N, 2]` lon/lat array from a ring of `(lon, lat)` pairs.
    fn ring_array(ring: &[(f64, f64)]) -> ArrayD<f64> {
        let mut flat = Vec::with_capacity(ring.len() * 2);
        for &(lon, lat) in ring {
            flat.push(lon);
            flat.push(lat);
        }
        ArrayD::from_shape_vec(IxDyn(&[ring.len(), 2]), flat).unwrap()
    }

    /// Clip two polygons through the public evaluator path — `eval_expression`
    /// → [`eval_op`] → `intersect_polygon` arm — exactly as a model's observed
    /// `clip` variable would be evaluated. Returns the overlap ring vertices.
    fn clip_via_evaluator(
        src: &[(f64, f64)],
        tgt: &[(f64, f64)],
        manifold: &str,
    ) -> Vec<(f64, f64)> {
        let mut inputs = HashMap::new();
        inputs.insert("src_poly".to_string(), ring_array(src));
        inputs.insert("tgt_poly".to_string(), ring_array(tgt));
        let node: Expr = serde_json::from_value(json!({
            "op": "intersect_polygon",
            "id": "overlap_clip",
            "manifold": manifold,
            "args": ["src_poly", "tgt_poly"],
        }))
        .unwrap();
        match eval_expression(&node, &inputs, &[], &[], 0.0) {
            Value::Array(a) => arrayd_to_lonlat(&a).expect("[N,2] ring"),
            Value::Scalar(s) => panic!("intersect_polygon evaluated to scalar {s}"),
        }
    }

    /// `polygon_area` as an ordinary `sum_product` FAQ over a ring (planar
    /// shoelace), evaluated by the M1 aggregate machinery. The integrand is the
    /// signed cross term `½·(xᵥ·yᵥ₊₁ − xᵥ₊₁·yᵥ)` summed over ring edges; the ring
    /// and its one-vertex rotation are supplied as arrays so the contracted `v`
    /// loop needs no wrap-around indexing. Returns the unsigned area.
    fn shoelace_area_faq(ring: &[(f64, f64)]) -> f64 {
        let n = ring.len();
        if n < 3 {
            return 0.0;
        }
        let next: Vec<(f64, f64)> = (0..n).map(|i| ring[(i + 1) % n]).collect();
        let mut inputs = HashMap::new();
        inputs.insert("clip".to_string(), ring_array(ring));
        inputs.insert("clip_next".to_string(), ring_array(&next));
        let agg: Expr = serde_json::from_value(json!({
            "op": "aggregate",
            "args": [],
            "semiring": "sum_product",
            "output_idx": [],
            "ranges": { "v": [1, n] },
            "expr": {
                "op": "*",
                "args": [
                    0.5,
                    { "op": "-", "args": [
                        { "op": "*", "args": [
                            { "op": "index", "args": ["clip", "v", 1] },
                            { "op": "index", "args": ["clip_next", "v", 2] }
                        ]},
                        { "op": "*", "args": [
                            { "op": "index", "args": ["clip_next", "v", 1] },
                            { "op": "index", "args": ["clip", "v", 2] }
                        ]}
                    ]}
                ]
            }
        }))
        .unwrap();
        match eval_expression(&agg, &inputs, &[], &[], 0.0) {
            Value::Scalar(s) => s.abs(),
            Value::Array(_) => panic!("scalar polygon_area FAQ expected"),
        }
    }

    #[test]
    fn planar_clip_then_polygon_area_faq_is_exact() {
        // [0,2]² ∩ [1,3]² = [1,2]², area 1. Clip through the evaluator, then take
        // `polygon_area` as a sum_product FAQ over the clipped ring.
        let src = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)];
        let tgt = [(1.0, 1.0), (3.0, 1.0), (3.0, 3.0), (1.0, 3.0)];
        let ring = clip_via_evaluator(&src, &tgt, "planar");
        assert!(ring.len() >= 3, "expected a non-degenerate overlap ring");
        let area = shoelace_area_faq(&ring);
        assert!(
            (area - 1.0).abs() < 1e-9,
            "polygon_area FAQ = {area}, expected 1"
        );
        // The FAQ agrees with the closed-form shoelace oracle.
        assert!((area - crate::geometry::shoelace_area(&ring)).abs() < 1e-12);
    }

    #[test]
    fn planar_clip_of_offset_triangles_area_faq() {
        // A non-rectangular case so the FAQ is exercised on a general ring.
        let src = [(0.0, 0.0), (4.0, 0.0), (0.0, 4.0)];
        let tgt = [(0.0, 0.0), (4.0, 0.0), (4.0, 4.0)];
        let ring = clip_via_evaluator(&src, &tgt, "planar");
        let area = shoelace_area_faq(&ring);
        // Overlap is the triangle (0,0),(4,0),(2,2): area = ½·base·height = 4.
        assert!(
            (area - 4.0).abs() < 1e-9,
            "polygon_area FAQ = {area}, expected 4"
        );
    }

    #[test]
    fn spherical_clip_via_s2_is_nonempty_with_analytic_area() {
        // Two quarter-hemisphere sectors; the s2 clip overlap is π/4 steradians.
        let src = [(0.0, 0.0), (90.0, 0.0), (0.0, 90.0)];
        let tgt = [(45.0, 0.0), (135.0, 0.0), (45.0, 90.0)];
        let ring = clip_via_evaluator(&src, &tgt, "spherical");
        assert!(ring.len() >= 3, "the s2 spherical clip should be non-empty");
        let area = crate::geometry::spherical_area(&ring).expect("spherical area");
        assert!(
            (area - std::f64::consts::FRAC_PI_4).abs() < 1e-9,
            "spherical overlap area = {area}, expected π/4"
        );
    }

    #[test]
    fn disjoint_clip_is_empty_ring_with_zero_area_faq() {
        let src = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)];
        let tgt = [(5.0, 5.0), (6.0, 5.0), (6.0, 6.0), (5.0, 6.0)];
        let ring = clip_via_evaluator(&src, &tgt, "planar");
        assert!(ring.is_empty(), "disjoint cells clip to an empty ring");
        // A sum_product FAQ over the empty clip_ring reduces to the additive 0̄.
        assert_eq!(shoelace_area_faq(&ring), 0.0);
    }

    #[test]
    fn intersect_polygon_without_manifold_is_unevaluable() {
        // `manifold` is required; absent, the node is not evaluable (NaN sentinel).
        let mut inputs = HashMap::new();
        inputs.insert(
            "src_poly".to_string(),
            ring_array(&[(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]),
        );
        inputs.insert(
            "tgt_poly".to_string(),
            ring_array(&[(1.0, 1.0), (3.0, 1.0), (3.0, 3.0), (1.0, 3.0)]),
        );
        let node: Expr = serde_json::from_value(json!({
            "op": "intersect_polygon",
            "args": ["src_poly", "tgt_poly"],
        }))
        .unwrap();
        match eval_expression(&node, &inputs, &[], &[], 0.0) {
            Value::Scalar(s) => assert!(s.is_nan(), "missing manifold should be NaN, got {s}"),
            Value::Array(_) => panic!("missing manifold must not produce a ring"),
        }
    }
}

#[cfg(test)]
mod ragged_eval_tests {
    //! Dynamic per-parent (ragged) contraction bounds in the array evaluator
    //! (bead ess-787; RFC `semiring-faq-unified-ir` §5.2). A `RangeSpec::RaggedDyn`
    //! contracted index reads its per-parent length `offsets[of…]` from a factor
    //! array at eval time, so each output cell reduces over its own dynamic
    //! extent — mirroring the Julia `_expand_int_range_dyn` einsum loop and the
    //! Python `_expand_ragged` reference (`test_ragged_index_set_dynamic_per_parent_bound`).
    use super::*;
    use serde_json::json;

    /// Build the standalone aggregate `out[i] = ⊕_{k∈edges(i)} k` with `k`'s
    /// range resolved to a ragged bound over the `nedges` factor. A file never
    /// authors a `RaggedDyn` range (the resolver produces it), so we parse the
    /// node and inject the resolved range directly.
    fn ragged_sum_node() -> Expr {
        let mut agg: Expr = serde_json::from_value(json!({
            "op": "aggregate",
            "args": [],
            "semiring": "sum_product",
            "output_idx": ["i"],
            "expr": "k",
            "ranges": { "i": [1, 2], "k": [1, 1] }
        }))
        .unwrap();
        if let Expr::Operator(node) = &mut agg {
            node.ranges.as_mut().unwrap().insert(
                "k".to_string(),
                RangeSpec::RaggedDyn {
                    offsets: "nedges".into(),
                    of: vec!["i".into()],
                },
            );
        }
        agg
    }

    fn nedges(values: &[f64]) -> HashMap<String, ArrayD<f64>> {
        HashMap::from([(
            "nedges".to_string(),
            ArrayD::from_shape_vec(IxDyn(&[values.len()]), values.to_vec()).unwrap(),
        )])
    }

    /// `nedges = [2, 3]` ⇒ `out = [1+2, 1+2+3] = [3, 6]` — the per-parent bound
    /// is read fresh for each output cell.
    #[test]
    fn ragged_contraction_uses_per_parent_dynamic_bound() {
        match eval_expression(&ragged_sum_node(), &nedges(&[2.0, 3.0]), &[], &[], 0.0) {
            Value::Array(a) => {
                assert_eq!(a.shape(), [2]);
                assert_eq!(a[IxDyn(&[0])], 3.0);
                assert_eq!(a[IxDyn(&[1])], 6.0);
            }
            Value::Scalar(s) => panic!("expected a [3, 6] array, got scalar {s}"),
        }
    }

    /// An isolated parent (zero-length ragged segment) reduces to the semiring's
    /// additive identity 0̄: `nedges = [0, 2]` ⇒ `out = [0, 1+2] = [0, 3]`.
    #[test]
    fn ragged_empty_segment_yields_additive_identity() {
        match eval_expression(&ragged_sum_node(), &nedges(&[0.0, 2.0]), &[], &[], 0.0) {
            Value::Array(a) => {
                assert_eq!(a[IxDyn(&[0])], 0.0);
                assert_eq!(a[IxDyn(&[1])], 3.0);
            }
            Value::Scalar(s) => panic!("expected a [0, 3] array, got scalar {s}"),
        }
    }
}
