package esm

import (
	"strings"
	"testing"
)

func TestFlatten_SingleModelNamespacesVariables(t *testing.T) {
	file := &EsmFile{
		Models: map[string]Model{
			"Atmos": {
				Variables: map[string]ModelVariable{
					"T": {Type: "state"},
					"k": {Type: "parameter"},
				},
				Equations: []Equation{},
			},
		},
	}

	flat, err := Flatten(file)
	if err != nil {
		t.Fatalf("Flatten: %v", err)
	}

	if !contains(flat.StateVariables, "Atmos.T") {
		t.Errorf("expected Atmos.T in state variables, got %v", flat.StateVariables)
	}
	if !contains(flat.Parameters, "Atmos.k") {
		t.Errorf("expected Atmos.k in parameters, got %v", flat.Parameters)
	}
	if !contains(flat.Metadata.SourceSystems, "Atmos") {
		t.Errorf("expected Atmos in source systems, got %v", flat.Metadata.SourceSystems)
	}
}

func TestFlatten_ReactionSystemNamespacesSpecies(t *testing.T) {
	file := &EsmFile{
		ReactionSystems: map[string]ReactionSystem{
			"Chem": {
				Species: map[string]Species{
					"O3": {},
				},
				Parameters: map[string]Parameter{
					"k1": {},
				},
				Reactions: []Reaction{},
			},
		},
	}

	flat, err := Flatten(file)
	if err != nil {
		t.Fatalf("Flatten: %v", err)
	}

	if !contains(flat.StateVariables, "Chem.O3") {
		t.Errorf("expected Chem.O3 in state variables, got %v", flat.StateVariables)
	}
	if !contains(flat.Parameters, "Chem.k1") {
		t.Errorf("expected Chem.k1 in parameters, got %v", flat.Parameters)
	}
}

func TestFlatten_RecordsCouplingRules(t *testing.T) {
	file := &EsmFile{
		Models: map[string]Model{
			"A": {
				Variables: map[string]ModelVariable{"x": {Type: "state"}},
				Equations: []Equation{},
			},
			"B": {
				Variables: map[string]ModelVariable{"y": {Type: "parameter"}},
				Equations: []Equation{},
			},
		},
		Coupling: []interface{}{
			VariableMapCoupling{
				Type:      "variable_map",
				From:      "A.x",
				To:        "B.y",
				Transform: "identity",
			},
		},
	}

	flat, err := Flatten(file)
	if err != nil {
		t.Fatalf("Flatten: %v", err)
	}

	if len(flat.Metadata.CouplingRules) == 0 {
		t.Fatalf("expected coupling rules to be recorded")
	}
	found := false
	for _, rule := range flat.Metadata.CouplingRules {
		if strings.Contains(rule, "variable_map") || strings.Contains(rule, "VariableMap") {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("expected variable_map rule, got %v", flat.Metadata.CouplingRules)
	}
}

func contains(haystack []string, needle string) bool {
	for _, h := range haystack {
		if h == needle {
			return true
		}
	}
	return false
}
