package esm

import (
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
