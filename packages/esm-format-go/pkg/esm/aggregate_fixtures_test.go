package esm

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

// TestAggregateValidFixtures asserts every tests/valid/aggregate/*.esm fixture
// parses and schema-validates cleanly through the Go loader. These exercise the
// additive aggregate/semiring schema deltas (op:"aggregate", the closed
// `semiring` enum, `ranges` { "from": <index-set> } references, and the
// model-level `index_sets` registry). Validation/round-trip only — the Go
// binding does no numeric evaluation. Cross-binding conformance bead
// ess-my4.1.5; RFC semiring-faq-unified-ir §5.1 / §5.2.
func TestAggregateValidFixtures(t *testing.T) {
	repoRoot, err := filepath.Abs(filepath.Join("..", "..", "..", ".."))
	if err != nil {
		t.Fatalf("resolve repo root: %v", err)
	}
	pattern := filepath.Join(repoRoot, "tests", "valid", "aggregate", "*.esm")
	files, err := filepath.Glob(pattern)
	if err != nil {
		t.Fatalf("glob %s: %v", pattern, err)
	}
	if len(files) == 0 {
		t.Fatalf("no .esm fixtures matched %s", pattern)
	}
	for _, path := range files {
		name := filepath.Base(path)
		t.Run(name, func(t *testing.T) {
			if _, err := Load(path); err != nil {
				t.Fatalf("expected %s to validate, got error: %v", name, err)
			}
		})
	}
}

// resolverOnlyInvalidFixtures reads tests/invalid/expected_errors.json and
// returns the set of fixture basenames flagged `resolver_only: true`. Such
// fixtures are SCHEMA-VALID but rejected only by an evaluator/resolver (e.g. an
// `aggregate` `{from}` range naming an index set absent from the registry, RFC
// semiring-faq-unified-ir §5.2). The schema-only Go binding does not run that
// resolver, so it must ACCEPT them — the invalid-fixture loop asserts schema
// acceptance for these rather than rejection. See bead ess-my4.1.6.
func resolverOnlyInvalidFixtures(t *testing.T, repoRoot string) map[string]bool {
	t.Helper()
	path := filepath.Join(repoRoot, "tests", "invalid", "expected_errors.json")
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read %s: %v", path, err)
	}
	var entries map[string]struct {
		ResolverOnly bool `json:"resolver_only"`
	}
	if err := json.Unmarshal(data, &entries); err != nil {
		t.Fatalf("parse %s: %v", path, err)
	}
	out := make(map[string]bool)
	for name, e := range entries {
		if e.ResolverOnly {
			out[name] = true
		}
	}
	return out
}

// TestAggregateInvalidFixtures asserts every tests/invalid/aggregate/*.esm
// fixture is handled correctly. Pure schema violations (unregistered semiring,
// ragged index set missing offsets/values, discrete variable missing shape,
// join not an array, join `on` pair wrong arity, refresh on a non-discrete
// variable) are REJECTED — Load returns a non-nil error at schema-validation
// time. Fixtures flagged `resolver_only` in expected_errors.json are
// SCHEMA-VALID and rejected only by an evaluating binding's resolver; the
// schema-only Go binding must ACCEPT those (Load returns nil).
func TestAggregateInvalidFixtures(t *testing.T) {
	repoRoot, err := filepath.Abs(filepath.Join("..", "..", "..", ".."))
	if err != nil {
		t.Fatalf("resolve repo root: %v", err)
	}
	resolverOnly := resolverOnlyInvalidFixtures(t, repoRoot)
	pattern := filepath.Join(repoRoot, "tests", "invalid", "aggregate", "*.esm")
	files, err := filepath.Glob(pattern)
	if err != nil {
		t.Fatalf("glob %s: %v", pattern, err)
	}
	if len(files) == 0 {
		t.Fatalf("no .esm fixtures matched %s", pattern)
	}
	for _, path := range files {
		name := filepath.Base(path)
		t.Run(name, func(t *testing.T) {
			if resolverOnly[name] {
				// Schema-valid; rejected only by a resolver the schema-only Go
				// binding does not run. Load must ACCEPT it.
				if _, err := Load(path); err != nil {
					t.Fatalf("resolver-only fixture %s must pass schema validation, got error: %v", name, err)
				}
				return
			}
			if _, err := Load(path); err == nil {
				t.Fatalf("expected %s to be rejected, but it validated", name)
			}
		})
	}
}
