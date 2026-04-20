//! RFC §11 discretization pipeline (gt-59sj, Julia reference gt-gbs2).
//!
//! Public entry point: [`discretize`]. Given a parsed ESM document as a
//! `serde_json::Value`, this walks every model, canonicalizes every
//! equation RHS and BC `value` expression, runs the rule engine against
//! the concatenation of top-level + per-model `rules`, checks for
//! leftover PDE ops, and returns a new document with `metadata.
//! discretized_from` provenance stamped.
//!
//! This implementation deliberately scopes to RFC §11 only. The §12 DAE
//! binding contract is out of scope (a separate bead). The §5.2 rule
//! engine, §5.4 canonicalizer, and §5.4.6 expression-level canonical JSON
//! emitter are all reused unchanged — this module only wires the
//! pipeline and adds a whole-document canonical JSON emitter required by
//! the cross-binding golden contract in
//! `tests/conformance/discretize/README.md`.

use crate::canonicalize::{canonicalize, format_canonical_float};
use crate::rule_engine::{
    DEFAULT_MAX_PASSES, GridMeta, Rule, RuleContext, RuleEngineError, VariableMeta, parse_expr,
    parse_rules, rewrite,
};
use crate::types::{Expr, ExpressionNode};
use serde_json::{Map, Value};

// ============================================================================
// Options
// ============================================================================

/// Caller-facing knobs for the discretization pipeline.
#[derive(Debug, Clone)]
pub struct DiscretizeOptions {
    /// Per-expression rule-engine budget (RFC §5.2.5).
    pub max_passes: usize,
    /// When `true` (default), an expression that still carries a PDE op
    /// after the rule engine runs raises `E_UNREWRITTEN_PDE_OP`. When
    /// `false`, the owning equation or BC is annotated
    /// `passthrough: true` and retained verbatim.
    pub strict_unrewritten: bool,
}

impl Default for DiscretizeOptions {
    fn default() -> Self {
        Self {
            max_passes: DEFAULT_MAX_PASSES,
            strict_unrewritten: true,
        }
    }
}

// ============================================================================
// Entry point
// ============================================================================

/// Run the RFC §11 pipeline on an ESM document.
///
/// The input is not mutated. The returned document carries
/// `metadata.discretized_from.name` and a `"discretized"` tag in
/// `metadata.tags`.
pub fn discretize(esm: &Value, opts: &DiscretizeOptions) -> Result<Value, RuleEngineError> {
    let mut out = esm.clone();
    if !out.is_object() {
        return Err(RuleEngineError::new(
            "E_RULE_PARSE",
            "discretize: input must be a JSON object",
        ));
    }

    let top_rules = match out.get("rules") {
        Some(v) if !v.is_null() => parse_rules(v)?,
        _ => Vec::new(),
    };
    let ctx = build_rule_context(&out);

    if let Some(models) = out.get_mut("models").and_then(Value::as_object_mut) {
        let model_names: Vec<String> = models.keys().cloned().collect();
        for mname in model_names {
            if let Some(model) = models.get_mut(&mname) {
                if model.is_object() {
                    discretize_model(&mname, model, &top_rules, &ctx, opts)?;
                }
            }
        }
    }

    record_discretized_from(&mut out);
    Ok(out)
}

// ============================================================================
// Rule-context assembly (grids + variables)
// ============================================================================

fn build_rule_context(esm: &Value) -> RuleContext {
    let mut ctx = RuleContext::default();

    if let Some(grids) = esm.get("grids").and_then(Value::as_object) {
        for (gname, graw) in grids {
            ctx.grids.insert(gname.clone(), extract_grid_meta(graw));
        }
    }

    if let Some(models) = esm.get("models").and_then(Value::as_object) {
        for (_, mraw) in models {
            let mgrid = mraw
                .get("grid")
                .and_then(Value::as_str)
                .map(|s| s.to_string());
            let Some(vars) = mraw.get("variables").and_then(Value::as_object) else {
                continue;
            };
            for (vname, vraw) in vars {
                let mut meta = VariableMeta::default();
                meta.grid = mgrid.clone();
                meta.location = vraw
                    .get("location")
                    .and_then(Value::as_str)
                    .map(|s| s.to_string());
                if let Some(arr) = vraw.get("shape").and_then(Value::as_array) {
                    meta.shape = Some(
                        arr.iter()
                            .filter_map(|v| v.as_str().map(String::from))
                            .collect(),
                    );
                }
                ctx.variables.insert(vname.clone(), meta);
            }
        }
    }

    ctx
}

fn extract_grid_meta(graw: &Value) -> GridMeta {
    let mut meta = GridMeta::default();
    let Some(dims) = graw.get("dimensions").and_then(Value::as_array) else {
        return meta;
    };
    for d in dims {
        let Some(name) = d.get("name").and_then(Value::as_str) else {
            continue;
        };
        meta.spatial_dims.push(name.to_string());
        if d.get("periodic").and_then(Value::as_bool) == Some(true) {
            meta.periodic_dims.push(name.to_string());
        }
        if let Some(sp) = d.get("spacing").and_then(Value::as_str) {
            if sp == "nonuniform" || sp == "stretched" {
                meta.nonuniform_dims.push(name.to_string());
            }
        }
    }
    meta
}

// ============================================================================
// Per-model pipeline
// ============================================================================

fn discretize_model(
    mname: &str,
    model: &mut Value,
    top_rules: &[Rule],
    ctx: &RuleContext,
    opts: &DiscretizeOptions,
) -> Result<(), RuleEngineError> {
    let local_rules = match model.get("rules") {
        Some(v) if !v.is_null() => parse_rules(v)?,
        _ => Vec::new(),
    };
    let rules: Vec<Rule> = if local_rules.is_empty() {
        top_rules.to_vec()
    } else {
        let mut combined = Vec::with_capacity(top_rules.len() + local_rules.len());
        combined.extend_from_slice(top_rules);
        combined.extend(local_rules);
        combined
    };
    let max_passes = lookup_max_passes(model, opts.max_passes);

    // Equations.
    if let Some(eqns) = model.get_mut("equations").and_then(Value::as_array_mut) {
        for (i, eqn) in eqns.iter_mut().enumerate() {
            if !eqn.is_object() {
                continue;
            }
            let path = format!("models.{}.equations[{}]", mname, i);
            discretize_equation(&path, eqn, &rules, ctx, max_passes, opts.strict_unrewritten)?;
        }
    }

    // Boundary conditions.
    if let Some(bcs) = model
        .get_mut("boundary_conditions")
        .and_then(Value::as_object_mut)
    {
        let bc_ids: Vec<String> = bcs.keys().cloned().collect();
        for bc_id in bc_ids {
            let Some(bc) = bcs.get_mut(&bc_id) else {
                continue;
            };
            if !bc.is_object() {
                continue;
            }
            let path = format!("models.{}.boundary_conditions.{}", mname, bc_id);
            discretize_bc(&path, bc, &rules, ctx, max_passes, opts.strict_unrewritten)?;
        }
    }

    Ok(())
}

fn lookup_max_passes(model: &Value, default: usize) -> usize {
    model
        .get("rules_config")
        .and_then(|r| r.get("max_passes"))
        .and_then(Value::as_u64)
        .map(|n| n as usize)
        .unwrap_or(default)
}

// ============================================================================
// Per-equation / per-BC rewrite
// ============================================================================

fn discretize_equation(
    path: &str,
    eqn: &mut Value,
    rules: &[Rule],
    ctx: &RuleContext,
    max_passes: usize,
    strict: bool,
) -> Result<(), RuleEngineError> {
    let passthrough = as_bool(eqn.get("passthrough"));

    // Canonicalize LHS without rewriting, so D(x, wrt=t) is preserved.
    if let Some(lhs) = eqn.get("lhs").cloned() {
        let lhs_val = canonicalize_value(&lhs, path)?;
        eqn.as_object_mut().unwrap().insert("lhs".into(), lhs_val);
    }

    if let Some(rhs) = eqn.get("rhs").cloned() {
        let sub = format!("{path}.rhs");
        let (new_rhs, pt) =
            rewrite_or_passthrough(&sub, &rhs, rules, ctx, max_passes, strict, passthrough)?;
        let obj = eqn.as_object_mut().unwrap();
        obj.insert("rhs".into(), new_rhs);
        if pt {
            obj.insert("passthrough".into(), Value::Bool(true));
        }
    }
    Ok(())
}

fn discretize_bc(
    path: &str,
    bc: &mut Value,
    rules: &[Rule],
    ctx: &RuleContext,
    max_passes: usize,
    strict: bool,
) -> Result<(), RuleEngineError> {
    let passthrough = as_bool(bc.get("passthrough"));
    let variable = bc.get("variable").and_then(Value::as_str).map(String::from);
    let kind = bc.get("kind").and_then(Value::as_str).map(String::from);
    let side = bc.get("side").and_then(Value::as_str).map(String::from);
    let value_raw = bc.get("value").cloned();

    let mut rewritten_via_bc_rule = false;
    if let (Some(variable), Some(kind)) = (&variable, &kind) {
        if !rules.is_empty() {
            // Build synthetic wrapper: {op: "bc", args: [variable, value?],
            //                          kind, side?}
            let mut wrapper_node = ExpressionNode::default();
            wrapper_node.op = "bc".into();
            wrapper_node.args.push(Expr::Variable(variable.clone()));
            if let Some(v) = &value_raw {
                wrapper_node.args.push(parse_expr(v)?);
            }
            // Julia's wrapper also carries `kind` and `side` as sibling
            // fields so §9 rules can match on them. Rust's
            // `ExpressionNode` has no arbitrary sibling-field slot, so
            // we match on op+args only; the closed-set guards (var_has_grid
            // et al.) already cover the cross-cutting constraints, and the
            // §9 rule templates the Julia reference ships do not
            // discriminate on kind/side via the pattern AST.
            let _ = (kind, side.as_deref());
            let wrapper = Expr::Operator(wrapper_node);
            let canon = canon_expr(&wrapper)?;
            let rewritten = rewrite(&canon, rules, ctx, max_passes)?;
            let fired = !is_bc_op(&rewritten);
            if fired {
                let final_expr = canon_expr(&rewritten)?;
                let mut pt_out = passthrough;
                if has_pde_op(&final_expr) && !passthrough {
                    if strict {
                        let op = first_pde_op(&final_expr).unwrap_or("");
                        return Err(RuleEngineError::new(
                            "E_UNREWRITTEN_PDE_OP",
                            format!(
                                "{path}.value still contains PDE op '{op}' after rewrite; \
                                 annotate the BC with 'passthrough: true' to opt out"
                            ),
                        ));
                    }
                    pt_out = true;
                }
                let obj = bc.as_object_mut().unwrap();
                obj.insert("value".into(), expr_to_value(&final_expr));
                if pt_out {
                    obj.insert("passthrough".into(), Value::Bool(true));
                }
                rewritten_via_bc_rule = true;
            }
        }
    }

    if !rewritten_via_bc_rule {
        if let Some(v) = value_raw {
            let sub = format!("{path}.value");
            let (new_val, pt) =
                rewrite_or_passthrough(&sub, &v, rules, ctx, max_passes, strict, passthrough)?;
            let obj = bc.as_object_mut().unwrap();
            obj.insert("value".into(), new_val);
            if pt {
                obj.insert("passthrough".into(), Value::Bool(true));
            }
        }
    }

    Ok(())
}

fn rewrite_or_passthrough(
    path: &str,
    raw: &Value,
    rules: &[Rule],
    ctx: &RuleContext,
    max_passes: usize,
    strict: bool,
    passthrough: bool,
) -> Result<(Value, bool), RuleEngineError> {
    let expr = parse_expr(raw)?;
    let canon0 = canon_expr(&expr)?;
    let rewritten = if rules.is_empty() {
        canon0
    } else {
        rewrite(&canon0, rules, ctx, max_passes)?
    };
    let canon1 = canon_expr(&rewritten)?;
    if passthrough {
        return Ok((expr_to_value(&canon1), false));
    }
    if has_pde_op(&canon1) {
        if strict {
            let op = first_pde_op(&canon1).unwrap_or("");
            return Err(RuleEngineError::new(
                "E_UNREWRITTEN_PDE_OP",
                format!(
                    "{path} still contains PDE op '{op}' after rewrite; \
                     annotate the equation/BC with 'passthrough: true' to opt out"
                ),
            ));
        }
        return Ok((expr_to_value(&canon1), true));
    }
    Ok((expr_to_value(&canon1), false))
}

fn canonicalize_value(raw: &Value, path: &str) -> Result<Value, RuleEngineError> {
    let expr = parse_expr(raw)?;
    let canon = canon_expr(&expr)
        .map_err(|e| RuleEngineError::new(e.code, format!("{path}: {msg}", msg = e.message)))?;
    Ok(expr_to_value(&canon))
}

fn canon_expr(e: &Expr) -> Result<Expr, RuleEngineError> {
    canonicalize(e).map_err(|err| {
        RuleEngineError::new(
            match &err {
                crate::canonicalize::CanonicalizeError::NonFinite => "E_CANONICAL_NONFINITE",
                crate::canonicalize::CanonicalizeError::DivByZero => "E_CANONICAL_DIVBY_ZERO",
            },
            err.to_string(),
        )
    })
}

fn is_bc_op(e: &Expr) -> bool {
    matches!(e, Expr::Operator(n) if n.op == "bc")
}

// ============================================================================
// PDE-op coverage scan (RFC §11 Step 7)
// ============================================================================

const PDE_OPS: &[&str] = &["grad", "div", "laplacian", "D", "bc"];

fn has_pde_op(e: &Expr) -> bool {
    first_pde_op(e).is_some()
}

fn first_pde_op(e: &Expr) -> Option<&'static str> {
    if let Expr::Operator(n) = e {
        for op in PDE_OPS {
            if n.op == *op {
                return Some(op);
            }
        }
        for a in &n.args {
            if let Some(r) = first_pde_op(a) {
                return Some(r);
            }
        }
    }
    None
}

// ============================================================================
// Expression ↔ Value
// ============================================================================

fn expr_to_value(e: &Expr) -> Value {
    // `Expr` derives Serialize, and its untagged enum encodes Integer/Number
    // as JSON Number and Variable as JSON String, which preserves the int/
    // float distinction for the whole-doc canonical emitter downstream.
    serde_json::to_value(e).expect("Expr is always Serialize-safe")
}

// ============================================================================
// Discretized-from provenance
// ============================================================================

fn record_discretized_from(esm: &mut Value) {
    let obj = esm
        .as_object_mut()
        .expect("esm is object (checked earlier)");
    let meta = obj
        .entry("metadata".to_string())
        .or_insert_with(|| Value::Object(Map::new()));
    if !meta.is_object() {
        *meta = Value::Object(Map::new());
    }
    let meta_obj = meta.as_object_mut().unwrap();
    let src_name = meta_obj
        .get("name")
        .and_then(Value::as_str)
        .map(|s| s.to_string());
    let mut prov = Map::new();
    if let Some(n) = src_name {
        prov.insert("name".into(), Value::String(n));
    }
    meta_obj.insert("discretized_from".into(), Value::Object(prov));
    match meta_obj.get_mut("tags") {
        Some(Value::Array(arr)) => {
            let already = arr.iter().any(|v| v.as_str() == Some("discretized"));
            if !already {
                arr.push(Value::String("discretized".into()));
            }
        }
        _ => {
            meta_obj.insert(
                "tags".into(),
                Value::Array(vec![Value::String("discretized".into())]),
            );
        }
    }
}

// ============================================================================
// Small helpers
// ============================================================================

fn as_bool(v: Option<&Value>) -> bool {
    match v {
        Some(Value::Bool(b)) => *b,
        Some(Value::String(s)) => s.eq_ignore_ascii_case("true"),
        _ => false,
    }
}

// ============================================================================
// Whole-document canonical JSON emitter (cross-binding byte-identity)
// ============================================================================

/// Emit `doc` as canonical JSON per the cross-binding discretize-conformance
/// contract (`tests/conformance/discretize/README.md`):
/// - sorted object keys (lexicographic by UTF-8 code units)
/// - minified (no whitespace)
/// - integers: minimal decimal form
/// - floats: shortest round-trip with `.0` disambiguation (see
///   `format_canonical_float`); however, to match the Julia reference
///   (which uses JSON3, which parses integer-valued JSON numbers as
///   Int64 regardless of `.0` in the source token), floats whose value
///   is an exact integer in the i64 range are emitted as integers.
/// - strings: RFC 8259 escapes.
pub fn canonical_doc_json(doc: &Value) -> String {
    let mut out = String::new();
    emit_value(doc, &mut out);
    out
}

fn emit_value(v: &Value, out: &mut String) {
    match v {
        Value::Null => out.push_str("null"),
        Value::Bool(b) => out.push_str(if *b { "true" } else { "false" }),
        Value::Number(n) => emit_number(n, out),
        Value::String(s) => emit_string(s, out),
        Value::Array(arr) => {
            out.push('[');
            for (i, item) in arr.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                emit_value(item, out);
            }
            out.push(']');
        }
        Value::Object(map) => {
            out.push('{');
            let mut keys: Vec<&String> = map.keys().collect();
            keys.sort();
            for (i, k) in keys.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                emit_string(k, out);
                out.push(':');
                emit_value(&map[*k], out);
            }
            out.push('}');
        }
    }
}

fn emit_number(n: &serde_json::Number, out: &mut String) {
    if let Some(i) = n.as_i64() {
        out.push_str(&i.to_string());
        return;
    }
    if let Some(u) = n.as_u64() {
        out.push_str(&u.to_string());
        return;
    }
    if let Some(f) = n.as_f64() {
        // Match Julia/JSON3 behaviour: float values that are exact
        // integers in the i64 range serialize as integers.
        if f.is_finite() && f.fract() == 0.0 && f >= i64::MIN as f64 && f <= i64::MAX as f64 {
            out.push_str(&(f as i64).to_string());
        } else {
            out.push_str(&format_canonical_float(f));
        }
        return;
    }
    // Shouldn't happen for valid JSON numbers; fall back.
    out.push_str(&n.to_string());
}

fn emit_string(s: &str, out: &mut String) {
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\u{08}' => out.push_str("\\b"),
            '\u{09}' => out.push_str("\\t"),
            '\u{0A}' => out.push_str("\\n"),
            '\u{0C}' => out.push_str("\\f"),
            '\u{0D}' => out.push_str("\\r"),
            c if (c as u32) < 0x20 => {
                out.push_str(&format!("\\u{:04x}", c as u32));
            }
            c => out.push(c),
        }
    }
    out.push('"');
}

// ============================================================================
// Tests (mirror Julia discretize_test.jl)
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    fn json(s: &str) -> Value {
        serde_json::from_str(s).expect("test json parse")
    }

    // ---- scalar ODE happy path ------------------------------------------------

    #[test]
    fn scalar_ode_canonicalizes_and_stamps_provenance() {
        let input = json(
            r#"{
              "esm": "0.2.0",
              "metadata": { "name": "scalar_ode" },
              "models": {
                "M": {
                  "variables": {
                    "x": { "type": "state", "default": 1.0 },
                    "k": { "type": "parameter", "default": 0.5 }
                  },
                  "equations": [
                    { "lhs": { "op": "D", "args": ["x"], "wrt": "t" },
                      "rhs": { "op": "*", "args": [ { "op": "-", "args": ["k"] }, "x" ] } }
                  ]
                }
              }
            }"#,
        );
        let out = discretize(&input, &DiscretizeOptions::default()).unwrap();
        assert_eq!(
            out["metadata"]["discretized_from"]["name"],
            Value::String("scalar_ode".into())
        );
        let tags = out["metadata"]["tags"].as_array().unwrap();
        assert!(tags.iter().any(|t| t == "discretized"));
        // Unary "-" canonicalizes to "neg".
        let rhs = &out["models"]["M"]["equations"][0]["rhs"];
        assert_eq!(rhs["op"], Value::String("*".into()));
    }

    // ---- determinism ---------------------------------------------------------

    #[test]
    fn discretize_is_deterministic() {
        let input = json(
            r#"{
              "esm": "0.2.0",
              "metadata": { "name": "d" },
              "models": { "M": { "variables": {}, "equations": [] } }
            }"#,
        );
        let a = discretize(&input, &DiscretizeOptions::default()).unwrap();
        let b = discretize(&input, &DiscretizeOptions::default()).unwrap();
        assert_eq!(canonical_doc_json(&a), canonical_doc_json(&b));
    }

    // ---- 1D PDE rewrite with a rule ------------------------------------------

    #[test]
    fn heat_1d_grad_rewrite() {
        let input = json(
            r#"{
              "esm": "0.2.0",
              "metadata": { "name": "h" },
              "grids": {
                "gx": { "family": "cartesian",
                        "dimensions": [ { "name": "i", "size": 8, "periodic": true } ] }
              },
              "rules": [
                { "name": "centered_grad",
                  "pattern":     { "op": "grad",  "args": ["$u"],               "dim": "$x" },
                  "replacement": { "op": "+", "args": [
                     { "op": "-", "args": [ { "op": "index",
                            "args": ["$u", { "op": "-", "args": ["$x", 1] } ] } ] },
                     { "op": "index", "args": ["$u", { "op": "+", "args": ["$x", 1] } ] }
                  ] } }
              ],
              "models": {
                "M": {
                  "grid": "gx",
                  "variables": {
                    "u": { "type": "state", "shape": ["i"], "location": "cell_center" }
                  },
                  "equations": [
                    { "lhs": { "op": "D", "args": ["u"], "wrt": "t" },
                      "rhs": { "op": "grad", "args": ["u"], "dim": "i" } }
                  ]
                }
              }
            }"#,
        );
        let out = discretize(&input, &DiscretizeOptions::default()).unwrap();
        let rhs = &out["models"]["M"]["equations"][0]["rhs"];
        // grad() gone; top op is "+".
        assert_eq!(rhs["op"], "+");
        // No leftover PDE op anywhere.
        let s = serde_json::to_string(rhs).unwrap();
        assert!(!s.contains("\"grad\""));
    }

    // ---- strict error on unrewritten PDE op ----------------------------------

    #[test]
    fn unrewritten_pde_op_strict() {
        let input = json(
            r#"{
              "esm": "0.2.0",
              "metadata": { "name": "e" },
              "models": {
                "M": {
                  "variables": {},
                  "equations": [
                    { "lhs": { "op": "D", "args": ["u"], "wrt": "t" },
                      "rhs": { "op": "grad", "args": ["u"], "dim": "i" } }
                  ]
                }
              }
            }"#,
        );
        let err = discretize(&input, &DiscretizeOptions::default()).unwrap_err();
        assert_eq!(err.code(), "E_UNREWRITTEN_PDE_OP");
    }

    // ---- passthrough on the equation opts out --------------------------------

    #[test]
    fn passthrough_equation_suppresses_error() {
        let input = json(
            r#"{
              "esm": "0.2.0",
              "metadata": { "name": "e" },
              "models": {
                "M": {
                  "variables": {},
                  "equations": [
                    { "lhs": { "op": "D", "args": ["u"], "wrt": "t" },
                      "rhs": { "op": "grad", "args": ["u"], "dim": "i" },
                      "passthrough": true }
                  ]
                }
              }
            }"#,
        );
        let out = discretize(&input, &DiscretizeOptions::default()).unwrap();
        assert_eq!(
            out["models"]["M"]["equations"][0]["passthrough"],
            Value::Bool(true)
        );
    }

    // ---- non-strict mode stamps passthrough ----------------------------------

    #[test]
    fn nonstrict_stamps_passthrough() {
        let input = json(
            r#"{
              "esm": "0.2.0",
              "metadata": { "name": "e" },
              "models": {
                "M": {
                  "variables": {},
                  "equations": [
                    { "lhs": { "op": "D", "args": ["u"], "wrt": "t" },
                      "rhs": { "op": "grad", "args": ["u"], "dim": "i" } }
                  ]
                }
              }
            }"#,
        );
        let mut opts = DiscretizeOptions::default();
        opts.strict_unrewritten = false;
        let out = discretize(&input, &opts).unwrap();
        assert_eq!(
            out["models"]["M"]["equations"][0]["passthrough"],
            Value::Bool(true)
        );
    }

    // ---- BC value canonicalization --------------------------------------------

    #[test]
    fn bc_value_is_canonicalized() {
        let input = json(
            r#"{
              "esm": "0.2.0",
              "metadata": { "name": "b" },
              "models": {
                "M": {
                  "variables": { "u": { "type": "state" } },
                  "equations": [
                    { "lhs": { "op": "D", "args": ["u"], "wrt": "t" }, "rhs": 0.0 }
                  ],
                  "boundary_conditions": {
                    "u0": { "variable": "u", "side": "xmin", "kind": "dirichlet",
                             "value": { "op": "+", "args": [1, 0] } }
                  }
                }
              }
            }"#,
        );
        let out = discretize(&input, &DiscretizeOptions::default()).unwrap();
        // +(1,0) canonicalizes to 1.
        assert_eq!(
            out["models"]["M"]["boundary_conditions"]["u0"]["value"],
            serde_json::json!(1)
        );
    }

    // ---- E_RULES_NOT_CONVERGED bubbles up -------------------------------------

    #[test]
    fn rules_not_converged_bubbles_up() {
        let input = json(
            r#"{
              "esm": "0.2.0",
              "metadata": { "name": "e" },
              "rules": [
                { "name": "explode",
                  "pattern":     "$a",
                  "replacement": { "op": "+", "args": ["$a", 0] } }
              ],
              "models": {
                "M": {
                  "variables": {},
                  "equations": [
                    { "lhs": { "op": "D", "args": ["u"], "wrt": "t" }, "rhs": "u" }
                  ]
                }
              }
            }"#,
        );
        let err = discretize(&input, &DiscretizeOptions::default()).unwrap_err();
        assert_eq!(err.code(), "E_RULES_NOT_CONVERGED");
    }

    // ---- max_passes per-model override ----------------------------------------

    #[test]
    fn per_model_max_passes_override() {
        let input = json(
            r#"{
              "esm": "0.2.0",
              "metadata": { "name": "e" },
              "rules": [
                { "name": "explode",
                  "pattern":     "$a",
                  "replacement": { "op": "+", "args": ["$a", 0] } }
              ],
              "models": {
                "M": {
                  "rules_config": { "max_passes": 1 },
                  "variables": {},
                  "equations": [
                    { "lhs": { "op": "D", "args": ["u"], "wrt": "t" }, "rhs": "u" }
                  ]
                }
              }
            }"#,
        );
        let err = discretize(&input, &DiscretizeOptions::default()).unwrap_err();
        assert_eq!(err.code(), "E_RULES_NOT_CONVERGED");
    }

    // ---- whole-doc canonical emitter -----------------------------------------

    #[test]
    fn canonical_doc_emits_integer_for_float_zero() {
        // Julia/JSON3 quirk: 0.0 in input ends up as int 0 in golden bytes.
        let v = json(r#"{"a": 0.0, "b": 1.0, "c": 0.5}"#);
        assert_eq!(canonical_doc_json(&v), r#"{"a":0,"b":1,"c":0.5}"#);
    }

    #[test]
    fn canonical_doc_sorts_keys_nested() {
        let v = json(r#"{"z":{"b":1,"a":2},"a":[3,2,1]}"#);
        assert_eq!(canonical_doc_json(&v), r#"{"a":[3,2,1],"z":{"a":2,"b":1}}"#);
    }

    // ---- round-trip through parse_expression ----------------------------------

    #[test]
    fn round_trip_canonicalize_twice_is_stable() {
        let input = json(
            r#"{
              "esm": "0.2.0",
              "metadata": { "name": "r" },
              "models": { "M": {
                "variables": {},
                "equations": [
                  { "lhs": { "op": "D", "args": ["y"], "wrt": "t" },
                    "rhs": { "op": "+", "args": ["y", 0] } }
                ]
              } }
            }"#,
        );
        let pass1 = discretize(&input, &DiscretizeOptions::default()).unwrap();
        // Strip provenance added each pass so we compare the stable core.
        let mut pass1_core = pass1.clone();
        pass1_core.as_object_mut().unwrap().remove("metadata");
        let input2 = {
            let mut v = pass1.clone();
            // reset name so we re-enter discretize cleanly
            v["metadata"]["name"] = Value::String("r".into());
            v.as_object_mut().unwrap().remove("rules");
            v
        };
        let pass2 = discretize(&input2, &DiscretizeOptions::default()).unwrap();
        let mut pass2_core = pass2.clone();
        pass2_core.as_object_mut().unwrap().remove("metadata");
        assert_eq!(
            canonical_doc_json(&pass1_core),
            canonical_doc_json(&pass2_core)
        );
    }
}
