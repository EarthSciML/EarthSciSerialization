// Tests for ApplyStencilGhosted1D (esm-vs5).
//
// Mirrors the Julia reference test suite in
// packages/EarthSciSerialization.jl/test/mms_evaluator_test.jl
// (apply_stencil_ghosted_1d testset).
package esm

import (
	"errors"
	"math"
	"testing"
)

// centeredFD2 builds the JSON-shaped centered 2nd-order finite-difference
// stencil at offsets ±1: coefficients ∓1/(2 dx) at offsets ±1.
func centeredFD2() []interface{} {
	return []interface{}{
		map[string]interface{}{
			"selector": map[string]interface{}{
				"kind": "cartesian", "axis": "x", "offset": -1,
			},
			"coeff": map[string]interface{}{
				"op": "/",
				"args": []interface{}{
					-1,
					map[string]interface{}{
						"op":   "*",
						"args": []interface{}{2, "dx"},
					},
				},
			},
		},
		map[string]interface{}{
			"selector": map[string]interface{}{
				"kind": "cartesian", "axis": "x", "offset": 1,
			},
			"coeff": map[string]interface{}{
				"op": "/",
				"args": []interface{}{
					1,
					map[string]interface{}{
						"op":   "*",
						"args": []interface{}{2, "dx"},
					},
				},
			},
		},
	}
}

// applyPeriodicReference is the wrap-around 1D centered FD reference used to
// pin the periodic ghost-fill output bit-equal.
func applyPeriodicReference(u []float64, dx float64) []float64 {
	n := len(u)
	out := make([]float64, n)
	for i := 0; i < n; i++ {
		left := u[(i-1+n)%n]
		right := u[(i+1)%n]
		out[i] = (right - left) / (2 * dx)
	}
	return out
}

func TestGhostedPeriodicMatchesPeriodicReference(t *testing.T) {
	n := 32
	dx := 1.0 / float64(n)
	u := make([]float64, n)
	for i := 0; i < n; i++ {
		u[i] = math.Sin(2 * math.Pi * (float64(i) + 0.5) * dx)
	}
	bindings := map[string]float64{"dx": dx}
	ref := applyPeriodicReference(u, dx)
	for _, Ng := range []int{1, 2, 5} {
		got, err := ApplyStencilGhosted1D(centeredFD2(), u, bindings, GhostFillOpts{
			GhostWidth:     Ng,
			BoundaryPolicy: "periodic",
		})
		if err != nil {
			t.Fatalf("Ng=%d: %v", Ng, err)
		}
		if len(got) != n {
			t.Fatalf("Ng=%d: len(got)=%d want %d", Ng, len(got), n)
		}
		for i := range got {
			if got[i] != ref[i] {
				t.Errorf("Ng=%d i=%d: got %v want %v (must be bit-equal)", Ng, i, got[i], ref[i])
			}
		}
	}
}

func TestGhostedReflectingZeroFluxOnSymmetricProfile(t *testing.T) {
	n := 16
	dx := 1.0 / float64(n)
	u := make([]float64, n)
	for i := 0; i < n; i++ {
		u[i] = math.Cos(math.Pi * (float64(i) + 0.5) * dx)
	}
	bindings := map[string]float64{"dx": dx}
	got, err := ApplyStencilGhosted1D(centeredFD2(), u, bindings, GhostFillOpts{
		GhostWidth:     1,
		BoundaryPolicy: "reflecting",
	})
	if err != nil {
		t.Fatal(err)
	}
	// First interior cell: ghost reads u[0] (mirror), so derivative is
	// (u[1]-u[0])/(2 dx) — one-sided forward FD shape.
	wantLeft := (u[1] - u[0]) / (2 * dx)
	if math.Abs(got[0]-wantLeft) > 1e-12 {
		t.Errorf("got[0]=%v want %v", got[0], wantLeft)
	}
	wantRight := (u[n-1] - u[n-2]) / (2 * dx)
	if math.Abs(got[n-1]-wantRight) > 1e-12 {
		t.Errorf("got[n-1]=%v want %v", got[n-1], wantRight)
	}
	// Interior compares acceptably against -π sin(πx).
	for i := 2; i < n-2; i++ {
		ref := -math.Pi * math.Sin(math.Pi*(float64(i)+0.5)*dx)
		if math.Abs(got[i]-ref) > 0.05 {
			t.Errorf("i=%d: got %v ref %v (>0.05)", i, got[i], ref)
		}
	}
}

func TestGhostedNeumannZeroAliasMatchesReflecting(t *testing.T) {
	n := 8
	dx := 1.0 / float64(n)
	u := make([]float64, n)
	for i := 0; i < n; i++ {
		u[i] = float64(i + 1)
	}
	bindings := map[string]float64{"dx": dx}
	viaReflect, err := ApplyStencilGhosted1D(centeredFD2(), u, bindings, GhostFillOpts{
		GhostWidth: 1, BoundaryPolicy: "reflecting",
	})
	if err != nil {
		t.Fatal(err)
	}
	viaNeumann, err := ApplyStencilGhosted1D(centeredFD2(), u, bindings, GhostFillOpts{
		GhostWidth: 1, BoundaryPolicy: "neumann_zero",
	})
	if err != nil {
		t.Fatal(err)
	}
	for i := range viaReflect {
		if viaReflect[i] != viaNeumann[i] {
			t.Errorf("i=%d: reflecting=%v neumann_zero=%v (alias must be bit-equal)",
				i, viaReflect[i], viaNeumann[i])
		}
	}
}

func TestGhostedOneSidedLinearExactOnLinearProfile(t *testing.T) {
	n := 12
	dx := 0.1
	u := make([]float64, n)
	for i := 0; i < n; i++ {
		u[i] = 2.0 + 3.0*float64(i+1)
	}
	bindings := map[string]float64{"dx": dx}
	got, err := ApplyStencilGhosted1D(centeredFD2(), u, bindings, GhostFillOpts{
		GhostWidth:     1,
		BoundaryPolicy: "one_sided_extrapolation",
	})
	if err != nil {
		t.Fatal(err)
	}
	want := 3.0 / dx
	for i, v := range got {
		if math.Abs(v-want) > 1e-10 {
			t.Errorf("i=%d: got %v want %v", i, v, want)
		}
	}
}

func TestGhostedOneSidedDegree2ExactOnQuadraticProfile(t *testing.T) {
	n := 10
	dx := 0.5
	u := make([]float64, n)
	for i := 0; i < n; i++ {
		u[i] = float64(i+1) * float64(i+1)
	}
	bindings := map[string]float64{"dx": dx}
	got, err := ApplyStencilGhosted1D(centeredFD2(), u, bindings, GhostFillOpts{
		GhostWidth: 1,
		BoundaryPolicy: BoundaryPolicySpec{
			Kind: "one_sided_extrapolation", Degree: 2, HasDegree: true,
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	for i := 0; i < n; i++ {
		ref := 2.0 * float64(i+1) / dx
		if math.Abs(got[i]-ref) > 1e-10 {
			t.Errorf("i=%d: got %v ref %v", i, got[i], ref)
		}
	}
}

func TestGhostedOneSidedDegree3ExactOnCubicProfile(t *testing.T) {
	n := 12
	dx := 0.25
	u := make([]float64, n)
	for i := 0; i < n; i++ {
		f := float64(i + 1)
		u[i] = f * f * f
	}
	bindings := map[string]float64{"dx": dx}
	got, err := ApplyStencilGhosted1D(centeredFD2(), u, bindings, GhostFillOpts{
		GhostWidth: 1,
		BoundaryPolicy: BoundaryPolicySpec{
			Kind: "one_sided_extrapolation", Degree: 3, HasDegree: true,
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	for i := 0; i < n; i++ {
		f := float64(i + 1)
		ref := (6.0*f*f + 2.0) / (2.0 * dx)
		if math.Abs(got[i]-ref) > 1e-10 {
			t.Errorf("i=%d: got %v ref %v", i, got[i], ref)
		}
	}
}

func TestGhostedExtrapolateAliasDefaultsLinear(t *testing.T) {
	n := 8
	dx := 0.1
	u := make([]float64, n)
	for i := 0; i < n; i++ {
		u[i] = 1.5*float64(i+1) + 0.5
	}
	bindings := map[string]float64{"dx": dx}
	got, err := ApplyStencilGhosted1D(centeredFD2(), u, bindings, GhostFillOpts{
		GhostWidth:     1,
		BoundaryPolicy: "extrapolate",
	})
	if err != nil {
		t.Fatal(err)
	}
	want := 1.5 / dx
	for i, v := range got {
		if math.Abs(v-want) > 1e-10 {
			t.Errorf("i=%d: got %v want %v", i, v, want)
		}
	}
}

func TestGhostedPrescribedSuppliesGhostValues(t *testing.T) {
	n := 8
	dx := 0.1
	u := make([]float64, n)
	for i := 0; i < n; i++ {
		u[i] = float64(i + 1)
	}
	bindings := map[string]float64{"dx": dx}
	type call struct {
		side string
		k    int
	}
	var calls []call
	prescribe := func(side string, k int) float64 {
		calls = append(calls, call{side, k})
		// Linear extension of u[i] = i: cell index 1-k on the left,
		// n+k on the right. Bit-equal Julia (which uses 1..n indexing).
		if side == "left" {
			return float64(1 - k)
		}
		return float64(n + k)
	}
	got, err := ApplyStencilGhosted1D(centeredFD2(), u, bindings, GhostFillOpts{
		GhostWidth:     1,
		BoundaryPolicy: "prescribed",
		Prescribe:      prescribe,
	})
	if err != nil {
		t.Fatal(err)
	}
	want := 1.0 / dx
	for i, v := range got {
		if math.Abs(v-want) > 1e-10 {
			t.Errorf("i=%d: got %v want %v", i, v, want)
		}
	}
	hasLeft, hasRight := false, false
	for _, c := range calls {
		if c.side == "left" && c.k == 1 {
			hasLeft = true
		}
		if c.side == "right" && c.k == 1 {
			hasRight = true
		}
	}
	if !hasLeft {
		t.Errorf("expected prescribe(left, 1) call; got %+v", calls)
	}
	if !hasRight {
		t.Errorf("expected prescribe(right, 1) call; got %+v", calls)
	}
}

func TestGhostedGhostedAliasRequiresPrescribe(t *testing.T) {
	n := 8
	dx := 0.1
	u := make([]float64, n)
	for i := range u {
		u[i] = float64(i + 1)
	}
	bindings := map[string]float64{"dx": dx}
	_, err := ApplyStencilGhosted1D(centeredFD2(), u, bindings, GhostFillOpts{
		GhostWidth:     1,
		BoundaryPolicy: "ghosted",
	})
	var mErr *MMSEvaluatorError
	if !errors.As(err, &mErr) {
		t.Fatalf("expected MMSEvaluatorError, got %T: %v", err, err)
	}
	if mErr.Code != "E_MMS_BAD_FIXTURE" {
		t.Errorf("expected E_MMS_BAD_FIXTURE, got %s", mErr.Code)
	}
}

func TestGhostedRejectsTooSmallGhostWidth(t *testing.T) {
	// 4th-order centered FD: offsets ±1, ±2 — needs ghost_width ≥ 2.
	wide := []interface{}{
		map[string]interface{}{
			"selector": map[string]interface{}{"kind": "cartesian", "axis": "x", "offset": -2},
			"coeff": map[string]interface{}{
				"op": "/", "args": []interface{}{1, map[string]interface{}{
					"op": "*", "args": []interface{}{12, "dx"}}},
			},
		},
		map[string]interface{}{
			"selector": map[string]interface{}{"kind": "cartesian", "axis": "x", "offset": -1},
			"coeff": map[string]interface{}{
				"op": "/", "args": []interface{}{-8, map[string]interface{}{
					"op": "*", "args": []interface{}{12, "dx"}}},
			},
		},
		map[string]interface{}{
			"selector": map[string]interface{}{"kind": "cartesian", "axis": "x", "offset": 1},
			"coeff": map[string]interface{}{
				"op": "/", "args": []interface{}{8, map[string]interface{}{
					"op": "*", "args": []interface{}{12, "dx"}}},
			},
		},
		map[string]interface{}{
			"selector": map[string]interface{}{"kind": "cartesian", "axis": "x", "offset": 2},
			"coeff": map[string]interface{}{
				"op": "/", "args": []interface{}{-1, map[string]interface{}{
					"op": "*", "args": []interface{}{12, "dx"}}},
			},
		},
	}
	n := 16
	dx := 1.0 / float64(n)
	u := make([]float64, n)
	for i := 0; i < n; i++ {
		u[i] = math.Sin(2 * math.Pi * (float64(i) + 0.5) * dx)
	}
	bindings := map[string]float64{"dx": dx}
	_, err := ApplyStencilGhosted1D(wide, u, bindings, GhostFillOpts{
		GhostWidth: 1, BoundaryPolicy: "periodic",
	})
	var mErr *MMSEvaluatorError
	if !errors.As(err, &mErr) {
		t.Fatalf("expected MMSEvaluatorError, got %T: %v", err, err)
	}
	if mErr.Code != "E_GHOST_WIDTH_TOO_SMALL" {
		t.Errorf("expected E_GHOST_WIDTH_TOO_SMALL, got %s", mErr.Code)
	}
}

func TestGhostedPanelDispatchUnsupported(t *testing.T) {
	n := 8
	dx := 0.1
	u := make([]float64, n)
	for i := range u {
		u[i] = float64(i + 1)
	}
	bindings := map[string]float64{"dx": dx}
	_, err := ApplyStencilGhosted1D(centeredFD2(), u, bindings, GhostFillOpts{
		GhostWidth: 1,
		BoundaryPolicy: BoundaryPolicySpec{
			Kind: "panel_dispatch", Interior: "dist", Boundary: "dist_bnd",
		},
	})
	var mErr *MMSEvaluatorError
	if !errors.As(err, &mErr) {
		t.Fatalf("expected MMSEvaluatorError, got %T: %v", err, err)
	}
	if mErr.Code != "E_GHOST_FILL_UNSUPPORTED" {
		t.Errorf("expected E_GHOST_FILL_UNSUPPORTED, got %s", mErr.Code)
	}
}

func TestGhostedRejectsUnknownKind(t *testing.T) {
	n := 8
	dx := 0.1
	u := make([]float64, n)
	for i := range u {
		u[i] = float64(i + 1)
	}
	bindings := map[string]float64{"dx": dx}
	_, err := ApplyStencilGhosted1D(centeredFD2(), u, bindings, GhostFillOpts{
		GhostWidth: 1, BoundaryPolicy: "not_a_real_kind",
	})
	var mErr *MMSEvaluatorError
	if !errors.As(err, &mErr) {
		t.Fatalf("expected MMSEvaluatorError, got %T: %v", err, err)
	}
}

func TestGhostedRejectsNegativeGhostWidth(t *testing.T) {
	n := 8
	dx := 0.1
	u := make([]float64, n)
	for i := range u {
		u[i] = float64(i + 1)
	}
	bindings := map[string]float64{"dx": dx}
	_, err := ApplyStencilGhosted1D(centeredFD2(), u, bindings, GhostFillOpts{
		GhostWidth: -1, BoundaryPolicy: "periodic",
	})
	var mErr *MMSEvaluatorError
	if !errors.As(err, &mErr) {
		t.Fatalf("expected MMSEvaluatorError, got %T: %v", err, err)
	}
}

func TestGhostedSubStencilSelection(t *testing.T) {
	// Multi-stencil mapping: caller supplies a name to disambiguate.
	multi := map[string]interface{}{
		"left":  centeredFD2(),
		"right": centeredFD2(),
	}
	n := 8
	dx := 0.1
	u := make([]float64, n)
	for i := 0; i < n; i++ {
		u[i] = 2.0 + 3.0*float64(i+1)
	}
	bindings := map[string]float64{"dx": dx}
	got, err := ApplyStencilGhosted1D(multi, u, bindings, GhostFillOpts{
		GhostWidth:     1,
		BoundaryPolicy: "one_sided_extrapolation",
		SubStencil:     "left",
	})
	if err != nil {
		t.Fatal(err)
	}
	want := 3.0 / dx
	for i, v := range got {
		if math.Abs(v-want) > 1e-10 {
			t.Errorf("i=%d: got %v want %v", i, v, want)
		}
	}
	// Missing sub_stencil name on a mapping must error.
	if _, err := ApplyStencilGhosted1D(multi, u, bindings, GhostFillOpts{
		GhostWidth: 1, BoundaryPolicy: "periodic",
	}); err == nil {
		t.Error("expected error when sub_stencil omitted on mapping form")
	}
	// sub_stencil supplied but stencil is a single list must error.
	if _, err := ApplyStencilGhosted1D(centeredFD2(), u, bindings, GhostFillOpts{
		GhostWidth: 1, BoundaryPolicy: "periodic", SubStencil: "left",
	}); err == nil {
		t.Error("expected error when sub_stencil supplied on list form")
	}
}
