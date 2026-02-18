package esm

import (
	"fmt"
	"strings"
)

// SchemaError represents a JSON Schema violation
type SchemaError struct {
	Path    string `json:"path"`    // JSON Pointer to the offending location
	Message string `json:"message"` // Human-readable description
	Keyword string `json:"keyword"` // JSON Schema keyword that failed
}

// StructuralError represents equation/unknown balance, reference integrity issues
type StructuralError struct {
	Path    string                 `json:"path"`    // JSON Pointer to the relevant component
	Code    string                 `json:"code"`    // Machine-readable error code
	Message string                 `json:"message"` // Human-readable description
	Details map[string]interface{} `json:"details"` // Additional context
}

// UnitWarning represents dimensional inconsistencies
type UnitWarning struct {
	Path     string `json:"path"`      // JSON Pointer to the equation or expression
	Message  string `json:"message"`   // Human-readable description
	LhsUnits string `json:"lhs_units"` // Inferred units of the LHS
	RhsUnits string `json:"rhs_units"` // Inferred units of the RHS
}

// ValidationResult holds the result of validation per ESM Libraries Spec Section 3.4
type ValidationResult struct {
	SchemaErrors     []SchemaError     `json:"schema_errors"`
	StructuralErrors []StructuralError `json:"structural_errors"`
	UnitWarnings     []UnitWarning     `json:"unit_warnings"`
	IsValid          bool              `json:"is_valid"`
}

// Structural error codes per ESM Libraries Spec Section 3.4
const (
	ErrorEquationCountMismatch  = "equation_count_mismatch"
	ErrorUndefinedVariable      = "undefined_variable"
	ErrorUndefinedSpecies       = "undefined_species"
	ErrorUndefinedParameter     = "undefined_parameter"
	ErrorUndefinedSystem        = "undefined_system"
	ErrorUndefinedOperator      = "undefined_operator"
	ErrorUnresolvedScopedRef    = "unresolved_scoped_ref"
	ErrorInvalidDiscreteParam   = "invalid_discrete_param"
	ErrorNullReaction          = "null_reaction"
	ErrorMissingObservedExpr   = "missing_observed_expr"
	ErrorEventVarUndeclared    = "event_var_undeclared"
)

// ValidationMessage represents a single validation issue (for backward compatibility)
type ValidationMessage struct {
	Level   string `json:"level"`   // "error", "warning", "info"
	Message string `json:"message"` // Human-readable description
	Path    string `json:"path"`    // JSON path to the problematic element
}

// DetailedValidationResult holds comprehensive validation results (for backward compatibility)
type DetailedValidationResult struct {
	Valid    bool                `json:"valid"`
	Messages []ValidationMessage `json:"messages,omitempty"`
}

// ValidateFile performs comprehensive validation of an ESM file per ESM Libraries Spec Section 3.4
// This includes schema validation, structural validation, and unit validation (future)
func ValidateFile(file *EsmFile, jsonStr string) *ValidationResult {
	// First validate JSON schema
	schemaResult, err := validateJSONSchema(jsonStr)
	if err != nil {
		// If schema validation fails, return with error
		return &ValidationResult{
			IsValid:          false,
			SchemaErrors:     []SchemaError{{Path: "$", Message: fmt.Sprintf("Schema validation failed: %v", err), Keyword: "error"}},
			StructuralErrors: []StructuralError{},
			UnitWarnings:     []UnitWarning{},
		}
	}

	// Start with schema validation results
	result := &ValidationResult{
		SchemaErrors:     schemaResult.SchemaErrors,
		StructuralErrors: []StructuralError{},
		UnitWarnings:     []UnitWarning{},
		IsValid:          schemaResult.IsValid,
	}

	// If schema validation failed, don't proceed with structural validation
	if !schemaResult.IsValid {
		return result
	}

	// Perform structural validation
	structuralResult := ValidateStructural(file)

	// Convert structural validation results
	for _, msg := range structuralResult.Messages {
		if msg.Level == "error" {
			structuralError := StructuralError{
				Path:    msg.Path,
				Code:    getErrorCodeFromMessage(msg.Message),
				Message: msg.Message,
				Details: map[string]interface{}{},
			}
			result.StructuralErrors = append(result.StructuralErrors, structuralError)
		} else if msg.Level == "warning" {
			// For now, treat non-unit warnings as unit warnings
			unitWarning := UnitWarning{
				Path:     msg.Path,
				Message:  msg.Message,
				LhsUnits: "unknown",
				RhsUnits: "unknown",
			}
			result.UnitWarnings = append(result.UnitWarnings, unitWarning)
		}
	}

	// Update IsValid based on both schema and structural errors
	result.IsValid = len(result.SchemaErrors) == 0 && len(result.StructuralErrors) == 0

	return result
}

// getErrorCodeFromMessage attempts to infer error code from message text
// This is a temporary solution until we refactor the structural validation to use codes directly
func getErrorCodeFromMessage(message string) string {
	if strings.Contains(message, "Unknown variable") {
		return ErrorUndefinedVariable
	}
	if strings.Contains(message, "Unknown species") {
		return ErrorUndefinedSpecies
	}
	if strings.Contains(message, "Unknown parameter") {
		return ErrorUndefinedParameter
	}
	if strings.Contains(message, "Unknown system") {
		return ErrorUndefinedSystem
	}
	if strings.Contains(message, "Equation-unknown balance") {
		return ErrorEquationCountMismatch
	}
	if strings.Contains(message, "Observed variable must have an expression") {
		return ErrorMissingObservedExpr
	}
	return "unknown_error"
}

// Validate is the backward compatibility function that returns DetailedValidationResult
// For the new spec-compliant validation, use ValidateFile
func Validate(file *EsmFile) *DetailedValidationResult {
	return ValidateStructural(file)
}

// ValidateStructural performs comprehensive structural validation of an ESM file (renamed for clarity)
// This includes equation balance, reference integrity, and reaction consistency
func ValidateStructural(file *EsmFile) *DetailedValidationResult {
	result := &DetailedValidationResult{
		Valid:    true,
		Messages: []ValidationMessage{},
	}

	// Basic struct validation (already done in types.go)
	if err := file.Validate(); err != nil {
		result.Valid = false
		result.Messages = append(result.Messages, ValidationMessage{
			Level:   "error",
			Message: fmt.Sprintf("Basic validation failed: %v", err),
			Path:    "$",
		})
		return result
	}

	// Validate models
	for modelName, model := range file.Models {
		validateModel(modelName, &model, result, file)
	}

	// Validate reaction systems
	for systemName, system := range file.ReactionSystems {
		validateReactionSystem(systemName, &system, result, file)
	}

	// Validate coupling references
	validateCouplingReferences(file, result)

	// Validate data loader references
	validateDataLoaderReferences(file, result)

	// Validate operator references
	validateOperatorReferences(file, result)

	return result
}

// validateModel checks model-specific validation rules
func validateModel(modelName string, model *Model, result *DetailedValidationResult, file *EsmFile) {
	basePath := fmt.Sprintf("$.models.%s", modelName)

	// Check that all variables referenced in equations exist
	allVars := make(map[string]bool)
	for varName := range model.Variables {
		allVars[varName] = true
	}

	for i, eq := range model.Equations {
		eqPath := fmt.Sprintf("%s.equations[%d]", basePath, i)
		validateExpressionVariablesWithScoped(eq.LHS, allVars, fmt.Sprintf("%s.lhs", eqPath), result, file, modelName)
		validateExpressionVariablesWithScoped(eq.RHS, allVars, fmt.Sprintf("%s.rhs", eqPath), result, file, modelName)
	}

	// Equation-unknown balance validation (Section 3.2.1)
	validateEquationUnknownBalance(modelName, model, basePath, result)

	// Check observed variables have expressions
	for varName, variable := range model.Variables {
		varPath := fmt.Sprintf("%s.variables.%s", basePath, varName)
		if variable.Type == "observed" && variable.Expression == nil {
			result.Valid = false
			result.Messages = append(result.Messages, ValidationMessage{
				Level:   "error",
				Message: "Observed variable must have an expression",
				Path:    varPath,
			})
		}
	}

	// Validate discrete events
	for i, event := range model.DiscreteEvents {
		validateDiscreteEvent(&event, allVars, fmt.Sprintf("%s.discrete_events[%d]", basePath, i), result, file, modelName)
	}

	// Validate continuous events
	for i, event := range model.ContinuousEvents {
		validateContinuousEvent(&event, allVars, fmt.Sprintf("%s.continuous_events[%d]", basePath, i), result, file, modelName)
	}
}

// validateReactionSystem checks reaction system-specific validation rules
func validateReactionSystem(systemName string, system *ReactionSystem, result *DetailedValidationResult, file *EsmFile) {
	basePath := fmt.Sprintf("$.reaction_systems.%s", systemName)

	// Check reaction stoichiometry balance (optional - could be intentionally unbalanced)
	for i, reaction := range system.Reactions {
		reactionPath := fmt.Sprintf("%s.reactions[%d]", basePath, i)
		validateReaction(&reaction, system, reactionPath, result)
	}

	// Check that all species referenced in reactions exist
	allSpecies := make(map[string]bool)
	for speciesName := range system.Species {
		allSpecies[speciesName] = true
	}

	allParams := make(map[string]bool)
	for paramName := range system.Parameters {
		allParams[paramName] = true
	}

	// Combined variables for expression validation
	allVars := make(map[string]bool)
	for name := range allSpecies {
		allVars[name] = true
	}
	for name := range allParams {
		allVars[name] = true
	}

	for i, reaction := range system.Reactions {
		reactionPath := fmt.Sprintf("%s.reactions[%d]", basePath, i)

		// Check substrates reference valid species
		for j, substrate := range reaction.Substrates {
			if !allSpecies[substrate.Species] {
				result.Valid = false
				result.Messages = append(result.Messages, ValidationMessage{
					Level:   "error",
					Message: fmt.Sprintf("Unknown species '%s' in reaction substrate", substrate.Species),
					Path:    fmt.Sprintf("%s.substrates[%d].species", reactionPath, j),
				})
			}
		}

		// Check products reference valid species
		for j, product := range reaction.Products {
			if !allSpecies[product.Species] {
				result.Valid = false
				result.Messages = append(result.Messages, ValidationMessage{
					Level:   "error",
					Message: fmt.Sprintf("Unknown species '%s' in reaction product", product.Species),
					Path:    fmt.Sprintf("%s.products[%d].species", reactionPath, j),
				})
			}
		}

		// Validate rate expression
		validateExpressionVariablesWithScoped(reaction.Rate, allVars, fmt.Sprintf("%s.rate", reactionPath), result, file, systemName)
	}
}

// validateReaction performs reaction-specific validation
func validateReaction(reaction *Reaction, system *ReactionSystem, path string, result *DetailedValidationResult) {
	// Check for duplicate species in substrates/products
	substrateSpecies := make(map[string]int)
	for i, substrate := range reaction.Substrates {
		if count, exists := substrateSpecies[substrate.Species]; exists {
			result.Messages = append(result.Messages, ValidationMessage{
				Level:   "warning",
				Message: fmt.Sprintf("Species '%s' appears multiple times in substrates (positions %d and %d)", substrate.Species, count, i),
				Path:    fmt.Sprintf("%s.substrates", path),
			})
		}
		substrateSpecies[substrate.Species] = i
	}

	productSpecies := make(map[string]int)
	for i, product := range reaction.Products {
		if count, exists := productSpecies[product.Species]; exists {
			result.Messages = append(result.Messages, ValidationMessage{
				Level:   "warning",
				Message: fmt.Sprintf("Species '%s' appears multiple times in products (positions %d and %d)", product.Species, count, i),
				Path:    fmt.Sprintf("%s.products", path),
			})
		}
		productSpecies[product.Species] = i
	}
}

// validateExpressionVariables checks that all variables in an expression exist
func validateExpressionVariables(expr Expression, allVars map[string]bool, path string, result *DetailedValidationResult) {
	validateExpressionVariablesWithScoped(expr, allVars, path, result, nil, "")
}

// validateExpressionVariablesWithScoped checks that all variables in an expression exist
// with support for scoped reference resolution
func validateExpressionVariablesWithScoped(expr Expression, allVars map[string]bool, path string, result *DetailedValidationResult, file *EsmFile, currentSystem string) {
	switch e := expr.(type) {
	case string:
		// Variable reference - check if it exists
		if !allVars[e] {
			// If it's a scoped reference and we have file context, try to resolve it
			if file != nil && strings.Contains(e, ".") {
				if _, resolved := resolveScopedReference(e, file, currentSystem); !resolved {
					result.Valid = false
					result.Messages = append(result.Messages, ValidationMessage{
						Level:   "error",
						Message: fmt.Sprintf("Unresolved scoped reference '%s'", e),
						Path:    path,
					})
				}
			} else {
				result.Valid = false
				result.Messages = append(result.Messages, ValidationMessage{
					Level:   "error",
					Message: fmt.Sprintf("Unknown variable '%s'", e),
					Path:    path,
				})
			}
		}
	case ExprNode:
		// Recursively validate arguments
		for i, arg := range e.Args {
			validateExpressionVariablesWithScoped(arg, allVars, fmt.Sprintf("%s.args[%d]", path, i), result, file, currentSystem)
		}
	case float64, int:
		// Numeric literals are always valid
	default:
		result.Messages = append(result.Messages, ValidationMessage{
			Level:   "warning",
			Message: fmt.Sprintf("Unknown expression type: %T", e),
			Path:    path,
		})
	}
}

// validateDiscreteEvent validates discrete event structure
func validateDiscreteEvent(event *DiscreteEvent, allVars map[string]bool, path string, result *DetailedValidationResult, file *EsmFile, currentSystem string) {
	// Validate trigger expression if it's a condition type
	if event.Trigger.Type == "condition" && event.Trigger.Expression != nil {
		validateExpressionVariablesWithScoped(event.Trigger.Expression, allVars, fmt.Sprintf("%s.trigger.expression", path), result, file, currentSystem)
	}

	// Validate affect equations
	for i, affect := range event.Affects {
		affectPath := fmt.Sprintf("%s.affects[%d]", path, i)

		// Check that the target variable exists (could be scoped)
		if !allVars[affect.LHS] {
			if file != nil && strings.Contains(affect.LHS, ".") {
				if _, resolved := resolveScopedReference(affect.LHS, file, currentSystem); !resolved {
					result.Valid = false
					result.Messages = append(result.Messages, ValidationMessage{
						Level:   "error",
						Message: fmt.Sprintf("Unresolved scoped reference '%s' in affect equation", affect.LHS),
						Path:    fmt.Sprintf("%s.lhs", affectPath),
					})
				}
			} else {
				result.Valid = false
				result.Messages = append(result.Messages, ValidationMessage{
					Level:   "error",
					Message: fmt.Sprintf("Unknown variable '%s' in affect equation", affect.LHS),
					Path:    fmt.Sprintf("%s.lhs", affectPath),
				})
			}
		}

		// Validate the RHS expression
		validateExpressionVariablesWithScoped(affect.RHS, allVars, fmt.Sprintf("%s.rhs", affectPath), result, file, currentSystem)
	}
}

// validateContinuousEvent validates continuous event structure
func validateContinuousEvent(event *ContinuousEvent, allVars map[string]bool, path string, result *DetailedValidationResult, file *EsmFile, currentSystem string) {
	// Validate condition expressions
	for i, condition := range event.Conditions {
		validateExpressionVariablesWithScoped(condition, allVars, fmt.Sprintf("%s.conditions[%d]", path, i), result, file, currentSystem)
	}

	// Validate affect equations
	for i, affect := range event.Affects {
		affectPath := fmt.Sprintf("%s.affects[%d]", path, i)

		if !allVars[affect.LHS] {
			if file != nil && strings.Contains(affect.LHS, ".") {
				if _, resolved := resolveScopedReference(affect.LHS, file, currentSystem); !resolved {
					result.Valid = false
					result.Messages = append(result.Messages, ValidationMessage{
						Level:   "error",
						Message: fmt.Sprintf("Unresolved scoped reference '%s' in affect equation", affect.LHS),
						Path:    fmt.Sprintf("%s.lhs", affectPath),
					})
				}
			} else {
				result.Valid = false
				result.Messages = append(result.Messages, ValidationMessage{
					Level:   "error",
					Message: fmt.Sprintf("Unknown variable '%s' in affect equation", affect.LHS),
					Path:    fmt.Sprintf("%s.lhs", affectPath),
				})
			}
		}

		validateExpressionVariablesWithScoped(affect.RHS, allVars, fmt.Sprintf("%s.rhs", affectPath), result, file, currentSystem)
	}

	// Validate affect_neg equations if present
	for i, affect := range event.AffectNeg {
		affectPath := fmt.Sprintf("%s.affect_neg[%d]", path, i)

		if !allVars[affect.LHS] {
			if file != nil && strings.Contains(affect.LHS, ".") {
				if _, resolved := resolveScopedReference(affect.LHS, file, currentSystem); !resolved {
					result.Valid = false
					result.Messages = append(result.Messages, ValidationMessage{
						Level:   "error",
						Message: fmt.Sprintf("Unresolved scoped reference '%s' in affect_neg equation", affect.LHS),
						Path:    fmt.Sprintf("%s.lhs", affectPath),
					})
				}
			} else {
				result.Valid = false
				result.Messages = append(result.Messages, ValidationMessage{
					Level:   "error",
					Message: fmt.Sprintf("Unknown variable '%s' in affect_neg equation", affect.LHS),
					Path:    fmt.Sprintf("%s.lhs", affectPath),
				})
			}
		}

		validateExpressionVariablesWithScoped(affect.RHS, allVars, fmt.Sprintf("%s.rhs", affectPath), result, file, currentSystem)
	}
}

// validateCouplingReferences validates that coupling entries reference valid systems
func validateCouplingReferences(file *EsmFile, result *DetailedValidationResult) {
	allSystems := make(map[string]bool)

	// Collect all system names
	for name := range file.Models {
		allSystems[name] = true
	}
	for name := range file.ReactionSystems {
		allSystems[name] = true
	}

	for i, coupling := range file.Coupling {
		basePath := fmt.Sprintf("$.coupling[%d]", i)

		// Now we can use proper type assertions for the typed coupling entries
		switch c := coupling.(type) {
		case OperatorComposeCoupling:
			for j, sysName := range c.Systems {
				if !allSystems[sysName] {
					result.Valid = false
					result.Messages = append(result.Messages, ValidationMessage{
						Level:   "error",
						Message: fmt.Sprintf("Unknown system '%s' in coupling", sysName),
						Path:    fmt.Sprintf("%s.systems[%d]", basePath, j),
					})
				}
			}

		case Couple2Coupling:
			for j, sysName := range c.Systems {
				if !allSystems[sysName] {
					result.Valid = false
					result.Messages = append(result.Messages, ValidationMessage{
						Level:   "error",
						Message: fmt.Sprintf("Unknown system '%s' in coupling", sysName),
						Path:    fmt.Sprintf("%s.systems[%d]", basePath, j),
					})
				}
			}

		case VariableMapCoupling:
			// For variable_map coupling, validate from/to system references
			if !allSystems[c.From] {
				result.Valid = false
				result.Messages = append(result.Messages, ValidationMessage{
					Level:   "error",
					Message: fmt.Sprintf("Unknown system '%s' in coupling", c.From),
					Path:    fmt.Sprintf("%s.from", basePath),
				})
			}
			if !allSystems[c.To] {
				result.Valid = false
				result.Messages = append(result.Messages, ValidationMessage{
					Level:   "error",
					Message: fmt.Sprintf("Unknown system '%s' in coupling", c.To),
					Path:    fmt.Sprintf("%s.to", basePath),
				})
			}

		case OperatorApplyCoupling:
			// For operator_apply coupling, we would need to validate operator references
			// but that would require checking if the operator exists in the operators section
			// For now, we'll skip this validation

		default:
			// Handle the case where coupling is still a map[string]interface{} (shouldn't happen with proper deserialization)
			result.Valid = false
			result.Messages = append(result.Messages, ValidationMessage{
				Level:   "warning",
				Message: fmt.Sprintf("Coupling entry has unknown type: %T", coupling),
				Path:    basePath,
			})
		}
	}
}

// validateDataLoaderReferences validates data loader configurations
func validateDataLoaderReferences(file *EsmFile, result *DetailedValidationResult) {
	for loaderName, loader := range file.DataLoaders {
		basePath := fmt.Sprintf("$.data_loaders.%s", loaderName)

		// Validate that required fields are present
		if loader.Type == "" {
			result.Valid = false
			result.Messages = append(result.Messages, ValidationMessage{
				Level:   "error",
				Message: "Data loader type is required",
				Path:    fmt.Sprintf("%s.type", basePath),
			})
		}

		if loader.LoaderID == "" {
			result.Valid = false
			result.Messages = append(result.Messages, ValidationMessage{
				Level:   "error",
				Message: "Data loader ID is required",
				Path:    fmt.Sprintf("%s.loader_id", basePath),
			})
		}

		if len(loader.Provides) == 0 {
			result.Messages = append(result.Messages, ValidationMessage{
				Level:   "warning",
				Message: "Data loader provides no variables",
				Path:    fmt.Sprintf("%s.provides", basePath),
			})
		}
	}
}

// validateOperatorReferences validates operator configurations
func validateOperatorReferences(file *EsmFile, result *DetailedValidationResult) {
	for operatorName, operator := range file.Operators {
		basePath := fmt.Sprintf("$.operators.%s", operatorName)

		if operator.OperatorID == "" {
			result.Valid = false
			result.Messages = append(result.Messages, ValidationMessage{
				Level:   "error",
				Message: "Operator ID is required",
				Path:    fmt.Sprintf("%s.operator_id", basePath),
			})
		}

		if len(operator.NeededVars) == 0 {
			result.Messages = append(result.Messages, ValidationMessage{
				Level:   "warning",
				Message: "Operator requires no variables",
				Path:    fmt.Sprintf("%s.needed_vars", basePath),
			})
		}
	}
}

// validateEquationUnknownBalance validates equation-unknown balance for models
// as per ESM libraries specification Section 3.2.1
func validateEquationUnknownBalance(modelName string, model *Model, basePath string, result *DetailedValidationResult) {
	// Count state variables
	stateVars := make(map[string]bool)
	for varName, variable := range model.Variables {
		if variable.Type == "state" {
			stateVars[varName] = true
		}
	}
	nStates := len(stateVars)

	// Count ODE equations (equations whose LHS is a time derivative D(var, t))
	odeEquations := make(map[string]bool) // track which state variables have ODE equations
	nOdes := 0

	for _, eq := range model.Equations {
		if lhsNode, ok := eq.LHS.(ExprNode); ok {
			if lhsNode.Op == "D" && len(lhsNode.Args) > 0 {
				// Check if this is a time derivative
				if lhsNode.Wrt != nil && *lhsNode.Wrt == "t" {
					nOdes++
					// Extract the variable name from the derivative
					if varName, ok := lhsNode.Args[0].(string); ok {
						odeEquations[varName] = true
					}
				}
			}
		}
	}

	// Check equation-unknown balance: n_odes == n_states
	if nOdes != nStates {
		result.Valid = false

		// Report which state variables lack ODE equations
		missingEquations := []string{}
		for varName := range stateVars {
			if !odeEquations[varName] {
				missingEquations = append(missingEquations, varName)
			}
		}

		// Report which ODE equations lack corresponding state variables
		extraEquations := []string{}
		for varName := range odeEquations {
			if !stateVars[varName] {
				extraEquations = append(extraEquations, varName)
			}
		}

		// Generate error message
		message := fmt.Sprintf("Equation-unknown balance failed: found %d state variables but %d ODE equations", nStates, nOdes)

		if len(missingEquations) > 0 {
			message += fmt.Sprintf("; state variables without ODE equations: %v", missingEquations)
		}

		if len(extraEquations) > 0 {
			message += fmt.Sprintf("; ODE equations for non-state variables: %v", extraEquations)
		}

		result.Messages = append(result.Messages, ValidationMessage{
			Level:   "error",
			Message: message,
			Path:    basePath,
		})
	}
}