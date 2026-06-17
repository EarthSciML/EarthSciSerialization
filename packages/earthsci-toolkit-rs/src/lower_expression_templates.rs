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

fn expand_apply(
    node: &Map<String, Value>,
    templates: &Map<String, Value>,
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
    let decl = templates.get(name).ok_or_else(|| {
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

    // Recursively expand bindings (template bodies cannot contain
    // apply_expression_template, but the *bindings* may).
    let mut resolved = Map::new();
    for (k, v) in bindings {
        resolved.insert(k.clone(), walk(v, templates, scope)?);
    }
    let body = decl_obj.get("body").cloned().unwrap_or(Value::Null);
    Ok(substitute(&body, &resolved))
}

fn walk(
    node: &Value,
    templates: &Map<String, Value>,
    scope: &str,
) -> Result<Value, ExpressionTemplateError> {
    match node {
        Value::Array(arr) => {
            let mut out = Vec::with_capacity(arr.len());
            for c in arr {
                out.push(walk(c, templates, scope)?);
            }
            Ok(Value::Array(out))
        }
        Value::Object(obj) => {
            if obj.get("op").and_then(|v| v.as_str()) == Some(APPLY_OP) {
                expand_apply(obj, templates, scope)
            } else {
                let mut out = Map::new();
                for (k, v) in obj {
                    out.insert(k.clone(), walk(v, templates, scope)?);
                }
                Ok(Value::Object(out))
            }
        }
        _ => Ok(node.clone()),
    }
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
                if let Some(comp_obj) = comp.as_object() {
                    if comp_obj.contains_key("expression_templates") {
                        offences.push(format!("/{compkind}/{cname}/expression_templates"));
                    }
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

/// Expand all `apply_expression_template` ops in `value` and strip
/// `expression_templates` blocks. Mutates `value` in place.
///
/// Pre-condition: the input has been schema-validated.
pub fn lower_expression_templates(value: &mut Value) -> Result<(), ExpressionTemplateError> {
    reject_expression_templates_pre_v04(value)?;

    let Some(_root) = value.as_object_mut() else {
        return Ok(());
    };

    let mut apply_paths: Vec<String> = Vec::new();
    find_apply_paths(value, "", &mut apply_paths);

    if apply_paths.is_empty() {
        strip_expression_templates(value);
        return Ok(());
    }

    let root = value.as_object_mut().unwrap();
    for compkind in ["models", "reaction_systems"] {
        let Some(Value::Object(comps)) = root.get_mut(compkind) else {
            continue;
        };
        for (cname, comp_value) in comps.iter_mut() {
            let Value::Object(comp) = comp_value else {
                continue;
            };
            // Take the templates block (if any) so we can borrow comp mutably.
            let templates_value = comp.remove("expression_templates");
            let templates: Map<String, Value> = match templates_value {
                Some(Value::Object(t)) => t,
                _ => Map::new(),
            };
            if !templates.is_empty() {
                validate_templates(&templates, &format!("{compkind}.{cname}"))?;
            }
            let keys: Vec<String> = comp.keys().cloned().collect();
            for k in keys {
                if k == "expression_templates" {
                    continue;
                }
                let scope = format!("{compkind}.{cname}.{k}");
                if let Some(child) = comp.get(&k).cloned() {
                    let walked = walk(&child, &templates, &scope)?;
                    comp.insert(k, walked);
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

fn strip_expression_templates(value: &mut Value) {
    let Some(root) = value.as_object_mut() else {
        return;
    };
    for compkind in ["models", "reaction_systems"] {
        let Some(Value::Object(comps)) = root.get_mut(compkind) else {
            continue;
        };
        for (_, comp_value) in comps.iter_mut() {
            if let Value::Object(comp) = comp_value {
                comp.remove("expression_templates");
            }
        }
    }
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
}
