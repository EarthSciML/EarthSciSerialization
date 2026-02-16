package esm

import (
	"encoding/json"
	"fmt"
	"os"
)

// Save serializes an ESM file to JSON string
func Save(file *EsmFile) (string, error) {
	if file == nil {
		return "", fmt.Errorf("cannot serialize nil ESM file")
	}

	// Validate the file before serializing
	if err := file.Validate(); err != nil {
		return "", fmt.Errorf("validation failed before serialization: %w", err)
	}

	// Marshal to JSON with indentation for readability
	jsonData, err := json.MarshalIndent(file, "", "  ")
	if err != nil {
		return "", fmt.Errorf("failed to marshal ESM file to JSON: %w", err)
	}

	return string(jsonData), nil
}

// SaveCompact serializes an ESM file to compact JSON string (no indentation)
func SaveCompact(file *EsmFile) (string, error) {
	if file == nil {
		return "", fmt.Errorf("cannot serialize nil ESM file")
	}

	// Validate the file before serializing
	if err := file.Validate(); err != nil {
		return "", fmt.Errorf("validation failed before serialization: %w", err)
	}

	// Marshal to compact JSON
	jsonData, err := json.Marshal(file)
	if err != nil {
		return "", fmt.Errorf("failed to marshal ESM file to JSON: %w", err)
	}

	return string(jsonData), nil
}

// SaveToFile saves an ESM file directly to a file path
func SaveToFile(file *EsmFile, filepath string) error {
	jsonStr, err := Save(file)
	if err != nil {
		return err
	}

	// Write to file
	if err := writeFile(filepath, []byte(jsonStr)); err != nil {
		return fmt.Errorf("failed to write file %s: %w", filepath, err)
	}

	return nil
}

// SaveCompactToFile saves an ESM file to a file path in compact format
func SaveCompactToFile(file *EsmFile, filepath string) error {
	jsonStr, err := SaveCompact(file)
	if err != nil {
		return err
	}

	// Write to file
	if err := writeFile(filepath, []byte(jsonStr)); err != nil {
		return fmt.Errorf("failed to write file %s: %w", filepath, err)
	}

	return nil
}

// writeFile is a simple file writing helper that can be easily mocked for testing
func writeFile(filepath string, data []byte) error {
	return os.WriteFile(filepath, data, 0644)
}

// SerializeExpression serializes just an expression to JSON
func SerializeExpression(expr Expression) (string, error) {
	jsonData, err := json.MarshalIndent(expr, "", "  ")
	if err != nil {
		return "", fmt.Errorf("failed to serialize expression: %w", err)
	}
	return string(jsonData), nil
}

// SerializeExpressionCompact serializes just an expression to compact JSON
func SerializeExpressionCompact(expr Expression) (string, error) {
	jsonData, err := json.Marshal(expr)
	if err != nil {
		return "", fmt.Errorf("failed to serialize expression: %w", err)
	}
	return string(jsonData), nil
}

// SerializeModel serializes just a model to JSON
func SerializeModel(model *Model) (string, error) {
	if model == nil {
		return "", fmt.Errorf("cannot serialize nil model")
	}

	jsonData, err := json.MarshalIndent(model, "", "  ")
	if err != nil {
		return "", fmt.Errorf("failed to serialize model: %w", err)
	}
	return string(jsonData), nil
}

// SerializeReactionSystem serializes just a reaction system to JSON
func SerializeReactionSystem(system *ReactionSystem) (string, error) {
	if system == nil {
		return "", fmt.Errorf("cannot serialize nil reaction system")
	}

	jsonData, err := json.MarshalIndent(system, "", "  ")
	if err != nil {
		return "", fmt.Errorf("failed to serialize reaction system: %w", err)
	}
	return string(jsonData), nil
}