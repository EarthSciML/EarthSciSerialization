package esm

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestValidateValidModel(t *testing.T) {
	esmFile := &EsmFile{
		Esm: "0.1.0",
		Metadata: Metadata{
			Name:    "TestModel",
			Authors: []string{"Test Author"},
		},
		Models: map[string]Model{
			"TestModel": {
				Variables: map[string]ModelVariable{
					"x": {
						Type:    "state",
						Units:   strPtr("m"),
						Default: 0.0,
					},
					"y": {
						Type:       "observed",
						Expression: "x",
					},
				},
				Equations: []Equation{
					{
						LHS: ExprNode{Op: "D", Args: []interface{}{"x"}, Wrt: strPtr("t")},
						RHS: float64(1.0),
					},
				},
			},
		},
	}

	result := Validate(esmFile)
	assert.True(t, result.Valid)
	assert.Empty(t, result.Messages)
}

func TestValidateModelWithUnknownVariable(t *testing.T) {
	esmFile := &EsmFile{
		Esm: "0.1.0",
		Metadata: Metadata{
			Name:    "TestModel",
			Authors: []string{"Test Author"},
		},
		Models: map[string]Model{
			"TestModel": {
				Variables: map[string]ModelVariable{
					"x": {Type: "state"},
				},
				Equations: []Equation{
					{
						LHS: ExprNode{Op: "D", Args: []interface{}{"x"}, Wrt: strPtr("t")},
						RHS: "unknown_var", // This variable doesn't exist
					},
				},
			},
		},
	}

	result := Validate(esmFile)
	assert.False(t, result.Valid)
	assert.Len(t, result.Messages, 1)
	assert.Contains(t, result.Messages[0].Message, "Unknown variable 'unknown_var'")
	assert.Equal(t, "error", result.Messages[0].Level)
}

func TestValidateObservedVariableWithoutExpression(t *testing.T) {
	esmFile := &EsmFile{
		Esm: "0.1.0",
		Metadata: Metadata{
			Name:    "TestModel",
			Authors: []string{"Test Author"},
		},
		Models: map[string]Model{
			"TestModel": {
				Variables: map[string]ModelVariable{
					"x": {Type: "state"},
					"y": {Type: "observed"}, // Missing expression
				},
				Equations: []Equation{
					{
						LHS: ExprNode{Op: "D", Args: []interface{}{"x"}, Wrt: strPtr("t")},
						RHS: float64(1.0),
					},
				},
			},
		},
	}

	result := Validate(esmFile)
	assert.False(t, result.Valid)
	assert.Len(t, result.Messages, 1)
	assert.Contains(t, result.Messages[0].Message, "Observed variable must have an expression")
}

func TestValidateReactionSystem(t *testing.T) {
	esmFile := &EsmFile{
		Esm: "0.1.0",
		Metadata: Metadata{
			Name:    "TestReactions",
			Authors: []string{"Test Author"},
		},
		ReactionSystems: map[string]ReactionSystem{
			"TestReactions": {
				Species: map[string]Species{
					"A": {Units: strPtr("mol/mol")},
					"B": {Units: strPtr("mol/mol")},
				},
				Parameters: map[string]Parameter{
					"k": {Units: strPtr("1/s")},
				},
				Reactions: []Reaction{
					{
						ID:         "R1",
						Substrates: []SubstrateProduct{{Species: "A", Stoichiometry: 1}},
						Products:   []SubstrateProduct{{Species: "B", Stoichiometry: 1}},
						Rate:       "k",
					},
				},
			},
		},
	}

	result := Validate(esmFile)
	assert.True(t, result.Valid)
	assert.Empty(t, result.Messages)
}

func TestValidateReactionWithUnknownSpecies(t *testing.T) {
	esmFile := &EsmFile{
		Esm: "0.1.0",
		Metadata: Metadata{
			Name:    "TestReactions",
			Authors: []string{"Test Author"},
		},
		ReactionSystems: map[string]ReactionSystem{
			"TestReactions": {
				Species: map[string]Species{
					"A": {Units: strPtr("mol/mol")},
				},
				Parameters: map[string]Parameter{
					"k": {Units: strPtr("1/s")},
				},
				Reactions: []Reaction{
					{
						ID:         "R1",
						Substrates: []SubstrateProduct{{Species: "A", Stoichiometry: 1}},
						Products:   []SubstrateProduct{{Species: "UnknownSpecies", Stoichiometry: 1}},
						Rate:       "k",
					},
				},
			},
		},
	}

	result := Validate(esmFile)
	assert.False(t, result.Valid)
	assert.Len(t, result.Messages, 1)
	assert.Contains(t, result.Messages[0].Message, "Unknown species 'UnknownSpecies'")
}

func TestValidateComplexExpression(t *testing.T) {
	esmFile := &EsmFile{
		Esm: "0.1.0",
		Metadata: Metadata{
			Name:    "TestModel",
			Authors: []string{"Test Author"},
		},
		Models: map[string]Model{
			"TestModel": {
				Variables: map[string]ModelVariable{
					"x": {Type: "state"},
					"y": {Type: "state"},
					"k": {Type: "parameter"},
				},
				Equations: []Equation{
					{
						LHS: ExprNode{Op: "D", Args: []interface{}{"x"}, Wrt: strPtr("t")},
						RHS: ExprNode{
							Op: "*",
							Args: []interface{}{
								"k",
								ExprNode{Op: "+", Args: []interface{}{"x", "y"}},
							},
						},
					},
					{
						LHS: ExprNode{Op: "D", Args: []interface{}{"y"}, Wrt: strPtr("t")},
						RHS: ExprNode{
							Op: "*",
							Args: []interface{}{
								"k",
								ExprNode{Op: "-", Args: []interface{}{"x", "y"}},
							},
						},
					},
				},
			},
		},
	}

	result := Validate(esmFile)
	assert.True(t, result.Valid)
	assert.Empty(t, result.Messages)
}

func TestValidateDiscreteEvent(t *testing.T) {
	esmFile := &EsmFile{
		Esm: "0.1.0",
		Metadata: Metadata{
			Name:    "TestModel",
			Authors: []string{"Test Author"},
		},
		Models: map[string]Model{
			"TestModel": {
				Variables: map[string]ModelVariable{
					"x": {Type: "state"},
				},
				Equations: []Equation{
					{
						LHS: ExprNode{Op: "D", Args: []interface{}{"x"}, Wrt: strPtr("t")},
						RHS: float64(1.0),
					},
				},
				DiscreteEvents: []DiscreteEvent{
					{
						Trigger: DiscreteEventTrigger{
							Type:       "condition",
							Expression: ExprNode{Op: ">", Args: []interface{}{"x", 10.0}},
						},
						Affects: []AffectEquation{
							{
								LHS: "x",
								RHS: float64(0.0),
							},
						},
					},
				},
			},
		},
	}

	result := Validate(esmFile)
	assert.True(t, result.Valid)
	assert.Empty(t, result.Messages)
}

func TestValidateDataLoaders(t *testing.T) {
	esmFile := &EsmFile{
		Esm: "0.1.0",
		Metadata: Metadata{
			Name:    "TestModel",
			Authors: []string{"Test Author"},
		},
		Models: map[string]Model{
			"TestModel": {
				Variables: map[string]ModelVariable{
					"x": {Type: "state"},
				},
				Equations: []Equation{
					{
						LHS: ExprNode{Op: "D", Args: []interface{}{"x"}, Wrt: strPtr("t")},
						RHS: float64(1.0),
					},
				},
			},
		},
		DataLoaders: map[string]DataLoader{
			"TestLoader": {
				Type:     "gridded_data",
				LoaderID: "test_loader",
				Provides: map[string]ProvidedVar{
					"temperature": {Units: "K"},
				},
			},
		},
	}

	result := Validate(esmFile)
	assert.True(t, result.Valid)
	assert.Empty(t, result.Messages)
}

func TestValidateDataLoaderMissingRequiredFields(t *testing.T) {
	esmFile := &EsmFile{
		Esm: "0.1.0",
		Metadata: Metadata{
			Name:    "TestModel",
			Authors: []string{"Test Author"},
		},
		Models: map[string]Model{
			"TestModel": {
				Variables: map[string]ModelVariable{
					"x": {Type: "state"},
				},
				Equations: []Equation{
					{
						LHS: ExprNode{Op: "D", Args: []interface{}{"x"}, Wrt: strPtr("t")},
						RHS: float64(1.0),
					},
				},
			},
		},
		DataLoaders: map[string]DataLoader{
			"BadLoader": {
				// Missing Type and LoaderID
				Provides: map[string]ProvidedVar{},
			},
		},
	}

	result := Validate(esmFile)
	assert.False(t, result.Valid)

	// Should have errors for missing type and loader_id, and warning for no provides
	errorCount := 0
	warningCount := 0
	for _, msg := range result.Messages {
		if msg.Level == "error" {
			errorCount++
		} else if msg.Level == "warning" {
			warningCount++
		}
	}

	assert.GreaterOrEqual(t, errorCount, 2) // Type and LoaderID missing
	assert.GreaterOrEqual(t, warningCount, 1) // No variables provided
}

// Test equation-unknown balance validation
func TestValidateEquationUnknownBalance(t *testing.T) {
	tests := []struct {
		name          string
		model         Model
		expectedValid bool
		expectedError string
	}{
		{
			name: "balanced model with one state variable and one ODE",
			model: Model{
				Variables: map[string]ModelVariable{
					"x": {Type: "state"},
				},
				Equations: []Equation{
					{
						LHS: ExprNode{Op: "D", Args: []interface{}{"x"}, Wrt: strPtr("t")},
						RHS: float64(1.0),
					},
				},
			},
			expectedValid: true,
		},
		{
			name: "balanced model with two state variables and two ODEs",
			model: Model{
				Variables: map[string]ModelVariable{
					"x": {Type: "state"},
					"y": {Type: "state"},
					"k": {Type: "parameter"},
				},
				Equations: []Equation{
					{
						LHS: ExprNode{Op: "D", Args: []interface{}{"x"}, Wrt: strPtr("t")},
						RHS: ExprNode{Op: "*", Args: []interface{}{"k", "y"}},
					},
					{
						LHS: ExprNode{Op: "D", Args: []interface{}{"y"}, Wrt: strPtr("t")},
						RHS: ExprNode{Op: "*", Args: []interface{}{"k", "x"}},
					},
				},
			},
			expectedValid: true,
		},
		{
			name: "unbalanced model with state variable but no ODE",
			model: Model{
				Variables: map[string]ModelVariable{
					"x": {Type: "state"},
					"y": {Type: "state"},
				},
				Equations: []Equation{
					{
						LHS: ExprNode{Op: "D", Args: []interface{}{"x"}, Wrt: strPtr("t")},
						RHS: float64(1.0),
					},
				},
			},
			expectedValid: false,
			expectedError: "state variables without ODE equations: [y]",
		},
		{
			name: "unbalanced model with ODE for non-state variable",
			model: Model{
				Variables: map[string]ModelVariable{
					"x": {Type: "state"},
					"k": {Type: "parameter"},
				},
				Equations: []Equation{
					{
						LHS: ExprNode{Op: "D", Args: []interface{}{"x"}, Wrt: strPtr("t")},
						RHS: float64(1.0),
					},
					{
						LHS: ExprNode{Op: "D", Args: []interface{}{"k"}, Wrt: strPtr("t")},
						RHS: float64(2.0),
					},
				},
			},
			expectedValid: false,
			expectedError: "ODE equations for non-state variables: [k]",
		},
		{
			name: "unbalanced model with no state variables but ODEs",
			model: Model{
				Variables: map[string]ModelVariable{
					"k": {Type: "parameter"},
				},
				Equations: []Equation{
					{
						LHS: ExprNode{Op: "D", Args: []interface{}{"k"}, Wrt: strPtr("t")},
						RHS: float64(1.0),
					},
				},
			},
			expectedValid: false,
			expectedError: "found 0 state variables but 1 ODE equations",
		},
		{
			name: "model with non-derivative equations (should be balanced)",
			model: Model{
				Variables: map[string]ModelVariable{
					"x": {Type: "state"},
					"y": {Type: "observed", Expression: ExprNode{Op: "*", Args: []interface{}{"x", 2.0}}},
				},
				Equations: []Equation{
					{
						LHS: ExprNode{Op: "D", Args: []interface{}{"x"}, Wrt: strPtr("t")},
						RHS: float64(1.0),
					},
					{
						// This is not an ODE, it's an algebraic constraint
						LHS: "y",
						RHS: ExprNode{Op: "*", Args: []interface{}{"x", 2.0}},
					},
				},
			},
			expectedValid: true,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			esmFile := &EsmFile{
				Esm: "0.1.0",
				Metadata: Metadata{
					Name:    "TestModel",
					Authors: []string{"Test Author"},
				},
				Models: map[string]Model{
					"TestModel": tc.model,
				},
			}

			result := Validate(esmFile)

			assert.Equal(t, tc.expectedValid, result.Valid, "Validation result should match expected")

			if !tc.expectedValid {
				assert.NotEmpty(t, result.Messages, "Should have validation messages")

				found := false
				for _, msg := range result.Messages {
					if tc.expectedError != "" && assert.Contains(t, msg.Message, tc.expectedError) {
						found = true
						break
					}
				}

				if tc.expectedError != "" {
					assert.True(t, found, "Should find expected error message containing: %s", tc.expectedError)
				}
			} else {
				// Check that there are no equation-unknown balance errors
				for _, msg := range result.Messages {
					assert.NotContains(t, msg.Message, "Equation-unknown balance", "Should not have equation-unknown balance errors")
				}
			}
		})
	}
}