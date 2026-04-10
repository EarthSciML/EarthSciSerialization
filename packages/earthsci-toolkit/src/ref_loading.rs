//! Subsystem reference loading and resolution
//!
//! This module provides functionality to resolve `$ref` references in
//! subsystem definitions. Local file references are resolved relative
//! to a base path, and circular references are detected.

use crate::types::EsmFile;
use std::collections::HashSet;
use std::path::{Path, PathBuf};

/// Resolve all subsystem `$ref` references in an ESM file.
///
/// Walks all models and reaction systems looking for subsystem entries
/// that contain a `$ref` field. For each reference found:
///
/// - If it starts with `http://` or `https://`, an error is returned
///   (remote references are not supported).
/// - Otherwise, the path is resolved relative to `base_path`, the
///   referenced file is read and parsed, and the reference object is
///   replaced with the resolved content.
/// - Circular references are detected and reported as errors.
/// - Resolution is recursive: resolved content may itself contain refs.
///
/// # Arguments
///
/// * `file` - The ESM file to resolve references in (modified in place)
/// * `base_path` - Directory to resolve relative file paths against
///
/// # Returns
///
/// * `Ok(())` on success
/// * `Err(String)` if a reference cannot be resolved
///
/// # Examples
///
/// ```rust,no_run
/// use earthsci_toolkit::ref_loading::resolve_subsystem_refs;
/// use earthsci_toolkit::load;
/// use std::path::Path;
///
/// let json = r#"{
///   "esm": "0.1.0",
///   "metadata": { "name": "test" },
///   "models": {
///     "main": {
///       "variables": {},
///       "equations": []
///     }
///   }
/// }"#;
/// let mut file = load(json).unwrap();
/// resolve_subsystem_refs(&mut file, Path::new("/some/dir")).unwrap();
/// ```
pub fn resolve_subsystem_refs(file: &mut EsmFile, base_path: &Path) -> Result<(), String> {
    let mut visited = HashSet::new();
    resolve_refs_in_file(file, base_path, &mut visited)
}

/// Internal recursive resolver that tracks visited paths to detect cycles.
fn resolve_refs_in_file(
    file: &mut EsmFile,
    base_path: &Path,
    visited: &mut HashSet<PathBuf>,
) -> Result<(), String> {
    // Resolve refs in models
    if let Some(ref mut models) = file.models {
        let model_names: Vec<String> = models.keys().cloned().collect();
        for name in model_names {
            let model = models.get_mut(&name).unwrap();
            // Models don't have a built-in subsystems field in the current types,
            // but equations or variables may contain $ref patterns in their
            // serde_json::Value content. We check the raw JSON representation
            // for any embedded refs.
            resolve_refs_in_equations(&mut model.equations, base_path, visited)?;
        }
    }

    // Resolve refs in reaction systems
    if let Some(ref mut reaction_systems) = file.reaction_systems {
        let rs_names: Vec<String> = reaction_systems.keys().cloned().collect();
        for name in rs_names {
            let rs = reaction_systems.get_mut(&name).unwrap();
            // Resolve refs in reaction rate expressions
            for reaction in &mut rs.reactions {
                resolve_refs_in_expr(&mut reaction.rate, base_path, visited)?;
            }
        }
    }

    // Resolve refs in coupling entries
    if let Some(ref mut coupling) = file.coupling {
        for entry in coupling.iter_mut() {
            resolve_refs_in_coupling_entry(entry, base_path, visited)?;
        }
    }

    Ok(())
}

/// Resolve `$ref` in a serde_json::Value, replacing the ref object with loaded content.
fn resolve_ref_value(
    value: &mut serde_json::Value,
    base_path: &Path,
    visited: &mut HashSet<PathBuf>,
) -> Result<(), String> {
    match value {
        serde_json::Value::Object(map) => {
            if let Some(ref_val) = map.get("$ref").cloned() {
                let ref_str = ref_val
                    .as_str()
                    .ok_or_else(|| "$ref must be a string".to_string())?;

                // Reject remote references
                if ref_str.starts_with("http://") || ref_str.starts_with("https://") {
                    return Err(format!(
                        "Remote references are not supported: {}",
                        ref_str
                    ));
                }

                // Resolve path relative to base
                let resolved_path = base_path.join(ref_str);
                let canonical = resolved_path
                    .canonicalize()
                    .map_err(|e| {
                        format!(
                            "Failed to resolve reference path '{}': {}",
                            resolved_path.display(),
                            e
                        )
                    })?;

                // Circular reference detection
                if visited.contains(&canonical) {
                    return Err(format!(
                        "Circular reference detected: {}",
                        canonical.display()
                    ));
                }
                visited.insert(canonical.clone());

                // Read and parse the referenced file
                let content = std::fs::read_to_string(&canonical).map_err(|e| {
                    format!(
                        "Failed to read referenced file '{}': {}",
                        canonical.display(),
                        e
                    )
                })?;

                let mut parsed: serde_json::Value =
                    serde_json::from_str(&content).map_err(|e| {
                        format!(
                            "Failed to parse referenced file '{}': {}",
                            canonical.display(),
                            e
                        )
                    })?;

                // Recursively resolve refs in the loaded content
                let parent_dir = canonical
                    .parent()
                    .unwrap_or(base_path);
                resolve_ref_value(&mut parsed, parent_dir, visited)?;

                // Remove from visited after successful resolution (allow the same
                // file to be referenced from independent branches, just not cycles)
                visited.remove(&canonical);

                // Replace the ref object with the resolved content
                *value = parsed;
            } else {
                // Recursively check all values in the object
                let keys: Vec<String> = map.keys().cloned().collect();
                for key in keys {
                    if let Some(v) = map.get_mut(&key) {
                        resolve_ref_value(v, base_path, visited)?;
                    }
                }
            }
        }
        serde_json::Value::Array(arr) => {
            for item in arr.iter_mut() {
                resolve_ref_value(item, base_path, visited)?;
            }
        }
        _ => {
            // Primitives have no refs to resolve
        }
    }
    Ok(())
}

/// Resolve refs within Expr values by converting to serde_json::Value,
/// resolving, and converting back.
fn resolve_refs_in_expr(
    expr: &mut crate::types::Expr,
    base_path: &Path,
    visited: &mut HashSet<PathBuf>,
) -> Result<(), String> {
    // Serialize the expression to a JSON value
    let mut json_val = serde_json::to_value(&*expr)
        .map_err(|e| format!("Failed to serialize expression: {}", e))?;

    // Check if there are any $ref patterns before doing work
    let json_str = serde_json::to_string(&json_val).unwrap_or_default();
    if !json_str.contains("$ref") {
        return Ok(());
    }

    resolve_ref_value(&mut json_val, base_path, visited)?;

    // Deserialize back
    *expr = serde_json::from_value(json_val)
        .map_err(|e| format!("Failed to deserialize resolved expression: {}", e))?;

    Ok(())
}

/// Resolve refs within equation lists
fn resolve_refs_in_equations(
    equations: &mut Vec<crate::types::Equation>,
    base_path: &Path,
    visited: &mut HashSet<PathBuf>,
) -> Result<(), String> {
    for eq in equations.iter_mut() {
        resolve_refs_in_expr(&mut eq.lhs, base_path, visited)?;
        resolve_refs_in_expr(&mut eq.rhs, base_path, visited)?;
    }
    Ok(())
}

/// Resolve refs within coupling entries that contain serde_json::Value fields
fn resolve_refs_in_coupling_entry(
    entry: &mut crate::types::CouplingEntry,
    base_path: &Path,
    visited: &mut HashSet<PathBuf>,
) -> Result<(), String> {
    use crate::types::CouplingEntry;

    match entry {
        CouplingEntry::OperatorCompose {
            translate, ..
        } => {
            if let Some(val) = translate {
                resolve_ref_value(val, base_path, visited)?;
            }
        }
        CouplingEntry::Couple {
            connector, ..
        } => {
            resolve_ref_value(connector, base_path, visited)?;
        }
        CouplingEntry::Callback {
            config, ..
        } => {
            if let Some(val) = config {
                resolve_ref_value(val, base_path, visited)?;
            }
        }
        CouplingEntry::Event {
            conditions,
            affects,
            functional_affect,
            ..
        } => {
            if let Some(conds) = conditions {
                for cond in conds.iter_mut() {
                    resolve_refs_in_expr(cond, base_path, visited)?;
                }
            }
            if let Some(affs) = affects {
                for aff in affs.iter_mut() {
                    resolve_refs_in_expr(&mut aff.rhs, base_path, visited)?;
                }
            }
            if let Some(fa) = functional_affect {
                if let Some(config) = &mut fa.config {
                    resolve_ref_value(config, base_path, visited)?;
                }
            }
        }
        // VariableMap and OperatorApply don't contain Value fields that could have refs
        CouplingEntry::VariableMap { .. } | CouplingEntry::OperatorApply { .. } => {}
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{Metadata, Model};
    use std::collections::HashMap;
    use std::io::Write;
    use tempfile::TempDir;

    fn make_metadata() -> Metadata {
        Metadata {
            name: Some("test".to_string()),
            description: None,
            authors: None,
            license: None,
            created: None,
            modified: None,
            tags: None,
            references: None,
        }
    }

    fn make_minimal_file() -> EsmFile {
        let mut models = HashMap::new();
        models.insert(
            "main".to_string(),
            Model {
                name: None,
                reference: None,
                variables: HashMap::new(),
                equations: vec![],
                discrete_events: None,
                continuous_events: None,
                description: None,
            },
        );
        EsmFile {
            esm: "0.1.0".to_string(),
            metadata: make_metadata(),
            models: Some(models),
            reaction_systems: None,
            data_loaders: None,
            operators: None,
            coupling: None,
            domain: None,
        }
    }

    #[test]
    fn test_resolve_no_refs() {
        let mut file = make_minimal_file();
        let result = resolve_subsystem_refs(&mut file, Path::new("/tmp"));
        assert!(result.is_ok());
    }

    #[test]
    fn test_reject_remote_ref() {
        let mut value = serde_json::json!({
            "$ref": "https://example.com/model.json"
        });
        let mut visited = HashSet::new();
        let result = resolve_ref_value(&mut value, Path::new("/tmp"), &mut visited);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("Remote references are not supported"));
    }

    #[test]
    fn test_reject_http_ref() {
        let mut value = serde_json::json!({
            "$ref": "http://example.com/model.json"
        });
        let mut visited = HashSet::new();
        let result = resolve_ref_value(&mut value, Path::new("/tmp"), &mut visited);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("Remote references are not supported"));
    }

    #[test]
    fn test_resolve_local_ref() {
        // Create a temporary directory with a referenced file
        let dir = TempDir::new().unwrap();
        let ref_path = dir.path().join("sub.json");
        let mut ref_file = std::fs::File::create(&ref_path).unwrap();
        writeln!(ref_file, r#"{{"name": "resolved_subsystem"}}"#).unwrap();

        let mut value = serde_json::json!({
            "$ref": "sub.json"
        });

        let mut visited = HashSet::new();
        let result = resolve_ref_value(&mut value, dir.path(), &mut visited);
        assert!(result.is_ok());
        assert_eq!(value["name"], "resolved_subsystem");
    }

    #[test]
    fn test_circular_ref_detection() {
        // Create two files that reference each other
        let dir = TempDir::new().unwrap();

        let a_path = dir.path().join("a.json");
        let b_path = dir.path().join("b.json");

        std::fs::write(&a_path, r#"{"$ref": "b.json"}"#).unwrap();
        std::fs::write(&b_path, r#"{"$ref": "a.json"}"#).unwrap();

        let mut value = serde_json::json!({
            "$ref": "a.json"
        });

        let mut visited = HashSet::new();
        let result = resolve_ref_value(&mut value, dir.path(), &mut visited);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("Circular reference detected"));
    }

    #[test]
    fn test_recursive_resolution() {
        // Create a chain: main -> sub1 -> sub2 (no cycle)
        let dir = TempDir::new().unwrap();

        let sub2_path = dir.path().join("sub2.json");
        std::fs::write(&sub2_path, r#"{"value": "leaf"}"#).unwrap();

        let sub1_path = dir.path().join("sub1.json");
        std::fs::write(&sub1_path, r#"{"nested": {"$ref": "sub2.json"}}"#).unwrap();

        let mut value = serde_json::json!({
            "$ref": "sub1.json"
        });

        let mut visited = HashSet::new();
        let result = resolve_ref_value(&mut value, dir.path(), &mut visited);
        assert!(result.is_ok());
        assert_eq!(value["nested"]["value"], "leaf");
    }

    #[test]
    fn test_ref_in_array() {
        let dir = TempDir::new().unwrap();
        let ref_path = dir.path().join("item.json");
        std::fs::write(&ref_path, r#"{"resolved": true}"#).unwrap();

        let mut value = serde_json::json!([
            {"$ref": "item.json"},
            {"normal": "value"}
        ]);

        let mut visited = HashSet::new();
        let result = resolve_ref_value(&mut value, dir.path(), &mut visited);
        assert!(result.is_ok());
        assert_eq!(value[0]["resolved"], true);
        assert_eq!(value[1]["normal"], "value");
    }

    #[test]
    fn test_nonexistent_ref() {
        let dir = TempDir::new().unwrap();
        let mut value = serde_json::json!({
            "$ref": "nonexistent.json"
        });

        let mut visited = HashSet::new();
        let result = resolve_ref_value(&mut value, dir.path(), &mut visited);
        assert!(result.is_err());
        // Should fail during canonicalize or read
        let err = result.unwrap_err();
        assert!(
            err.contains("Failed to resolve reference path")
                || err.contains("Failed to read referenced file")
        );
    }
}
