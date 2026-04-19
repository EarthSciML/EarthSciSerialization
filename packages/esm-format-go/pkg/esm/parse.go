package esm

import (
	"bytes"
	_ "embed"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/xeipuuv/gojsonschema"
)

//go:embed esm-schema.json
var embeddedSchema []byte

// Load loads an ESM file from the specified path and validates it against the JSON schema.
// After parsing, it resolves any subsystem references relative to the file's directory.
func Load(path string) (*EsmFile, error) {
	// Read the file
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read file %s: %w", path, err)
	}

	esmFile, err := LoadString(string(data))
	if err != nil {
		return nil, err
	}

	// Resolve subsystem references relative to the file's directory
	basePath := filepath.Dir(path)
	if err := ResolveSubsystemRefs(esmFile, basePath); err != nil {
		return nil, fmt.Errorf("failed to resolve subsystem references: %w", err)
	}

	return esmFile, nil
}

// LoadString parses an ESM file from JSON string and validates it against the JSON schema
func LoadString(jsonStr string) (*EsmFile, error) {
	// First, validate against JSON schema
	result, err := validateJSONSchema(jsonStr)
	if err != nil {
		return nil, fmt.Errorf("schema validation failed: %w", err)
	}

	if !result.IsValid {
		var errorStrs []string
		for _, schemaErr := range result.SchemaErrors {
			errorStrs = append(errorStrs, schemaErr.Message)
		}
		return nil, fmt.Errorf("JSON schema validation failed: %v", errorStrs)
	}

	// Parse JSON into our struct. Use UseNumber so that JSON numbers in
	// Expression (interface{}) slots retain their wire form — otherwise
	// json.Unmarshal coerces every number to float64, destroying the
	// integer/float node distinction required by discretization RFC §5.4.1.
	var esmFile EsmFile
	dec := json.NewDecoder(bytes.NewReader([]byte(jsonStr)))
	dec.UseNumber()
	if err := dec.Decode(&esmFile); err != nil {
		return nil, fmt.Errorf("failed to unmarshal JSON: %w", err)
	}

	// Convert residual json.Number tokens (only appear inside Expression
	// slots and other interface{} fields) to int64 or float64 per RFC §5.4.6
	// round-trip parse rule: a token containing '.', 'e', or 'E' is a float;
	// otherwise it is an integer.
	normalizeNumericLiterals(&esmFile)

	// According to spec Section 2.1a: load() should succeed for valid JSON that
	// passes schema validation but fails structural validation. Structural issues
	// should only be reported by the separate validate() function.
	// Therefore, we skip the structural validation here.

	return &esmFile, nil
}

// normalizeJSONNumber converts a json.Number to int64 (no '.', no 'e'/'E') or
// float64 per discretization RFC §5.4.6 round-trip parse rule. Values outside
// int64 range fall back to float64.
func normalizeJSONNumber(n json.Number) interface{} {
	s := string(n)
	if strings.ContainsAny(s, ".eE") {
		f, err := n.Float64()
		if err != nil {
			return s
		}
		return f
	}
	i, err := n.Int64()
	if err == nil {
		return i
	}
	// Integer grammar but outside int64 range — fall back to float.
	f, err := n.Float64()
	if err != nil {
		return s
	}
	return f
}

// normalizeExpression walks an Expression tree and replaces json.Number
// tokens with int64 or float64 per RFC §5.4.6.
func normalizeExpression(expr Expression) Expression {
	switch e := expr.(type) {
	case json.Number:
		return normalizeJSONNumber(e)
	case ExprNode:
		for i, a := range e.Args {
			e.Args[i] = normalizeExpression(a)
		}
		return e
	case *ExprNode:
		for i, a := range e.Args {
			e.Args[i] = normalizeExpression(a)
		}
		return e
	case []interface{}:
		for i, a := range e {
			e[i] = normalizeExpression(a)
		}
		return e
	case map[string]interface{}:
		for k, v := range e {
			e[k] = normalizeExpression(v)
		}
		return e
	default:
		return expr
	}
}

// normalizeNumericLiterals walks the parsed EsmFile and normalizes json.Number
// tokens to int64 or float64 in every Expression-bearing field.
func normalizeNumericLiterals(ef *EsmFile) {
	if ef.Models != nil {
		for name, model := range ef.Models {
			normalizeModelLiterals(&model)
			ef.Models[name] = model
		}
	}
	if ef.ReactionSystems != nil {
		for name, rs := range ef.ReactionSystems {
			normalizeReactionSystemLiterals(&rs)
			ef.ReactionSystems[name] = rs
		}
	}
}

func normalizeModelLiterals(m *Model) {
	if m == nil {
		return
	}
	for name, v := range m.Variables {
		if v.Expression != nil {
			v.Expression = normalizeExpression(v.Expression)
		}
		if v.Default != nil {
			v.Default = normalizeExpression(v.Default)
		}
		m.Variables[name] = v
	}
	for i := range m.Equations {
		m.Equations[i].LHS = normalizeExpression(m.Equations[i].LHS)
		m.Equations[i].RHS = normalizeExpression(m.Equations[i].RHS)
	}
	for i := range m.DiscreteEvents {
		for j := range m.DiscreteEvents[i].Affects {
			m.DiscreteEvents[i].Affects[j].RHS = normalizeExpression(m.DiscreteEvents[i].Affects[j].RHS)
		}
		if m.DiscreteEvents[i].Trigger.Expression != nil {
			m.DiscreteEvents[i].Trigger.Expression = normalizeExpression(m.DiscreteEvents[i].Trigger.Expression)
		}
	}
	for i := range m.ContinuousEvents {
		for j := range m.ContinuousEvents[i].Conditions {
			m.ContinuousEvents[i].Conditions[j] = normalizeExpression(m.ContinuousEvents[i].Conditions[j])
		}
		for j := range m.ContinuousEvents[i].Affects {
			m.ContinuousEvents[i].Affects[j].RHS = normalizeExpression(m.ContinuousEvents[i].Affects[j].RHS)
		}
	}
}

func normalizeReactionSystemLiterals(rs *ReactionSystem) {
	if rs == nil {
		return
	}
	for i := range rs.Reactions {
		rs.Reactions[i].Rate = normalizeExpression(rs.Reactions[i].Rate)
	}
	for i := range rs.ConstraintEquations {
		rs.ConstraintEquations[i].LHS = normalizeExpression(rs.ConstraintEquations[i].LHS)
		rs.ConstraintEquations[i].RHS = normalizeExpression(rs.ConstraintEquations[i].RHS)
	}
}

// validateJSONSchema validates the JSON string against the ESM JSON schema
func validateJSONSchema(jsonStr string) (*ValidationResult, error) {
	// Load the embedded schema
	schemaLoader := gojsonschema.NewBytesLoader(embeddedSchema)

	// Load the document
	documentLoader := gojsonschema.NewStringLoader(jsonStr)

	// Validate
	result, err := gojsonschema.Validate(schemaLoader, documentLoader)
	if err != nil {
		return nil, fmt.Errorf("validation error: %w", err)
	}

	// Convert result to new ValidationResult format
	validationResult := &ValidationResult{
		IsValid:          result.Valid(),
		SchemaErrors:     []SchemaError{},
		StructuralErrors: []StructuralError{},
		UnitWarnings:     []UnitWarning{},
	}

	if !result.Valid() {
		for _, desc := range result.Errors() {
			schemaError := SchemaError{
				Path:    desc.Context().String(),
				Message: desc.Description(),
				Keyword: desc.Type(),
			}
			validationResult.SchemaErrors = append(validationResult.SchemaErrors, schemaError)
		}
	}

	return validationResult, nil
}
