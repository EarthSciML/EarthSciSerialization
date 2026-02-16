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