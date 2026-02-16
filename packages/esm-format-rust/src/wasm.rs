//! WASM bindings for ESM format library
//!
//! This module provides WebAssembly bindings for use with TypeScript/JavaScript.

#[cfg(feature = "wasm")]
use wasm_bindgen::prelude::*;
#[cfg(feature = "wasm")]
use crate::{
    EsmFile, load as rust_load, save as rust_save, validate as rust_validate,
    substitute_in_model, substitute_in_reaction_system
};

// WASM bindings
#[cfg(feature = "wasm")]
#[wasm_bindgen]
extern "C" {
    #[wasm_bindgen(js_namespace = console)]
    fn log(s: &str);
}

#[cfg(feature = "wasm")]
macro_rules! console_log {
    ($($t:tt)*) => (log(&format_args!($($t)*).to_string()))
}

/// Load an ESM file from JSON string (WASM version)
#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn load(json_str: &str) -> Result<JsValue, JsValue> {
    match rust_load(json_str) {
        Ok(esm_file) => {
            match serde_wasm_bindgen::to_value(&esm_file) {
                Ok(js_value) => Ok(js_value),
                Err(e) => Err(JsValue::from_str(&format!("Serialization error: {}", e))),
            }
        },
        Err(e) => Err(JsValue::from_str(&format!("Load error: {}", e))),
    }
}

/// Save an ESM file to JSON string (WASM version)
#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn save(esm_file_js: &JsValue) -> Result<String, JsValue> {
    let esm_file: EsmFile = serde_wasm_bindgen::from_value(esm_file_js.clone())
        .map_err(|e| JsValue::from_str(&format!("Deserialization error: {}", e)))?;

    match rust_save(&esm_file) {
        Ok(json) => Ok(json),
        Err(e) => Err(JsValue::from_str(&format!("Save error: {}", e))),
    }
}

/// Validate an ESM file (WASM version)
#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn validate(json_str: &str) -> Result<JsValue, JsValue> {
    let esm_file = rust_load(json_str)
        .map_err(|e| JsValue::from_str(&format!("Parse error: {}", e)))?;

    let result = rust_validate(&esm_file);

    match serde_wasm_bindgen::to_value(&result) {
        Ok(js_value) => Ok(js_value),
        Err(e) => Err(JsValue::from_str(&format!("Serialization error: {}", e))),
    }
}

/// Convert ESM file to Unicode display (WASM version)
#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn to_unicode(json_str: &str) -> Result<String, JsValue> {
    let esm_file = rust_load(json_str)
        .map_err(|e| JsValue::from_str(&format!("Parse error: {}", e)))?;

    // Simple implementation: convert the JSON to a Unicode-friendly string representation
    let mut result = String::new();
    result.push_str(&format!("ESM Format v{}\n", esm_file.esm));

    let metadata = &esm_file.metadata;
    if let Some(ref name) = metadata.name {
        result.push_str(&format!("Name: {}\n", name));
    }
    if let Some(ref desc) = metadata.description {
        result.push_str(&format!("Description: {}\n", desc));
    }

    if let Some(models) = &esm_file.models {
        result.push_str(&format!("\n{} Models:\n", models.len()));
        for (name, _) in models {
            result.push_str(&format!("• {}\n", name));
        }
    }

    Ok(result)
}

/// Convert ESM file to LaTeX display (WASM version)
#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn to_latex(json_str: &str) -> Result<String, JsValue> {
    let esm_file = rust_load(json_str)
        .map_err(|e| JsValue::from_str(&format!("Parse error: {}", e)))?;

    // Simple implementation: convert the JSON to a LaTeX-friendly string representation
    let mut result = String::new();
    result.push_str(&format!("\\textbf{{ESM Format v{}}}\\\\\n", esm_file.esm));

    let metadata = &esm_file.metadata;
    if let Some(ref name) = metadata.name {
        result.push_str(&format!("\\textit{{Name:}} {}\\\\\n", name));
    }
    if let Some(ref desc) = metadata.description {
        result.push_str(&format!("\\textit{{Description:}} {}\\\\\n", desc));
    }

    if let Some(models) = &esm_file.models {
        result.push_str(&format!("\n\\textbf{{{} Models:}}\\\\\n", models.len()));
        for (name, _) in models {
            result.push_str(&format!("$\\bullet$ {}\\\\\n", name));
        }
    }

    Ok(result)
}

/// Substitute expressions in ESM file (WASM version)
#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn substitute(json_str: &str, bindings_str: &str) -> Result<String, JsValue> {
    use crate::Expr;

    let esm_file = rust_load(json_str)
        .map_err(|e| JsValue::from_str(&format!("Parse error: {}", e)))?;

    // Parse bindings as JSON object
    let bindings: serde_json::Value = serde_json::from_str(bindings_str)
        .map_err(|e| JsValue::from_str(&format!("Bindings parse error: {}", e)))?;

    // Convert bindings to Expr objects
    let mut expr_bindings = std::collections::HashMap::new();
    if let serde_json::Value::Object(obj) = bindings {
        for (key, value) in obj {
            let expr = match value {
                serde_json::Value::Number(n) => {
                    if let Some(f) = n.as_f64() {
                        Expr::Number(f)
                    } else {
                        return Err(JsValue::from_str(&format!("Invalid number in bindings: {}", n)));
                    }
                },
                serde_json::Value::String(s) => {
                    // Try to parse as number first, otherwise treat as variable
                    if let Ok(f) = s.parse::<f64>() {
                        Expr::Number(f)
                    } else {
                        Expr::Variable(s)
                    }
                },
                _ => {
                    return Err(JsValue::from_str(&format!("Unsupported binding type for key '{}': {:?}", key, value)));
                }
            };
            expr_bindings.insert(key, expr);
        }
    }

    let mut result_file = esm_file.clone();

    // Apply substitutions to all models
    if let Some(ref mut models) = result_file.models {
        for (_, model) in models.iter_mut() {
            *model = substitute_in_model(model, &expr_bindings);
        }
    }

    // Apply substitutions to reaction systems if present
    if let Some(ref mut reactions) = result_file.reaction_systems {
        for (_, reaction_system) in reactions.iter_mut() {
            *reaction_system = substitute_in_reaction_system(reaction_system, &expr_bindings);
        }
    }

    // Convert back to JSON string
    match rust_save(&result_file) {
        Ok(json) => Ok(json),
        Err(e) => Err(JsValue::from_str(&format!("Save error: {}", e))),
    }
}

/// Initialize WASM module
#[cfg(feature = "wasm")]
#[wasm_bindgen(start)]
pub fn main() {
    console_log!("ESM Format Rust WASM module initialized");
}