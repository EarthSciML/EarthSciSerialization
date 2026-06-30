//! Load-time expansion pass for `apply_expression_template` AST ops.
//!
//! esm-spec §9.6, docs/rfcs/ast-expression-templates.md, esm-giy.
//!
//! Walks each `models.<m>` and `reaction_systems.<rs>` block; if an
//! `expression_templates` entry is present, every `apply_expression_template`
//! node anywhere in that component's expressions is replaced by the
//! substituted template body. After the pass, the file's expression trees
//! contain no `apply_expression_template` nodes and no `expression_templates`
//! blocks — downstream consumers see only normal Expression ASTs (Option A
//! round-trip).
//!
//! Operates on the pre-deserialization `serde_json::Value` view, so it must
//! run after schema validation but before deserializing into typed structs.

use serde_json::{Map, Value};

const APPLY_OP: &str = "apply_expression_template";

/// Stable diagnostic codes raised by the expression-template expansion
/// pass. Mirrors the codes emitted by the TS / Python / Julia / Go bindings.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ExpressionTemplateError {
    pub code: &'static str,
    pub message: String,
}

impl std::fmt::Display for ExpressionTemplateError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "[{}] {}", self.code, self.message)
    }
}

impl std::error::Error for ExpressionTemplateError {}

fn err(code: &'static str, message: impl Into<String>) -> ExpressionTemplateError {
    ExpressionTemplateError {
        code,
        message: message.into(),
    }
}

fn assert_no_nested_apply(
    body: &Value,
    template_name: &str,
    path: &str,
) -> Result<(), ExpressionTemplateError> {
    match body {
        Value::Array(arr) => {
            for (i, child) in arr.iter().enumerate() {
                assert_no_nested_apply(child, template_name, &format!("{path}/{i}"))?;
            }
        }
        Value::Object(obj) => {
            if obj.get("op").and_then(|v| v.as_str()) == Some(APPLY_OP) {
                return Err(err(
                    "apply_expression_template_recursive_body",
                    format!(
                        "expression_templates.{template_name}: body contains nested \
                         'apply_expression_template' at {path}; templates MUST NOT call \
                         other templates"
                    ),
                ));
            }
            for (k, v) in obj {
                assert_no_nested_apply(v, template_name, &format!("{path}/{k}"))?;
            }
        }
        _ => {}
    }
    Ok(())
}

fn validate_templates(
    templates: &Map<String, Value>,
    scope: &str,
) -> Result<(), ExpressionTemplateError> {
    for (name, decl) in templates {
        let decl_obj = decl.as_object().ok_or_else(|| {
            err(
                "apply_expression_template_invalid_declaration",
                format!(
                    "{scope}.expression_templates.{name}: entry must be an object \
                     with params + body"
                ),
            )
        })?;
        let params = decl_obj
            .get("params")
            .and_then(|p| p.as_array())
            .ok_or_else(|| {
                err(
                    "apply_expression_template_invalid_declaration",
                    format!(
                        "{scope}.expression_templates.{name}: 'params' must be a non-empty array"
                    ),
                )
            })?;
        if params.is_empty() {
            return Err(err(
                "apply_expression_template_invalid_declaration",
                format!("{scope}.expression_templates.{name}: 'params' must be a non-empty array"),
            ));
        }
        let mut seen: std::collections::HashSet<&str> = std::collections::HashSet::new();
        for p in params {
            let p_str = p.as_str().ok_or_else(|| {
                err(
                    "apply_expression_template_invalid_declaration",
                    format!("{scope}.expression_templates.{name}: param names must be strings"),
                )
            })?;
            if p_str.is_empty() {
                return Err(err(
                    "apply_expression_template_invalid_declaration",
                    format!("{scope}.expression_templates.{name}: param names must be non-empty"),
                ));
            }
            if !seen.insert(p_str) {
                return Err(err(
                    "apply_expression_template_invalid_declaration",
                    format!("{scope}.expression_templates.{name}: param '{p_str}' declared twice"),
                ));
            }
        }
        let body = decl_obj.get("body").ok_or_else(|| {
            err(
                "apply_expression_template_invalid_declaration",
                format!("{scope}.expression_templates.{name}: 'body' is required"),
            )
        })?;
        assert_no_nested_apply(body, name, "/body")?;
    }
    Ok(())
}

fn substitute(body: &Value, bindings: &Map<String, Value>) -> Value {
    match body {
        Value::String(s) => {
            if let Some(v) = bindings.get(s) {
                v.clone()
            } else {
                body.clone()
            }
        }
        Value::Array(arr) => Value::Array(arr.iter().map(|c| substitute(c, bindings)).collect()),
        Value::Object(obj) => {
            let mut out = Map::new();
            for (k, v) in obj {
                out.insert(k.clone(), substitute(v, bindings));
            }
            Value::Object(out)
        }
        _ => body.clone(),
    }
}

/// An auto-applied rewrite rule: an `expression_templates` entry that carries
/// a `match` pattern (esm-spec §9.6). Named templates *without* a `match` are
/// expanded only by explicit `apply_expression_template`; those with a `match`
/// fire wherever the pattern structurally matches a node.
struct MatchRule {
    /// Template id (for diagnostics).
    name: String,
    /// Metavariable names (wildcards in `pattern`, slots in `body`).
    params: Vec<String>,
    /// The pattern Expression a node is matched against.
    pattern: Value,
    /// The replacement Expression instantiated with the bound metavariables.
    body: Value,
}

/// Bundles the per-component rewrite inputs threaded through the single pass.
struct RewriteCtx<'a> {
    /// All templates declared in the component (named-expansion lookup table).
    templates: &'a Map<String, Value>,
    /// Auto-applied `match` rules, in template **declaration order**.
    rules: &'a [MatchRule],
}

/// Collect the auto-applied `match` rules from a component's templates, in
/// declaration order, and reject any rule whose `body` re-introduces its own
/// pattern (`rewrite_rule_nonterminating`, esm-spec §9.6.3).
fn collect_match_rules(
    templates: &Map<String, Value>,
    scope: &str,
) -> Result<Vec<MatchRule>, ExpressionTemplateError> {
    let mut rules = Vec::new();
    for (name, decl) in templates {
        let Some(obj) = decl.as_object() else { continue };
        let Some(pattern) = obj.get("match") else {
            continue;
        };
        let params: Vec<String> = obj
            .get("params")
            .and_then(|p| p.as_array())
            .map(|arr| {
                arr.iter()
                    .filter_map(|v| v.as_str().map(String::from))
                    .collect()
            })
            .unwrap_or_default();
        let body = obj.get("body").cloned().unwrap_or(Value::Null);

        // Single-pass, no-rescan: a replacement is not re-scanned, so a rule
        // whose body re-introduces its own pattern is a static error.
        let param_set: std::collections::HashSet<&str> =
            params.iter().map(String::as_str).collect();
        if pattern_occurs_in(pattern, &param_set, &body) {
            return Err(err(
                "rewrite_rule_nonterminating",
                format!(
                    "{scope}.expression_templates.{name}: 'body' re-introduces the rule's own \
                     'match' pattern; a replacement is never re-scanned (esm-spec §9.6.3)"
                ),
            ));
        }
        rules.push(MatchRule {
            name: name.clone(),
            params,
            pattern: pattern.clone(),
            body,
        });
    }
    Ok(rules)
}

/// Structurally match `pattern` against `target`, binding metavariables (names
/// in `params`) into `binds`. A metavariable in an operand/`args` position
/// binds the matched sub-AST; in a scalar field it binds the matched literal.
/// A metavariable appearing twice must bind consistently. Pattern object keys
/// are matched as a subset: `target` MAY carry extra keys.
fn try_match(
    pattern: &Value,
    target: &Value,
    params: &std::collections::HashSet<&str>,
    binds: &mut Map<String, Value>,
) -> bool {
    match pattern {
        Value::String(s) => {
            if params.contains(s.as_str()) {
                match binds.get(s) {
                    Some(prev) => prev == target,
                    None => {
                        binds.insert(s.clone(), target.clone());
                        true
                    }
                }
            } else {
                pattern == target
            }
        }
        Value::Array(parr) => match target {
            Value::Array(tarr) if parr.len() == tarr.len() => parr
                .iter()
                .zip(tarr.iter())
                .all(|(p, t)| try_match(p, t, params, binds)),
            _ => false,
        },
        Value::Object(pobj) => match target {
            Value::Object(tobj) => pobj.iter().all(|(k, pv)| match tobj.get(k) {
                Some(tv) => try_match(pv, tv, params, binds),
                None => false,
            }),
            _ => false,
        },
        // numbers / bools / null: exact equality.
        _ => pattern == target,
    }
}

/// True if `pattern` matches `node` or any descendant of `node`. Used for the
/// static `rewrite_rule_nonterminating` check.
fn pattern_occurs_in(
    pattern: &Value,
    params: &std::collections::HashSet<&str>,
    node: &Value,
) -> bool {
    let mut binds = Map::new();
    if try_match(pattern, node, params, &mut binds) {
        return true;
    }
    match node {
        Value::Array(arr) => arr.iter().any(|c| pattern_occurs_in(pattern, params, c)),
        Value::Object(obj) => obj.values().any(|c| pattern_occurs_in(pattern, params, c)),
        _ => false,
    }
}

fn expand_apply(
    node: &Map<String, Value>,
    ctx: &RewriteCtx,
    scope: &str,
) -> Result<Value, ExpressionTemplateError> {
    let name = node.get("name").and_then(|v| v.as_str()).ok_or_else(|| {
        err(
            "apply_expression_template_invalid_declaration",
            format!("{scope}: apply_expression_template node missing or empty 'name'"),
        )
    })?;
    if name.is_empty() {
        return Err(err(
            "apply_expression_template_invalid_declaration",
            format!("{scope}: apply_expression_template 'name' must be non-empty"),
        ));
    }
    let decl = ctx.templates.get(name).ok_or_else(|| {
        err(
            "apply_expression_template_unknown_template",
            format!("{scope}: apply_expression_template references undeclared template '{name}'"),
        )
    })?;
    let decl_obj = decl.as_object().ok_or_else(|| {
        err(
            "apply_expression_template_invalid_declaration",
            format!("{scope}: template '{name}' declaration is not an object"),
        )
    })?;
    let bindings = node
        .get("bindings")
        .and_then(|v| v.as_object())
        .ok_or_else(|| {
            err(
                "apply_expression_template_bindings_mismatch",
                format!("{scope}: apply_expression_template '{name}' missing 'bindings' object"),
            )
        })?;

    let params: Vec<&str> = decl_obj
        .get("params")
        .and_then(|p| p.as_array())
        .map(|arr| arr.iter().filter_map(|v| v.as_str()).collect())
        .unwrap_or_default();
    let declared: std::collections::HashSet<&str> = params.iter().copied().collect();
    let provided: std::collections::HashSet<&str> = bindings.keys().map(String::as_str).collect();
    for p in &params {
        if !provided.contains(p) {
            return Err(err(
                "apply_expression_template_bindings_mismatch",
                format!(
                    "{scope}: apply_expression_template '{name}' missing binding for param '{p}'"
                ),
            ));
        }
    }
    for p in &provided {
        if !declared.contains(p) {
            return Err(err(
                "apply_expression_template_bindings_mismatch",
                format!("{scope}: apply_expression_template '{name}' supplies unknown param '{p}'"),
            ));
        }
    }

    // Recursively rewrite bindings (template bodies cannot contain
    // apply_expression_template, but the *bindings* may, and may themselves
    // match auto-applied rules).
    let mut resolved = Map::new();
    for (k, v) in bindings {
        resolved.insert(k.clone(), rewrite(v, ctx, scope)?);
    }
    let body = decl_obj.get("body").cloned().unwrap_or(Value::Null);
    // The substituted body is a replacement and is NOT re-scanned (§9.6.3).
    Ok(substitute(&body, &resolved))
}

/// The single bottom-up load-time rewrite pass (esm-spec §9.6.3). For each
/// node: rewrite children first; expand an `apply_expression_template` node
/// into its substituted body; otherwise try the auto-applied `match` rules in
/// declaration order against the (children-rewritten) node and instantiate the
/// first rule that fires. A replacement is returned as-is — never re-scanned.
fn rewrite(node: &Value, ctx: &RewriteCtx, scope: &str) -> Result<Value, ExpressionTemplateError> {
    let processed = match node {
        Value::Array(arr) => {
            let mut out = Vec::with_capacity(arr.len());
            for c in arr {
                out.push(rewrite(c, ctx, scope)?);
            }
            Value::Array(out)
        }
        Value::Object(obj) => {
            if obj.get("op").and_then(|v| v.as_str()) == Some(APPLY_OP) {
                // Named-template expansion is itself a replacement: return it
                // without offering it to the auto-applied `match` rules.
                return expand_apply(obj, ctx, scope);
            }
            let mut out = Map::new();
            for (k, v) in obj {
                out.insert(k.clone(), rewrite(v, ctx, scope)?);
            }
            Value::Object(out)
        }
        _ => node.clone(),
    };

    for rule in ctx.rules {
        let param_set: std::collections::HashSet<&str> =
            rule.params.iter().map(String::as_str).collect();
        let mut binds = Map::new();
        if try_match(&rule.pattern, &processed, &param_set, &mut binds) {
            let _ = &rule.name; // retained for diagnostics / future tracing
            // Instantiate the body; first rule wins, result is not re-scanned.
            return Ok(substitute(&rule.body, &binds));
        }
    }

    Ok(processed)
}

fn find_apply_paths(view: &Value, path: &str, hits: &mut Vec<String>) {
    match view {
        Value::Array(arr) => {
            for (i, child) in arr.iter().enumerate() {
                find_apply_paths(child, &format!("{path}/{i}"), hits);
            }
        }
        Value::Object(obj) => {
            if obj.get("op").and_then(|v| v.as_str()) == Some(APPLY_OP) {
                hits.push(path.to_string());
            }
            for (k, v) in obj {
                find_apply_paths(v, &format!("{path}/{k}"), hits);
            }
        }
        _ => {}
    }
}

/// Reject `expression_templates` and `apply_expression_template` constructs
/// in files declaring `esm` < 0.4.0. Mirrors the equivalent TS / Python /
/// Julia / Go checks for cross-binding-uniform diagnostics.
pub fn reject_expression_templates_pre_v04(view: &Value) -> Result<(), ExpressionTemplateError> {
    let Some(obj) = view.as_object() else {
        return Ok(());
    };
    let Some(esm) = obj.get("esm").and_then(|v| v.as_str()) else {
        return Ok(());
    };
    let parts: Vec<&str> = esm.split('.').collect();
    if parts.len() != 3 {
        return Ok(());
    }
    let major: u32 = match parts[0].parse() {
        Ok(v) => v,
        Err(_) => return Ok(()),
    };
    let minor: u32 = match parts[1].parse() {
        Ok(v) => v,
        Err(_) => return Ok(()),
    };
    if !(major == 0 && minor < 4) {
        return Ok(());
    }

    let mut offences: Vec<String> = Vec::new();
    for compkind in ["models", "reaction_systems"] {
        if let Some(comps) = obj.get(compkind).and_then(|v| v.as_object()) {
            for (cname, comp) in comps {
                if let Some(comp_obj) = comp.as_object()
                    && comp_obj.contains_key("expression_templates")
                {
                    offences.push(format!("/{compkind}/{cname}/expression_templates"));
                }
            }
        }
    }
    find_apply_paths(view, "", &mut offences);

    if !offences.is_empty() {
        return Err(err(
            "apply_expression_template_version_too_old",
            format!(
                "expression_templates / apply_expression_template require esm >= 0.4.0; \
                 file declares {esm}. Offending paths: {}",
                offences.join(", ")
            ),
        ));
    }
    Ok(())
}

/// Run the single load-time rewrite pass (esm-spec §9.6): expand every
/// `apply_expression_template` op, auto-apply each component's `match` rules in
/// declaration order, and strip the `expression_templates` blocks. Mutates
/// `value` in place. This is the format's one structural-substitution engine —
/// variable substitution, named-template expansion, and PDE-operator / `bc`
/// lowering all flow through [`rewrite`].
///
/// Pre-condition: the input has been schema-validated.
pub fn lower_expression_templates(value: &mut Value) -> Result<(), ExpressionTemplateError> {
    reject_expression_templates_pre_v04(value)?;

    let Some(root) = value.as_object_mut() else {
        return Ok(());
    };

    for compkind in ["models", "reaction_systems"] {
        let Some(Value::Object(comps)) = root.get_mut(compkind) else {
            continue;
        };
        for (cname, comp_value) in comps.iter_mut() {
            let Value::Object(comp) = comp_value else {
                continue;
            };
            let scope_base = format!("{compkind}.{cname}");
            // Take the templates block (if any) so we can borrow comp mutably.
            let templates: Map<String, Value> = match comp.remove("expression_templates") {
                Some(Value::Object(t)) => t,
                _ => Map::new(),
            };
            // A template-less component has nothing to expand or auto-apply.
            // Stray `apply_expression_template` nodes (if any) are caught by
            // the post-pass leftover scan below as `unknown_template`.
            if templates.is_empty() {
                continue;
            }
            validate_templates(&templates, &scope_base)?;
            let rules = collect_match_rules(&templates, &scope_base)?;
            let ctx = RewriteCtx {
                templates: &templates,
                rules: &rules,
            };
            let keys: Vec<String> = comp.keys().cloned().collect();
            for k in keys {
                let scope = format!("{scope_base}.{k}");
                if let Some(child) = comp.get(&k).cloned() {
                    let rewritten = rewrite(&child, &ctx, &scope)?;
                    comp.insert(k, rewritten);
                }
            }
        }
    }

    let mut leftover: Vec<String> = Vec::new();
    find_apply_paths(value, "", &mut leftover);
    if !leftover.is_empty() {
        return Err(err(
            "apply_expression_template_unknown_template",
            format!(
                "apply_expression_template ops remain after expansion at: {} \
                 — likely referenced from a component lacking an expression_templates block",
                leftover.join(", ")
            ),
        ));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn arrhenius_fixture() -> Value {
        json!({
          "esm": "0.4.0",
          "metadata": {"name": "expr_template_smoke", "authors": ["esm-giy"]},
          "reaction_systems": {
            "chem": {
              "species": {"A": {"default": 1.0}, "B": {"default": 0.5}},
              "parameters": {"T": {"default": 298.15}, "num_density": {"default": 2.5e19}},
              "expression_templates": {
                "arrhenius": {
                  "params": ["A_pre", "Ea"],
                  "body": {
                    "op": "*",
                    "args": [
                      "A_pre",
                      {"op": "exp", "args": [
                        {"op": "/", "args": [{"op": "-", "args": ["Ea"]}, "T"]}
                      ]},
                      "num_density"
                    ]
                  }
                }
              },
              "reactions": [
                {"id": "R1",
                 "substrates": [{"species": "A", "stoichiometry": 1}],
                 "products": [{"species": "B", "stoichiometry": 1}],
                 "rate": {"op": "apply_expression_template", "args": [],
                          "name": "arrhenius",
                          "bindings": {"A_pre": 1.8e-12, "Ea": 1500}}}
              ]
            }
          }
        })
    }

    #[test]
    fn expansion_strips_templates_block_and_replaces_apply_node() {
        let mut v = arrhenius_fixture();
        lower_expression_templates(&mut v).expect("expansion");
        let chem = &v["reaction_systems"]["chem"];
        assert!(chem.get("expression_templates").is_none());
        let rate = &chem["reactions"][0]["rate"];
        assert_eq!(rate["op"], json!("*"));
        // First arg: the scalar 1.8e-12.
        assert_eq!(rate["args"][0], json!(1.8e-12));
    }

    #[test]
    fn rejects_unknown_template_name() {
        let mut v = arrhenius_fixture();
        v["reaction_systems"]["chem"]["reactions"][0]["rate"]["name"] = json!("missing");
        let e = lower_expression_templates(&mut v).expect_err("should fail");
        assert_eq!(e.code, "apply_expression_template_unknown_template");
    }

    #[test]
    fn rejects_missing_binding() {
        let mut v = arrhenius_fixture();
        v["reaction_systems"]["chem"]["reactions"][0]["rate"]["bindings"]
            .as_object_mut()
            .unwrap()
            .remove("Ea");
        let e = lower_expression_templates(&mut v).expect_err("should fail");
        assert_eq!(e.code, "apply_expression_template_bindings_mismatch");
    }

    #[test]
    fn rejects_extra_binding() {
        let mut v = arrhenius_fixture();
        v["reaction_systems"]["chem"]["reactions"][0]["rate"]["bindings"]["bogus"] = json!(99);
        let e = lower_expression_templates(&mut v).expect_err("should fail");
        assert_eq!(e.code, "apply_expression_template_bindings_mismatch");
    }

    #[test]
    fn rejects_recursive_body() {
        let mut v = arrhenius_fixture();
        v["reaction_systems"]["chem"]["expression_templates"]["arrhenius"]["body"] = json!({
            "op": "apply_expression_template",
            "args": [],
            "name": "arrhenius",
            "bindings": {"A_pre": 1, "Ea": 1}
        });
        let e = lower_expression_templates(&mut v).expect_err("should fail");
        assert_eq!(e.code, "apply_expression_template_recursive_body");
    }

    #[test]
    fn rejects_pre_v04_files_using_templates() {
        let mut v = arrhenius_fixture();
        v["esm"] = json!("0.3.5");
        let e = lower_expression_templates(&mut v).expect_err("should fail");
        assert_eq!(e.code, "apply_expression_template_version_too_old");
    }

    #[test]
    fn ast_valued_bindings_substitute_into_body() {
        let mut v = arrhenius_fixture();
        v["reaction_systems"]["chem"]["reactions"][0]["rate"]["bindings"]["Ea"] = json!({
            "op": "*", "args": [3, "T"]
        });
        lower_expression_templates(&mut v).expect("expansion");
        let rate = &v["reaction_systems"]["chem"]["reactions"][0]["rate"];
        let exp_node = &rate["args"][1];
        assert_eq!(exp_node["op"], json!("exp"));
        let div_node = &exp_node["args"][0];
        assert_eq!(div_node["op"], json!("/"));
        let neg_node = &div_node["args"][0];
        assert_eq!(neg_node["op"], json!("-"));
        let inner = &neg_node["args"][0];
        assert_eq!(inner["op"], json!("*"));
    }

    #[test]
    fn conformance_fixture_matches_expanded_form() {
        let manifest_dir = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        let repo_root = manifest_dir
            .parent()
            .and_then(|p| p.parent())
            .expect("repo_root from CARGO_MANIFEST_DIR")
            .to_path_buf();
        let fixture_path =
            repo_root.join("tests/conformance/expression_templates/arrhenius_smoke/fixture.esm");
        let expanded_path =
            repo_root.join("tests/conformance/expression_templates/arrhenius_smoke/expanded.esm");
        let src = std::fs::read_to_string(&fixture_path).expect("read fixture.esm");
        let mut got: Value = serde_json::from_str(&src).expect("parse fixture");
        lower_expression_templates(&mut got).expect("expansion");
        let expanded_src = std::fs::read_to_string(&expanded_path).expect("read expanded.esm");
        let want: Value = serde_json::from_str(&expanded_src).expect("parse expanded");
        let got_reactions = &got["reaction_systems"]["chem"]["reactions"];
        let want_reactions = &want["reaction_systems"]["chem"]["reactions"];
        assert_eq!(got_reactions, want_reactions);
    }

    #[test]
    fn no_templates_block_is_a_noop() {
        let mut v = json!({
            "esm": "0.4.0",
            "metadata": {"name": "no_templates", "authors": ["t"]},
            "reaction_systems": {
                "chem": {
                    "species": {"A": {}},
                    "parameters": {"k": {"default": 1.0}},
                    "reactions": [{
                        "id": "R1",
                        "substrates": [{"species": "A", "stoichiometry": 1}],
                        "products": null,
                        "rate": "k"
                    }]
                }
            }
        });
        lower_expression_templates(&mut v).expect("expansion");
        assert_eq!(
            v["reaction_systems"]["chem"]["reactions"][0]["rate"],
            json!("k")
        );
    }

    /// A `match` rule (esm-spec §9.6) auto-applies wherever its operator pattern
    /// matches — no `apply_expression_template` node required — binding an
    /// operand metavariable to the matched sub-AST. Non-matching siblings (the
    /// equation LHS) are left untouched.
    #[test]
    fn match_rule_lowers_grad_operator() {
        let mut v = json!({
          "esm": "0.4.0",
          "metadata": {"name": "grad_lowering", "authors": ["t"]},
          "models": {
            "Diff": {
              "variables": {"u": {"type": "state"}},
              "expression_templates": {
                "central_grad_x": {
                  "params": ["f"],
                  "match": {"op": "grad", "args": ["f"], "dim": "x"},
                  "body": {
                    "op": "-",
                    "args": [
                      {"op": "index", "args": ["f", {"op": "+", "args": ["i", 1]}]},
                      {"op": "index", "args": ["f", {"op": "-", "args": ["i", 1]}]}
                    ]
                  }
                }
              },
              "equations": [
                {"lhs": {"op": "D", "args": ["u"], "wrt": "t"},
                 "rhs": {"op": "grad", "args": ["u"], "dim": "x"}}
              ]
            }
          }
        });
        lower_expression_templates(&mut v).expect("rewrite");
        let model = &v["models"]["Diff"];
        assert!(model.get("expression_templates").is_none());
        let rhs = &model["equations"][0]["rhs"];
        // grad(u, dim=x) lowered to the finite-difference body, f -> "u".
        assert_eq!(rhs["op"], json!("-"));
        assert_eq!(rhs["args"][0]["op"], json!("index"));
        assert_eq!(rhs["args"][0]["args"][0], json!("u"));
        assert_eq!(rhs["args"][1]["args"][0], json!("u"));
        // The non-matching LHS is left untouched.
        assert_eq!(model["equations"][0]["lhs"]["op"], json!("D"));
    }

    /// A metavariable appearing in a scalar field (`dim`) binds the matched
    /// literal, while one in `args` binds the matched sub-AST.
    #[test]
    fn match_rule_binds_scalar_field_metavariable() {
        let mut v = json!({
          "esm": "0.4.0",
          "metadata": {"name": "scalar_meta", "authors": ["t"]},
          "models": {
            "M": {
              "variables": {"u": {"type": "state"}},
              "expression_templates": {
                "grad_to_deriv": {
                  "params": ["f", "d"],
                  "match": {"op": "grad", "args": ["f"], "dim": "d"},
                  "body": {"op": "deriv", "args": ["f"], "wrt": "d"}
                }
              },
              "equations": [
                {"lhs": "u", "rhs": {"op": "grad", "args": ["u"], "dim": "y"}}
              ]
            }
          }
        });
        lower_expression_templates(&mut v).expect("rewrite");
        let rhs = &v["models"]["M"]["equations"][0]["rhs"];
        assert_eq!(rhs["op"], json!("deriv"));
        assert_eq!(rhs["args"][0], json!("u")); // operand metavar f -> "u"
        assert_eq!(rhs["wrt"], json!("y")); // scalar metavar d -> literal "y"
    }

    /// A `match` rule whose `body` re-introduces its own pattern is rejected;
    /// replacements are never re-scanned (esm-spec §9.6.3).
    #[test]
    fn rejects_nonterminating_match_rule() {
        let mut v = json!({
          "esm": "0.4.0",
          "metadata": {"name": "nonterm", "authors": ["t"]},
          "models": {
            "M": {
              "variables": {"u": {"type": "state"}},
              "expression_templates": {
                "loop_rule": {
                  "params": ["f"],
                  "match": {"op": "grad", "args": ["f"], "dim": "x"},
                  "body": {"op": "+", "args": [
                    {"op": "grad", "args": ["f"], "dim": "x"}, 1]}
                }
              },
              "equations": [
                {"lhs": "u", "rhs": {"op": "grad", "args": ["u"], "dim": "x"}}
              ]
            }
          }
        });
        let e = lower_expression_templates(&mut v).expect_err("should fail");
        assert_eq!(e.code, "rewrite_rule_nonterminating");
    }

    /// Rules are applied in template *declaration order* (not the alphabetical
    /// key order of an unordered map): the first declared rule whose pattern
    /// matches wins. `z_rule` is declared before `a_rule`, so it must fire.
    #[test]
    fn match_rules_apply_in_declaration_order() {
        let mut v = json!({
          "esm": "0.4.0",
          "metadata": {"name": "order", "authors": ["t"]},
          "models": {
            "M": {
              "variables": {"u": {"type": "state"}},
              "expression_templates": {
                "z_rule": {
                  "params": ["f"],
                  "match": {"op": "grad", "args": ["f"], "dim": "x"},
                  "body": {"op": "winner", "args": ["f"]}
                },
                "a_rule": {
                  "params": ["f"],
                  "match": {"op": "grad", "args": ["f"], "dim": "x"},
                  "body": {"op": "loser", "args": ["f"]}
                }
              },
              "equations": [
                {"lhs": "u", "rhs": {"op": "grad", "args": ["u"], "dim": "x"}}
              ]
            }
          }
        });
        lower_expression_templates(&mut v).expect("rewrite");
        let rhs = &v["models"]["M"]["equations"][0]["rhs"];
        assert_eq!(rhs["op"], json!("winner"));
    }
}
