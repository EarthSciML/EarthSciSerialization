//! WASM bindings for earthsci-toolkit
//!
//! This module provides WebAssembly bindings for use with TypeScript/JavaScript.

#[cfg(feature = "wasm")]
use crate::{
    EsmFile, graph::component_graph as rust_component_graph, load as rust_load,
    performance::CompactExpr, save as rust_save, stoichiometric_matrix, substitute_in_model,
    substitute_in_reaction_system, validate as rust_validate,
};
#[cfg(feature = "wasm")]
use wasm_bindgen::prelude::*;

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
        Ok(esm_file) => match serde_wasm_bindgen::to_value(&esm_file) {
            Ok(js_value) => Ok(js_value),
            Err(e) => Err(JsValue::from_str(&format!("Serialization error: {e}"))),
        },
        Err(e) => Err(JsValue::from_str(&format!("Load error: {e}"))),
    }
}

/// Save an ESM file to JSON string (WASM version)
#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn save(esm_file_js: &JsValue) -> Result<String, JsValue> {
    let esm_file: EsmFile = serde_wasm_bindgen::from_value(esm_file_js.clone())
        .map_err(|e| JsValue::from_str(&format!("Deserialization error: {e}")))?;

    match rust_save(&esm_file) {
        Ok(json) => Ok(json),
        Err(e) => Err(JsValue::from_str(&format!("Save error: {e}"))),
    }
}

/// Validate an ESM file (WASM version)
#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn validate(json_str: &str) -> Result<JsValue, JsValue> {
    let esm_file =
        rust_load(json_str).map_err(|e| JsValue::from_str(&format!("Parse error: {e}")))?;

    let result = rust_validate(&esm_file);

    match serde_wasm_bindgen::to_value(&result) {
        Ok(js_value) => Ok(js_value),
        Err(e) => Err(JsValue::from_str(&format!("Serialization error: {e}"))),
    }
}

/// Convert ESM file to Unicode display (WASM version)
#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn to_unicode(json_str: &str) -> Result<String, JsValue> {
    let esm_file =
        rust_load(json_str).map_err(|e| JsValue::from_str(&format!("Parse error: {e}")))?;

    // Simple implementation: convert the JSON to a Unicode-friendly string representation
    let mut result = String::new();
    result.push_str(&format!("ESM Format v{}\n", esm_file.esm));

    let metadata = &esm_file.metadata;
    if let Some(ref name) = metadata.name {
        result.push_str(&format!("Name: {name}\n"));
    }
    if let Some(ref desc) = metadata.description {
        result.push_str(&format!("Description: {desc}\n"));
    }

    if let Some(models) = &esm_file.models {
        result.push_str(&format!("\n{} Models:\n", models.len()));
        for name in models.keys() {
            result.push_str(&format!("• {name}\n"));
        }
    }

    Ok(result)
}

/// Convert ESM file to LaTeX display (WASM version)
#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn to_latex(json_str: &str) -> Result<String, JsValue> {
    let esm_file =
        rust_load(json_str).map_err(|e| JsValue::from_str(&format!("Parse error: {e}")))?;

    // Simple implementation: convert the JSON to a LaTeX-friendly string representation
    let mut result = String::new();
    result.push_str(&format!("\\textbf{{ESM Format v{}}}\\\\\n", esm_file.esm));

    let metadata = &esm_file.metadata;
    if let Some(ref name) = metadata.name {
        result.push_str(&format!("\\textit{{Name:}} {name}\\\\\n"));
    }
    if let Some(ref desc) = metadata.description {
        result.push_str(&format!("\\textit{{Description:}} {desc}\\\\\n"));
    }

    if let Some(models) = &esm_file.models {
        result.push_str(&format!("\n\\textbf{{{} Models:}}\\\\\n", models.len()));
        for name in models.keys() {
            result.push_str(&format!("$\\bullet$ {name}\\\\\n"));
        }
    }

    Ok(result)
}

/// Convert ESM file to ASCII display (WASM version)
#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn to_ascii(json_str: &str) -> Result<String, JsValue> {
    let esm_file =
        rust_load(json_str).map_err(|e| JsValue::from_str(&format!("Parse error: {e}")))?;

    // Simple implementation: convert the JSON to an ASCII-friendly string representation
    let mut result = String::new();
    result.push_str(&format!("ESM Format v{}\n", esm_file.esm));

    let metadata = &esm_file.metadata;
    if let Some(ref name) = metadata.name {
        result.push_str(&format!("Name: {name}\n"));
    }
    if let Some(ref desc) = metadata.description {
        result.push_str(&format!("Description: {desc}\n"));
    }

    if let Some(models) = &esm_file.models {
        result.push_str(&format!("\n{} Models:\n", models.len()));
        for name in models.keys() {
            result.push_str(&format!("• {name}\n"));
        }
    }

    Ok(result)
}

/// Substitute expressions in ESM file (WASM version)
#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn substitute(json_str: &str, bindings_str: &str) -> Result<String, JsValue> {
    use crate::Expr;

    let esm_file =
        rust_load(json_str).map_err(|e| JsValue::from_str(&format!("Parse error: {e}")))?;

    // Parse bindings as JSON object
    let bindings: serde_json::Value = serde_json::from_str(bindings_str)
        .map_err(|e| JsValue::from_str(&format!("Bindings parse error: {e}")))?;

    // Convert bindings to Expr objects
    let mut expr_bindings = std::collections::HashMap::new();
    if let serde_json::Value::Object(obj) = bindings {
        for (key, value) in obj {
            let expr = match value {
                serde_json::Value::Number(n) => {
                    if let Some(f) = n.as_f64() {
                        Expr::Number(f)
                    } else {
                        return Err(JsValue::from_str(&format!(
                            "Invalid number in bindings: {n}"
                        )));
                    }
                }
                serde_json::Value::String(s) => {
                    // Try to parse as number first, otherwise treat as variable
                    if let Ok(f) = s.parse::<f64>() {
                        Expr::Number(f)
                    } else {
                        Expr::Variable(s)
                    }
                }
                _ => {
                    return Err(JsValue::from_str(&format!(
                        "Unsupported binding type for key '{key}': {value:?}"
                    )));
                }
            };
            expr_bindings.insert(key, expr);
        }
    }

    let mut result_file = esm_file.clone();

    // Apply substitutions to all models
    if let Some(ref mut models) = result_file.models {
        for model in models.values_mut() {
            *model = substitute_in_model(model, &expr_bindings);
        }
    }

    // Apply substitutions to reaction systems if present
    if let Some(ref mut reactions) = result_file.reaction_systems {
        for reaction_system in reactions.values_mut() {
            *reaction_system = substitute_in_reaction_system(reaction_system, &expr_bindings);
        }
    }

    // Convert back to JSON string
    match rust_save(&result_file) {
        Ok(json) => Ok(json),
        Err(e) => Err(JsValue::from_str(&format!("Save error: {e}"))),
    }
}

/// Create a compact expression for fast evaluation (WASM version)
#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn create_compact_expression(expr_str: &str) -> Result<JsValue, JsValue> {
    // Parse expression from JSON string
    let expr: crate::Expr = serde_json::from_str(expr_str)
        .map_err(|e| JsValue::from_str(&format!("Parse error: {e}")))?;

    let compact = CompactExpr::from_expr(&expr);

    match serde_wasm_bindgen::to_value(&compact) {
        Ok(js_value) => Ok(js_value),
        Err(e) => Err(JsValue::from_str(&format!("Serialization error: {e}"))),
    }
}

/// Compute stoichiometric matrix (WASM version)
#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn compute_stoichiometric_matrix(reaction_system_str: &str) -> Result<JsValue, JsValue> {
    let reaction_system: crate::ReactionSystem = serde_json::from_str(reaction_system_str)
        .map_err(|e| JsValue::from_str(&format!("Parse error: {e}")))?;

    let matrix = stoichiometric_matrix(&reaction_system);

    match serde_wasm_bindgen::to_value(&matrix) {
        Ok(js_value) => Ok(js_value),
        Err(e) => Err(JsValue::from_str(&format!("Serialization error: {e}"))),
    }
}

/// Run an ODE simulation in the browser (WASM version, gt-5ws / spike S1).
///
/// Flattens and solves the `.esm` file through diffsol's Faer backend, entirely
/// client-side. This is the **0-D / box-model** tier: pure-ODE files only.
/// Array-op or spatial files require the native `simulate_array` backend (the
/// s2bindings geometry kernel does not target wasm) and are rejected here with
/// an `UnsupportedDimensionalityError` — route those to the cloud workers.
///
/// Arguments:
/// - `json_str`: the `.esm` file as a JSON string.
/// - `t0`, `t_end`: the integration interval.
/// - `params_str`: JSON object mapping parameter name → value (`{}` for none).
/// - `ic_str`: JSON object mapping state name → initial value (`{}` to use the
///   model's `default`s).
/// - `opts_str`: JSON object, all fields optional —
///   `{ "solver": "bdf"|"sdirk"|"erk", "abstol": f64, "reltol": f64,
///      "maxSteps": u32, "outputPoints": u32 }`. `outputPoints` samples the
///   solution at that many evenly spaced times in `[t0, t_end]` (nice for
///   plotting); omit it to get the solver's natural step grid.
///
/// Returns a JS object `{ time: number[], state: number[][],
/// stateVariableNames: string[], metadata: {...} }` where
/// `state[i][k]` is variable `stateVariableNames[i]` at `time[k]`.
#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn simulate(
    json_str: &str,
    t0: f64,
    t_end: f64,
    params_str: &str,
    ic_str: &str,
    opts_str: &str,
) -> Result<JsValue, JsValue> {
    use crate::simulate::{SimulateOptions, SolverChoice, simulate as rust_simulate};
    use std::collections::HashMap;

    let esm_file =
        rust_load(json_str).map_err(|e| JsValue::from_str(&format!("Parse error: {e}")))?;

    let parse_map = |s: &str, what: &str| -> Result<HashMap<String, f64>, JsValue> {
        let s = s.trim();
        if s.is_empty() {
            return Ok(HashMap::new());
        }
        serde_json::from_str(s).map_err(|e| JsValue::from_str(&format!("{what} parse error: {e}")))
    };
    let params = parse_map(params_str, "Params")?;
    let initial_conditions = parse_map(ic_str, "Initial-conditions")?;

    let opts_json: serde_json::Value = {
        let s = opts_str.trim();
        if s.is_empty() {
            serde_json::json!({})
        } else {
            serde_json::from_str(s)
                .map_err(|e| JsValue::from_str(&format!("Options parse error: {e}")))?
        }
    };

    let mut opts = SimulateOptions::default();
    if let Some(s) = opts_json.get("solver").and_then(|v| v.as_str()) {
        opts.solver = match s.to_ascii_lowercase().as_str() {
            "bdf" => SolverChoice::Bdf,
            "sdirk" => SolverChoice::Sdirk,
            "erk" => SolverChoice::Erk,
            other => return Err(JsValue::from_str(&format!("Unknown solver '{other}'"))),
        };
    }
    if let Some(v) = opts_json.get("abstol").and_then(|v| v.as_f64()) {
        opts.abstol = v;
    }
    if let Some(v) = opts_json.get("reltol").and_then(|v| v.as_f64()) {
        opts.reltol = v;
    }
    if let Some(v) = opts_json.get("maxSteps").and_then(|v| v.as_u64()) {
        opts.max_steps = v as usize;
    }
    if let Some(n) = opts_json.get("outputPoints").and_then(|v| v.as_u64()) {
        let n = (n as usize).max(2);
        let span = t_end - t0;
        opts.output_times = Some(
            (0..n)
                .map(|i| t0 + span * (i as f64) / ((n - 1) as f64))
                .collect(),
        );
    }

    let sol = rust_simulate(&esm_file, (t0, t_end), &params, &initial_conditions, &opts)
        .map_err(|e| JsValue::from_str(&format!("Simulation error: {e}")))?;

    let out = serde_json::json!({
        "time": sol.time,
        "state": sol.state,
        "stateVariableNames": sol.state_variable_names,
        "metadata": {
            "solver": sol.metadata.solver,
            "nRhsCalls": sol.metadata.n_rhs_calls,
            "nJacobianCalls": sol.metadata.n_jacobian_calls,
            "nAcceptedSteps": sol.metadata.n_accepted_steps,
            "nRejectedSteps": sol.metadata.n_rejected_steps,
        }
    });

    // Serialize JSON objects as plain JS objects (not ES `Map`s) so callers can
    // use `result.time` / `result.state` dot-access.
    use serde::Serialize;
    let serializer = serde_wasm_bindgen::Serializer::new().serialize_maps_as_objects(true);
    out.serialize(&serializer)
        .map_err(|e| JsValue::from_str(&format!("Serialization error: {e}")))
}

/// Generate component graph for ESM file (WASM version)
#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn component_graph(json_str: &str) -> Result<JsValue, JsValue> {
    let esm_file =
        rust_load(json_str).map_err(|e| JsValue::from_str(&format!("Parse error: {e}")))?;

    let graph = rust_component_graph(&esm_file);

    match serde_wasm_bindgen::to_value(&graph) {
        Ok(js_value) => Ok(js_value),
        Err(e) => Err(JsValue::from_str(&format!("Serialization error: {e}"))),
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
        rust_load(json_str).map_err(|e| JsValue::from_str(&format!("Parse error: {e}")))?;
    }

    let end = js_sys::Date::now();
    let total_time = end - start;

    Ok(total_time / iterations as f64)
}

/// Initialize WASM module
#[cfg(feature = "wasm")]
#[wasm_bindgen(start)]
pub fn main() {
    console_log!("earthsci-toolkit Rust WASM module initialized");
    console_log!(
        "Features enabled: parallel={}, simd={}, zero_copy={}, custom_alloc={}",
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
                    "variables": {
                        "x": {"type": "state", "units": "m", "default": 1.0},
                        "k": {"type": "parameter", "default": 0.5}
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
