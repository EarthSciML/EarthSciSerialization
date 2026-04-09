//! JSON parsing and schema validation for ESM files

use crate::{error::EsmError, EsmFile};
use jsonschema::JSONSchema;
use serde_json::Value;
use std::sync::OnceLock;
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

/// Bundled ESM JSON Schema
const ESM_SCHEMA_JSON: &str = include_str!("esm-schema.json");

/// Get the compiled JSON schema (cached for performance)
fn get_schema() -> &'static JSONSchema {
    static SCHEMA: OnceLock<JSONSchema> = OnceLock::new();
    SCHEMA.get_or_init(|| {
        let schema_value: Value =
            serde_json::from_str(ESM_SCHEMA_JSON).expect("Bundled schema should be valid JSON");
        JSONSchema::compile(&schema_value).expect("Bundled schema should compile successfully")
    })
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
/// use earthsci_toolkit::load;
///
/// let json = r#"
/// {
///   "esm": "0.1.0",
///   "metadata": {
///     "name": "test_model"
///   },
///   "models": {
///     "simple": {
///       "variables": {},
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
    let json_value: Value = serde_json::from_str(json_str).map_err(|e| EsmError::JsonParse(e))?;

    // Validate against schema
    validate_schema(&json_value)?;

    // Deserialize into our types
    let esm_file: EsmFile =
        serde_json::from_value(json_value).map_err(|e| EsmError::JsonParse(e))?;

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
    let schema = get_schema();
    let validation_result = schema.validate(json_value);

    match validation_result {
        Ok(_) => Ok(()),
        Err(errors) => {
            let error_messages: Vec<String> = errors.map(|error| error.to_string()).collect();
            Err(EsmError::SchemaValidation(error_messages.join("; ")))
        }
    }
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
              "variables": {},
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
            EsmError::JsonParse(_) => {} // Expected
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
            EsmError::SchemaValidation(_) => {} // Expected
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
            EsmError::SchemaValidation(_) => {} // Expected
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
            EsmError::SchemaValidation(_) => {} // Expected
            _ => panic!("Expected SchemaValidation error"),
        }
    }

    #[test]
    fn test_round_trip() {
        use crate::save;

        let json = r#"
        {
          "esm": "0.1.0",
          "metadata": {
            "name": "test_model"
          },
          "models": {
            "simple": {
              "variables": {},
              "equations": []
            }
          }
        }
        "#;

        // Load the JSON
        let esm_file = load(json).expect("Failed to load ESM file");

        // Save it back to JSON
        let serialized_json = save(&esm_file).expect("Failed to save ESM file");

        // Load it again
        let round_trip_file = load(&serialized_json).expect("Failed to load round-trip ESM file");

        // Verify the structure is preserved
        assert_eq!(esm_file.esm, round_trip_file.esm);
        assert_eq!(esm_file.metadata.name, round_trip_file.metadata.name);
        assert!(esm_file.models.is_some());
        assert!(round_trip_file.models.is_some());

        let models1 = esm_file.models.as_ref().unwrap();
        let models2 = round_trip_file.models.as_ref().unwrap();
        assert_eq!(models1.len(), models2.len());
        assert!(models1.contains_key("simple"));
        assert!(models2.contains_key("simple"));
    }
}
