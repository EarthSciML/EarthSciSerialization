package esm

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

// TestStaggeringRulesRoundtrip verifies the Go binding parses the §7.4
// top-level `staggering_rules` map (esm-15f) on the mpas_c_grid_staggering
// fixture and preserves it across a marshal / unmarshal cycle.
func TestStaggeringRulesRoundtrip(t *testing.T) {
	repoRoot, err := filepath.Abs(filepath.Join("..", "..", "..", ".."))
	if err != nil {
		t.Fatalf("resolve repo root: %v", err)
	}

	path := filepath.Join(repoRoot, "tests", "grids", "mpas_c_grid_staggering.esm")
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read fixture: %v", err)
	}

	esmFile, err := LoadString(string(data))
	if err != nil {
		t.Fatalf("initial load: %v", err)
	}
	if len(esmFile.StaggeringRules) != 1 {
		t.Fatalf("expected 1 staggering rule, got %d", len(esmFile.StaggeringRules))
	}
	rule, ok := esmFile.StaggeringRules["mpas_c_grid_staggering"]
	if !ok {
		t.Fatalf("missing mpas_c_grid_staggering rule")
	}
	if rule.Kind != "unstructured_c_grid" {
		t.Errorf("kind: want unstructured_c_grid, got %q", rule.Kind)
	}
	if rule.Grid != "mpas_cvmesh" {
		t.Errorf("grid: want mpas_cvmesh, got %q", rule.Grid)
	}
	if rule.EdgeNormalConvention != "outward_from_first_cell" {
		t.Errorf("edge_normal_convention: want outward_from_first_cell, got %q",
			rule.EdgeNormalConvention)
	}
	if loc := rule.CellQuantityLocations["u"]; loc != "edge_midpoint" {
		t.Errorf("u should live at edge_midpoint, got %q", loc)
	}

	out, err := esmFile.ToJSON()
	if err != nil {
		t.Fatalf("marshal back: %v", err)
	}

	var orig, round map[string]interface{}
	if err := json.Unmarshal(data, &orig); err != nil {
		t.Fatalf("unmarshal original: %v", err)
	}
	if err := json.Unmarshal(out, &round); err != nil {
		t.Fatalf("unmarshal round-tripped: %v", err)
	}

	origRules := orig["staggering_rules"]
	roundRules := round["staggering_rules"]
	if !reflect.DeepEqual(origRules, roundRules) {
		t.Errorf("staggering_rules block did not round-trip.\n orig:  %#v\n round: %#v",
			origRules, roundRules)
	}
}
