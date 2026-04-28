package esm

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func loadFixture(t *testing.T) string {
	t.Helper()
	repoRoot, err := filepath.Abs("../../../..")
	if err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(repoRoot, "tests", "valid", "expression_templates_arrhenius.esm")
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read fixture: %v", err)
	}
	return string(data)
}

// arrheniusInline returns the expanded AST as ExprNode (the shape
// json.Unmarshal produces against the typed Go schema).
func arrheniusInline(aPre float64, ea int64) any {
	return ExprNode{
		Op: "*",
		Args: []interface{}{
			aPre,
			ExprNode{
				Op: "exp",
				Args: []interface{}{
					ExprNode{
						Op: "/",
						Args: []interface{}{
							ExprNode{Op: "-", Args: []interface{}{ea}},
							"T",
						},
					},
				},
			},
			"num_density",
		},
	}
}

func TestExpressionTemplates_LoadFixtureExpanded(t *testing.T) {
	src := loadFixture(t)
	esm, err := LoadString(src)
	if err != nil {
		t.Fatalf("Load: %v", err)
	}
	rs, ok := esm.ReactionSystems["ToyArrhenius"]
	if !ok {
		t.Fatal("ToyArrhenius missing")
	}
	if len(rs.Reactions) != 3 {
		t.Fatalf("expected 3 reactions, got %d", len(rs.Reactions))
	}

	cases := []struct {
		id   string
		aPre float64
		ea   int64
	}{
		{"R1", 1.8e-12, 1500},
		{"R2", 3.0e-13, 460},
		{"R3", 4.5e-14, 920},
	}
	for _, c := range cases {
		var r *Reaction
		for i := range rs.Reactions {
			if rs.Reactions[i].ID == c.id {
				r = &rs.Reactions[i]
				break
			}
		}
		if r == nil {
			t.Fatalf("reaction %s not found", c.id)
		}
		expected := arrheniusInline(c.aPre, c.ea)
		if !reflect.DeepEqual(r.Rate, expected) {
			t.Errorf("%s rate mismatch:\n got: %#v\n want: %#v", c.id, r.Rate, expected)
		}
	}
}

func TestExpressionTemplates_RejectsPre040(t *testing.T) {
	src := loadFixture(t)
	mutated := strings.Replace(src, `"esm": "0.4.0"`, `"esm": "0.3.0"`, 1)
	if _, err := LoadString(mutated); err == nil {
		t.Fatal("expected error for esm: 0.3.0 with apply_expression_template")
	}
}

func TestExpressionTemplates_RejectsUnknownTemplate(t *testing.T) {
	mutated := mutateFirstRate(t, `{"op":"apply_expression_template","args":[],"name":"no_such_template","bindings":{"A_pre":1.0,"Ea":1.0}}`)
	if _, err := LoadString(mutated); err == nil {
		t.Fatal("expected error for unknown template")
	}
}

func TestExpressionTemplates_RejectsMissingBinding(t *testing.T) {
	mutated := mutateFirstRate(t, `{"op":"apply_expression_template","args":[],"name":"arrhenius","bindings":{"A_pre":1.0}}`)
	if _, err := LoadString(mutated); err == nil {
		t.Fatal("expected error for missing binding")
	}
}

func TestExpressionTemplates_RejectsExtraBinding(t *testing.T) {
	mutated := mutateFirstRate(t, `{"op":"apply_expression_template","args":[],"name":"arrhenius","bindings":{"A_pre":1.0,"Ea":1.0,"Junk":2.0}}`)
	if _, err := LoadString(mutated); err == nil {
		t.Fatal("expected error for unknown binding")
	}
}

// mutateFirstRate replaces the first "rate": {...} object in the fixture
// with the literal `rateJSON` so per-test malformed bindings surface
// through the loader.
func mutateFirstRate(t *testing.T, rateJSON string) string {
	t.Helper()
	src := loadFixture(t)
	var data map[string]any
	if err := json.Unmarshal([]byte(src), &data); err != nil {
		t.Fatal(err)
	}
	rs := data["reaction_systems"].(map[string]any)["ToyArrhenius"].(map[string]any)
	reactions := rs["reactions"].([]any)
	first := reactions[0].(map[string]any)
	var newRate map[string]any
	if err := json.Unmarshal([]byte(rateJSON), &newRate); err != nil {
		t.Fatal(err)
	}
	first["rate"] = newRate
	out, err := json.Marshal(data)
	if err != nil {
		t.Fatal(err)
	}
	return string(out)
}

func TestExpressionTemplates_ExpansionDeterministic(t *testing.T) {
	src := loadFixture(t)
	a, err := LoadString(src)
	if err != nil {
		t.Fatal(err)
	}
	b, err := LoadString(src)
	if err != nil {
		t.Fatal(err)
	}
	rsa := a.ReactionSystems["ToyArrhenius"].Reactions
	rsb := b.ReactionSystems["ToyArrhenius"].Reactions
	for i := range rsa {
		if !reflect.DeepEqual(rsa[i].Rate, rsb[i].Rate) {
			t.Errorf("reaction %d expansion differs across loads", i)
		}
	}
}
