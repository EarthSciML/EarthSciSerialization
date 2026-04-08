//! WASM bindings for ESM format library
//!
//! This module provides WebAssembly bindings for use with TypeScript/JavaScript.

#[cfg(feature = "wasm")]
use wasm_bindgen::prelude::*;
#[cfg(feature = "wasm")]
use crate::{
    EsmFile, load as rust_load, save as rust_save, validate as rust_validate,
    substitute_in_model, substitute_in_reaction_system,
    performance::{CompactExpr, PerformanceError},
    stoichiometric_matrix,
    graph::component_graph as rust_component_graph
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

/// Convert ESM file to ASCII display (WASM version)
#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn to_ascii(json_str: &str) -> Result<String, JsValue> {
    let esm_file = rust_load(json_str)
        .map_err(|e| JsValue::from_str(&format!("Parse error: {}", e)))?;

    // Simple implementation: convert the JSON to an ASCII-friendly string representation
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

/// Create a compact expression for fast evaluation (WASM version)
#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn create_compact_expression(expr_str: &str) -> Result<JsValue, JsValue> {
    // Parse expression from JSON string
    let expr: crate::Expr = serde_json::from_str(expr_str)
        .map_err(|e| JsValue::from_str(&format!("Parse error: {}", e)))?;

    let compact = CompactExpr::from_expr(&expr);

    match serde_wasm_bindgen::to_value(&compact) {
        Ok(js_value) => Ok(js_value),
        Err(e) => Err(JsValue::from_str(&format!("Serialization error: {}", e))),
    }
}

/// Compute stoichiometric matrix (WASM version)
#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn compute_stoichiometric_matrix(reaction_system_str: &str) -> Result<JsValue, JsValue> {
    let reaction_system: crate::ReactionSystem = serde_json::from_str(reaction_system_str)
        .map_err(|e| JsValue::from_str(&format!("Parse error: {}", e)))?;

    let matrix = stoichiometric_matrix(&reaction_system);

    match serde_wasm_bindgen::to_value(&matrix) {
        Ok(js_value) => Ok(js_value),
        Err(e) => Err(JsValue::from_str(&format!("Serialization error: {}", e))),
    }
}

/// Generate component graph for ESM file (WASM version)
#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn component_graph(json_str: &str) -> Result<JsValue, JsValue> {
    let esm_file = rust_load(json_str)
        .map_err(|e| JsValue::from_str(&format!("Parse error: {}", e)))?;

    let graph = rust_component_graph(&esm_file);

    match serde_wasm_bindgen::to_value(&graph) {
        Ok(js_value) => Ok(js_value),
        Err(e) => Err(JsValue::from_str(&format!("Serialization error: {}", e))),
    }
}

/// Get performance metrics (WASM version)
#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn get_performance_info() -> JsValue {
    let info = serde_json::json!({
        "features": {
            "parallel": cfg!(feature = "parallel"),
            "simd": cfg!(feature = "simd"),
            "zero_copy": cfg!(feature = "zero_copy"),
            "custom_alloc": cfg!(feature = "custom_alloc"),
            "wasm": true
        },
        "version": crate::VERSION,
        "schema_version": crate::SCHEMA_VERSION
    });

    serde_wasm_bindgen::to_value(&info).unwrap_or(JsValue::NULL)
}

/// Benchmark parsing performance (WASM version)
#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn benchmark_parsing(json_str: &str, iterations: u32) -> Result<f64, JsValue> {
    let start = js_sys::Date::now();

    for _ in 0..iterations {
        rust_load(json_str)
            .map_err(|e| JsValue::from_str(&format!("Parse error: {}", e)))?;
    }

    let end = js_sys::Date::now();
    let total_time = end - start;

    Ok(total_time / iterations as f64)
}

/// Initialize WASM module
#[cfg(feature = "wasm")]
#[wasm_bindgen(start)]
pub fn main() {
    console_log!("ESM Format Rust WASM module initialized");
    console_log!("Features enabled: parallel={}, simd={}, zero_copy={}, custom_alloc={}",
        cfg!(feature = "parallel"),
        cfg!(feature = "simd"),
        cfg!(feature = "zero_copy"),
        cfg!(feature = "custom_alloc")
    );
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_new_wasm_exports_compile() {
        let json = r#"{
            "esm": "0.1.0",
            "metadata": {
                "name": "Test Model",
                "description": "A simple test model for WASM exports"
            },
            "models": {
                "SimpleModel": {
                    "name": "Simple Model",
                    "variables": {
                        "x": {"type": "state", "units": "m", "initial_value": 1.0},
                        "k": {"type": "parameter", "value": 0.5}
                    },
                    "equations": [
                        {"lhs": {"op": "D", "args": ["x"]}, "rhs": {"op": "*", "args": ["k", "x"]}}
                    ]
                }
            }
        }"#;

        // Test that the core functions work (without WASM feature for regular tests)
        let esm_file = rust_load(json).expect("Should load valid ESM file");
        let graph = rust_component_graph(&esm_file);

        assert_eq!(graph.nodes.len(), 1, "Should have 1 model node");
        assert_eq!(graph.edges.len(), 0, "Should have no edges");
        assert_eq!(graph.nodes[0].id, "SimpleModel");

        println!("✓ New WASM export functions compile and core functionality works");
    }
}