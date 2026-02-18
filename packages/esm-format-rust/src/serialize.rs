//! JSON serialization for ESM files

use crate::{EsmFile, error::EsmError};

/// Serialize an ESM file to JSON string
///
/// This function converts an `EsmFile` struct back to a JSON string.
/// The output will be pretty-printed for human readability.
///
/// # Arguments
///
/// * `esm_file` - The ESM file to serialize
///
/// # Returns
///
/// * `Ok(String)` - Successfully serialized JSON string
/// * `Err(EsmError)` - Serialization error
///
/// # Examples
///
/// ```rust
/// use esm_format::{EsmFile, Metadata, save};
///
/// let esm_file = EsmFile {
///     esm: "0.1.0".to_string(),
///     metadata: Metadata {
///         name: Some("test_model".to_string()),
///         description: None,
///         authors: None,
///         created: None,
///         modified: None,
///         version: None,
///     },
///     models: None,
///     reaction_systems: None,
///     data_loaders: None,
///     operators: None,
///     coupling: None,
///     domain: None,
///     solver: None,
/// };
///
/// let json = save(&esm_file).expect("Failed to serialize ESM file");
/// assert!(json.contains("\"esm\": \"0.1.0\""));
/// ```
pub fn save(esm_file: &EsmFile) -> Result<String, EsmError> {
    serde_json::to_string_pretty(esm_file)
        .map_err(|e| EsmError::JsonParse(e))
}

/// Serialize an ESM file to compact JSON string (no pretty printing)
///
/// This function is similar to `save` but produces compact JSON without
/// extra whitespace, suitable for storage or transmission.
///
/// # Arguments
///
/// * `esm_file` - The ESM file to serialize
///
/// # Returns
///
/// * `Ok(String)` - Successfully serialized compact JSON string
/// * `Err(EsmError)` - Serialization error
pub fn save_compact(esm_file: &EsmFile) -> Result<String, EsmError> {
    serde_json::to_string(esm_file)
        .map_err(|e| EsmError::JsonParse(e))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Model, Expr};
    use crate::types::{Metadata, ModelVariable, VariableType, Equation};
    use std::collections::HashMap;

    #[test]
    fn test_save_minimal_file() {
        let esm_file = EsmFile {
            esm: "0.1.0".to_string(),
            metadata: Metadata {
                name: Some("test_model".to_string()),
                description: None,
                authors: None,
                created: None,
                modified: None,
                version: None,
            },
            models: None,
            reaction_systems: None,
            data_loaders: None,
            operators: None,
            coupling: None,
            domain: None,
            solver: None,
        };

        let result = save(&esm_file);
        assert!(result.is_ok());

        let json = result.unwrap();
        assert!(json.contains("\"esm\": \"0.1.0\""));
        assert!(json.contains("\"name\": \"test_model\""));
    }

    #[test]
    fn test_save_with_model() {
        let mut models = HashMap::new();
        let mut variables = HashMap::new();
        variables.insert("x".to_string(), ModelVariable {
            var_type: VariableType::State,
            units: Some("m".to_string()),
            default: Some(0.0),
            description: None,
        });

        models.insert("test".to_string(), Model {
            name: Some("Test Model".to_string()),
            variables,
            equations: vec![
                Equation {
                    lhs: Expr::Variable("d(x)/dt".to_string()),
                    rhs: Expr::Number(1.0),
                }
            ],
            discrete_events: None,
            continuous_events: None,
            description: None,
        });

        let esm_file = EsmFile {
            esm: "0.1.0".to_string(),
            metadata: Metadata {
                name: Some("test_model".to_string()),
                description: None,
                authors: None,
                created: None,
                modified: None,
                version: None,
            },
            models: Some(models),
            reaction_systems: None,
            data_loaders: None,
            operators: None,
            coupling: None,
            domain: None,
            solver: None,
        };

        let result = save(&esm_file);
        assert!(result.is_ok());

        let json = result.unwrap();
        assert!(json.contains("\"models\""));
        assert!(json.contains("\"test\""));
        assert!(json.contains("\"variables\""));
        assert!(json.contains("\"equations\""));
    }

    #[test]
    fn test_save_compact() {
        let esm_file = EsmFile {
            esm: "0.1.0".to_string(),
            metadata: Metadata {
                name: Some("test_model".to_string()),
                description: None,
                authors: None,
                created: None,
                modified: None,
                version: None,
            },
            models: None,
            reaction_systems: None,
            data_loaders: None,
            operators: None,
            coupling: None,
            domain: None,
            solver: None,
        };

        let result = save_compact(&esm_file);
        assert!(result.is_ok());

        let json = result.unwrap();
        // Compact JSON shouldn't have extra whitespace
        assert!(!json.contains("  "));
        assert!(json.contains("\"esm\":\"0.1.0\""));
    }
}