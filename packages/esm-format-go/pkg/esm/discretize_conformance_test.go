package esm

import (
	"encoding/json"
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

// TestDiscretizeConformanceFixtures drives the §11 Step-1 end-to-end fixtures
// at tests/conformance/discretize/. For each entry in the manifest we parse
// the input, run Discretize with manifest options, and assert that two calls
// on the same input produce byte-identical canonical JSON (determinism —
// the §11 acceptance bar for this binding; cross-binding golden byte-match
// is tracked by the Julia reference harness since goldens were generated
// there and carry its JSON parser's integer-valued-float coercion).
func TestDiscretizeConformanceFixtures(t *testing.T) {
	dir := discretizeFixturesDir(t)
	manifestPath := filepath.Join(dir, "manifest.json")
	manifestBytes, err := os.ReadFile(manifestPath)
	if err != nil {
		t.Fatalf("read manifest: %v", err)
	}
	var manifest struct {
		Options struct {
			MaxPasses         *int  `json:"max_passes"`
			StrictUnrewritten *bool `json:"strict_unrewritten"`
		} `json:"options"`
		Fixtures []struct {
			ID     string `json:"id"`
			Input  string `json:"input"`
			Golden string `json:"golden"`
		} `json:"fixtures"`
	}
	if err := json.Unmarshal(manifestBytes, &manifest); err != nil {
		t.Fatalf("parse manifest: %v", err)
	}
	if len(manifest.Fixtures) == 0 {
		t.Fatal("manifest has no fixtures")
	}

	opts := DefaultDiscretizeOptions()
	if manifest.Options.MaxPasses != nil {
		opts.MaxPasses = *manifest.Options.MaxPasses
	}
	if manifest.Options.StrictUnrewritten != nil {
		opts.StrictUnrewritten = *manifest.Options.StrictUnrewritten
	}

	for _, f := range manifest.Fixtures {
		f := f
		t.Run(f.ID, func(t *testing.T) {
			raw, err := os.ReadFile(filepath.Join(dir, f.Input))
			if err != nil {
				t.Fatalf("read input: %v", err)
			}
			in1, err := LoadAsMap(raw)
			if err != nil {
				t.Fatalf("LoadAsMap #1: %v", err)
			}
			in2, err := LoadAsMap(raw)
			if err != nil {
				t.Fatalf("LoadAsMap #2: %v", err)
			}
			out1, err := Discretize(in1, opts)
			if err != nil {
				t.Fatalf("Discretize #1: %v", err)
			}
			out2, err := Discretize(in2, opts)
			if err != nil {
				t.Fatalf("Discretize #2: %v", err)
			}
			a, err := CanonicalDocJSON(out1)
			if err != nil {
				t.Fatalf("canonical JSON #1: %v", err)
			}
			b, err := CanonicalDocJSON(out2)
			if err != nil {
				t.Fatalf("canonical JSON #2: %v", err)
			}
			if string(a) != string(b) {
				t.Errorf("non-deterministic output for fixture %s:\n  a: %s\n  b: %s",
					f.ID, a, b)
			}
			// Sanity: output re-parses as a map.
			var reparsed map[string]interface{}
			if err := json.Unmarshal(a, &reparsed); err != nil {
				t.Errorf("output for %s does not re-parse as JSON object: %v", f.ID, err)
			}
		})
	}
}

func discretizeFixturesDir(t *testing.T) string {
	t.Helper()
	_, thisFile, _, _ := runtime.Caller(0)
	pkgDir := filepath.Dir(thisFile)
	repoRoot := filepath.Join(pkgDir, "..", "..", "..", "..")
	return filepath.Join(repoRoot, "tests", "conformance", "discretize")
}
