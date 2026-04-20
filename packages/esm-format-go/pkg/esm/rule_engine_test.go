package esm

import (
	"testing"
)

func opNode(op string, args ...interface{}) ExprNode {
	return ExprNode{Op: op, Args: args}
}

func TestMatchAndReplace(t *testing.T) {
	rule := Rule{
		Name:        "add_zero",
		Pattern:     opNode("+", "$a", int64(0)),
		Replacement: "$a",
	}
	seed := opNode("+", "x", int64(0))
	out, err := Rewrite(seed, []Rule{rule}, NewRuleContext(), 0)
	if err != nil {
		t.Fatal(err)
	}
	got, err := CanonicalJSON(out)
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != `"x"` {
		t.Errorf("got %s, want %q", got, "x")
	}
}

func TestNonlinearMatch(t *testing.T) {
	pat := opNode("-", "$a", "$a")
	if _, ok := MatchPattern(pat, opNode("-", "x", "x")); !ok {
		t.Error("expected match on -(x, x)")
	}
	if _, ok := MatchPattern(pat, opNode("-", "x", "y")); ok {
		t.Error("expected no match on -(x, y)")
	}
}

func TestSiblingFieldPvar(t *testing.T) {
	pat := ExprNode{Op: "D", Args: []interface{}{"$u"}, Wrt: strPtr("$x")}
	repl := opNode("index", "$u", "$x")
	rule := Rule{Name: "d_to_index", Pattern: pat, Replacement: repl}
	seed := ExprNode{Op: "D", Args: []interface{}{"T"}, Wrt: strPtr("t")}
	out, err := Rewrite(seed, []Rule{rule}, NewRuleContext(), 0)
	if err != nil {
		t.Fatal(err)
	}
	got, _ := CanonicalJSON(out)
	want := `{"args":["T","t"],"op":"index"}`
	if string(got) != want {
		t.Errorf("got %s, want %s", got, want)
	}
}

func TestNotConverged(t *testing.T) {
	rule := Rule{
		Name:        "explode",
		Pattern:     "$a",
		Replacement: opNode("+", "$a", int64(0)),
	}
	_, err := Rewrite("x", []Rule{rule}, NewRuleContext(), 3)
	re, ok := err.(*RuleEngineError)
	if !ok || re.Code != "E_RULES_NOT_CONVERGED" {
		t.Errorf("got %v, want E_RULES_NOT_CONVERGED", err)
	}
}

func TestTopDownSeal(t *testing.T) {
	// (x+x)+(x+x) with rule $a+$a -> 2*$a
	rule := Rule{
		Name:        "double",
		Pattern:     opNode("+", "$a", "$a"),
		Replacement: opNode("*", int64(2), "$a"),
	}
	inner := opNode("+", "x", "x")
	seed := opNode("+", inner, inner)
	out, err := Rewrite(seed, []Rule{rule}, NewRuleContext(), 0)
	if err != nil {
		t.Fatal(err)
	}
	want := opNode("*", int64(2), opNode("*", int64(2), "x"))
	gotJSON, _ := CanonicalJSON(out)
	wantJSON, _ := CanonicalJSON(want)
	if string(gotJSON) != string(wantJSON) {
		t.Errorf("got %s, want %s", gotJSON, wantJSON)
	}
}

func TestPDEOpUnrewritten(t *testing.T) {
	expr := ExprNode{Op: "grad", Args: []interface{}{"T"}, Dim: strPtr("x")}
	err := CheckUnrewrittenPDEOps(expr)
	re, ok := err.(*RuleEngineError)
	if !ok || re.Code != "E_UNREWRITTEN_PDE_OP" {
		t.Errorf("got %v, want E_UNREWRITTEN_PDE_OP", err)
	}
	ok2 := opNode("index", "T", "x")
	if err := CheckUnrewrittenPDEOps(ok2); err != nil {
		t.Errorf("expected nil, got %v", err)
	}
}

func TestPatternVarUnbound(t *testing.T) {
	// Replacement references unbound $b.
	_, err := ApplyBindings("$b", map[string]Expression{"$a": "x"})
	re, ok := err.(*RuleEngineError)
	if !ok || re.Code != "E_PATTERN_VAR_UNBOUND" {
		t.Errorf("got %v, want E_PATTERN_VAR_UNBOUND", err)
	}
}

func TestParseRulesArrayAndObject(t *testing.T) {
	arr := []byte(`[
		{"name": "first",  "pattern": {"op": "*", "args": ["$a", 0]}, "replacement": 0},
		{"name": "second", "pattern": {"op": "+", "args": ["$a", 0]}, "replacement": "$a"}
	]`)
	rs, err := ParseRules(arr)
	if err != nil {
		t.Fatal(err)
	}
	if len(rs) != 2 || rs[0].Name != "first" || rs[1].Name != "second" {
		t.Errorf("got %+v", rs)
	}

	obj := []byte(`{"a": {"pattern": {"op": "+", "args": ["$x", 0]}, "replacement": "$x"}}`)
	rs2, err := ParseRules(obj)
	if err != nil {
		t.Fatal(err)
	}
	if len(rs2) != 1 || rs2[0].Name != "a" {
		t.Errorf("got %+v", rs2)
	}
}

func TestParseRuleMissingReplacement(t *testing.T) {
	raw := []byte(`[{"name": "no_repl", "pattern": "$a", "use": "scheme"}]`)
	_, err := ParseRules(raw)
	re, ok := err.(*RuleEngineError)
	if !ok || re.Code != "E_RULE_REPLACEMENT_MISSING" {
		t.Errorf("got %v, want E_RULE_REPLACEMENT_MISSING", err)
	}
}
