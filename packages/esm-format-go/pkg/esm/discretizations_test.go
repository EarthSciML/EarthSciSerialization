package esm

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

func intPtr(n int) *int { return &n }

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
		wantOrder    *int
	}{
		{"centered_2nd_uniform", "tests/discretizations/centered_2nd_uniform.esm", "centered_2nd_uniform", "cartesian", 2, nil},
		{"upwind_1st_advection", "tests/discretizations/upwind_1st_advection.esm", "upwind_1st", "cartesian", 3, nil},
		{"periodic_bc", "tests/discretizations/periodic_bc.esm", "periodic_bc_x", "cartesian", 1, nil},
		{"mpas_cell_div", "tests/discretizations/mpas_cell_div.esm", "mpas_cell_div", "unstructured", 1, nil},
		{"centered_arbitrary_order_uniform", "tests/discretizations/centered_arbitrary_order_uniform.esm", "centered_arbitrary_order_uniform", "cartesian", 4, intPtr(4)},
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
			switch {
			case f.wantOrder == nil && scheme.Order != nil:
				t.Errorf("order = %d, want absent", *scheme.Order)
			case f.wantOrder != nil && scheme.Order == nil:
				t.Errorf("order absent, want %d", *f.wantOrder)
			case f.wantOrder != nil && scheme.Order != nil && *scheme.Order != *f.wantOrder:
				t.Errorf("order = %d, want %d", *scheme.Order, *f.wantOrder)
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
