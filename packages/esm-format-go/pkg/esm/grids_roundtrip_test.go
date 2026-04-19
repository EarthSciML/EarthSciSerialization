package esm

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

// TestGridsRoundtrip verifies that the Go binding parses, re-marshals, and
// preserves the §6 top-level `grids` map (gt-5kq3) across the three canonical
// family fixtures: cartesian, unstructured, cubed_sphere.
func TestGridsRoundtrip(t *testing.T) {
	repoRoot, err := filepath.Abs(filepath.Join("..", "..", "..", ".."))
	if err != nil {
		t.Fatalf("resolve repo root: %v", err)
	}

	fixtures := []string{
		"cartesian_uniform.esm",
		"unstructured_mpas.esm",
		"cubed_sphere_c48.esm",
	}

	for _, name := range fixtures {
		name := name
		t.Run(name, func(t *testing.T) {
			path := filepath.Join(repoRoot, "tests", "grids", name)
			data, err := os.ReadFile(path)
			if err != nil {
				t.Fatalf("read fixture: %v", err)
			}

			esmFile, err := LoadString(string(data))
			if err != nil {
				t.Fatalf("initial load: %v", err)
			}
			if len(esmFile.Grids) == 0 {
				t.Fatalf("expected at least one grid after load, got 0")
			}

			out, err := esmFile.ToJSON()
			if err != nil {
				t.Fatalf("marshal back: %v", err)
			}

			// Compare semantically (unmarshal both to map[string]interface{}) to
			// sidestep key-ordering / whitespace differences in the marshaled form.
			var orig, round map[string]interface{}
			if err := json.Unmarshal(data, &orig); err != nil {
				t.Fatalf("unmarshal original: %v", err)
			}
			if err := json.Unmarshal(out, &round); err != nil {
				t.Fatalf("unmarshal round-tripped: %v", err)
			}

			origGrids, ok := orig["grids"].(map[string]interface{})
			if !ok {
				t.Fatalf("fixture %s has no grids block", name)
			}
			roundGrids, ok := round["grids"].(map[string]interface{})
			if !ok {
				t.Fatalf("round-tripped output missing grids block")
			}
			if !reflect.DeepEqual(origGrids, roundGrids) {
				t.Errorf("grids block did not round-trip.\n orig:  %#v\n round: %#v", origGrids, roundGrids)
			}
		})
	}
}

// TestGridsRejectUnknownLoader verifies that a loader-kind generator pointing
// at a data_loaders name that does not exist is rejected by LoadString.
func TestGridsRejectUnknownLoader(t *testing.T) {
	fixture := `{
		"esm": "0.2.0",
		"metadata": {"name": "BadLoaderRef", "authors": ["Tester"]},
		"models": {
			"M": {
				"variables": {"x": {"type": "state", "units": "1", "default": 0.0}},
				"equations": [{"lhs": "D(x)", "rhs": "0"}]
			}
		},
		"grids": {
			"g": {
				"family": "unstructured",
				"dimensions": ["cell"],
				"connectivity": {
					"cellsOnEdge": {
						"shape": ["nEdges", 2],
						"rank": 2,
						"loader": "does_not_exist",
						"field": "cellsOnEdge"
					}
				}
			}
		}
	}`

	_, err := LoadString(fixture)
	if err == nil {
		t.Fatalf("expected error for unknown loader reference, got nil")
	}
	if !strings.Contains(err.Error(), "does_not_exist") {
		t.Errorf("error should mention the bad loader name, got: %v", err)
	}
}

// TestGridsRejectUnknownBuiltin verifies the E_UNKNOWN_BUILTIN path for a
// generator whose builtin name is outside the closed set (§6.4.1).
func TestGridsRejectUnknownBuiltin(t *testing.T) {
	fixture := `{
		"esm": "0.2.0",
		"metadata": {"name": "BadBuiltin", "authors": ["Tester"]},
		"models": {
			"M": {
				"variables": {"x": {"type": "state", "units": "1", "default": 0.0}},
				"equations": [{"lhs": "D(x)", "rhs": "0"}]
			}
		},
		"grids": {
			"g": {
				"family": "cubed_sphere",
				"dimensions": ["panel", "i", "j"],
				"extents": {"panel": {"n": 6}, "i": {"n": "Nc"}, "j": {"n": "Nc"}},
				"panel_connectivity": {
					"neighbors": {
						"shape": [6, 4],
						"rank": 2,
						"generator": {"kind": "builtin", "name": "not_a_real_builtin"}
					}
				},
				"parameters": {"Nc": {"default": 48}}
			}
		}
	}`

	_, err := LoadString(fixture)
	if err == nil {
		t.Fatalf("expected error for unknown builtin, got nil")
	}
	if !strings.Contains(err.Error(), "E_UNKNOWN_BUILTIN") {
		t.Errorf("error should contain E_UNKNOWN_BUILTIN, got: %v", err)
	}
}
