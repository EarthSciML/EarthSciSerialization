package esm

import (
	"bytes"
	_ "embed"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"

	"github.com/xeipuuv/gojsonschema"
)

// DeprecationWarningCode identifies a specific deprecation warning emitted at load time.
type DeprecationWarningCode string

const (
	// DeprecatedDomainBC is emitted when a file declares
	// domains.<d>.boundary_conditions. The field moved to
	// models.<M>.boundary_conditions in v0.2.0 (RFC §9 / §10.1).
	DeprecatedDomainBC DeprecationWarningCode = "E_DEPRECATED_DOMAIN_BC"
)

// DeprecationWarningLogger is invoked once per deprecation the loader detects.
// Default is to log via the standard `log` package; set to nil to silence.
var DeprecationWarningLogger = func(code DeprecationWarningCode, message string) {
	log.Printf("[%s] %s", code, message)
}

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

	// Emit deprecation warnings for any domain-level boundary_conditions
	// encountered. v0.2.0 supersedes this field with Model.BoundaryConditions
	// (RFC §9 / §10.1); a follow-up bead will turn this into a hard error.
	if DeprecationWarningLogger != nil {
		for domainName, domain := range esmFile.Domains {
			if len(domain.BoundaryConditions) > 0 {
				DeprecationWarningLogger(DeprecatedDomainBC, fmt.Sprintf(
					"domains.%s.boundary_conditions is deprecated; "+
						"migrate to models.<M>.boundary_conditions (RFC §9).",
					domainName,
				))
			}
		}
	}

	// Validate grid cross-references (§6). Schema already handles shape, but we
	// check that loader-kind generators/connectivity point at a real data_loaders
	// entry and that builtin names are in the closed set §6.4.1 defines.
	if err := validateGrids(&esmFile); err != nil {
		return nil, err
	}

	// According to spec Section 2.1a: load() should succeed for valid JSON that
	// passes schema validation but fails structural validation. Structural issues
	// should only be reported by the separate validate() function.
	// Therefore, we skip the structural validation here.

	return &esmFile, nil
}

// knownGridBuiltins is the closed set of grid builtin generator names per
// docs/rfcs/discretization.md §6.4.1. Adding a new name is a minor version
// bump.
var knownGridBuiltins = map[string]struct{}{
	"gnomonic_c6_neighbors":  {},
	"gnomonic_c6_d4_action":  {},
}

// validateGrids checks grid cross-references against top-level data_loaders
// and the closed builtin set (RFC §6.4 / §6.5).
func validateGrids(esmFile *EsmFile) error {
	for gridName, grid := range esmFile.Grids {
		// Metric arrays
		for arrName, arr := range grid.MetricArrays {
			if err := validateGridGenerator(
				fmt.Sprintf("grids.%s.metric_arrays.%s.generator", gridName, arrName),
				&arr.Generator, esmFile); err != nil {
				return err
			}
		}
		// Unstructured connectivity
		for cName, c := range grid.Connectivity {
			if err := validateGridConnectivity(
				fmt.Sprintf("grids.%s.connectivity.%s", gridName, cName),
				&c, esmFile); err != nil {
				return err
			}
		}
		// Cubed-sphere panel_connectivity
		for cName, c := range grid.PanelConnectivity {
			if err := validateGridConnectivity(
				fmt.Sprintf("grids.%s.panel_connectivity.%s", gridName, cName),
				&c, esmFile); err != nil {
				return err
			}
		}
	}
	return nil
}

func validateGridGenerator(path string, g *GridMetricGenerator, esmFile *EsmFile) error {
	switch g.Kind {
	case "loader":
		if g.Loader == nil || *g.Loader == "" {
			return fmt.Errorf("%s: kind=loader requires a loader name", path)
		}
		if _, ok := esmFile.DataLoaders[*g.Loader]; !ok {
			return fmt.Errorf("%s: loader %q not found in top-level data_loaders", path, *g.Loader)
		}
	case "builtin":
		if g.Name == nil || *g.Name == "" {
			return fmt.Errorf("%s: kind=builtin requires a name", path)
		}
		if _, ok := knownGridBuiltins[*g.Name]; !ok {
			return fmt.Errorf("%s: E_UNKNOWN_BUILTIN: unknown grid builtin %q (allowed: gnomonic_c6_neighbors, gnomonic_c6_d4_action)", path, *g.Name)
		}
	}
	return nil
}

func validateGridConnectivity(path string, c *GridConnectivity, esmFile *EsmFile) error {
	if c.Loader != nil && *c.Loader != "" {
		if _, ok := esmFile.DataLoaders[*c.Loader]; !ok {
			return fmt.Errorf("%s: loader %q not found in top-level data_loaders", path, *c.Loader)
		}
	}
	if c.Generator != nil {
		if err := validateGridGenerator(path+".generator", c.Generator, esmFile); err != nil {
			return err
		}
	}
	return nil
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
