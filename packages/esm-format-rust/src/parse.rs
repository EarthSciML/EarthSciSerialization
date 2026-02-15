//! JSON parsing and schema validation for ESM files

use crate::{EsmFile, error::EsmError};
use serde_json::Value;
use thiserror::Error;

/// Error type for JSON parsing failures
#[derive(Error, Debug)]
#[error("Failed to parse JSON: {message}")]
pub struct ParseError {
    pub message: String,
}

impl From<serde_json::Error> for ParseError {
    fn from(err: serde_json::Error) -> Self {
        ParseError {
            message: err.to_string(),
        }
    }
}

/// Error type for schema validation failures
#[derive(Error, Debug)]
#[error("Schema validation failed: {errors:?}")]
pub struct SchemaValidationError {
    pub errors: Vec<String>,
}

/// Load and parse an ESM file from JSON string
///
/// This function performs both JSON parsing and schema validation.
/// It will throw an error for malformed JSON or schema violations.
///
/// # Arguments
///
/// * `json_str` - The JSON string to parse
///
/// # Returns
///
/// * `Ok(EsmFile)` - Successfully parsed and validated ESM file
/// * `Err(EsmError)` - Parse error or schema validation error
///
/// # Examples
///
/// ```rust
/// use esm_format::load;
///
/// let json = r#"
/// {
///   "esm": "0.1.0",
///   "metadata": {
///     "name": "test_model"
///   },
///   "models": {
///     "simple": {
///       "variables": [],
///       "equations": []
///     }
///   }
/// }
/// "#;
///
/// let esm_file = load(json).expect("Failed to load ESM file");
/// assert_eq!(esm_file.esm, "0.1.0");
/// ```
pub fn load(json_str: &str) -> Result<EsmFile, EsmError> {
    // First, parse the JSON
    let json_value: Value = serde_json::from_str(json_str)
        .map_err(|e| EsmError::JsonParse(e))?;

    // Validate against schema
    validate_schema(&json_value)?;

    // Deserialize into our types
    let esm_file: EsmFile = serde_json::from_value(json_value)
        .map_err(|e| EsmError::JsonParse(e))?;

    Ok(esm_file)
}

/// Validate a JSON value against the ESM schema
///
/// This performs schema validation only. The JSON is assumed to be valid.
///
/// # Arguments
///
/// * `json_value` - The JSON value to validate
///
/// # Returns
///
/// * `Ok(())` - JSON passes schema validation
/// * `Err(EsmError::SchemaValidation)` - Schema validation errors
pub fn validate_schema(json_value: &Value) -> Result<(), EsmError> {
    // For now, we'll implement basic validation
    // In a complete implementation, we would load the actual JSON schema
    // and use jsonschema crate to validate against it

    // Basic validation: check required fields
    let obj = json_value.as_object()
        .ok_or_else(|| EsmError::SchemaValidation("Root must be an object".to_string()))?;

    // Check required 'esm' field
    let esm_version = obj.get("esm")
        .ok_or_else(|| EsmError::SchemaValidation("Missing required field 'esm'".to_string()))?
        .as_str()
        .ok_or_else(|| EsmError::SchemaValidation("Field 'esm' must be a string".to_string()))?;

    // Check ESM version
    if esm_version != "0.1.0" {
        return Err(EsmError::SchemaValidation(format!("Unsupported ESM version: {}", esm_version)));
    }

    // Check required 'metadata' field
    obj.get("metadata")
        .ok_or_else(|| EsmError::SchemaValidation("Missing required field 'metadata'".to_string()))?;

    // Check that at least one of 'models' or 'reaction_systems' is present
    if !obj.contains_key("models") && !obj.contains_key("reaction_systems") {
        return Err(EsmError::SchemaValidation(
            "At least one of 'models' or 'reaction_systems' must be present".to_string()
        ));
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_load_minimal_model() {
        let json = r#"
        {
          "esm": "0.1.0",
          "metadata": {
            "name": "test_model"
          },
          "models": {
            "simple": {
              "variables": [],
              "equations": []
            }
          }
        }
        "#;

        let result = load(json);
        assert!(result.is_ok());

        let esm_file = result.unwrap();
        assert_eq!(esm_file.esm, "0.1.0");
        assert!(esm_file.models.is_some());
    }

    #[test]
    fn test_load_invalid_json() {
        let json = r#"{ invalid json }"#;
        let result = load(json);
        assert!(result.is_err());
        match result.unwrap_err() {
            EsmError::JsonParse(_) => {}, // Expected
            _ => panic!("Expected JsonParse error"),
        }
    }

    #[test]
    fn test_load_missing_esm_version() {
        let json = r#"
        {
          "metadata": {
            "name": "test_model"
          },
          "models": {}
        }
        "#;

        let result = load(json);
        assert!(result.is_err());
        match result.unwrap_err() {
            EsmError::SchemaValidation(_) => {}, // Expected
            _ => panic!("Expected SchemaValidation error"),
        }
    }

    #[test]
    fn test_load_wrong_esm_version() {
        let json = r#"
        {
          "esm": "0.2.0",
          "metadata": {
            "name": "test_model"
          },
          "models": {}
        }
        "#;

        let result = load(json);
        assert!(result.is_err());
        match result.unwrap_err() {
            EsmError::SchemaValidation(_) => {}, // Expected
            _ => panic!("Expected SchemaValidation error"),
        }
    }

    #[test]
    fn test_load_missing_content() {
        let json = r#"
        {
          "esm": "0.1.0",
          "metadata": {
            "name": "test_model"
          }
        }
        "#;

        let result = load(json);
        assert!(result.is_err());
        match result.unwrap_err() {
            EsmError::SchemaValidation(_) => {}, // Expected
            _ => panic!("Expected SchemaValidation error"),
        }
    }
}