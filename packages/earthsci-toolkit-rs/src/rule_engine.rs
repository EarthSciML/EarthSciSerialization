//! Rule engine per discretization RFC §5.2.
//!
//! Pattern-match rewriting over the ESM expression AST with typed pattern
//! variables, guards, non-linear matching (via canonical equality), and a
//! top-down fixed-point loop with per-pass sealing of rewritten subtrees.
//!
//! The MVP supports only the inline `replacement` form; `use:<scheme>`
//! (RFC §7.2.1) is deferred to Step 1b.
//!
//! See `docs/rfcs/discretization.md` §5.2 for the normative rules.
//!
//! Design note: this implementation mirrors the Julia reference in
//! `packages/EarthSciSerialization.jl/src/rule_engine.jl`. Each rewrite
//! pass walks top-down; the first rule whose pattern matches and whose
//! guards pass fires, and the rewritten subtree is sealed (the walker
//! does not descend into it for the remainder of the current pass). A
//! pass that produces no rewrites terminates the loop; if `max_passes`
//! is reached the engine aborts with `E_RULES_NOT_CONVERGED`.

use crate::canonicalize::canonical_json;
use crate::types::{Expr, ExpressionNode};
use std::collections::HashMap;

// ============================================================================
// Error type
// ============================================================================

/// Errors raised by the rule engine.
///
/// `code()` returns one of the RFC stable error codes:
/// - `E_RULES_NOT_CONVERGED` (§5.2.5)
/// - `E_UNREWRITTEN_PDE_OP` (§11 Step 7)
/// - `E_SCHEME_MISMATCH` (§7.2.1; reserved for the deferred `use:` form)
/// - `E_UNKNOWN_GUARD`, `E_PATTERN_VAR_UNBOUND`, `E_PATTERN_VAR_TYPE`,
///   `E_RULE_PARSE`, `E_RULE_REPLACEMENT_MISSING` (implementation-level).
#[derive(Debug, Clone, PartialEq)]
pub struct RuleEngineError {
    pub code: String,
    pub message: String,
}

impl RuleEngineError {
    pub fn new(code: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            code: code.into(),
            message: message.into(),
        }
    }
    pub fn code(&self) -> &str {
        &self.code
    }
}

impl std::fmt::Display for RuleEngineError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "RuleEngineError({}): {}", self.code, self.message)
    }
}

impl std::error::Error for RuleEngineError {}

// ============================================================================
// Guard
// ============================================================================

/// A single constraint on pattern-variable bindings (RFC §5.2.4).
///
/// `name` is one of the closed-set guard names; `params` carries the
/// fields from the JSON guard object (`pvar`, `grid`, `location`, …).
#[derive(Debug, Clone)]
pub struct Guard {
    pub name: String,
    pub params: HashMap<String, serde_json::Value>,
}

// ============================================================================
// Rule
// ============================================================================

/// Spatial scope of a rule (RFC §5.2.7). Absent when the rule applies
/// everywhere its pattern matches, a legacy advisory [`RuleRegion::Tag`]
/// string with no runtime effect, or a concrete per-query-point scope.
#[derive(Debug, Clone)]
pub enum RuleRegion {
    /// Legacy advisory tag (no runtime effect). Pre-v0.3 authoring idiom.
    Tag(String),
    /// `{kind:"boundary", side}` — rule applies only on the named axis side.
    Boundary { side: String },
    /// `{kind:"panel_boundary", panel, side}` — cubed_sphere only.
    PanelBoundary { panel: i64, side: String },
    /// `{kind:"mask_field", field}` — rule applies where the named field is truthy.
    MaskField { field: String },
    /// `{kind:"index_range", axis, lo, hi}` — inclusive index-range scope.
    IndexRange { axis: String, lo: i64, hi: i64 },
}

/// A rewrite rule (RFC §5.2). MVP supports the inline `replacement`
/// form only; `use:<scheme>` is tracked as Step 1b follow-up.
///
/// `where_expr`, if present, is a per-query-point boolean predicate
/// AST (RFC §5.2.7) — mutually exclusive with the guard-list `where_`
/// at the author level, structurally distinguished by JSON shape at
/// parse time.
#[derive(Debug, Clone)]
pub struct Rule {
    pub name: String,
    pub pattern: Expr,
    pub where_: Vec<Guard>,
    pub replacement: Expr,
    pub region: Option<RuleRegion>,
    pub where_expr: Option<Expr>,
}

impl Rule {
    pub fn new(name: impl Into<String>, pattern: Expr, replacement: Expr) -> Self {
        Self {
            name: name.into(),
            pattern,
            where_: Vec::new(),
            replacement,
            region: None,
            where_expr: None,
        }
    }
}

// ============================================================================
// RuleContext
// ============================================================================

/// Context supplied to [`rewrite`] and guard evaluation (RFC §5.2.4).
///
/// - `grids`: per-grid metadata. Each entry may carry `spatial_dims`,
///   `periodic_dims`, `nonuniform_dims` as string vectors.
/// - `variables`: per-variable metadata. Each entry may carry `grid`
///   (string), `location` (string), `shape` (string vector).
#[derive(Debug, Clone, Default)]
pub struct RuleContext {
    pub grids: HashMap<String, GridMeta>,
    pub variables: HashMap<String, VariableMeta>,
    /// Per-query-point index bindings used to evaluate RFC §5.2.7
    /// region / where-expression scopes. Empty for ordinary tree
    /// rewriting (scope-bearing rules then fall through).
    pub query_point: HashMap<String, i64>,
    /// Name of the grid the `query_point` refers to (used to resolve
    /// `region.boundary.side` against `GridMeta::dim_bounds`).
    pub grid_name: Option<String>,
}

/// Subset of grid metadata consumed by the closed-set guards.
#[derive(Debug, Clone, Default)]
pub struct GridMeta {
    pub spatial_dims: Vec<String>,
    pub periodic_dims: Vec<String>,
    pub nonuniform_dims: Vec<String>,
    /// Optional per-dim `[lo, hi]` index bounds, used by
    /// `region.boundary` scope evaluation (RFC §5.2.7). Absence is
    /// equivalent to "scope disabled" (conservative fall-through).
    pub dim_bounds: HashMap<String, [i64; 2]>,
    /// Cubed-sphere panel connectivity tables (RFC §6.4). Present only
    /// on `cubed_sphere` grids; its presence is the runtime marker used
    /// by `region.panel_boundary` scope evaluation (RFC §5.2.7) to
    /// distinguish cubed-sphere from other grid families. Applying a
    /// `panel_boundary`-scoped rule to a grid without this field emits
    /// `E_REGION_GRID_MISMATCH`.
    pub panel_connectivity: Option<PanelConnectivity>,
}

/// Cubed-sphere panel-connectivity tables (RFC §6.4). `neighbors[p][s]`
/// gives the neighboring panel index at (panel `p`, side `s` ∈ {0:−i,
/// 1:+i, 2:−j, 3:+j}); `axis_flip[p][s]` encodes the D₄ group element
/// (§6.4.1) acting on local (Δi, Δj) displacements when crossing that
/// seam. Consumed by `region.panel_boundary` scope evaluation and,
/// downstream, by `regrid` with `method: "panel_seam"`.
#[derive(Debug, Clone, Default)]
pub struct PanelConnectivity {
    pub neighbors: Vec<Vec<i64>>,
    pub axis_flip: Vec<Vec<i64>>,
}

/// Subset of variable metadata consumed by the closed-set guards.
#[derive(Debug, Clone, Default)]
pub struct VariableMeta {
    pub grid: Option<String>,
    pub location: Option<String>,
    pub shape: Option<Vec<String>>,
}

// ============================================================================
// Pattern variable detection
// ============================================================================

fn is_pvar_string(s: &str) -> bool {
    s.len() >= 2 && s.starts_with('$')
}

// ============================================================================
// Match
// ============================================================================

/// Attempt to match `pattern` against `expr`. On success, returns a
/// substitution mapping each pattern-variable name (including the
/// leading `$`) to the bound [`Expr`]. Bare-name bindings (for sibling
/// fields like `wrt` or `dim`) are wrapped as `Expr::Variable` so the
/// substitution has a uniform type. On failure, returns `None`.
pub fn match_pattern(pattern: &Expr, expr: &Expr) -> Option<HashMap<String, Expr>> {
    match_inner(pattern, expr, HashMap::new())
}

fn match_inner(pat: &Expr, expr: &Expr, b: HashMap<String, Expr>) -> Option<HashMap<String, Expr>> {
    if let Expr::Variable(name) = pat
        && is_pvar_string(name)
    {
        return unify(name, expr.clone(), b);
    }
    match (pat, expr) {
        (Expr::Integer(pi), Expr::Integer(ei)) if pi == ei => Some(b),
        (Expr::Number(pf), Expr::Number(ef)) if pf == ef => Some(b),
        (Expr::Variable(pn), Expr::Variable(en)) if pn == en => Some(b),
        (Expr::Operator(pn), Expr::Operator(en)) => match_op(pn, en, b),
        _ => None,
    }
}

fn match_op(
    pat: &ExpressionNode,
    expr: &ExpressionNode,
    b: HashMap<String, Expr>,
) -> Option<HashMap<String, Expr>> {
    if pat.op != expr.op || pat.args.len() != expr.args.len() {
        return None;
    }
    let b = match_sibling_name(pat.wrt.as_deref(), expr.wrt.as_deref(), b)?;
    let b = match_sibling_name(pat.dim.as_deref(), expr.dim.as_deref(), b)?;
    let mut cur = b;
    for (pa, ea) in pat.args.iter().zip(expr.args.iter()) {
        cur = match_inner(pa, ea, cur)?;
    }
    Some(cur)
}

fn match_sibling_name(
    pat: Option<&str>,
    val: Option<&str>,
    b: HashMap<String, Expr>,
) -> Option<HashMap<String, Expr>> {
    match (pat, val) {
        (None, None) => Some(b),
        (None, Some(_)) | (Some(_), None) => None,
        (Some(p), Some(v)) => {
            if is_pvar_string(p) {
                unify(p, Expr::Variable(v.to_string()), b)
            } else if p == v {
                Some(b)
            } else {
                None
            }
        }
    }
}

fn unify(pvar: &str, candidate: Expr, b: HashMap<String, Expr>) -> Option<HashMap<String, Expr>> {
    if let Some(prev) = b.get(pvar) {
        // Non-linear: existing binding must match canonically.
        let prev_json = canonical_json(prev).ok()?;
        let new_json = canonical_json(&candidate).ok()?;
        if prev_json == new_json { Some(b) } else { None }
    } else {
        let mut nb = b;
        nb.insert(pvar.to_string(), candidate);
        Some(nb)
    }
}

// ============================================================================
// Apply bindings (build replacement AST)
// ============================================================================

/// Substitute pattern variables in `template` with their bound values.
///
/// Returns `Err(E_PATTERN_VAR_UNBOUND)` if `template` references a
/// pattern variable that is not in `bindings`.
pub fn apply_bindings(template: &Expr, b: &HashMap<String, Expr>) -> Result<Expr, RuleEngineError> {
    match template {
        Expr::Variable(name) if is_pvar_string(name) => b.get(name).cloned().ok_or_else(|| {
            RuleEngineError::new(
                "E_PATTERN_VAR_UNBOUND",
                format!("pattern variable {name} is not bound"),
            )
        }),
        Expr::Operator(node) => {
            let mut new_args = Vec::with_capacity(node.args.len());
            for a in &node.args {
                new_args.push(apply_bindings(a, b)?);
            }
            let new_wrt = apply_name_field(node.wrt.as_deref(), b)?;
            let new_dim = apply_name_field(node.dim.as_deref(), b)?;
            let mut out = node.clone();
            out.args = new_args;
            out.wrt = new_wrt;
            out.dim = new_dim;
            Ok(Expr::Operator(out))
        }
        other => Ok(other.clone()),
    }
}

fn apply_name_field(
    field: Option<&str>,
    b: &HashMap<String, Expr>,
) -> Result<Option<String>, RuleEngineError> {
    let Some(f) = field else { return Ok(None) };
    if is_pvar_string(f) {
        let val = b.get(f).ok_or_else(|| {
            RuleEngineError::new(
                "E_PATTERN_VAR_UNBOUND",
                format!("pattern variable {f} is not bound"),
            )
        })?;
        match val {
            Expr::Variable(s) => Ok(Some(s.clone())),
            _ => Err(RuleEngineError::new(
                "E_PATTERN_VAR_TYPE",
                format!("pattern variable {f} used in name-class field must bind a bare name"),
            )),
        }
    } else {
        Ok(Some(f.to_string()))
    }
}

// ============================================================================
// Guards (§5.2.4)
// ============================================================================

/// Evaluate `guards` left-to-right, threading bindings. A guard whose
/// pvar-valued `grid` field is unbound at entry binds it to the
/// variable's actual grid (§9.2.1 pattern). Returns the extended
/// bindings on success, `None` on failure.
pub fn check_guards(
    guards: &[Guard],
    bindings: &HashMap<String, Expr>,
    ctx: &RuleContext,
) -> Result<Option<HashMap<String, Expr>>, RuleEngineError> {
    let mut b = bindings.clone();
    for g in guards {
        match check_guard(g, &b, ctx)? {
            Some(nb) => b = nb,
            None => return Ok(None),
        }
    }
    Ok(Some(b))
}

/// Evaluate a single guard. Returns `Some(extended_bindings)` on match,
/// `None` on miss, or `Err` for unknown guards.
pub fn check_guard(
    g: &Guard,
    b: &HashMap<String, Expr>,
    ctx: &RuleContext,
) -> Result<Option<HashMap<String, Expr>>, RuleEngineError> {
    match g.name.as_str() {
        "var_has_grid" => Ok(guard_var_has_grid(g, b, ctx)),
        "dim_is_spatial_dim_of" => Ok(guard_dim_is_spatial_dim_of(g, b, ctx)),
        "dim_is_periodic" => Ok(guard_dim_is_periodic(g, b, ctx)),
        "dim_is_nonuniform" => Ok(guard_dim_is_nonuniform(g, b, ctx)),
        "var_location_is" => Ok(guard_var_location_is(g, b, ctx)),
        "var_shape_rank" => Ok(guard_var_shape_rank(g, b, ctx)),
        other => Err(RuleEngineError::new(
            "E_UNKNOWN_GUARD",
            format!("unknown guard: {other} (§5.2.4 closed set)"),
        )),
    }
}

fn resolve_name(b: &HashMap<String, Expr>, key: &str) -> Option<String> {
    match b.get(key)? {
        Expr::Variable(s) => Some(s.clone()),
        _ => None,
    }
}

fn param_str<'a>(g: &'a Guard, field: &str) -> Option<&'a str> {
    g.params.get(field).and_then(|v| v.as_str())
}

/// Resolve a guard field that may be a literal string or a pvar
/// reference. Returns `(resolved_value, pvar_name_if_unbound)`.
fn resolve_or_mark(
    g: &Guard,
    b: &HashMap<String, Expr>,
    field: &str,
) -> (Option<String>, Option<String>) {
    let Some(raw) = param_str(g, field) else {
        return (None, None);
    };
    if is_pvar_string(raw) {
        match b.get(raw) {
            Some(Expr::Variable(s)) => (Some(s.clone()), None),
            Some(_) => (None, None),
            None => (None, Some(raw.to_string())),
        }
    } else {
        (Some(raw.to_string()), None)
    }
}

fn bind_pvar_name(b: &HashMap<String, Expr>, pvar: &str, name: &str) -> HashMap<String, Expr> {
    let mut nb = b.clone();
    nb.insert(pvar.to_string(), Expr::Variable(name.to_string()));
    nb
}

fn guard_var_has_grid(
    g: &Guard,
    b: &HashMap<String, Expr>,
    ctx: &RuleContext,
) -> Option<HashMap<String, Expr>> {
    let pvar = param_str(g, "pvar")?;
    let var_name = resolve_name(b, pvar)?;
    let meta = ctx.variables.get(&var_name)?;
    let actual = meta.grid.as_deref()?;
    let (wanted, need_bind) = resolve_or_mark(g, b, "grid");
    if let Some(pname) = need_bind {
        return Some(bind_pvar_name(b, &pname, actual));
    }
    if wanted.as_deref() == Some(actual) {
        Some(b.clone())
    } else {
        None
    }
}

fn dim_from_pvar_or_literal(g: &Guard, b: &HashMap<String, Expr>) -> Option<String> {
    let pvar = param_str(g, "pvar")?;
    if is_pvar_string(pvar) {
        resolve_name(b, pvar)
    } else {
        Some(pvar.to_string())
    }
}

fn guard_dim_is_spatial_dim_of(
    g: &Guard,
    b: &HashMap<String, Expr>,
    ctx: &RuleContext,
) -> Option<HashMap<String, Expr>> {
    let dim_name = dim_from_pvar_or_literal(g, b)?;
    let (grid, _) = resolve_or_mark(g, b, "grid");
    let grid = grid?;
    let meta = ctx.grids.get(&grid)?;
    if meta.spatial_dims.iter().any(|d| d == &dim_name) {
        Some(b.clone())
    } else {
        None
    }
}

fn guard_dim_is_periodic(
    g: &Guard,
    b: &HashMap<String, Expr>,
    ctx: &RuleContext,
) -> Option<HashMap<String, Expr>> {
    let dim_name = dim_from_pvar_or_literal(g, b)?;
    let (grid, _) = resolve_or_mark(g, b, "grid");
    let grid = grid?;
    let meta = ctx.grids.get(&grid)?;
    if meta.periodic_dims.iter().any(|d| d == &dim_name) {
        Some(b.clone())
    } else {
        None
    }
}

fn guard_dim_is_nonuniform(
    g: &Guard,
    b: &HashMap<String, Expr>,
    ctx: &RuleContext,
) -> Option<HashMap<String, Expr>> {
    let dim_name = dim_from_pvar_or_literal(g, b)?;
    let (grid, _) = resolve_or_mark(g, b, "grid");
    let grid = grid?;
    let meta = ctx.grids.get(&grid)?;
    if meta.nonuniform_dims.iter().any(|d| d == &dim_name) {
        Some(b.clone())
    } else {
        None
    }
}

fn guard_var_location_is(
    g: &Guard,
    b: &HashMap<String, Expr>,
    ctx: &RuleContext,
) -> Option<HashMap<String, Expr>> {
    let pvar = param_str(g, "pvar")?;
    let var_name = resolve_name(b, pvar)?;
    let target = param_str(g, "location")?;
    let meta = ctx.variables.get(&var_name)?;
    if meta.location.as_deref() == Some(target) {
        Some(b.clone())
    } else {
        None
    }
}

fn guard_var_shape_rank(
    g: &Guard,
    b: &HashMap<String, Expr>,
    ctx: &RuleContext,
) -> Option<HashMap<String, Expr>> {
    let pvar = param_str(g, "pvar")?;
    let var_name = resolve_name(b, pvar)?;
    let want = g.params.get("rank").and_then(|v| v.as_u64())? as usize;
    let meta = ctx.variables.get(&var_name)?;
    let shape = meta.shape.as_ref()?;
    if shape.len() == want {
        Some(b.clone())
    } else {
        None
    }
}

// ============================================================================
// Rewriter (§5.2.5)
// ============================================================================

pub const DEFAULT_MAX_PASSES: usize = 32;

/// Run the rule engine on `expr` per RFC §5.2.5. Top-down walker, per-
/// pass sealing of rewritten subtrees, fixed-point loop bounded by
/// `max_passes`. On non-convergence returns `E_RULES_NOT_CONVERGED`.
pub fn rewrite(
    expr: &Expr,
    rules: &[Rule],
    ctx: &RuleContext,
    max_passes: usize,
) -> Result<Expr, RuleEngineError> {
    let mut current = expr.clone();
    for _ in 0..max_passes {
        let mut changed = false;
        current = rewrite_pass(&current, rules, ctx, &mut changed)?;
        if !changed {
            return Ok(current);
        }
    }
    Err(RuleEngineError::new(
        "E_RULES_NOT_CONVERGED",
        format!("rule engine did not converge within {max_passes} passes"),
    ))
}

fn rewrite_pass(
    expr: &Expr,
    rules: &[Rule],
    ctx: &RuleContext,
    changed: &mut bool,
) -> Result<Expr, RuleEngineError> {
    for rule in rules {
        if let Some(m) = match_pattern(&rule.pattern, expr)
            && let Some(m2) = check_guards(&rule.where_, &m, ctx)?
            && check_scope(rule, &m2, ctx)?
        {
            let new_expr = apply_bindings(&rule.replacement, &m2)?;
            *changed = true;
            return Ok(new_expr); // sealed: do not descend
        }
    }
    if let Expr::Operator(node) = expr {
        let mut new_args = Vec::with_capacity(node.args.len());
        for a in &node.args {
            new_args.push(rewrite_pass(a, rules, ctx, changed)?);
        }
        let mut out = node.clone();
        out.args = new_args;
        return Ok(Expr::Operator(out));
    }
    Ok(expr.clone())
}

// ============================================================================
// JSON parsing (rules and expressions)
// ============================================================================

/// Parse a `rules` section into an ordered vector. Accepts either the
/// JSON-object-keyed-by-name form or the array form (RFC §5.2.5).
pub fn parse_rules(value: &serde_json::Value) -> Result<Vec<Rule>, RuleEngineError> {
    if let Some(arr) = value.as_array() {
        return arr.iter().map(parse_rule_value).collect();
    }
    if let Some(obj) = value.as_object() {
        let mut out = Vec::with_capacity(obj.len());
        for (name, v) in obj {
            out.push(parse_rule_named(name, v)?);
        }
        return Ok(out);
    }
    Err(RuleEngineError::new(
        "E_RULE_PARSE",
        "`rules` must be an object or array".to_string(),
    ))
}

fn parse_rule_value(v: &serde_json::Value) -> Result<Rule, RuleEngineError> {
    let name = v
        .get("name")
        .and_then(|s| s.as_str())
        .ok_or_else(|| RuleEngineError::new("E_RULE_PARSE", "array-form rule missing `name`"))?;
    parse_rule_named(name, v)
}

fn parse_rule_named(name: &str, v: &serde_json::Value) -> Result<Rule, RuleEngineError> {
    let pattern = parse_expr(v.get("pattern").ok_or_else(|| {
        RuleEngineError::new("E_RULE_PARSE", format!("rule `{name}` missing `pattern`"))
    })?)?;
    let replacement = v.get("replacement").ok_or_else(|| {
        RuleEngineError::new(
            "E_RULE_REPLACEMENT_MISSING",
            format!(
                "rule `{name}`: MVP supports only the `replacement` form; \
                 `use:` rules are deferred"
            ),
        )
    })?;
    let replacement = parse_expr(replacement)?;
    let (where_, where_expr) = parse_where(name, v.get("where"))?;
    let region = parse_region(name, v.get("region"))?;
    Ok(Rule {
        name: name.to_string(),
        pattern,
        where_,
        replacement,
        region,
        where_expr,
    })
}

/// Discriminate the RFC §5.2.7 `where` forms by JSON shape: array of
/// guards (legacy, selection-time) vs expression-node object (new,
/// per-query-point predicate).
fn parse_where(
    name: &str,
    v: Option<&serde_json::Value>,
) -> Result<(Vec<Guard>, Option<Expr>), RuleEngineError> {
    let Some(v) = v else {
        return Ok((Vec::new(), None));
    };
    if let Some(arr) = v.as_array() {
        let guards = arr.iter().map(parse_guard).collect::<Result<Vec<_>, _>>()?;
        return Ok((guards, None));
    }
    if let Some(obj) = v.as_object() {
        if !obj.contains_key("op") {
            return Err(RuleEngineError::new(
                "E_RULE_PARSE",
                format!("rule `{name}`: `where` object must be an expression node with an `op` field"),
            ));
        }
        return Ok((Vec::new(), Some(parse_expr(v)?)));
    }
    Err(RuleEngineError::new(
        "E_RULE_PARSE",
        format!("rule `{name}`: `where` must be an array of guards or an expression object"),
    ))
}

/// Discriminate the RFC §5.2.7 `region` forms: a legacy advisory
/// string vs a scope object with a `kind` tag.
fn parse_region(
    name: &str,
    v: Option<&serde_json::Value>,
) -> Result<Option<RuleRegion>, RuleEngineError> {
    let Some(v) = v else {
        return Ok(None);
    };
    if let Some(s) = v.as_str() {
        return Ok(Some(RuleRegion::Tag(s.to_string())));
    }
    let obj = v.as_object().ok_or_else(|| {
        RuleEngineError::new(
            "E_RULE_PARSE",
            format!("rule `{name}`: `region` must be a string (legacy) or object (normative scope)"),
        )
    })?;
    let kind = obj.get("kind").and_then(|s| s.as_str()).ok_or_else(|| {
        RuleEngineError::new(
            "E_RULE_PARSE",
            format!("rule `{name}`: region object must carry a `kind` field"),
        )
    })?;
    let missing = |field: &str| {
        RuleEngineError::new(
            "E_RULE_PARSE",
            format!("rule `{name}`: region.{kind} requires `{field}`"),
        )
    };
    let str_field = |field: &str| -> Result<String, RuleEngineError> {
        obj.get(field)
            .and_then(|s| s.as_str())
            .map(|s| s.to_string())
            .ok_or_else(|| missing(field))
    };
    let int_field = |field: &str| -> Result<i64, RuleEngineError> {
        obj.get(field)
            .and_then(|s| s.as_i64())
            .ok_or_else(|| missing(field))
    };
    match kind {
        "boundary" => Ok(Some(RuleRegion::Boundary {
            side: str_field("side")?,
        })),
        "panel_boundary" => Ok(Some(RuleRegion::PanelBoundary {
            panel: int_field("panel")?,
            side: str_field("side")?,
        })),
        "mask_field" => Ok(Some(RuleRegion::MaskField {
            field: str_field("field")?,
        })),
        "index_range" => Ok(Some(RuleRegion::IndexRange {
            axis: str_field("axis")?,
            lo: int_field("lo")?,
            hi: int_field("hi")?,
        })),
        other => Err(RuleEngineError::new(
            "E_RULE_PARSE",
            format!(
                "rule `{name}`: unknown region.kind `{other}` \
                 (closed set: boundary, panel_boundary, mask_field, index_range)"
            ),
        )),
    }
}

fn parse_guard(v: &serde_json::Value) -> Result<Guard, RuleEngineError> {
    let obj = v
        .as_object()
        .ok_or_else(|| RuleEngineError::new("E_RULE_PARSE", "guard must be an object"))?;
    let name = obj
        .get("guard")
        .and_then(|s| s.as_str())
        .ok_or_else(|| RuleEngineError::new("E_RULE_PARSE", "guard object missing `guard` field"))?
        .to_string();
    let mut params = HashMap::new();
    for (k, val) in obj {
        if k == "guard" {
            continue;
        }
        params.insert(k.clone(), val.clone());
    }
    Ok(Guard { name, params })
}

/// Parse a JSON value into an [`Expr`], preserving int-vs-float per RFC §5.4.
pub fn parse_expr(v: &serde_json::Value) -> Result<Expr, RuleEngineError> {
    use serde_json::Value;
    match v {
        Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                // `serde_json::Number::as_i64` returns Some only for JSON
                // tokens without `.`, `e`, or `E` — matches RFC §5.4.1
                // integer grammar.
                Ok(Expr::Integer(i))
            } else if let Some(f) = n.as_f64() {
                Ok(Expr::Number(f))
            } else {
                Err(RuleEngineError::new(
                    "E_RULE_PARSE",
                    "number out of i64/f64 range",
                ))
            }
        }
        Value::String(s) => Ok(Expr::Variable(s.clone())),
        Value::Object(obj) => {
            let op = obj
                .get("op")
                .and_then(|x| x.as_str())
                .ok_or_else(|| RuleEngineError::new("E_RULE_PARSE", "operator node missing `op`"))?
                .to_string();
            let empty = Vec::new();
            let args_raw = obj.get("args").and_then(|a| a.as_array()).unwrap_or(&empty);
            let mut args = Vec::with_capacity(args_raw.len());
            for a in args_raw {
                args.push(parse_expr(a)?);
            }
            let wrt = obj
                .get("wrt")
                .and_then(|s| s.as_str())
                .map(|s| s.to_string());
            let dim = obj
                .get("dim")
                .and_then(|s| s.as_str())
                .map(|s| s.to_string());
            Ok(Expr::Operator(ExpressionNode {
                op,
                args,
                wrt,
                dim,
                ..Default::default()
            }))
        }
        _ => Err(RuleEngineError::new(
            "E_RULE_PARSE",
            format!("cannot parse expression of JSON type {v}"),
        )),
    }
}

// ============================================================================
// Scope evaluation — region object + where expression (RFC §5.2.7)
// ============================================================================

/// Evaluate a rule's per-query-point scope: `region` (when an object
/// variant) and `where_expr` (expression predicate). Returns `true`
/// when the rule should fire at the current query point, `false`
/// otherwise (conservative fall-through).
///
/// A legacy string `region` and a missing `where_expr` pass
/// unconditionally, preserving v0.2 semantics.
pub fn check_scope(
    rule: &Rule,
    bindings: &HashMap<String, Expr>,
    ctx: &RuleContext,
) -> Result<bool, RuleEngineError> {
    if let Some(region) = &rule.region
        && !eval_region(region, ctx)?
    {
        return Ok(false);
    }
    if let Some(where_expr) = &rule.where_expr
        && !eval_where_expr(where_expr, bindings, ctx)
    {
        return Ok(false);
    }
    Ok(true)
}

fn eval_region(region: &RuleRegion, ctx: &RuleContext) -> Result<bool, RuleEngineError> {
    match region {
        // Legacy advisory tag: no runtime effect.
        RuleRegion::Tag(_) => Ok(true),
        RuleRegion::IndexRange { axis, lo, hi } => Ok(match ctx.query_point.get(axis) {
            Some(v) => lo <= v && v <= hi,
            None => false,
        }),
        RuleRegion::Boundary { side } => Ok(eval_boundary(side, ctx)),
        RuleRegion::PanelBoundary { panel, side } => eval_panel_boundary(*panel, side, ctx),
        // Deferred — mask_field needs data_loaders plumbing (follow-up).
        RuleRegion::MaskField { .. } => Ok(false),
    }
}

/// Evaluate a `{kind:"panel_boundary", panel, side}` scope (RFC §5.2.7,
/// §6.4). Cubed-sphere only: presence of `GridMeta::panel_connectivity`
/// is the runtime marker for that family. Applying the scope to a grid
/// without it emits `E_REGION_GRID_MISMATCH`.
///
/// Canonical cubed-sphere query-point axes are `p`, `i`, `j` (§7 query-
/// point table). `side` names map to the panel-local axes:
/// `xmin`/`west` → `-i`, `xmax`/`east` → `+i`, `ymin`/`south` → `-j`,
/// `ymax`/`north` → `+j`. Edge detection uses `GridMeta::dim_bounds`;
/// absent bounds or an unrecognised `side` fall through (returns `Ok(false)`).
fn eval_panel_boundary(
    panel: i64,
    side: &str,
    ctx: &RuleContext,
) -> Result<bool, RuleEngineError> {
    let Some(grid_name) = &ctx.grid_name else {
        return Ok(false);
    };
    let Some(meta) = ctx.grids.get(grid_name) else {
        return Ok(false);
    };
    if meta.panel_connectivity.is_none() {
        return Err(RuleEngineError::new(
            "E_REGION_GRID_MISMATCH",
            format!(
                "rule region.panel_boundary applied to grid `{grid_name}` \
                 which has no panel_connectivity metadata (cubed_sphere-only scope)"
            ),
        ));
    }
    if ctx.query_point.is_empty() {
        return Ok(false);
    }
    let Some(p) = ctx.query_point.get("p") else {
        return Ok(false);
    };
    if *p != panel {
        return Ok(false);
    }
    let (axis, which_hi) = match side {
        "xmin" | "west" => ("i", false),
        "xmax" | "east" => ("i", true),
        "ymin" | "south" => ("j", false),
        "ymax" | "north" => ("j", true),
        _ => return Ok(false),
    };
    let Some(bounds) = meta.dim_bounds.get(axis) else {
        return Ok(false);
    };
    let Some(v) = ctx.query_point.get(axis) else {
        return Ok(false);
    };
    let target = if which_hi { bounds[1] } else { bounds[0] };
    Ok(*v == target)
}

fn eval_boundary(side: &str, ctx: &RuleContext) -> bool {
    let Some(grid_name) = &ctx.grid_name else {
        return false;
    };
    let Some(meta) = ctx.grids.get(grid_name) else {
        return false;
    };
    let (dim, which_hi) = match side {
        "xmin" | "west" => ("x", false),
        "xmax" | "east" => ("x", true),
        "ymin" | "south" => ("y", false),
        "ymax" | "north" => ("y", true),
        "zmin" | "bottom" => ("z", false),
        "zmax" | "top" => ("z", true),
        _ => return false,
    };
    let Some(bounds) = meta.dim_bounds.get(dim) else {
        return false;
    };
    let Some(idx_pos) = meta.spatial_dims.iter().position(|d| d == dim) else {
        return false;
    };
    let canonical = ["i", "j", "k", "l", "m"];
    if idx_pos >= canonical.len() {
        return false;
    }
    let idx_name = canonical[idx_pos];
    let Some(v) = ctx.query_point.get(idx_name) else {
        return false;
    };
    let target = if which_hi { bounds[1] } else { bounds[0] };
    *v == target
}

fn eval_where_expr(expr: &Expr, bindings: &HashMap<String, Expr>, ctx: &RuleContext) -> bool {
    if ctx.query_point.is_empty() {
        return false;
    }
    match eval_scalar(expr, bindings, ctx) {
        Some(ScalarValue::Bool(b)) => b,
        Some(ScalarValue::Int(i)) => i != 0,
        Some(ScalarValue::Float(f)) => f != 0.0,
        _ => false,
    }
}

#[derive(Debug, Clone, Copy)]
enum ScalarValue {
    Bool(bool),
    Int(i64),
    Float(f64),
}

impl ScalarValue {
    fn to_f64(self) -> f64 {
        match self {
            ScalarValue::Bool(b) => {
                if b {
                    1.0
                } else {
                    0.0
                }
            }
            ScalarValue::Int(i) => i as f64,
            ScalarValue::Float(f) => f,
        }
    }

    fn truthy(self) -> bool {
        match self {
            ScalarValue::Bool(b) => b,
            ScalarValue::Int(i) => i != 0,
            ScalarValue::Float(f) => f != 0.0,
        }
    }
}

fn eval_scalar(
    e: &Expr,
    b: &HashMap<String, Expr>,
    ctx: &RuleContext,
) -> Option<ScalarValue> {
    match e {
        Expr::Integer(i) => Some(ScalarValue::Int(*i)),
        Expr::Number(f) => Some(ScalarValue::Float(*f)),
        Expr::Variable(name) => {
            if is_pvar_string(name)
                && let Some(bound) = b.get(name)
            {
                return eval_scalar(bound, b, ctx);
            }
            ctx.query_point.get(name).map(|v| ScalarValue::Int(*v))
        }
        Expr::Operator(node) => eval_op(node, b, ctx),
    }
}

fn eval_op(
    node: &ExpressionNode,
    b: &HashMap<String, Expr>,
    ctx: &RuleContext,
) -> Option<ScalarValue> {
    let args: Option<Vec<ScalarValue>> =
        node.args.iter().map(|a| eval_scalar(a, b, ctx)).collect();
    match node.op.as_str() {
        "==" | "!=" | "<" | "<=" | ">" | ">=" => {
            let args = args?;
            if args.len() != 2 {
                return None;
            }
            let (l, r) = (args[0].to_f64(), args[1].to_f64());
            let b = match node.op.as_str() {
                "==" => l == r,
                "!=" => l != r,
                "<" => l < r,
                "<=" => l <= r,
                ">" => l > r,
                ">=" => l >= r,
                _ => unreachable!(),
            };
            Some(ScalarValue::Bool(b))
        }
        "+" => {
            let args = args?;
            let all_int = args.iter().all(|v| matches!(v, ScalarValue::Int(_)));
            if all_int {
                Some(ScalarValue::Int(
                    args.into_iter()
                        .map(|v| match v {
                            ScalarValue::Int(i) => i,
                            _ => unreachable!(),
                        })
                        .sum(),
                ))
            } else {
                Some(ScalarValue::Float(args.into_iter().map(|v| v.to_f64()).sum()))
            }
        }
        "-" => {
            let args = args?;
            if args.len() == 1 {
                return match args[0] {
                    ScalarValue::Int(i) => Some(ScalarValue::Int(-i)),
                    ScalarValue::Float(f) => Some(ScalarValue::Float(-f)),
                    ScalarValue::Bool(_) => None,
                };
            }
            if args.len() != 2 {
                return None;
            }
            let (l, r) = (args[0], args[1]);
            if let (ScalarValue::Int(li), ScalarValue::Int(ri)) = (l, r) {
                Some(ScalarValue::Int(li - ri))
            } else {
                Some(ScalarValue::Float(l.to_f64() - r.to_f64()))
            }
        }
        "*" => {
            let args = args?;
            let all_int = args.iter().all(|v| matches!(v, ScalarValue::Int(_)));
            if all_int {
                Some(ScalarValue::Int(
                    args.into_iter()
                        .map(|v| match v {
                            ScalarValue::Int(i) => i,
                            _ => unreachable!(),
                        })
                        .product(),
                ))
            } else {
                Some(ScalarValue::Float(args.into_iter().map(|v| v.to_f64()).product()))
            }
        }
        "and" => {
            let args = args?;
            Some(ScalarValue::Bool(args.iter().all(|v| v.truthy())))
        }
        "or" => {
            let args = args?;
            Some(ScalarValue::Bool(args.iter().any(|v| v.truthy())))
        }
        "not" => {
            let args = args?;
            if args.len() != 1 {
                return None;
            }
            Some(ScalarValue::Bool(!args[0].truthy()))
        }
        _ => None,
    }
}

// ============================================================================
// Unrewritten PDE op check (§11 Step 7)
// ============================================================================

const PDE_OPS: &[&str] = &["grad", "div", "laplacian", "D", "bc"];

/// Scan `expr` for leftover PDE ops after rewriting. Returns
/// `E_UNREWRITTEN_PDE_OP` if any are found.
pub fn check_unrewritten_pde_ops(expr: &Expr) -> Result<(), RuleEngineError> {
    if let Some(op) = find_pde_op(expr) {
        return Err(RuleEngineError::new(
            "E_UNREWRITTEN_PDE_OP",
            format!(
                "equation still contains PDE op '{op}' after rewrite; \
                 annotate the equation with 'passthrough: true' to opt out"
            ),
        ));
    }
    Ok(())
}

fn find_pde_op(e: &Expr) -> Option<&str> {
    if let Expr::Operator(node) = e {
        for op in PDE_OPS {
            if node.op == *op {
                return Some(op);
            }
        }
        for a in &node.args {
            if let Some(x) = find_pde_op(a) {
                return Some(x);
            }
        }
    }
    None
}

// ============================================================================
// Unit tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    fn op(name: &str, args: Vec<Expr>) -> Expr {
        Expr::Operator(ExpressionNode {
            op: name.to_string(),
            args,
            ..Default::default()
        })
    }

    fn op_with(name: &str, args: Vec<Expr>, wrt: Option<&str>, dim: Option<&str>) -> Expr {
        Expr::Operator(ExpressionNode {
            op: name.to_string(),
            args,
            wrt: wrt.map(|s| s.to_string()),
            dim: dim.map(|s| s.to_string()),
            ..Default::default()
        })
    }

    fn var(s: &str) -> Expr {
        Expr::Variable(s.to_string())
    }

    #[test]
    fn match_and_replace() {
        let rule = Rule::new(
            "add_zero",
            op("+", vec![var("$a"), Expr::Integer(0)]),
            var("$a"),
        );
        let seed = op("+", vec![var("x"), Expr::Integer(0)]);
        let out = rewrite(&seed, &[rule], &RuleContext::default(), 32).unwrap();
        assert_eq!(canonical_json(&out).unwrap(), "\"x\"");
    }

    #[test]
    fn non_linear_match() {
        let rule = Rule::new(
            "self_minus",
            op("-", vec![var("$a"), var("$a")]),
            Expr::Integer(0),
        );
        let yes = op("-", vec![var("x"), var("x")]);
        assert!(match_pattern(&rule.pattern, &yes).is_some());
        let no = op("-", vec![var("x"), var("y")]);
        assert!(match_pattern(&rule.pattern, &no).is_none());
    }

    #[test]
    fn sibling_field_pvar() {
        let pat = op_with("D", vec![var("$u")], Some("$x"), None);
        let repl = op("index", vec![var("$u"), var("$x")]);
        let rule = Rule::new("d_to_index", pat, repl);
        let seed = op_with("D", vec![var("T")], Some("t"), None);
        let out = rewrite(&seed, &[rule], &RuleContext::default(), 32).unwrap();
        assert_eq!(
            canonical_json(&out).unwrap(),
            "{\"args\":[\"T\",\"t\"],\"op\":\"index\"}"
        );
    }

    #[test]
    fn fixed_point_reduce() {
        let rule = Rule::new(
            "add_zero",
            op("+", vec![var("$a"), Expr::Integer(0)]),
            var("$a"),
        );
        let seed = op(
            "+",
            vec![op("+", vec![var("x"), Expr::Integer(0)]), Expr::Integer(0)],
        );
        let out = rewrite(&seed, &[rule], &RuleContext::default(), 32).unwrap();
        assert_eq!(canonical_json(&out).unwrap(), "\"x\"");
    }

    #[test]
    fn not_converged_error() {
        let rule = Rule::new(
            "explode",
            var("$a"),
            op("+", vec![var("$a"), Expr::Integer(0)]),
        );
        let err = rewrite(&var("x"), &[rule], &RuleContext::default(), 3).unwrap_err();
        assert_eq!(err.code(), "E_RULES_NOT_CONVERGED");
    }

    #[test]
    fn top_down_seal() {
        // (x+x)+(x+x) — rule $a+$a -> 2*$a fires once at root, seals,
        // then next pass fires on the remaining (x+x) once.
        let rule = Rule::new(
            "double",
            op("+", vec![var("$a"), var("$a")]),
            op("*", vec![Expr::Integer(2), var("$a")]),
        );
        let inner = op("+", vec![var("x"), var("x")]);
        let seed = op("+", vec![inner.clone(), inner]);
        let out = rewrite(&seed, &[rule], &RuleContext::default(), 32).unwrap();
        let want = op(
            "*",
            vec![Expr::Integer(2), op("*", vec![Expr::Integer(2), var("x")])],
        );
        assert_eq!(
            canonical_json(&out).unwrap(),
            canonical_json(&want).unwrap()
        );
    }

    #[test]
    fn pde_op_unrewritten() {
        let expr = op_with("grad", vec![var("T")], None, Some("x"));
        let err = check_unrewritten_pde_ops(&expr).unwrap_err();
        assert_eq!(err.code(), "E_UNREWRITTEN_PDE_OP");
        let ok = op("index", vec![var("T"), var("x")]);
        assert!(check_unrewritten_pde_ops(&ok).is_ok());
    }

    #[test]
    fn guard_var_has_grid_bind() {
        // Rule: grad($u, dim=$x) -> $u when $u.grid == g1
        let pat = op_with("grad", vec![var("$u")], None, Some("$x"));
        let rule = Rule {
            name: "drop".into(),
            pattern: pat,
            where_: vec![Guard {
                name: "var_has_grid".into(),
                params: {
                    let mut m = HashMap::new();
                    m.insert("pvar".into(), serde_json::json!("$u"));
                    m.insert("grid".into(), serde_json::json!("g1"));
                    m
                },
            }],
            replacement: var("$u"),
            region: None,
            where_expr: None,
        };
        let mut ctx = RuleContext::default();
        ctx.variables.insert(
            "T".into(),
            VariableMeta {
                grid: Some("g1".into()),
                ..Default::default()
            },
        );
        let seed = op_with("grad", vec![var("T")], None, Some("x"));
        let out = rewrite(&seed, std::slice::from_ref(&rule), &ctx, 32).unwrap();
        assert_eq!(canonical_json(&out).unwrap(), "\"T\"");
        // Wrong grid: does not fire.
        let mut ctx2 = RuleContext::default();
        ctx2.variables.insert(
            "T".into(),
            VariableMeta {
                grid: Some("g2".into()),
                ..Default::default()
            },
        );
        let out2 = rewrite(&seed, &[rule], &ctx2, 32).unwrap();
        assert!(matches!(out2, Expr::Operator(_)));
    }

    /// Conformance fixture consumer — the Julia and Rust bindings are both
    /// required by RFC §13.1 Step 1 to emit byte-identical canonical output.
    /// This test walks the same manifest the Julia conformance harness uses.
    #[test]
    fn rule_engine_conformance_fixtures() {
        use std::path::PathBuf;
        let manifest_dir = env!("CARGO_MANIFEST_DIR");
        let repo_root: PathBuf = PathBuf::from(manifest_dir)
            .parent()
            .unwrap()
            .parent()
            .unwrap()
            .to_path_buf();
        let dir = repo_root
            .join("tests")
            .join("conformance")
            .join("discretization")
            .join("infra")
            .join("rule_engine");
        let manifest_bytes = std::fs::read(dir.join("manifest.json")).expect("read manifest");
        let manifest: serde_json::Value =
            serde_json::from_slice(&manifest_bytes).expect("parse manifest");
        let fixtures = manifest["fixtures"].as_array().expect("fixtures array");
        assert!(!fixtures.is_empty(), "manifest has no fixtures");
        for f in fixtures {
            let id = f["id"].as_str().unwrap();
            let path = dir.join(f["path"].as_str().unwrap());
            let raw = std::fs::read(&path).expect("read fixture");
            let fixture: serde_json::Value = serde_json::from_slice(&raw).expect("parse fixture");

            let rules = parse_rules(&fixture["rules"]).expect("parse_rules");
            let input = parse_expr(&fixture["input"]).expect("parse_expr");
            let max_passes = fixture
                .get("max_passes")
                .and_then(|v| v.as_u64())
                .map(|n| n as usize)
                .unwrap_or(DEFAULT_MAX_PASSES);
            let ctx = build_test_context(&fixture);

            let expect = &fixture["expect"];
            let kind = expect["kind"].as_str().unwrap();
            match kind {
                "output" => {
                    let out = rewrite(&input, &rules, &ctx, max_passes)
                        .unwrap_or_else(|e| panic!("fixture {id}: {e}"));
                    let got = canonical_json(&out).expect("canonicalize output");
                    let want = expect["canonical_json"].as_str().unwrap();
                    assert_eq!(got, want, "fixture {id}: got {got}, want {want}");
                }
                "error" => {
                    let err = rewrite(&input, &rules, &ctx, max_passes)
                        .expect_err("expected rule-engine error");
                    let want = expect["code"].as_str().unwrap();
                    assert_eq!(err.code(), want, "fixture {id}: code mismatch");
                }
                other => panic!("fixture {id}: unknown expect.kind {other}"),
            }
        }
    }

    fn build_test_context(fixture: &serde_json::Value) -> RuleContext {
        let Some(ctx) = fixture.get("context") else {
            return RuleContext::default();
        };
        let mut out = RuleContext::default();
        if let Some(grids) = ctx.get("grids").and_then(|v| v.as_object()) {
            for (k, v) in grids {
                let mut meta = GridMeta::default();
                if let Some(arr) = v.get("spatial_dims").and_then(|x| x.as_array()) {
                    meta.spatial_dims = arr
                        .iter()
                        .filter_map(|s| s.as_str().map(|x| x.to_string()))
                        .collect();
                }
                if let Some(arr) = v.get("periodic_dims").and_then(|x| x.as_array()) {
                    meta.periodic_dims = arr
                        .iter()
                        .filter_map(|s| s.as_str().map(|x| x.to_string()))
                        .collect();
                }
                if let Some(arr) = v.get("nonuniform_dims").and_then(|x| x.as_array()) {
                    meta.nonuniform_dims = arr
                        .iter()
                        .filter_map(|s| s.as_str().map(|x| x.to_string()))
                        .collect();
                }
                if let Some(bounds) = v.get("dim_bounds").and_then(|x| x.as_object()) {
                    for (dk, dv) in bounds {
                        if let Some(arr) = dv.as_array()
                            && arr.len() == 2
                            && let (Some(lo), Some(hi)) =
                                (arr[0].as_i64(), arr[1].as_i64())
                        {
                            meta.dim_bounds.insert(dk.clone(), [lo, hi]);
                        }
                    }
                }
                if let Some(pc) = v.get("panel_connectivity").and_then(|x| x.as_object()) {
                    let parse_table = |key: &str| -> Vec<Vec<i64>> {
                        pc.get(key)
                            .and_then(|x| x.as_array())
                            .map(|rows| {
                                rows.iter()
                                    .filter_map(|r| r.as_array())
                                    .map(|r| r.iter().filter_map(|x| x.as_i64()).collect())
                                    .collect()
                            })
                            .unwrap_or_default()
                    };
                    meta.panel_connectivity = Some(PanelConnectivity {
                        neighbors: parse_table("neighbors"),
                        axis_flip: parse_table("axis_flip"),
                    });
                }
                out.grids.insert(k.clone(), meta);
            }
        }
        if let Some(qp) = ctx.get("query_point").and_then(|v| v.as_object()) {
            for (k, v) in qp {
                if let Some(i) = v.as_i64() {
                    out.query_point.insert(k.clone(), i);
                }
            }
        }
        if let Some(g) = ctx.get("grid_name").and_then(|v| v.as_str()) {
            out.grid_name = Some(g.to_string());
        }
        if let Some(vars) = ctx.get("variables").and_then(|v| v.as_object()) {
            for (k, v) in vars {
                let mut meta = VariableMeta {
                    grid: v
                        .get("grid")
                        .and_then(|x| x.as_str())
                        .map(|s| s.to_string()),
                    location: v
                        .get("location")
                        .and_then(|x| x.as_str())
                        .map(|s| s.to_string()),
                    ..Default::default()
                };
                if let Some(arr) = v.get("shape").and_then(|x| x.as_array()) {
                    meta.shape = Some(
                        arr.iter()
                            .filter_map(|s| s.as_str().map(|x| x.to_string()))
                            .collect(),
                    );
                }
                out.variables.insert(k.clone(), meta);
            }
        }
        out
    }

    #[test]
    fn parse_rules_object_and_array() {
        let obj = serde_json::json!({
            "a": {"pattern": {"op": "+", "args": ["$x", 0]}, "replacement": "$x"}
        });
        let rs = parse_rules(&obj).unwrap();
        assert_eq!(rs.len(), 1);
        assert_eq!(rs[0].name, "a");

        let arr = serde_json::json!([
            {"name": "first",  "pattern": {"op": "*", "args": ["$a", 0]}, "replacement": 0},
            {"name": "second", "pattern": {"op": "+", "args": ["$a", 0]}, "replacement": "$a"}
        ]);
        let rs2 = parse_rules(&arr).unwrap();
        assert_eq!(
            rs2.iter().map(|r| r.name.as_str()).collect::<Vec<_>>(),
            vec!["first", "second"]
        );
    }
}
