//! Parse-time expansion of `expression_templates` (RFC v2 §4 Option A
//! always-expanded; docs/content/rfcs/ast-expression-templates.md, esm-giy).
//!
//! Operates on the in-memory `serde_json::Value` tree before
//! deserialization into typed `EsmFile`. Templates are component-local
//! (declared inside one Model or ReactionSystem). After expansion every
//! `apply_expression_template` reference has been replaced by the
//! substituted body and the originating `expression_templates` block
//! has been removed.

use serde_json::{Map, Value};

use crate::error::EsmError;

const APPLY_OP: &str = "apply_expression_template";

/// Expand `expression_templates` in place across all models and reaction
/// systems. Mutates `root`. Returns `EsmError::SchemaValidation` if the
/// file declares `esm: < 0.4.0` while using templates or
/// `apply_expression_template`.
pub fn expand_expression_templates(root: &mut Value) -> Result<(), EsmError> {
    let Some(obj) = root.as_object_mut() else {
        return Ok(());
    };

    let has_use = scan_for_apply_template(&Value::Object(obj.clone()));
    let mut has_block = false;
    for section in ["models", "reaction_systems"] {
        if let Some(comps) = obj.get(section).and_then(Value::as_object) {
            for c in comps.values() {
                if let Some(t) = c.get("expression_templates").and_then(Value::as_object) {
                    if !t.is_empty() {
                        has_block = true;
                        break;
                    }
                }
            }
        }
        if has_block {
            break;
        }
    }
    if has_use || has_block {
        let v = obj.get("esm").and_then(Value::as_str).unwrap_or("");
        if !esm_version_at_least(v, 0, 4, 0) {
            return Err(EsmError::SchemaValidation(format!(
                "expression_templates / apply_expression_template require esm: 0.4.0 or later \
                 (file declares esm: {v:?})"
            )));
        }
    }

    for section in ["models", "reaction_systems"] {
        let Some(comps) = obj.get_mut(section).and_then(Value::as_object_mut) else {
            continue;
        };
        let names: Vec<String> = comps.keys().cloned().collect();
        for n in names {
            if let Some(c) = comps.get_mut(&n).and_then(Value::as_object_mut) {
                expand_in_component(c)?;
            }
        }
    }
    Ok(())
}

fn expand_in_component(component: &mut Map<String, Value>) -> Result<(), EsmError> {
    let templates_value = component.remove("expression_templates").unwrap_or(Value::Null);
    let templates: Map<String, Value> = match templates_value {
        Value::Object(m) => m,
        _ => Map::new(),
    };

    if !templates.is_empty() {
        let keys: Vec<String> = component
            .keys()
            .filter(|k| k.as_str() != "subsystems")
            .cloned()
            .collect();
        for k in keys {
            if let Some(v) = component.remove(&k) {
                let rewritten = expand_walk(v, &templates)?;
                component.insert(k, rewritten);
            }
        }
    }

    if let Some(subs) = component.get_mut("subsystems").and_then(Value::as_object_mut) {
        let sub_keys: Vec<String> = subs.keys().cloned().collect();
        for sk in sub_keys {
            if let Some(sub) = subs.get_mut(&sk).and_then(Value::as_object_mut) {
                if sub.contains_key("ref") {
                    continue;
                }
                expand_in_component(sub)?;
            }
        }
    }
    Ok(())
}

fn expand_walk(node: Value, templates: &Map<String, Value>) -> Result<Value, EsmError> {
    match node {
        Value::Object(mut obj) => {
            if obj.get("op").and_then(Value::as_str) == Some(APPLY_OP) {
                return expand_apply_node(&obj, templates);
            }
            let keys: Vec<String> = obj.keys().cloned().collect();
            for k in keys {
                if let Some(v) = obj.remove(&k) {
                    obj.insert(k, expand_walk(v, templates)?);
                }
            }
            Ok(Value::Object(obj))
        }
        Value::Array(arr) => {
            let mut out = Vec::with_capacity(arr.len());
            for v in arr {
                out.push(expand_walk(v, templates)?);
            }
            Ok(Value::Array(out))
        }
        v => Ok(v),
    }
}

fn expand_apply_node(
    node: &Map<String, Value>,
    templates: &Map<String, Value>,
) -> Result<Value, EsmError> {
    let name = node.get("name").and_then(Value::as_str).unwrap_or("");
    let template = templates.get(name).and_then(Value::as_object).ok_or_else(|| {
        EsmError::SchemaValidation(format!(
            "apply_expression_template references unknown template {name:?}"
        ))
    })?;
    let params: Vec<String> = template
        .get("params")
        .and_then(Value::as_array)
        .map(|a| {
            a.iter()
                .filter_map(|v| v.as_str().map(String::from))
                .collect()
        })
        .unwrap_or_default();
    let bindings = node.get("bindings").and_then(Value::as_object).ok_or_else(|| {
        EsmError::SchemaValidation(format!(
            "apply_expression_template {name:?} missing 'bindings' object"
        ))
    })?;
    for p in &params {
        if !bindings.contains_key(p) {
            return Err(EsmError::SchemaValidation(format!(
                "apply_expression_template {name:?} missing binding {p:?}"
            )));
        }
    }
    for k in bindings.keys() {
        if !params.iter().any(|p| p == k) {
            return Err(EsmError::SchemaValidation(format!(
                "apply_expression_template {name:?} has unknown binding {k:?}"
            )));
        }
    }
    let body = template.get("body").cloned().unwrap_or(Value::Null);
    Ok(substitute_template_body(body, bindings))
}

fn substitute_template_body(body: Value, bindings: &Map<String, Value>) -> Value {
    match body {
        Value::String(s) => {
            if let Some(b) = bindings.get(&s) {
                b.clone()
            } else {
                Value::String(s)
            }
        }
        Value::Object(mut obj) => {
            let keys: Vec<String> = obj.keys().cloned().collect();
            for k in keys {
                let v = obj.remove(&k).unwrap();
                let new_v = match k.as_str() {
                    "args" | "values" => match v {
                        Value::Array(arr) => Value::Array(
                            arr.into_iter()
                                .map(|x| substitute_template_body(x, bindings))
                                .collect(),
                        ),
                        other => other,
                    },
                    "expr" => substitute_template_body(v, bindings),
                    _ => v,
                };
                obj.insert(k, new_v);
            }
            Value::Object(obj)
        }
        Value::Array(arr) => Value::Array(
            arr.into_iter()
                .map(|x| substitute_template_body(x, bindings))
                .collect(),
        ),
        v => v,
    }
}

fn scan_for_apply_template(node: &Value) -> bool {
    match node {
        Value::Object(obj) => {
            if obj.get("op").and_then(Value::as_str) == Some(APPLY_OP) {
                return true;
            }
            obj.values().any(scan_for_apply_template)
        }
        Value::Array(arr) => arr.iter().any(scan_for_apply_template),
        _ => false,
    }
}

fn esm_version_at_least(v: &str, ma: u32, mi: u32, pa: u32) -> bool {
    let parts: Vec<&str> = v.split('.').collect();
    if parts.len() != 3 {
        return false;
    }
    let parsed: Vec<u32> = match parts.iter().map(|p| p.parse::<u32>()).collect() {
        Ok(v) => v,
        Err(_) => return false,
    };
    if parsed[0] != ma {
        return parsed[0] > ma;
    }
    if parsed[1] != mi {
        return parsed[1] > mi;
    }
    parsed[2] >= pa
}
