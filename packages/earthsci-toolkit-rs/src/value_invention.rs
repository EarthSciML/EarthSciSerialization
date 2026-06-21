//! Build-time value-invention front-door (Rust binding).
//!
//! Port of the Julia reference `value_invention.jl` (bead ess-3lj.1 → ess-3lj.2);
//! RFC `semiring-faq-unified-ir` §6.1 (cadence-partition) / §5.5 (determinism) /
//! §7.3 (edge enumeration); `CONFORMANCE_SPEC.md` §5.5 / §5.7.
//!
//! A `kind:"derived"` index set whose `from_faq` names a value-invention
//! aggregate (an `aggregate` with `distinct:true`, or whose body / `key` is
//! `skolem` / `rank`) is materialised here, ONCE at setup, off the per-step hot
//! path — the §6.1 CONST/DISCRETE materialisation point. The aggregate's keys
//! are evaluated over the build-time const-array factors and run through the
//! [`crate::relational`] engine (skolem / distinct, §5.5 determinism); the
//! distinct set's cardinality is handed to the index-set resolver as the dense
//! extent `[1, n]`. Concretely, [`apply_value_invention`] rewrites the typed
//! model's `kind:"derived"` set into `kind:"interval"` with `size = n`, so
//! [`crate::aggregate::resolve_aggregate_ranges`] resolves it via the existing
//! interval arm (a derived **output** index — e.g. the `rank` dense-id buffer —
//! is otherwise rejected, since a data-dependent extent cannot size an output
//! array). The value-invention outputs are dropped from the ODE.
//!
//! The pass runs on the **raw `serde_json::Value`** model document, not the
//! typed `Model`: the typed `ExpressionNode` drops the aggregate `key` /
//! `distinct` fields (mirroring [`crate::cadence`], which walks raw JSON for the
//! same reason). The materialised members are **byte-identical** across the
//! Julia / Rust / Python bindings (the M3 determinism goldens) because every
//! emitted key is the canonical Skolem tuple in §5.5.1 sorted total order.

use std::collections::{HashMap, HashSet};

use ndarray::{ArrayD, IxDyn};
use serde_json::{Map, Value};

use crate::cadence::{self, Cadence};
use crate::relational::{self, Key};
use crate::types::{Expr, Model};

/// A value-invention build-time materialisation error (the Rust analog of
/// Julia's `TreeWalkError` value-invention codes).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ValueInventionError(pub String);

impl std::fmt::Display for ValueInventionError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "ValueInventionError: {}", self.0)
    }
}

impl std::error::Error for ValueInventionError {}

fn err<T>(msg: impl Into<String>) -> Result<T, ValueInventionError> {
    Err(ValueInventionError(msg.into()))
}

/// The relational body ops that mark a value-invention output (excluded from the
/// ODE): mirrors Julia `_VI_BODY_OPS`.
const VI_BODY_OPS: [&str; 3] = ["skolem", "rank", "distinct"];

/// Result of [`materialize_value_invention`].
///
/// - `extents` — `from_faq` producer id → derived index-set cardinality (the
///   dense extent `[1, n]` the resolver consumes).
/// - `members` — `from_faq` producer id → the distinct member keys in §5.5.1
///   sorted order (for byte-identity assertions).
/// - `vi_var_names` — value-invention LHS vars to drop from the ODE.
#[derive(Debug, Clone, Default)]
pub struct ValueInventionResult {
    pub extents: HashMap<String, i64>,
    pub members: HashMap<String, Vec<Key>>,
    pub vi_var_names: HashSet<String>,
}

// --------------------------------------------------------------------------- //
// Intermediate build-time value
// --------------------------------------------------------------------------- //

/// A build-time value produced by [`vi_eval`]: an int / float / bool / relation
/// tag / canonical Skolem key, depending on the op.
#[derive(Debug, Clone, PartialEq)]
enum Val {
    Bool(bool),
    Int(i64),
    Float(f64),
    Str(String),
    Key(Key),
}

impl Val {
    fn as_f64(&self) -> Result<f64, ValueInventionError> {
        match self {
            Val::Int(i) => Ok(*i as f64),
            Val::Float(f) => Ok(*f),
            Val::Bool(b) => Ok(if *b { 1.0 } else { 0.0 }),
            other => err(format!("value {other:?} is not numeric")),
        }
    }

    /// Coerce to an exact integer relational key component (§5.5.1 rule 1: no
    /// floats in keys). A non-integral float is a misuse — fail loudly.
    fn key_int(&self) -> Result<i64, ValueInventionError> {
        match self {
            Val::Int(i) => Ok(*i),
            Val::Bool(b) => Ok(*b as i64),
            Val::Float(f) => {
                if f.fract() == 0.0 && f.is_finite() {
                    Ok(*f as i64)
                } else {
                    err(format!(
                        "value-invention key component {f} is not integer-valued; relational \
                         keys must be integer / categorical IDs (CONFORMANCE_SPEC.md §5.5.1 rule 1)"
                    ))
                }
            }
            other => err(format!("non-numeric key component {other:?}")),
        }
    }
}

// --------------------------------------------------------------------------- //
// Raw-node accessors
// --------------------------------------------------------------------------- //

fn obj(v: &Value) -> Option<&Map<String, Value>> {
    v.as_object()
}

fn node_op(node: &Value) -> Option<&str> {
    node.get("op").and_then(|v| v.as_str())
}

fn node_args(node: &Value) -> &[Value] {
    node.get("args")
        .and_then(|v| v.as_array())
        .map(|a| a.as_slice())
        .unwrap_or(&[])
}

// --------------------------------------------------------------------------- //
// Detection — classify raw aggregate nodes (mirror of _vi_node_kind / _vi_detect)
// --------------------------------------------------------------------------- //

#[derive(Debug, Clone, Copy, PartialEq)]
enum NodeKind {
    Producer,
    Map,
    Exclude,
    None,
}

fn vi_node_kind(node: &Value) -> NodeKind {
    let Some(map) = obj(node) else {
        return NodeKind::None;
    };
    if map.get("op").and_then(|v| v.as_str()) != Some("aggregate") {
        return NodeKind::None;
    }
    if map.get("distinct").and_then(|v| v.as_bool()) == Some(true) {
        return NodeKind::Producer;
    }
    if let Some(bop) = map
        .get("expr")
        .and_then(|b| b.get("op"))
        .and_then(|v| v.as_str())
    {
        if bop == "skolem" {
            return NodeKind::Map;
        }
        if VI_BODY_OPS.contains(&bop) {
            return NodeKind::Exclude;
        }
    }
    if map
        .get("key")
        .and_then(|k| k.get("op"))
        .and_then(|v| v.as_str())
        == Some("skolem")
    {
        return NodeKind::Map;
    }
    NodeKind::None
}

/// Base variable name written by a raw LHS node: `name`,
/// `{op:index,args:[name,…]}` or `{op:D,args:[name,…]}`. `None` if unrecognised.
fn lhs_base_raw(lhs: &Value) -> Option<String> {
    if let Some(s) = lhs.as_str() {
        return Some(s.to_string());
    }
    let op = node_op(lhs)?;
    if op == "index" || op == "D" {
        return node_args(lhs).first().and_then(lhs_base_raw);
    }
    None
}

/// Base variable name of a typed LHS `Expr` (`Variable` / `index` / `D`), used to
/// drop value-invention equations from the ODE.
fn lhs_base_typed(expr: &Expr) -> Option<String> {
    match expr {
        Expr::Variable(name) => Some(name.clone()),
        Expr::Operator(node) if node.op == "index" || node.op == "D" => {
            node.args.first().and_then(lhs_base_typed)
        }
        _ => None,
    }
}

struct Detection {
    has_vi: bool,
    vi_var_names: HashSet<String>,
    maps: Vec<(String, Value)>,
    producers: Vec<(String, Value)>,
}

/// Scan a raw model for value-invention assignments: the equation list (LHS base
/// resolved from the node) plus the `expression` of each observed variable (the
/// base is the variable name). `vi_var_names` is the set of LHS variables
/// produced by skolem/distinct/rank (excluded from the ODE, as the geometry
/// clip-ring vars are); `maps` / `producers` are `(base, node)` pairs.
fn vi_detect(model_json: &Value) -> Detection {
    let mut det = Detection {
        has_vi: false,
        vi_var_names: HashSet::new(),
        maps: Vec::new(),
        producers: Vec::new(),
    };
    if let Some(eqs) = model_json.get("equations").and_then(|v| v.as_array()) {
        for eq in eqs {
            let (Some(lhs), Some(rhs)) = (eq.get("lhs"), eq.get("rhs")) else {
                continue;
            };
            if let Some(base) = lhs_base_raw(lhs) {
                classify_assignment(&base, rhs, &mut det);
            }
        }
    }
    if let Some(vars) = model_json.get("variables").and_then(|v| v.as_object()) {
        for (vname, v) in vars {
            if let Some(expr) = v.get("expression") {
                classify_assignment(vname, expr, &mut det);
            }
        }
    }
    det.has_vi = !det.maps.is_empty() || !det.producers.is_empty();
    det
}

fn classify_assignment(base: &str, rhs: &Value, det: &mut Detection) {
    let kind = vi_node_kind(rhs);
    if kind == NodeKind::None {
        return;
    }
    det.vi_var_names.insert(base.to_string()); // every value-invention output leaves the ODE
    match kind {
        NodeKind::Producer => det.producers.push((base.to_string(), rhs.clone())),
        NodeKind::Map => det.maps.push((base.to_string(), rhs.clone())),
        _ => {}
    }
}

// --------------------------------------------------------------------------- //
// Build-time evaluation context (mirror of _ViCtx)
// --------------------------------------------------------------------------- //

struct ViCtx<'a> {
    const_arrays: &'a HashMap<String, ArrayD<f64>>,
    params: &'a HashMap<String, f64>,
    index_sets: &'a Map<String, Value>,
    variables: &'a Map<String, Value>,
    /// materialised map var → {output-index value → key value}
    maps: HashMap<String, HashMap<i64, Val>>,
}

impl<'a> ViCtx<'a> {
    fn param(&self, name: &str) -> Result<f64, ValueInventionError> {
        if let Some(v) = self.params.get(name) {
            return Ok(*v);
        }
        if let Some(d) = self
            .variables
            .get(name)
            .and_then(|v| v.get("default"))
            .and_then(|v| v.as_f64())
        {
            return Ok(d);
        }
        err(format!(
            "value-invention scalar parameter {name:?} has no override or default"
        ))
    }
}

type Bindings = HashMap<String, i64>;

fn vi_eval(node: &Value, ctx: &ViCtx, bindings: &Bindings) -> Result<Val, ValueInventionError> {
    match node {
        Value::Bool(b) => Ok(Val::Bool(*b)),
        Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Ok(Val::Int(i))
            } else {
                Ok(Val::Float(n.as_f64().unwrap()))
            }
        }
        Value::String(s) => {
            if let Some(v) = bindings.get(s) {
                return Ok(Val::Int(*v)); // bound range symbol
            }
            if ctx.const_arrays.contains_key(s) {
                return Ok(Val::Str(s.clone())); // bare factor name (used by index)
            }
            if ctx
                .variables
                .get(s)
                .and_then(|v| v.get("type"))
                .and_then(|v| v.as_str())
                == Some("parameter")
            {
                return Ok(Val::Float(ctx.param(s)?)); // scalar parameter
            }
            Ok(Val::Str(s.clone())) // relation tag ("edge"/"bin"/"pair")
        }
        Value::Object(_) => vi_eval_op(node, ctx, bindings),
        other => err(format!("unevaluable value-invention node {other}")),
    }
}

fn vi_eval_op(node: &Value, ctx: &ViCtx, bindings: &Bindings) -> Result<Val, ValueInventionError> {
    let op = node_op(node)
        .ok_or_else(|| ValueInventionError("value-invention node has no `op`".into()))?;
    let args = node_args(node);
    match op {
        "index" => vi_index(node, ctx, bindings),
        "skolem" => Ok(Val::Key(vi_skolem(node, ctx, bindings)?)),
        "true" => Ok(Val::Bool(true)),
        "false" => Ok(Val::Bool(false)),
        "floor" => Ok(Val::Int(
            vi_eval(&args[0], ctx, bindings)?.as_f64()?.floor() as i64,
        )),
        "ceil" => Ok(Val::Int(
            vi_eval(&args[0], ctx, bindings)?.as_f64()?.ceil() as i64
        )),
        "/" => Ok(Val::Float(
            vi_eval(&args[0], ctx, bindings)?.as_f64()?
                / vi_eval(&args[1], ctx, bindings)?.as_f64()?,
        )),
        "*" => {
            let mut acc = 1.0;
            for a in args {
                acc *= vi_eval(a, ctx, bindings)?.as_f64()?;
            }
            Ok(Val::Float(acc))
        }
        "+" => {
            let mut acc = 0.0;
            for a in args {
                acc += vi_eval(a, ctx, bindings)?.as_f64()?;
            }
            Ok(Val::Float(acc))
        }
        "-" => {
            if args.len() == 1 {
                Ok(Val::Float(-vi_eval(&args[0], ctx, bindings)?.as_f64()?))
            } else {
                Ok(Val::Float(
                    vi_eval(&args[0], ctx, bindings)?.as_f64()?
                        - vi_eval(&args[1], ctx, bindings)?.as_f64()?,
                ))
            }
        }
        "<" | ">" | "<=" | ">=" | "==" | "!=" => {
            let a = vi_eval(&args[0], ctx, bindings)?.as_f64()?;
            let b = vi_eval(&args[1], ctx, bindings)?.as_f64()?;
            Ok(Val::Bool(match op {
                "<" => a < b,
                ">" => a > b,
                "<=" => a <= b,
                ">=" => a >= b,
                "==" => a == b,
                _ => a != b,
            }))
        }
        other => err(format!(
            "value-invention build-time evaluator does not support op {other:?}"
        )),
    }
}

/// `index(factor, i, …)`: gather from a const-array factor (1-based). The factor
/// is build-time data supplied in `const_arrays`.
fn vi_index(node: &Value, ctx: &ViCtx, bindings: &Bindings) -> Result<Val, ValueInventionError> {
    let args = node_args(node);
    let name = args.first().and_then(|v| v.as_str());
    let Some(name) = name else {
        return err("value-invention index target must be a const-array factor name");
    };
    let Some(arr) = ctx.const_arrays.get(name) else {
        return err(format!(
            "value-invention index target {name:?} must be a const-array factor"
        ));
    };
    let mut idx = Vec::with_capacity(args.len() - 1);
    for a in &args[1..] {
        let one_based = vi_eval(a, ctx, bindings)?.key_int()?;
        idx.push((one_based - 1) as usize);
    }
    Ok(Val::Float(arr[IxDyn(&idx)]))
}

/// `skolem(tag?, c1, c2, …)` → the canonical key tuple. A leading STRING literal
/// is the relation tag (the relation name) and is NOT part of the emitted key —
/// this is what makes the materialised set byte-identical to the M3 determinism
/// golden (edges `[[1,2],…]`, candidate pairs `(i,j)`), which carry no tag. The
/// remaining components are exact integer IDs (§5.5.1 rule 4). A single component
/// degrades to a scalar key.
fn vi_skolem(node: &Value, ctx: &ViCtx, bindings: &Bindings) -> Result<Key, ValueInventionError> {
    let args = node_args(node);
    let mut comps: Vec<Val> = Vec::with_capacity(args.len());
    for a in args {
        comps.push(vi_eval(a, ctx, bindings)?);
    }
    let start = if matches!(comps.first(), Some(Val::Str(_))) {
        1
    } else {
        0
    };
    let mut key_comps: Vec<Key> = Vec::with_capacity(comps.len() - start);
    for c in &comps[start..] {
        key_comps.push(Key::Int(c.key_int()?));
    }
    if key_comps.len() == 1 {
        Ok(key_comps.into_iter().next().unwrap())
    } else {
        Ok(Key::Tuple(key_comps))
    }
}

// --------------------------------------------------------------------------- //
// Range resolution (mirror of _vi_order_syms / _vi_range_values / _vi_enumerate)
// --------------------------------------------------------------------------- //

/// Order range symbols so a ragged range's `of` parents precede it (a stable
/// topological order over the per-symbol `of` dependency).
fn vi_order_syms(ranges: &Map<String, Value>) -> Result<Vec<String>, ValueInventionError> {
    let syms: Vec<String> = ranges.keys().cloned().collect();
    let mut ordered: Vec<String> = Vec::new();
    let mut remaining = syms.clone();
    while !remaining.is_empty() {
        let mut progressed = false;
        let mut i = 0;
        while i < remaining.len() {
            let s = &remaining[i];
            let of: Vec<String> = ranges[s]
                .get("of")
                .and_then(|v| v.as_array())
                .map(|a| {
                    a.iter()
                        .filter_map(|x| x.as_str().map(String::from))
                        .collect()
                })
                .unwrap_or_default();
            let ready = of.iter().all(|p| ordered.contains(p) || !syms.contains(p));
            if ready {
                ordered.push(remaining.remove(i));
                progressed = true;
            } else {
                i += 1;
            }
        }
        if !progressed {
            return err(format!(
                "value-invention ranges have a cyclic `of` dependency: {remaining:?}"
            ));
        }
    }
    Ok(ordered)
}

/// The element values a range symbol binds to. interval/categorical → 1-based
/// positions; ragged → the MEMBER values gathered from the set's `values` factor
/// sliced by its `offsets` factor (so a range symbol over `face_vertices` binds
/// to the vertex IDs of the parent face, §5.2).
fn vi_range_values(
    spec: &Value,
    ctx: &ViCtx,
    bindings: &Bindings,
) -> Result<Vec<i64>, ValueInventionError> {
    let from = spec.get("from").and_then(|v| v.as_str());
    let Some(from) = from else {
        return err("value-invention range spec is missing `from`");
    };
    let Some(iset) = ctx.index_sets.get(from) else {
        return err(format!(
            "value-invention range references undeclared index set {from:?}"
        ));
    };
    let kind = iset.get("kind").and_then(|v| v.as_str());
    match kind {
        Some("interval") => {
            let size = iset.get("size").and_then(|v| v.as_i64()).unwrap_or(0);
            Ok((1..=size).collect())
        }
        Some("categorical") => {
            let n = iset
                .get("members")
                .and_then(|v| v.as_array())
                .map(|a| a.len())
                .unwrap_or(0) as i64;
            Ok((1..=n).collect())
        }
        Some("ragged") => {
            let of: Vec<String> = spec
                .get("of")
                .and_then(|v| v.as_array())
                .map(|a| {
                    a.iter()
                        .filter_map(|x| x.as_str().map(String::from))
                        .collect()
                })
                .unwrap_or_default();
            let Some(parent_sym) = of.first() else {
                return err(format!(
                    "ragged value-invention range {from:?} needs an `of` parent"
                ));
            };
            let parent = *bindings.get(parent_sym).ok_or_else(|| {
                ValueInventionError(format!("ragged parent {parent_sym:?} is not bound"))
            })?;
            let offsets_name = iset.get("offsets").and_then(|v| v.as_str()).unwrap_or("");
            let values_name = iset.get("values").and_then(|v| v.as_str()).unwrap_or("");
            let offs = ctx.const_arrays.get(offsets_name).ok_or_else(|| {
                ValueInventionError(format!(
                    "ragged offsets factor {offsets_name:?} not supplied"
                ))
            })?;
            let vals = ctx.const_arrays.get(values_name).ok_or_else(|| {
                ValueInventionError(format!("ragged values factor {values_name:?} not supplied"))
            })?;
            let nmem = offs[IxDyn(&[(parent - 1) as usize])] as i64;
            let mut out = Vec::with_capacity(nmem as usize);
            for l in 1..=nmem {
                let v = vals[IxDyn(&[(parent - 1) as usize, (l - 1) as usize])];
                out.push(Val::Float(v).key_int()?);
            }
            Ok(out)
        }
        other => err(format!(
            "value-invention range over index set kind {other:?} is unsupported"
        )),
    }
}

/// Enumerate every full binding of an aggregate's `ranges`, calling `visit` at
/// each leaf binding.
fn vi_enumerate<F>(
    ranges: &Map<String, Value>,
    ctx: &ViCtx,
    mut visit: F,
) -> Result<(), ValueInventionError>
where
    F: FnMut(&Bindings) -> Result<(), ValueInventionError>,
{
    let syms = vi_order_syms(ranges)?;
    let mut bindings: Bindings = HashMap::new();
    vi_enumerate_rec(&syms, 0, ranges, ctx, &mut bindings, &mut visit)
}

fn vi_enumerate_rec<F>(
    syms: &[String],
    k: usize,
    ranges: &Map<String, Value>,
    ctx: &ViCtx,
    bindings: &mut Bindings,
    visit: &mut F,
) -> Result<(), ValueInventionError>
where
    F: FnMut(&Bindings) -> Result<(), ValueInventionError>,
{
    if k >= syms.len() {
        return visit(bindings);
    }
    let s = &syms[k];
    for v in vi_range_values(&ranges[s], ctx, bindings)? {
        bindings.insert(s.clone(), v);
        vi_enumerate_rec(syms, k + 1, ranges, ctx, bindings, visit)?;
    }
    bindings.remove(s);
    Ok(())
}

// --------------------------------------------------------------------------- //
// Materialisation (mirror of _vi_join_* / _vi_materialize_*)
// --------------------------------------------------------------------------- //

/// The index range symbol of a join-key variable within the producer's ranges:
/// the producer range whose `from` equals the variable's (1-D) shape index set.
fn vi_join_index_sym(
    vname: &str,
    producer_ranges: &Map<String, Value>,
    ctx: &ViCtx,
) -> Result<String, ValueInventionError> {
    let v = ctx.variables.get(vname).ok_or_else(|| {
        ValueInventionError(format!("join references unknown variable {vname:?}"))
    })?;
    let shape: Vec<String> = v
        .get("shape")
        .and_then(|s| s.as_array())
        .map(|a| {
            a.iter()
                .filter_map(|x| x.as_str().map(String::from))
                .collect()
        })
        .unwrap_or_default();
    if shape.len() != 1 {
        return err(format!(
            "value-invention join key {vname:?} must be a 1-D buffer; shape={shape:?}"
        ));
    }
    let target = &shape[0];
    for (sym, spec) in producer_ranges {
        if spec.get("from").and_then(|v| v.as_str()) == Some(target.as_str()) {
            return Ok(sym.clone());
        }
    }
    err(format!(
        "no producer range binds the index set {target:?} of join key {vname:?}"
    ))
}

/// True iff every `join.on` key-column pair compares equal at this binding (the
/// value-equality equi-join gate, §5.3); each key is a materialised map buffer.
fn vi_join_ok(
    join: &[Value],
    producer_ranges: &Map<String, Value>,
    ctx: &ViCtx,
    bindings: &Bindings,
) -> Result<bool, ValueInventionError> {
    for clause in join {
        if let Some(on) = clause.get("on").and_then(|v| v.as_array()) {
            for pair in on {
                let cols = pair.as_array().ok_or_else(|| {
                    ValueInventionError("join.on entry must be a [left, right] pair".into())
                })?;
                let lname = cols[0].as_str().unwrap_or_default();
                let rname = cols[1].as_str().unwrap_or_default();
                let ls = vi_join_index_sym(lname, producer_ranges, ctx)?;
                let rs = vi_join_index_sym(rname, producer_ranges, ctx)?;
                let lval = ctx.maps[lname].get(&bindings[&ls]);
                let rval = ctx.maps[rname].get(&bindings[&rs]);
                if lval != rval {
                    return Ok(false);
                }
            }
        }
    }
    Ok(true)
}

/// Materialise a per-element value-invention map var → {output-index → value}.
fn vi_materialize_map(
    ctx: &mut ViCtx,
    vname: &str,
    node: &Value,
) -> Result<(), ValueInventionError> {
    let output_idx: Vec<String> = node
        .get("output_idx")
        .and_then(|v| v.as_array())
        .map(|a| {
            a.iter()
                .filter_map(|x| x.as_str().map(String::from))
                .collect()
        })
        .unwrap_or_default();
    if output_idx.len() != 1 {
        return err(format!(
            "value-invention map {vname:?} must have a single output index; got {output_idx:?}"
        ));
    }
    let body = node.get("expr").ok_or_else(|| {
        ValueInventionError(format!("value-invention map {vname:?} has no `expr` body"))
    })?;
    let empty = Map::new();
    let ranges = node
        .get("ranges")
        .and_then(|v| v.as_object())
        .unwrap_or(&empty);
    let sym = output_idx[0].clone();
    let mut out: HashMap<i64, Val> = HashMap::new();
    // Borrow the body / ranges via a const reference inside the closure; collect
    // into `out`, then store it on the context after enumeration completes.
    {
        let ctx_ref = &*ctx;
        vi_enumerate(ranges, ctx_ref, |bindings| {
            let value = vi_eval(body, ctx_ref, bindings)?;
            out.insert(bindings[&sym], value);
            Ok(())
        })?;
    }
    ctx.maps.insert(vname.to_string(), out);
    Ok(())
}

/// Materialise an index-set-producing aggregate → the distinct member set (§5.5
/// sorted total order, via the relational engine). Returns the member list.
fn vi_materialize_producer(ctx: &ViCtx, node: &Value) -> Result<Vec<Key>, ValueInventionError> {
    let key = node.get("key").ok_or_else(|| {
        ValueInventionError("value-invention producer aggregate requires a `key` (§5.5)".into())
    })?;
    let empty = Map::new();
    let ranges = node
        .get("ranges")
        .and_then(|v| v.as_object())
        .unwrap_or(&empty);
    let filt = node.get("filter");
    let join: Vec<Value> = node
        .get("join")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();
    let mut members: Vec<Key> = Vec::new();
    vi_enumerate(ranges, ctx, |bindings| {
        if let Some(f) = filt {
            let fv = vi_eval(f, ctx, bindings)?;
            let pass = match fv {
                Val::Bool(b) => b,
                Val::Int(i) => i > 0,
                Val::Float(x) => x > 0.0,
                _ => false,
            };
            if !pass {
                return Ok(());
            }
        }
        if !join.is_empty() && !vi_join_ok(&join, ranges, ctx, bindings)? {
            return Ok(());
        }
        members.push(vi_skolem(key, ctx, bindings)?);
        Ok(())
    })?;
    Ok(relational::distinct(&members))
}

/// A model copy whose value-invention MAP vars are re-typed to their body's
/// cadence class (`const`→parameter, `discrete`→discrete), so a producer joining
/// on a map buffer classifies by the buffer's true (input-derived) cadence rather
/// than the seed of its declared `state` kind (§6.1). A `continuous` body is left
/// unchanged so the §5.7 guard still rejects state-dependent topology.
fn vi_classification_model(
    model_json: &Value,
    maps: &[(String, Value)],
) -> Result<Value, ValueInventionError> {
    if maps.is_empty() {
        return Ok(model_json.clone());
    }
    let mut out = model_json.clone();
    let variables = out.get_mut("variables").and_then(|v| v.as_object_mut());
    let Some(variables) = variables else {
        return Ok(out);
    };
    // Compute new types first (immutable classify against the original model),
    // then apply, to avoid borrowing `out` mutably and immutably at once.
    let mut retypes: Vec<(String, String)> = Vec::new();
    for (vname, node) in maps {
        if !variables.contains_key(vname) {
            continue;
        }
        let Some(body) = node.get("expr") else {
            continue;
        };
        let bcls = cadence::classify(body, model_json)
            .map_err(|e| ValueInventionError(format!("cadence classify failed: {e}")))?;
        let newtype = match bcls {
            Cadence::Const => "parameter",
            Cadence::Discrete => "discrete",
            Cadence::Continuous => continue,
        };
        retypes.push((vname.clone(), newtype.to_string()));
    }
    for (vname, newtype) in retypes {
        if let Some(v) = variables.get_mut(&vname).and_then(|v| v.as_object_mut()) {
            v.insert("type".to_string(), Value::String(newtype));
        }
    }
    Ok(out)
}

// --------------------------------------------------------------------------- //
// Public entrypoint
// --------------------------------------------------------------------------- //

/// Run the build-time value-invention engine over a raw model document.
///
/// `const_arrays` supplies the build-time factor arrays (the connectivity /
/// coordinates the keys are computed from); `params` supplies scalar parameter
/// overrides. A producer that classifies CONTINUOUS is rejected (§5.7 guard 2).
///
/// A no-op (empty result) for a model with no skolem/distinct/rank node — the
/// evaluator front-door then behaves byte-identically to before.
pub fn materialize_value_invention(
    model_json: &Value,
    const_arrays: &HashMap<String, ArrayD<f64>>,
    params: &HashMap<String, f64>,
) -> Result<ValueInventionResult, ValueInventionError> {
    let det = vi_detect(model_json);
    let mut result = ValueInventionResult {
        vi_var_names: det.vi_var_names.clone(),
        ..Default::default()
    };
    if !det.has_vi {
        return Ok(result);
    }

    let empty = Map::new();
    let index_sets = model_json
        .get("index_sets")
        .and_then(|v| v.as_object())
        .unwrap_or(&empty);
    let variables = model_json
        .get("variables")
        .and_then(|v| v.as_object())
        .unwrap_or(&empty);
    let mut ctx = ViCtx {
        const_arrays,
        params,
        index_sets,
        variables,
        maps: HashMap::new(),
    };

    // Maps first (a producer's join / key may reference them).
    for (vname, node) in &det.maps {
        vi_materialize_map(&mut ctx, vname, node)?;
    }

    // Cadence classification model: re-type each map var to its body's class so
    // the §5.7 guard 2 below classifies a producer that joins on it correctly (a
    // CONST-derived bin map passes; a genuinely state-dependent one still
    // classifies CONTINUOUS → reject).
    let cls_model = vi_classification_model(model_json, &det.maps)?;

    // `from_faq` id → derived index-set name (so we only materialise producers a
    // derived set actually names; geometry producers are handled elsewhere).
    let mut faq_to_set: HashMap<String, String> = HashMap::new();
    for (sname, iset) in index_sets {
        if iset.get("kind").and_then(|v| v.as_str()) != Some("derived") {
            continue;
        }
        if let Some(faq) = iset.get("from_faq").and_then(|v| v.as_str()) {
            faq_to_set.insert(faq.to_string(), sname.clone());
        }
    }

    for (_, node) in &det.producers {
        let node_id = node.get("id").and_then(|v| v.as_str()).ok_or_else(|| {
            ValueInventionError(
                "value-invention producer aggregate requires an `id` naming it for `from_faq`"
                    .into(),
            )
        })?;
        if !faq_to_set.contains_key(node_id) {
            continue; // no derived set names this producer
        }
        // §5.7 guard 2: a relational node may not run on the hot path.
        let cls = cadence::classify(node, &cls_model)
            .map_err(|e| ValueInventionError(format!("cadence classify failed: {e}")))?;
        if cls == Cadence::Continuous {
            return err(format!(
                "value-invention producer {node_id:?} classifies CONTINUOUS — it may not run per \
                 step (RFC §5.7 guard 2); its inputs must be CONST/DISCRETE"
            ));
        }
        let mem = vi_materialize_producer(&ctx, node)?;
        result.extents.insert(node_id.to_string(), mem.len() as i64);
        result.members.insert(node_id.to_string(), mem);
    }

    Ok(result)
}

// --------------------------------------------------------------------------- //
// Evaluator integration: rewrite the typed model so derived sets resolve
// --------------------------------------------------------------------------- //

/// Rewrite each typed `kind:"derived"` index set named by a materialised
/// value-invention producer into `kind:"interval"` with `size = n`, so
/// [`crate::aggregate::resolve_aggregate_ranges`] resolves it via the existing
/// interval arm (handing the resolver the dense extent `[1, n]`). Generalises the
/// geometry clip-ring handoff (§8.1) to the relational engine.
pub fn rewrite_derived_index_sets(model: &mut Model, extents: &HashMap<String, i64>) {
    let Some(sets) = &mut model.index_sets else {
        return;
    };
    for iset in sets.values_mut() {
        if iset.kind != "derived" {
            continue;
        }
        let Some(faq) = &iset.from_faq else { continue };
        if let Some(&n) = extents.get(faq) {
            iset.kind = "interval".to_string();
            iset.size = Some(n);
            iset.from_faq = None;
        }
    }
}

/// Drop the value-invention equations (and their LHS variables) from the typed
/// model: the skolem/distinct/rank outputs are materialised at setup, not
/// integrated, so their defining equations must not reach the numeric pipeline
/// (RFC §6.1). A no-op for an empty `vi_var_names`.
pub fn drop_value_invention_equations(model: &mut Model, vi_var_names: &HashSet<String>) {
    if vi_var_names.is_empty() {
        return;
    }
    model.equations.retain(|eq| match lhs_base_typed(&eq.lhs) {
        Some(base) => !vi_var_names.contains(&base),
        None => true,
    });
    if let Some(init) = &mut model.initialization_equations {
        init.retain(|eq| match lhs_base_typed(&eq.lhs) {
            Some(base) => !vi_var_names.contains(&base),
            None => true,
        });
    }
    for name in vi_var_names {
        model.variables.remove(name);
    }
}

/// The combined front-door applied to a typed model: rewrite the derived index
/// sets to their materialised dense extents and drop the value-invention
/// equations. After this the existing resolver / array compiler handles the
/// model with no value-invention-specific path.
pub fn apply_value_invention(model: &mut Model, result: &ValueInventionResult) {
    rewrite_derived_index_sets(model, &result.extents);
    drop_value_invention_equations(model, &result.vi_var_names);
}

// =========================================================================== //
// Value-invention evaluator front-door — conformance (bead ess-3lj.2, F2).
//
// Port-parity counterpart of the Julia reference test
// `value_invention_frontdoor_test.jl` (F1, ess-3lj.1) and the Python
// `test_value_invention_frontdoor.py`. RFC `semiring-faq-unified-ir` §6.1 / §5.5
// / §7.3; `CONFORMANCE_SPEC.md` §5.5 / §5.7.
//
// Two proof cases, both BYTE-IDENTICAL to the landed M3 goldens — the SAME
// canonical index-set JSON the Julia and Python bindings assert, which is what
// makes the value-invention .esm run end-to-end byte-identical across all three:
//   (1) the §7.3 edge-enumeration .esm — `edges` -> [[1,2],[1,3],[2,3],[2,4],[3,4]];
//   (2) the conservative-regridder overlap-join .esm — `candidate_pairs` ->
//       [[1,1],[2,2],[3,3]] via the bin-Skolem equi-join.
// =========================================================================== //

#[cfg(test)]
mod tests {
    use super::*;
    use crate::relational::canonical_index_set_json;

    // The shared M3 goldens — the byte-for-byte canonical index-set JSON every
    // binding (Julia / Rust / Python) must reproduce (§5.5.3).
    const EDGE_GOLDEN: &str = "[[1,2],[1,3],[2,3],[2,4],[3,4]]";
    const CANDIDATE_GOLDEN: &str = "[[1,1],[2,2],[3,3]]";

    const EDGE_FIXTURE: &str =
        include_str!("../../../tests/valid/aggregate/edge_enumeration_area_eff.esm");
    const REGRID_FIXTURE: &str =
        include_str!("../../../tests/valid/geometry/conservative_regrid_overlap_join.esm");

    fn model_json(fixture: &str, model_name: &str) -> Value {
        let doc: Value = serde_json::from_str(fixture).expect("fixture parses");
        doc["models"][model_name].clone()
    }

    fn arr(shape: &[usize], data: Vec<f64>) -> ArrayD<f64> {
        ArrayD::from_shape_vec(IxDyn(shape), data).expect("shape matches data")
    }

    fn ca(pairs: Vec<(&str, ArrayD<f64>)>) -> HashMap<String, ArrayD<f64>> {
        pairs.into_iter().map(|(k, v)| (k.to_string(), v)).collect()
    }

    fn params(pairs: &[(&str, f64)]) -> HashMap<String, f64> {
        pairs.iter().map(|(k, v)| (k.to_string(), *v)).collect()
    }

    fn sorted(set: &HashSet<String>) -> Vec<String> {
        let mut v: Vec<String> = set.iter().cloned().collect();
        v.sort();
        v
    }

    fn k(i: i64, j: i64) -> Key {
        Key::Tuple(vec![Key::Int(i), Key::Int(j)])
    }

    #[test]
    fn edge_enumeration_materializes_to_m3_golden() {
        let mj = model_json(EDGE_FIXTURE, "EdgeEnumerationAreaEff");
        // Canonical 2-triangle mesh connectivity (the ragged face_vertices factors).
        let const_arrays = ca(vec![
            ("n_verts_on_face", arr(&[2], vec![3.0, 3.0])),
            (
                "verts_on_face",
                arr(&[2, 3], vec![1.0, 2.0, 3.0, 2.0, 3.0, 4.0]),
            ),
            ("n_edges_on_cell", arr(&[2], vec![3.0, 3.0])),
            (
                "edges_on_cell",
                arr(&[2, 3], vec![1.0, 2.0, 3.0, 3.0, 4.0, 5.0]),
            ),
            ("dc", arr(&[5], vec![2.0, 3.0, 5.0, 7.0, 11.0])),
            ("dv", arr(&[5], vec![13.0, 17.0, 19.0, 23.0, 29.0])),
        ]);
        let vi = materialize_value_invention(&mj, &const_arrays, &HashMap::new()).unwrap();

        // The derived `edges` set materializes via the relational engine,
        // BYTE-IDENTICAL to the M3 determinism golden.
        assert_eq!(vi.extents["edge_set"], 5);
        let edges = &vi.members["edge_set"];
        assert_eq!(*edges, vec![k(1, 2), k(1, 3), k(2, 3), k(2, 4), k(3, 4)]);
        assert_eq!(canonical_index_set_json(edges), EDGE_GOLDEN);
        // the skolem/rank LHS vars are dropped from the ODE (materialized at setup).
        assert_eq!(
            sorted(&vi.vi_var_names),
            vec!["edge_dense_id", "edge_exists"]
        );
    }

    #[test]
    fn edge_enumeration_adversarial_inputs_collapse_to_golden() {
        // §5.5.4: reversed winding yields the identical canonically-sorted edge set.
        let mj = model_json(EDGE_FIXTURE, "EdgeEnumerationAreaEff");
        let base = ca(vec![
            ("n_verts_on_face", arr(&[2], vec![3.0, 3.0])),
            (
                "verts_on_face",
                arr(&[2, 3], vec![1.0, 2.0, 3.0, 2.0, 3.0, 4.0]),
            ),
        ]);
        let rev = ca(vec![
            ("n_verts_on_face", arr(&[2], vec![3.0, 3.0])),
            (
                "verts_on_face",
                arr(&[2, 3], vec![3.0, 2.0, 1.0, 4.0, 3.0, 2.0]),
            ),
        ]);
        for const_arrays in [base, rev] {
            let vi = materialize_value_invention(&mj, &const_arrays, &HashMap::new()).unwrap();
            assert_eq!(
                canonical_index_set_json(&vi.members["edge_set"]),
                EDGE_GOLDEN
            );
        }
    }

    #[test]
    fn regridder_candidate_set_bin_skolem_equijoin() {
        let mj = model_json(REGRID_FIXTURE, "ConservativeRegridOverlapJoin");
        let p = params(&[("dx", 1.0), ("dy", 1.0), ("atol", 1e-12)]);

        // Aligned grids: src/tgt cell i share bin (i-1, 0) ⇒ diagonal candidate set.
        let aligned = ca(vec![
            ("src_lon", arr(&[3], vec![0.2, 1.2, 2.2])),
            ("src_lat", arr(&[3], vec![0.0, 0.0, 0.0])),
            ("tgt_lon", arr(&[3], vec![0.2, 1.2, 2.2])),
            ("tgt_lat", arr(&[3], vec![0.0, 0.0, 0.0])),
        ]);
        let vi = materialize_value_invention(&mj, &aligned, &p).unwrap();
        assert_eq!(vi.members["candidate_set"], vec![k(1, 1), k(2, 2), k(3, 3)]);
        assert_eq!(vi.extents["candidate_set"], 3);
        assert_eq!(
            canonical_index_set_json(&vi.members["candidate_set"]),
            CANDIDATE_GOLDEN
        );
        assert_eq!(
            sorted(&vi.vi_var_names),
            vec!["pair_exists", "src_bin", "tgt_bin"]
        );

        // Shifted target grid: only the overlapping bins join (broad phase is
        // load-bearing — NOT the full cross product).
        let shifted = ca(vec![
            ("src_lon", arr(&[3], vec![0.2, 1.2, 2.2])),
            ("src_lat", arr(&[3], vec![0.0, 0.0, 0.0])),
            ("tgt_lon", arr(&[3], vec![1.2, 2.2, 9.9])),
            ("tgt_lat", arr(&[3], vec![0.0, 0.0, 0.0])),
        ]);
        let vi2 = materialize_value_invention(&mj, &shifted, &p).unwrap();
        assert_eq!(vi2.members["candidate_set"], vec![k(2, 1), k(3, 2)]);
    }

    #[test]
    fn resolver_resolves_derived_set_after_rewrite() {
        // The evaluator integration: WITHOUT the front-door, the resolver rejects
        // the `rank` eq's derived OUTPUT index `e` over `edges`; WITH the rewrite
        // (edges -> interval[1,5]) it resolves cleanly.
        let mj = model_json(EDGE_FIXTURE, "EdgeEnumerationAreaEff");
        let const_arrays = ca(vec![
            ("n_verts_on_face", arr(&[2], vec![3.0, 3.0])),
            (
                "verts_on_face",
                arr(&[2, 3], vec![1.0, 2.0, 3.0, 2.0, 3.0, 4.0]),
            ),
        ]);
        let vi = materialize_value_invention(&mj, &const_arrays, &HashMap::new()).unwrap();

        let mut file = crate::parse::load(EDGE_FIXTURE).expect("fixture loads");
        let model = file
            .models
            .as_mut()
            .unwrap()
            .get_mut("EdgeEnumerationAreaEff")
            .unwrap();

        // Without the rewrite: the derived output index is rejected.
        assert!(crate::aggregate::resolve_aggregate_ranges(&mut model.clone()).is_err());

        // With the rewrite: the derived `edges` set resolves to the dense [1, 5].
        rewrite_derived_index_sets(model, &vi.extents);
        let edges = model.index_sets.as_ref().unwrap().get("edges").unwrap();
        assert_eq!(edges.kind, "interval");
        assert_eq!(edges.size, Some(5));
        assert!(crate::aggregate::resolve_aggregate_ranges(model).is_ok());
    }

    #[test]
    fn continuous_relational_node_is_rejected() {
        // §5.7 guard 2: a distinct producer whose key reads a genuine state
        // variable classifies CONTINUOUS and must be refused.
        let model: Value = serde_json::json!({
            "index_sets": {
                "items": {"kind": "interval", "size": 2},
                "tags": {"kind": "derived", "from_faq": "tag_set"}
            },
            "variables": {
                "u": {"type": "state", "shape": ["items"]},
                "tag": {"type": "state", "shape": ["tags"]}
            },
            "equations": [{
                "lhs": {"op": "index", "args": ["tag", "p"]},
                "rhs": {
                    "op": "aggregate", "id": "tag_set", "semiring": "bool_and_or",
                    "distinct": true, "output_idx": ["p"],
                    "ranges": {"i": {"from": "items"}},
                    "key": {"op": "skolem", "args": ["t", {"op": "index", "args": ["u", "i"]}]},
                    "expr": {"op": "true", "args": []}
                }
            }]
        });
        let const_arrays = ca(vec![("u", arr(&[2], vec![1.0, 2.0]))]);
        assert!(materialize_value_invention(&model, &const_arrays, &HashMap::new()).is_err());
    }

    #[test]
    fn no_op_for_plain_model() {
        let plain: Value = serde_json::json!({
            "variables": {"x": {"type": "state", "shape": []}},
            "equations": [{"lhs": {"op": "D", "args": ["x"], "wrt": "t"}, "rhs": -1.0}]
        });
        let vi = materialize_value_invention(&plain, &HashMap::new(), &HashMap::new()).unwrap();
        assert!(vi.extents.is_empty());
        assert!(vi.vi_var_names.is_empty());
    }
}
