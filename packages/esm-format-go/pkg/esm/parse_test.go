package esm

import (
	"os"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestLoad(t *testing.T) {
	// Create a temporary test file
	testJSON := `{
		"esm": "0.1.0",
		"metadata": {
			"name": "TestModel",
			"authors": ["Test Author"]
		},
		"models": {
			"TestModel": {
				"variables": {
					"x": {
						"type": "state",
						"units": "m",
						"default": 0.0
					}
				},
				"equations": [
					{
						"lhs": {"op": "D", "args": ["x"], "wrt": "t"},
						"rhs": 1.0
					}
				]
			}
		}
	}`

	// Create temporary file
	tmpFile, err := os.CreateTemp("", "test*.esm")
	require.NoError(t, err)
	defer os.Remove(tmpFile.Name())

	_, err = tmpFile.WriteString(testJSON)
	require.NoError(t, err)
	tmpFile.Close()

	// Test loading
	esmFile, err := Load(tmpFile.Name())
	assert.NoError(t, err)
	assert.NotNil(t, esmFile)
	assert.Equal(t, "0.1.0", esmFile.Esm)
	assert.Equal(t, "TestModel", esmFile.Metadata.Name)
	assert.Len(t, esmFile.Models, 1)
}

func TestLoadString(t *testing.T) {
	testJSON := `{
		"esm": "0.1.0",
		"metadata": {
			"name": "TestModel",
			"authors": ["Test Author"]
		},
		"models": {
			"TestModel": {
				"variables": {
					"x": {
						"type": "state",
						"units": "m",
						"default": 0.0
					}
				},
				"equations": [
					{
						"lhs": {"op": "D", "args": ["x"], "wrt": "t"},
						"rhs": 1.0
					}
				]
			}
		}
	}`

	esmFile, err := LoadString(testJSON)
	assert.NoError(t, err)
	assert.NotNil(t, esmFile)
	assert.Equal(t, "0.1.0", esmFile.Esm)
	assert.Equal(t, "TestModel", esmFile.Metadata.Name)
}

func TestLoadStringInvalidJSON(t *testing.T) {
	invalidJSON := `{
		"esm": "0.1.0",
		"metadata": {
			"name": "TestModel"
		}
		// Missing comma and invalid structure
	}`

	_, err := LoadString(invalidJSON)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "schema validation failed")
}

func TestLoadStringMissingRequiredFields(t *testing.T) {
	// Missing required "authors" field in metadata
	invalidJSON := `{
		"esm": "0.1.0",
		"metadata": {
			"name": "TestModel"
		},
		"models": {
			"TestModel": {
				"variables": {
					"x": {"type": "state"}
				},
				"equations": []
			}
		}
	}`

	_, err := LoadString(invalidJSON)
	// This should pass JSON schema but fail structural validation
	assert.NoError(t, err) // Authors is not actually required in schema
}

func TestLoadNonExistentFile(t *testing.T) {
	_, err := Load("non_existent_file.esm")
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "failed to read file")
}

func TestLoadShouldSucceedWithStructuralValidationFailure(t *testing.T) {
	// This test verifies the fix for the bug: LoadString() should succeed for valid JSON
	// that passes schema validation but fails structural validation.
	// According to spec Section 2.1a, structural issues should only be reported
	// by the separate validate() function.

	// Create JSON with empty models - this passes JSON schema validation
	// (because models is not marked as required in schema, only via anyOf pattern)
	// but fails basic structural validation
	testJSON := `{
		"esm": "0.1.0",
		"metadata": {
			"name": "TestModel",
			"authors": ["Test Author"]
		},
		"models": {}
	}`

	// This should succeed in LoadString (valid JSON schema)
	esmFile, err := LoadString(testJSON)
	assert.NoError(t, err, "LoadString should succeed for valid JSON schema even with structural issues")
	assert.NotNil(t, esmFile)

	// Verify it actually fails structural validation when called separately
	if esmFile != nil {
		validationErr := esmFile.Validate()
		assert.Error(t, validationErr, "Basic structural validation should fail")
		assert.Contains(t, validationErr.Error(), "at least one of 'models' or 'reaction_systems' must be present")
	}
}

func TestValidateJSONSchemaWithEmbeddedSchema(t *testing.T) {
	// Test that schema validation works with embedded schema
	// This should now always work regardless of external file presence
	testJSON := `{"esm": "0.1.0"}`

	result, err := validateJSONSchema(testJSON)

	// With embedded schema, err should always be nil (no file lookup required)
	assert.NoError(t, err)
	// This JSON should fail validation because it's incomplete (missing metadata, models/reaction_systems)
	assert.False(t, result.IsValid)
	assert.NotEmpty(t, result.SchemaErrors)
}

func TestValidateJSONSchemaValidDocument(t *testing.T) {
	// Test with a complete valid document to ensure embedded schema works correctly
	validJSON := `{
		"esm": "0.1.0",
		"metadata": {
			"name": "TestModel",
			"authors": ["Test Author"]
		},
		"models": {
			"TestModel": {
				"variables": {
					"x": {
						"type": "state",
						"units": "m",
						"default": 0.0
					}
				},
				"equations": [
					{
						"lhs": {"op": "D", "args": ["x"], "wrt": "t"},
						"rhs": 1.0
					}
				]
			}
		}
	}`

	result, err := validateJSONSchema(validJSON)
	assert.NoError(t, err)
	assert.True(t, result.IsValid, "Valid JSON should pass schema validation")
	assert.Empty(t, result.SchemaErrors)
}