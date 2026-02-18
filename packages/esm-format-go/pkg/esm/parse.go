package esm

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/xeipuuv/gojsonschema"
)

// ValidationResult holds the result of schema validation
type ValidationResult struct {
	Valid  bool     `json:"valid"`
	Errors []string `json:"errors,omitempty"`
}

// Load loads an ESM file from the specified path and validates it against the JSON schema
func Load(path string) (*EsmFile, error) {
	// Read the file
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read file %s: %w", path, err)
	}

	return LoadString(string(data))
}

// LoadString parses an ESM file from JSON string and validates it against the JSON schema
func LoadString(jsonStr string) (*EsmFile, error) {
	// First, validate against JSON schema
	result, err := validateJSONSchema(jsonStr)
	if err != nil {
		return nil, fmt.Errorf("schema validation failed: %w", err)
	}

	if !result.Valid {
		return nil, fmt.Errorf("JSON schema validation failed: %v", result.Errors)
	}

	// Parse JSON into our struct
	var esmFile EsmFile
	if err := json.Unmarshal([]byte(jsonStr), &esmFile); err != nil {
		return nil, fmt.Errorf("failed to unmarshal JSON: %w", err)
	}

	// According to spec Section 2.1a: load() should succeed for valid JSON that
	// passes schema validation but fails structural validation. Structural issues
	// should only be reported by the separate validate() function.
	// Therefore, we skip the structural validation here.

	return &esmFile, nil
}

// validateJSONSchema validates the JSON string against the ESM JSON schema
func validateJSONSchema(jsonStr string) (*ValidationResult, error) {
	// Get the schema file path - look for it in several locations
	schemaPaths := []string{
		"../../esm-schema.json",                    // from pkg/esm directory
		"../../../esm-schema.json",                 // from packages/esm-format-go
		"../../../../esm-schema.json",              // from deeper
		"/home/ctessum/EarthSciSerialization/esm-schema.json", // absolute path fallback
	}

	var schemaLoader gojsonschema.JSONLoader
	var schemaFound bool

	for _, schemaPath := range schemaPaths {
		if _, err := os.Stat(schemaPath); err == nil {
			absPath, err := filepath.Abs(schemaPath)
			if err != nil {
				continue
			}
			schemaLoader = gojsonschema.NewReferenceLoader("file://" + absPath)
			schemaFound = true
			break
		}
	}

	if !schemaFound {
		return nil, fmt.Errorf("ESM schema file not found in any expected location")
	}

	// Load the document
	documentLoader := gojsonschema.NewStringLoader(jsonStr)

	// Validate
	result, err := gojsonschema.Validate(schemaLoader, documentLoader)
	if err != nil {
		return nil, fmt.Errorf("validation error: %w", err)
	}

	// Convert result
	validationResult := &ValidationResult{
		Valid: result.Valid(),
	}

	if !result.Valid() {
		for _, desc := range result.Errors() {
			validationResult.Errors = append(validationResult.Errors, desc.String())
		}
	}

	return validationResult, nil
}