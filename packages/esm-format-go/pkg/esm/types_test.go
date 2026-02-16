package esm

import (
	"encoding/json"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestEsmFileBasicStructure(t *testing.T) {
	// Test creating a basic ESM file structure
	esmFile := EsmFile{
		Esm: "0.1.0",
		Metadata: Metadata{
			Name:        "TestModel",
			Description: strPtr("A test model"),
			Authors:     []string{"Test Author"},
		},
	}

	// Test validation - this should fail because no models or reaction systems
	err := esmFile.Validate()
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "at least one of 'models' or 'reaction_systems' must be present")
}

func TestEsmFileWithModel(t *testing.T) {
	// Test creating an ESM file with a simple model
	esmFile := EsmFile{
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

	// Test validation - this should pass
	err := esmFile.Validate()
	assert.NoError(t, err)
}

func TestEsmFileWithReactionSystem(t *testing.T) {
	// Test creating an ESM file with a reaction system
	esmFile := EsmFile{
		Esm: "0.1.0",
		Metadata: Metadata{
			Name:    "TestReactions",
			Authors: []string{"Test Author"},
		},
		ReactionSystems: map[string]ReactionSystem{
			"TestReactions": {
				Species: map[string]Species{
					"A": {Units: strPtr("mol/mol"), Default: 1e-9},
					"B": {Units: strPtr("mol/mol"), Default: 1e-9},
				},
				Parameters: map[string]Parameter{
					"k": {Units: strPtr("1/s"), Default: 1e-3},
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

	// Test validation - this should pass
	err := esmFile.Validate()
	assert.NoError(t, err)
}

func TestJSONSerialization(t *testing.T) {
	// Test basic JSON serialization
	esmFile := EsmFile{
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

	// Serialize to JSON
	jsonData, err := esmFile.ToJSON()
	require.NoError(t, err)
	assert.NotEmpty(t, jsonData)

	// Test that we can unmarshal it back
	var parsed EsmFile
	err = json.Unmarshal(jsonData, &parsed)
	require.NoError(t, err)

	// Basic checks
	assert.Equal(t, "0.1.0", parsed.Esm)
	assert.Equal(t, "TestModel", parsed.Metadata.Name)
	assert.Len(t, parsed.Models, 1)
}

func TestUnmarshalExpression(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected interface{}
	}{
		{
			name:     "number",
			input:    "3.14",
			expected: float64(3.14),
		},
		{
			name:     "string",
			input:    `"x"`,
			expected: "x",
		},
		{
			name:  "object",
			input: `{"op": "+", "args": ["a", "b"]}`,
			expected: ExprNode{
				Op:   "+",
				Args: []interface{}{"a", "b"},
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := UnmarshalExpression([]byte(tt.input))
			require.NoError(t, err)
			assert.Equal(t, tt.expected, result)
		})
	}
}

// Helper function to get string pointers
func strPtr(s string) *string {
	return &s
}