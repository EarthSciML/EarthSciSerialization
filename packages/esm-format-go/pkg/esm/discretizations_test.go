package esm

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

// assertJSONEqual compares two Go values by re-encoding to JSON and decoding
// into generic interface{} form — so json.RawMessage byte differences due to
// whitespace do not cause spurious mismatches.
func assertJSONEqual(t *testing.T, a, b interface{}, name string) {
	t.Helper()
	aj, err := json.Marshal(a)
	if err != nil {
		t.Fatalf("%s: marshal a: %v", name, err)
	}
	bj, err := json.Marshal(b)
	if err != nil {
		t.Fatalf("%s: marshal b: %v", name, err)
	}
	var ax, bx interface{}
	if err := json.Unmarshal(aj, &ax); err != nil {
		t.Fatalf("%s: decode a: %v", name, err)
	}
	if err := json.Unmarshal(bj, &bx); err != nil {
		t.Fatalf("%s: decode b: %v", name, err)
	}
	if !reflect.DeepEqual(ax, bx) {
		t.Errorf("%s: value mismatch after round-trip\n got: %s\nwant: %s", name, string(bj), string(aj))
	}
}

// Round-trip each §7 discretization fixture and verify the top-level
// Discretizations map and its stencil body survive unchanged.
func TestDiscretizationsRoundTrip(t *testing.T) {
	repoRoot := filepath.Join("..", "..", "..", "..")
	fixtures := []struct {
		id           string
		path         string
		schemeName   string
		gridFamily   string
		stencilLen   int
	}{
		{"centered_2nd_uniform", "tests/discretizations/centered_2nd_uniform.esm", "centered_2nd_uniform", "cartesian", 2},
		{"upwind_1st_advection", "tests/discretizations/upwind_1st_advection.esm", "upwind_1st", "cartesian", 3},
		{"periodic_bc", "tests/discretizations/periodic_bc.esm", "periodic_bc_x", "cartesian", 1},
		{"mpas_cell_div", "tests/discretizations/mpas_cell_div.esm", "mpas_cell_div", "unstructured", 1},
		// The cross-metric fixture's *named* entry is a composite (no stencil);
		// stencilLen 0 signals "composite — inspect Terms instead".
		{"cross_metric_cartesian_composite", "tests/discretizations/cross_metric_cartesian.esm", "laplacian_full_covariant_toy", "cartesian", 0},
		{"cross_metric_cartesian_dxi2", "tests/discretizations/cross_metric_cartesian.esm", "d2_dxi2_uniform", "cartesian", 3},
		{"cross_metric_cartesian_deta2", "tests/discretizations/cross_metric_cartesian.esm", "d2_deta2_uniform", "cartesian", 3},
	}
	for _, f := range fixtures {
		t.Run(f.id, func(t *testing.T) {
			raw, err := os.ReadFile(filepath.Join(repoRoot, f.path))
			if err != nil {
				t.Fatalf("read: %v", err)
			}
			var parsed EsmFile
			if err := json.Unmarshal(raw, &parsed); err != nil {
				t.Fatalf("unmarshal: %v", err)
			}
			scheme, ok := parsed.Discretizations[f.schemeName]
			if !ok {
				t.Fatalf("scheme %q not found", f.schemeName)
			}
			if scheme.GridFamily != f.gridFamily {
				t.Errorf("grid_family = %q, want %q", scheme.GridFamily, f.gridFamily)
			}
			if len(scheme.Stencil) != f.stencilLen {
				t.Errorf("stencil len = %d, want %d", len(scheme.Stencil), f.stencilLen)
			}
			// For composite entries (stencilLen == 0 and no Stencil) we expect
			// a nonempty Terms array and IsCrossMetric()==true (RFC §7.4).
			if f.stencilLen == 0 && len(scheme.Stencil) == 0 {
				if !scheme.IsCrossMetric() {
					t.Errorf("scheme %q: expected composite (Terms nonempty), got Terms=%v", f.schemeName, scheme.Terms)
				}
				if len(scheme.Axes) == 0 {
					t.Errorf("scheme %q: composite must declare axes", f.schemeName)
				}
			}

			out, err := json.Marshal(&parsed)
			if err != nil {
				t.Fatalf("marshal: %v", err)
			}
			var reparsed EsmFile
			if err := json.Unmarshal(out, &reparsed); err != nil {
				t.Fatalf("unmarshal round-trip: %v", err)
			}
			// Compare the full discretizations section as decoded JSON values
			// (raw-byte equality is too strict — whitespace differs).
			assertJSONEqual(t, parsed.Discretizations, reparsed.Discretizations, "discretizations")

			// Second hop must also be a fixed point.
			out2, err := json.Marshal(&reparsed)
			if err != nil {
				t.Fatalf("second marshal: %v", err)
			}
			var reparsed2 EsmFile
			if err := json.Unmarshal(out2, &reparsed2); err != nil {
				t.Fatalf("second unmarshal: %v", err)
			}
			assertJSONEqual(t, reparsed.Discretizations, reparsed2.Discretizations, "discretizations (second hop)")
		})
	}
}
