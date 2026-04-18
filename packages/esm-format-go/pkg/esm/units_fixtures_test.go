package esm

import (
	"fmt"
	"os"
	"path/filepath"
	"testing"
)

// TestUnitsFixturesCrossBinding wires the three canonical units fixtures
// (tests/valid/units_*.esm) into the Go test suite as part of gt-gtf.
// These fixtures are shared across Julia/Python/Rust/TypeScript/Go and
// exist specifically to drive cross-binding agreement on units handling.
//
// Each binding's unit registry covers a different subset of physical
// units; the fixtures intentionally exercise the union. The test asserts:
//   - every fixture loads via the public Load API,
//   - every fixture has at least one model,
//   - ValidateFile runs to completion on every fixture (warnings are
//     logged but not asserted, because per-binding registry coverage
//     differs and is the audit signal these fixtures exist to surface).
func TestUnitsFixturesCrossBinding(t *testing.T) {
	repoRoot, err := filepath.Abs(filepath.Join("..", "..", "..", ".."))
	if err != nil {
		t.Fatalf("resolve repo root: %v", err)
	}
	fixtures := []string{
		"units_conversions.esm",
		"units_dimensional_analysis.esm",
		"units_propagation.esm",
	}
	for _, name := range fixtures {
		t.Run(name, func(t *testing.T) {
			path := filepath.Join(repoRoot, "tests", "valid", name)
			content, err := os.ReadFile(path)
			if err != nil {
				t.Fatalf("read %s: %v", path, err)
			}
			file, err := LoadString(string(content))
			if err != nil {
				t.Fatalf("load %s: %v", name, err)
			}
			if len(file.Models) == 0 {
				t.Fatalf("%s: expected at least one model", name)
			}
			result := ValidateFile(file, string(content))
			t.Logf("%s: %d unit warnings (cross-binding registry coverage signal)",
				name, len(result.UnitWarnings))
			for _, w := range result.UnitWarnings {
				t.Logf("  %s: %s", w.Path, w.Message)
			}
		})
	}
}

// TestReactionRateUnitsMismatchFixtureRejected verifies that the shared
// tests/invalid/units_reaction_rate_mismatch.esm fixture (2nd-order reaction
// A + B -> C whose rate parameter is declared with 1/s units) is rejected
// as a structural error with code "unit_inconsistency". This mirrors the
// Python/TS/Julia/Rust checks so all five bindings agree (gt-zs9o).
func TestReactionRateUnitsMismatchFixtureRejected(t *testing.T) {
	repoRoot, err := filepath.Abs(filepath.Join("..", "..", "..", ".."))
	if err != nil {
		t.Fatalf("resolve repo root: %v", err)
	}
	path := filepath.Join(repoRoot, "tests", "invalid", "units_reaction_rate_mismatch.esm")
	content, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read %s: %v", path, err)
	}
	file, err := LoadString(string(content))
	if err != nil {
		t.Fatalf("load fixture: %v", err)
	}
	result := ValidateFile(file, string(content))
	if result.IsValid {
		t.Fatalf("expected fixture to fail validation, got is_valid=true")
	}
	var found *StructuralError
	for i, e := range result.StructuralErrors {
		if e.Code == ErrorUnitInconsistency {
			found = &result.StructuralErrors[i]
			break
		}
	}
	if found == nil {
		t.Fatalf("expected unit_inconsistency error, got: %+v", result.StructuralErrors)
	}
	// Match the contract in tests/invalid/expected_errors.json.
	if found.Message != "Reaction rate expression has incompatible units for reaction stoichiometry" {
		t.Errorf("unexpected message: %q", found.Message)
	}
	expectDetail := func(key string, want interface{}) {
		t.Helper()
		got, ok := found.Details[key]
		if !ok {
			t.Errorf("details[%q] missing", key)
			return
		}
		if fmt.Sprint(got) != fmt.Sprint(want) {
			t.Errorf("details[%q] = %v, want %v", key, got, want)
		}
	}
	expectDetail("reaction_id", "R1")
	expectDetail("rate_units", "1/s")
	expectDetail("expected_rate_units", "L/(mol*s)")
	expectDetail("reaction_order", 2)
}
