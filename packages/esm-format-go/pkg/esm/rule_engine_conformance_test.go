package esm

import (
	"encoding/json"
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

// TestRuleEngineConformanceFixtures consumes
// tests/conformance/discretization/infra/rule_engine/*.json. Each
// fixture's expect.canonical_json is the byte-exact form that every
// binding's CanonicalJSON(Rewrite(input, rules)) must produce; error
// fixtures assert that the engine aborts with a specific stable code.
// Shared with the Julia and Rust conformance harnesses per RFC §13.1
// Step 1.
func TestRuleEngineConformanceFixtures(t *testing.T) {
	dir := ruleEngineFixturesDir(t)
	manifestBytes, err := os.ReadFile(filepath.Join(dir, "manifest.json"))
	if err != nil {
		t.Fatalf("read manifest: %v", err)
	}
	var manifest struct {
		Fixtures []struct {
			ID   string `json:"id"`
			Path string `json:"path"`
		} `json:"fixtures"`
	}
	if err := json.Unmarshal(manifestBytes, &manifest); err != nil {
		t.Fatalf("parse manifest: %v", err)
	}
	if len(manifest.Fixtures) == 0 {
		t.Fatal("manifest has no fixtures")
	}
	for _, f := range manifest.Fixtures {
		f := f
		t.Run(f.ID, func(t *testing.T) {
			raw, err := os.ReadFile(filepath.Join(dir, f.Path))
			if err != nil {
				t.Fatalf("read fixture: %v", err)
			}
			var fixture struct {
				ID                     string          `json:"id"`
				Rules                  json.RawMessage `json:"rules"`
				Input                  json.RawMessage `json:"input"`
				MaxPasses              *int            `json:"max_passes,omitempty"`
				Context                json.RawMessage `json:"context,omitempty"`
				RequiresPerPointScope  bool            `json:"requires_per_point_scope,omitempty"`
				Expect                 struct {
					Kind          string `json:"kind"`
					CanonicalJSON string `json:"canonical_json,omitempty"`
					Code          string `json:"code,omitempty"`
				} `json:"expect"`
			}
			if err := json.Unmarshal(raw, &fixture); err != nil {
				t.Fatalf("parse fixture: %v", err)
			}

			rules, err := ParseRules(fixture.Rules)
			if err != nil {
				t.Fatalf("parse rules: %v", err)
			}
			// RFC §5.2.7 fixtures require a per-query-point scope evaluator.
			// The Go binding is parse-only for this capability (see manifest
			// note); parse_rules above asserted the fixture loads — skip the
			// evaluation assertion.
			if fixture.RequiresPerPointScope {
				t.Skipf("fixture %s requires RFC §5.2.7 per-query-point scope evaluator "+
					"(Go binding is parse-only for this capability)", f.ID)
			}
			input, err := ParseExpr(fixture.Input)
			if err != nil {
				t.Fatalf("parse input: %v", err)
			}
			maxPasses := DefaultMaxPasses
			if fixture.MaxPasses != nil {
				maxPasses = *fixture.MaxPasses
			}
			ctx, err := buildFixtureContext(fixture.Context)
			if err != nil {
				t.Fatalf("build ctx: %v", err)
			}

			switch fixture.Expect.Kind {
			case "output":
				out, err := Rewrite(input, rules, ctx, maxPasses)
				if err != nil {
					t.Fatalf("fixture %s: %v", f.ID, err)
				}
				got, err := CanonicalJSON(out)
				if err != nil {
					t.Fatalf("canonicalize: %v", err)
				}
				if string(got) != fixture.Expect.CanonicalJSON {
					t.Errorf("\n   id: %s\n  got: %s\n want: %s",
						f.ID, got, fixture.Expect.CanonicalJSON)
				}
			case "error":
				_, err := Rewrite(input, rules, ctx, maxPasses)
				if err == nil {
					t.Fatalf("fixture %s: expected error %s, got nil",
						f.ID, fixture.Expect.Code)
				}
				re, ok := err.(*RuleEngineError)
				if !ok {
					t.Fatalf("fixture %s: expected *RuleEngineError, got %T: %v",
						f.ID, err, err)
				}
				if re.Code != fixture.Expect.Code {
					t.Errorf("fixture %s: got code %s, want %s",
						f.ID, re.Code, fixture.Expect.Code)
				}
			default:
				t.Fatalf("fixture %s: unknown expect.kind %q",
					f.ID, fixture.Expect.Kind)
			}
		})
	}
}

func buildFixtureContext(raw json.RawMessage) (RuleContext, error) {
	ctx := NewRuleContext()
	if len(raw) == 0 || string(raw) == "null" {
		return ctx, nil
	}
	var obj struct {
		Grids     map[string]map[string]interface{} `json:"grids"`
		Variables map[string]map[string]interface{} `json:"variables"`
	}
	if err := json.Unmarshal(raw, &obj); err != nil {
		return ctx, err
	}
	for k, v := range obj.Grids {
		meta := GridMeta{}
		if arr, ok := v["spatial_dims"].([]interface{}); ok {
			meta.SpatialDims = stringSlice(arr)
		}
		if arr, ok := v["periodic_dims"].([]interface{}); ok {
			meta.PeriodicDims = stringSlice(arr)
		}
		if arr, ok := v["nonuniform_dims"].([]interface{}); ok {
			meta.NonuniformDims = stringSlice(arr)
		}
		ctx.Grids[k] = meta
	}
	for k, v := range obj.Variables {
		meta := VariableMeta{}
		if g, ok := v["grid"].(string); ok {
			meta.Grid = g
		}
		if l, ok := v["location"].(string); ok {
			meta.Location = l
		}
		if arr, ok := v["shape"].([]interface{}); ok {
			meta.Shape = stringSlice(arr)
			meta.HasShape = true
		}
		ctx.Variables[k] = meta
	}
	return ctx, nil
}

func stringSlice(arr []interface{}) []string {
	out := make([]string, 0, len(arr))
	for _, e := range arr {
		if s, ok := e.(string); ok {
			out = append(out, s)
		}
	}
	return out
}

func ruleEngineFixturesDir(t *testing.T) string {
	t.Helper()
	_, thisFile, _, _ := runtime.Caller(0)
	pkgDir := filepath.Dir(thisFile)
	repoRoot := filepath.Join(pkgDir, "..", "..", "..", "..")
	return filepath.Join(repoRoot, "tests", "conformance",
		"discretization", "infra", "rule_engine")
}
