package esm

import (
	"encoding/json"
	"strings"
	"testing"
)

// ============================================================================
// Fixtures (mirror packages/EarthSciSerialization.jl/test/discretize_test.jl)
// ============================================================================

func scalarOdeESM() map[string]interface{} {
	return map[string]interface{}{
		"esm": "0.2.0",
		"metadata": map[string]interface{}{
			"name":        "scalar_ode",
			"description": "dx/dt = -k * x",
		},
		"models": map[string]interface{}{
			"M": map[string]interface{}{
				"variables": map[string]interface{}{
					"x": map[string]interface{}{"type": "state", "default": 1.0, "units": "1"},
					"k": map[string]interface{}{"type": "parameter", "default": 0.5, "units": "1/s"},
				},
				"equations": []interface{}{
					map[string]interface{}{
						"lhs": map[string]interface{}{"op": "D", "args": []interface{}{"x"}, "wrt": "t"},
						"rhs": map[string]interface{}{"op": "*", "args": []interface{}{
							map[string]interface{}{"op": "-", "args": []interface{}{"k"}},
							"x",
						}},
					},
				},
			},
		},
	}
}

func heat1dESM(withRule bool) map[string]interface{} {
	esm := map[string]interface{}{
		"esm": "0.2.0",
		"metadata": map[string]interface{}{
			"name": "heat_1d",
		},
		"grids": map[string]interface{}{
			"gx": map[string]interface{}{
				"family": "cartesian",
				"dimensions": []interface{}{
					map[string]interface{}{
						"name": "i", "size": int64(8), "periodic": true, "spacing": "uniform",
					},
				},
			},
		},
		"models": map[string]interface{}{
			"M": map[string]interface{}{
				"grid": "gx",
				"variables": map[string]interface{}{
					"u": map[string]interface{}{
						"type": "state", "default": 0.0, "units": "1",
						"shape": []interface{}{"i"}, "location": "cell_center",
					},
				},
				"equations": []interface{}{
					map[string]interface{}{
						"lhs": map[string]interface{}{"op": "D", "args": []interface{}{"u"}, "wrt": "t"},
						"rhs": map[string]interface{}{"op": "grad", "args": []interface{}{"u"}, "dim": "i"},
					},
				},
			},
		},
	}
	if withRule {
		esm["rules"] = []interface{}{
			map[string]interface{}{
				"name":    "centered_grad",
				"pattern": map[string]interface{}{"op": "grad", "args": []interface{}{"$u"}, "dim": "$x"},
				"replacement": map[string]interface{}{
					"op": "+",
					"args": []interface{}{
						map[string]interface{}{
							"op": "-", "args": []interface{}{
								map[string]interface{}{
									"op": "index", "args": []interface{}{
										"$u",
										map[string]interface{}{"op": "-", "args": []interface{}{"$x", int64(1)}},
									},
								},
							},
						},
						map[string]interface{}{
							"op": "index", "args": []interface{}{
								"$u",
								map[string]interface{}{"op": "+", "args": []interface{}{"$x", int64(1)}},
							},
						},
					},
				},
			},
		}
	}
	return esm
}

// ============================================================================
// Acceptance tests
// ============================================================================

func TestDiscretizeScalarODEEndToEnd(t *testing.T) {
	esm := scalarOdeESM()
	out, err := Discretize(esm, DefaultDiscretizeOptions())
	if err != nil {
		t.Fatalf("discretize: %v", err)
	}
	meta, ok := out["metadata"].(map[string]interface{})
	if !ok {
		t.Fatalf("missing metadata map")
	}
	df, ok := meta["discretized_from"].(map[string]interface{})
	if !ok || df["name"] != "scalar_ode" {
		t.Errorf("discretized_from = %v, want {name: scalar_ode}", df)
	}
	tags, ok := meta["tags"].([]interface{})
	if !ok {
		t.Fatalf("missing tags")
	}
	found := false
	for _, v := range tags {
		if s, _ := v.(string); s == "discretized" {
			found = true
		}
	}
	if !found {
		t.Errorf("tags %v missing 'discretized'", tags)
	}

	// Input must not be mutated.
	if _, present := (esm["metadata"].(map[string]interface{}))["discretized_from"]; present {
		t.Error("input was mutated (discretized_from leaked into input)")
	}
}

func TestDiscretizeHeat1DEndToEnd(t *testing.T) {
	esm := heat1dESM(true)
	out, err := Discretize(esm, DefaultDiscretizeOptions())
	if err != nil {
		t.Fatalf("discretize: %v", err)
	}
	rhs := nestedRHS(t, out)
	js, _ := json.Marshal(rhs)
	if strings.Contains(string(js), `"grad"`) {
		t.Errorf("grad op still present in RHS: %s", js)
	}
	if !strings.Contains(string(js), `"index"`) {
		t.Errorf("index op missing from rewritten RHS: %s", js)
	}
}

func TestDiscretizeDeterminism(t *testing.T) {
	esm := heat1dESM(true)
	a, err := Discretize(esm, DefaultDiscretizeOptions())
	if err != nil {
		t.Fatal(err)
	}
	b, err := Discretize(esm, DefaultDiscretizeOptions())
	if err != nil {
		t.Fatal(err)
	}
	aJSON, err := CanonicalDocJSON(a)
	if err != nil {
		t.Fatal(err)
	}
	bJSON, err := CanonicalDocJSON(b)
	if err != nil {
		t.Fatal(err)
	}
	if string(aJSON) != string(bJSON) {
		t.Errorf("non-deterministic output:\n  a: %s\n  b: %s", aJSON, bJSON)
	}
}

func TestDiscretizeOutputReparses(t *testing.T) {
	out, err := Discretize(scalarOdeESM(), DefaultDiscretizeOptions())
	if err != nil {
		t.Fatal(err)
	}
	rhs := nestedRHS(t, out)
	if _, err := parseExprForRewrite(rhs); err != nil {
		t.Errorf("rewritten RHS does not re-parse: %v", err)
	}
}

func TestDiscretizeUnrewrittenPDEOpErrors(t *testing.T) {
	_, err := Discretize(heat1dESM(false), DefaultDiscretizeOptions())
	re, ok := err.(*RuleEngineError)
	if !ok {
		t.Fatalf("got %T %v, want *RuleEngineError", err, err)
	}
	if re.Code != "E_UNREWRITTEN_PDE_OP" {
		t.Errorf("code %q, want E_UNREWRITTEN_PDE_OP", re.Code)
	}
}

func TestDiscretizeStrictFalseStampsPassthrough(t *testing.T) {
	opts := DefaultDiscretizeOptions()
	opts.StrictUnrewritten = false
	out, err := Discretize(heat1dESM(false), opts)
	if err != nil {
		t.Fatalf("discretize: %v", err)
	}
	eqn := firstEquation(t, out)
	if eqn["passthrough"] != true {
		t.Errorf("passthrough = %v, want true", eqn["passthrough"])
	}
	js, _ := json.Marshal(eqn["rhs"])
	if !strings.Contains(string(js), `"grad"`) {
		t.Errorf("grad op should be retained verbatim when passthrough; got %s", js)
	}
}

func TestDiscretizeInputPassthroughSkipsCheck(t *testing.T) {
	esm := heat1dESM(false)
	eqns := esm["models"].(map[string]interface{})["M"].(map[string]interface{})["equations"].([]interface{})
	eqns[0].(map[string]interface{})["passthrough"] = true
	out, err := Discretize(esm, DefaultDiscretizeOptions())
	if err != nil {
		t.Fatalf("discretize: %v", err)
	}
	eqn := firstEquation(t, out)
	if eqn["passthrough"] != true {
		t.Errorf("passthrough should remain true, got %v", eqn["passthrough"])
	}
}

func TestDiscretizeBCValueCanonicalization(t *testing.T) {
	esm := map[string]interface{}{
		"esm": "0.2.0",
		"metadata": map[string]interface{}{
			"name": "bc_plain",
		},
		"models": map[string]interface{}{
			"M": map[string]interface{}{
				"variables": map[string]interface{}{
					"u": map[string]interface{}{"type": "state", "default": 0.0, "units": "1"},
				},
				"equations": []interface{}{
					map[string]interface{}{
						"lhs": map[string]interface{}{"op": "D", "args": []interface{}{"u"}, "wrt": "t"},
						"rhs": 0.0,
					},
				},
				"boundary_conditions": map[string]interface{}{
					"u_dirichlet_xmin": map[string]interface{}{
						"variable": "u", "side": "xmin", "kind": "dirichlet",
						"value": map[string]interface{}{
							"op": "+", "args": []interface{}{int64(1), int64(0)},
						},
					},
				},
			},
		},
	}
	out, err := Discretize(esm, DefaultDiscretizeOptions())
	if err != nil {
		t.Fatalf("discretize: %v", err)
	}
	bcs := out["models"].(map[string]interface{})["M"].(map[string]interface{})["boundary_conditions"].(map[string]interface{})
	bc := bcs["u_dirichlet_xmin"].(map[string]interface{})
	val := bc["value"]
	if i, ok := val.(int64); !ok || i != 1 {
		t.Errorf("bc value = %v (%T), want int64(1)", val, val)
	}
}

func TestDiscretizeMaxPassesNotConverged(t *testing.T) {
	esm := map[string]interface{}{
		"esm":      "0.2.0",
		"metadata": map[string]interface{}{"name": "loop"},
		"rules": []interface{}{
			map[string]interface{}{
				"name":    "never",
				"pattern": "$a",
				"replacement": map[string]interface{}{
					"op": "+", "args": []interface{}{"$a", int64(1)},
				},
			},
		},
		"models": map[string]interface{}{
			"M": map[string]interface{}{
				"variables": map[string]interface{}{
					"y": map[string]interface{}{"type": "state", "default": 0.0, "units": "1"},
				},
				"equations": []interface{}{
					map[string]interface{}{
						"lhs": map[string]interface{}{"op": "D", "args": []interface{}{"y"}, "wrt": "t"},
						"rhs": "y",
					},
				},
			},
		},
	}
	opts := DefaultDiscretizeOptions()
	opts.MaxPasses = 3
	_, err := Discretize(esm, opts)
	re, ok := err.(*RuleEngineError)
	if !ok || re.Code != "E_RULES_NOT_CONVERGED" {
		t.Errorf("got %v, want E_RULES_NOT_CONVERGED", err)
	}
}

// ============================================================================
// Helpers
// ============================================================================

func nestedRHS(t *testing.T, out map[string]interface{}) interface{} {
	t.Helper()
	return firstEquation(t, out)["rhs"]
}

func firstEquation(t *testing.T, out map[string]interface{}) map[string]interface{} {
	t.Helper()
	m := out["models"].(map[string]interface{})
	mod := m["M"].(map[string]interface{})
	eqns := mod["equations"].([]interface{})
	return eqns[0].(map[string]interface{})
}
