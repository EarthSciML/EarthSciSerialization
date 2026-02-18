//! Schema validation error tests for invalid fixtures
//!
//! Tests that invalid ESM files properly fail schema validation with appropriate error messages.

use esm_format::{*, validate};

/// Test that missing ESM version fails schema validation
#[test]
fn test_missing_esm_version_schema_error() {
    let fixture = include_str!("../../../tests/invalid/missing_esm_version.esm");

    let result = load(fixture);
    assert!(result.is_err());

    if let Err(EsmError::SchemaValidation(schema_err)) = result {
        // Should contain information about missing esm field
        assert!(schema_err.contains("esm") || schema_err.to_lowercase().contains("version"));
    } else {
        panic!("Expected schema validation error for missing ESM version");
    }
}

/// Test that missing required fields fail schema validation
#[test]
fn test_missing_required_fields_schema_error() {
    let fixture = include_str!("../../../tests/invalid/missing_required_fields.esm");

    let result = load(fixture);
    assert!(result.is_err());

    match result {
        Err(EsmError::SchemaValidation(_)) => {
            // Expected schema error
        },
        Err(other) => panic!("Expected schema error, got: {:?}", other),
        Ok(_) => panic!("Expected parsing to fail for missing required fields"),
    }
}

/// Test that wrong data types fail schema validation
#[test]
fn test_wrong_data_types_schema_error() {
    let fixture = include_str!("../../../tests/invalid/wrong_data_types.esm");

    let result = load(fixture);
    assert!(result.is_err());

    match result {
        Err(EsmError::SchemaValidation(_)) | Err(EsmError::JsonParse(_)) => {
            // Either schema or JSON parse error is acceptable for wrong data types
        },
        Err(other) => panic!("Expected schema/JSON parse error, got: {:?}", other),
        Ok(_) => panic!("Expected parsing to fail for wrong data types"),
    }
}

/// Test that invalid enum values fail schema validation
#[test]
fn test_invalid_enum_values_schema_error() {
    let fixture = include_str!("../../../tests/invalid/invalid_enum_values.esm");

    let result = load(fixture);
    assert!(result.is_err());
}

/// Test that empty required arrays fail schema validation
#[test]
fn test_empty_required_arrays_schema_error() {
    let fixture = include_str!("../../../tests/invalid/empty_required_arrays.esm");

    let result = load(fixture);
    assert!(result.is_err());
}

/// Test various metadata validation errors
#[test]
fn test_metadata_validation_errors() {
    let fixtures = [
        ("missing_metadata", include_str!("../../../tests/invalid/missing_metadata.esm")),
        ("missing_metadata_name", include_str!("../../../tests/invalid/missing_metadata_name.esm")),
        ("invalid_date_format", include_str!("../../../tests/invalid/invalid_date_format.esm")),
        ("malformed_doi", include_str!("../../../tests/invalid/malformed_doi.esm")),
        ("invalid_url_format", include_str!("../../../tests/invalid/invalid_url_format.esm")),
        ("extra_metadata_fields", include_str!("../../../tests/invalid/extra_metadata_fields.esm")),
        ("invalid_metadata_types", include_str!("../../../tests/invalid/invalid_metadata_types.esm")),
        ("empty_reference_fields", include_str!("../../../tests/invalid/empty_reference_fields.esm")),
    ];

    for (name, fixture) in fixtures.iter() {
        let result = load(fixture);
        assert!(result.is_err(), "Expected {} to fail validation", name);
    }
}

/// Test data loader validation errors
#[test]
fn test_data_loader_validation_errors() {
    let fixtures = [
        ("missing_type", include_str!("../../../tests/invalid/data_loader_missing_type.esm")),
        ("missing_loader_id", include_str!("../../../tests/invalid/data_loader_missing_loader_id.esm")),
        ("missing_provides", include_str!("../../../tests/invalid/data_loader_missing_provides.esm")),
        ("invalid_type", include_str!("../../../tests/invalid/data_loader_invalid_type.esm")),
        ("undefined_reference", include_str!("../../../tests/invalid/data_loader_undefined_reference.esm")),
        ("config_schema_violation", include_str!("../../../tests/invalid/data_loader_config_schema_violation.esm")),
        ("provides_missing_units", include_str!("../../../tests/invalid/data_loader_provides_missing_units.esm")),
        ("provides_missing_description", include_str!("../../../tests/invalid/data_loader_provides_missing_description.esm")),
    ];

    for (name, fixture) in fixtures.iter() {
        let result = load(fixture);
        assert!(result.is_err(), "Expected data loader {} to fail validation", name);
    }
}

/// Test operator validation errors
#[test]
fn test_operator_validation_errors() {
    let fixtures = [
        ("missing_operator_id", include_str!("../../../tests/invalid/operator_missing_operator_id.esm")),
        ("missing_needed_vars", include_str!("../../../tests/invalid/operator_missing_needed_vars.esm")),
        ("variable_mismatch", include_str!("../../../tests/invalid/operator_variable_mismatch.esm")),
        ("interpolation_method_invalid", include_str!("../../../tests/invalid/interpolation_method_invalid.esm")),
        ("temporal_resolution_invalid", include_str!("../../../tests/invalid/temporal_resolution_invalid.esm")),
    ];

    for (name, fixture) in fixtures.iter() {
        let load_result = load(fixture);

        let validation_failed = match load_result {
            Err(_) => true, // JSON parsing or schema validation failed
            Ok(esm_file) => {
                // JSON parsing passed, check structural validation
                let validation_result = validate(&esm_file);
                !validation_result.is_valid
            }
        };

        assert!(validation_failed, "Expected operator {} to fail validation", name);
    }
}

/// Test version compatibility validation errors
#[test]
fn test_version_compatibility_validation_errors() {
    let fixtures = [
        ("invalid_version_string", include_str!("../../../tests/version_compatibility/invalid_version_string.esm")),
        ("missing_version_field", include_str!("../../../tests/version_compatibility/missing_version_field.esm")),
        ("malformed_version_number", include_str!("../../../tests/version_compatibility/malformed_version_number.esm")),
        ("version_with_prerelease", include_str!("../../../tests/version_compatibility/version_with_prerelease.esm")),
    ];

    for (name, fixture) in fixtures.iter() {
        let result = load(fixture);
        // Note: Some version compatibility issues might be warnings rather than hard errors
        // depending on implementation, but generally malformed versions should fail
        if name.contains("malformed") || name.contains("invalid") {
            assert!(result.is_err(), "Expected {} to fail validation", name);
        }
    }
}

/// Test that major version rejection works
#[test]
fn test_major_version_rejection() {
    let fixture = include_str!("../../../tests/version_compatibility/version_2_5_1_major_rejection.esm");

    let result = load(fixture);
    // Major version 2.x.x should be rejected by 0.1.0 implementation
    assert!(result.is_err(), "Expected major version 2.x.x to be rejected");
}

/// Test coupling validation errors
#[test]
fn test_coupling_validation_errors() {
    let fixtures = [
        ("circular_coupling", include_str!("../../../tests/invalid/circular_coupling.esm")),
        ("coupling_resolution_errors", include_str!("../../../tests/invalid/coupling_resolution_errors.esm")),
    ];

    for (name, fixture) in fixtures.iter() {
        let result = load(fixture);
        assert!(result.is_err(), "Expected coupling {} to fail validation", name);
    }
}

/// Test comprehensive error coverage
#[test]
fn test_complete_error_coverage() {
    let fixture = include_str!("../../../tests/invalid/complete_error_coverage.esm");

    let result = load(fixture);
    assert!(result.is_err(), "Expected complete error coverage fixture to fail");
}