// Walker ghost-fill kernel (RFC §5.2.8 / §7, esm-bet, esm-37k, esm-vs5).
//
// Mirrors apply_stencil_ghosted_1d in
// packages/EarthSciSerialization.jl/src/mms_evaluator.jl. Applies a 1D
// Cartesian stencil on an interior sample vector after extending the input
// by ghost_width cells per side using the rule's declared boundary_policy.
package esm

import (
	"fmt"
)

// MMSEvaluatorError is a stable-coded error raised by the walker ghost-fill
// kernel. Codes mirror the Julia reference (mms_evaluator.jl).
type MMSEvaluatorError struct {
	Code    string
	Message string
}

func (e *MMSEvaluatorError) Error() string {
	return fmt.Sprintf("MMSEvaluatorError(%s): %s", e.Code, e.Message)
}

func newMMSErr(code, msg string) *MMSEvaluatorError {
	return &MMSEvaluatorError{Code: code, Message: msg}
}

// BoundaryPolicyKinds is the closed set of policy kinds recognised by
// ApplyStencilGhosted1D. Mirrors mms_evaluator.jl::BOUNDARY_POLICY_KINDS.
var BoundaryPolicyKinds = []string{
	"periodic", "reflecting", "one_sided_extrapolation", "prescribed",
	"ghosted", "neumann_zero", "extrapolate", "panel_dispatch",
}

// canonicalBoundaryKind resolves v0.3.x backwards-compat aliases to the
// canonical kind. Mirrors _BOUNDARY_POLICY_KIND_ALIASES in rule_engine.jl.
func canonicalBoundaryKind(k string) string {
	switch k {
	case "ghosted":
		return "prescribed"
	case "neumann_zero":
		return "reflecting"
	case "extrapolate":
		return "one_sided_extrapolation"
	}
	return k
}

// GhostFillOpts configures ApplyStencilGhosted1D. BoundaryPolicy is required
// and must be either a closed-set string or a BoundaryPolicySpec (single
// per-axis spec — callers with the multi-axis BoundaryPolicy.PerAxis form
// must select their axis first).
//
// Prescribe is required when the resolved kind is "prescribed" (or its
// "ghosted" alias). It receives side ∈ {"left", "right"} and k ∈ 1..GhostWidth
// (1 = cell closest to the boundary), and returns the ghost value.
//
// Degree provides the default polynomial order for one_sided_extrapolation
// when the spec carries no `degree` field. Zero is treated as "unset" and
// resolves to 1 (linear); request degree 0 by setting the spec's
// BoundaryPolicySpec.Degree=0 with HasDegree=true.
//
// SubStencil selects a named entry list when the stencil argument is a
// multi-stencil mapping (map[string]interface{}); empty when stencil is a
// single entry list ([]interface{}).
type GhostFillOpts struct {
	GhostWidth     int
	BoundaryPolicy interface{}
	Prescribe      func(side string, k int) float64
	Degree         int
	SubStencil     string
}

// ApplyStencilGhosted1D applies a 1D Cartesian stencil on the interior sample
// vector u after extending it on each side by opts.GhostWidth cells using the
// rule's declared boundary_policy (RFC §5.2.8). Returns the length-len(u)
// interior outputs, having sliced ghosts back off.
//
// The stencil argument is the JSON-decoded shape of a rule's `stencil`
// field — either a list of {selector, coeff} entries ([]interface{}) or
// a multi-stencil mapping (map[string]interface{}) keyed by name; in the
// latter case opts.SubStencil selects the entry list to apply.
//
// Supported boundary_policy values (closed set per RFC §5.2.8):
//
//   - "periodic" — wrap-around fill. Bit-equal to the periodic walker on
//     identical inputs.
//   - "reflecting" (alias "neumann_zero") — mirror across the boundary
//     face: ghost cell k (1 = closest to the edge) gets u[k-1] on the left
//     and u[n-k] on the right (zero-indexed).
//   - "one_sided_extrapolation" (alias "extrapolate") — polynomial
//     extrapolation from the interior. degree ∈ 0..3; default 1.
//   - "prescribed" (alias "ghosted") — caller-supplied ghost values via
//     opts.Prescribe.
//
// "panel_dispatch" is recognised but not implemented — returns
// MMSEvaluatorError(E_GHOST_FILL_UNSUPPORTED).
//
// opts.GhostWidth MUST be ≥ max(|offset|) across all stencil entries; else
// MMSEvaluatorError(E_GHOST_WIDTH_TOO_SMALL).
func ApplyStencilGhosted1D(stencil interface{}, u []float64,
	bindings map[string]float64, opts GhostFillOpts) ([]float64, error) {
	if opts.GhostWidth < 0 {
		return nil, newMMSErr("E_MMS_BAD_FIXTURE",
			fmt.Sprintf("ghost_width must be non-negative, got %d", opts.GhostWidth))
	}
	entries, err := resolveSubStencil(stencil, opts.SubStencil)
	if err != nil {
		return nil, err
	}

	type coeffPair struct {
		offset int
		coeff  float64
	}
	pairs := make([]coeffPair, 0, len(entries))
	maxOff := 0
	for _, e := range entries {
		em, ok := e.(map[string]interface{})
		if !ok {
			return nil, newMMSErr("E_MMS_BAD_FIXTURE",
				fmt.Sprintf("stencil entry must be an object, got %T", e))
		}
		selRaw, has := em["selector"]
		if !has {
			return nil, newMMSErr("E_MMS_BAD_FIXTURE",
				"stencil entry missing required `selector` field")
		}
		sel, ok := selRaw.(map[string]interface{})
		if !ok {
			return nil, newMMSErr("E_MMS_BAD_FIXTURE",
				"stencil entry `selector` must be an object")
		}
		offRaw, has := sel["offset"]
		if !has {
			return nil, newMMSErr("E_MMS_BAD_FIXTURE",
				"stencil entry selector missing required `offset` field")
		}
		off, ok := jsonAsInt(offRaw)
		if !ok {
			return nil, newMMSErr("E_MMS_BAD_FIXTURE",
				fmt.Sprintf("stencil entry selector `offset` must be an integer, got %T", offRaw))
		}
		coeffRaw, has := em["coeff"]
		if !has {
			return nil, newMMSErr("E_MMS_BAD_FIXTURE",
				"stencil entry missing required `coeff` field")
		}
		coeffExpr, err := parseExprValue(coeffRaw)
		if err != nil {
			return nil, newMMSErr("E_MMS_BAD_FIXTURE",
				fmt.Sprintf("stencil coeff parse: %v", err))
		}
		cVal, err := Evaluate(coeffExpr, bindings)
		if err != nil {
			return nil, newMMSErr("E_MMS_BAD_FIXTURE",
				fmt.Sprintf("stencil coeff evaluate: %v", err))
		}
		pairs = append(pairs, coeffPair{offset: off, coeff: cVal})
		ao := off
		if ao < 0 {
			ao = -ao
		}
		if ao > maxOff {
			maxOff = ao
		}
	}
	if opts.GhostWidth < maxOff {
		return nil, newMMSErr("E_GHOST_WIDTH_TOO_SMALL",
			fmt.Sprintf("stencil offset %d exceeds ghost_width %d; "+
				"rule must declare `ghost_width` ≥ max(|offset|)",
				maxOff, opts.GhostWidth))
	}

	n := len(u)
	if n < 2 {
		return nil, newMMSErr("E_MMS_BAD_FIXTURE",
			fmt.Sprintf("ghosted stencil application requires at least 2 interior cells; got %d", n))
	}
	Ng := opts.GhostWidth
	uExt := make([]float64, n+2*Ng)
	for i := 0; i < n; i++ {
		uExt[Ng+i] = u[i]
	}

	kindRaw, err := extractPolicyKind(opts.BoundaryPolicy)
	if err != nil {
		return nil, err
	}
	kind := canonicalBoundaryKind(kindRaw)
	degree := resolveExtrapolationDegree(opts.BoundaryPolicy, opts.Degree)

	switch kind {
	case "periodic":
		fillGhostsPeriodic(uExt, u, Ng)
	case "reflecting":
		fillGhostsReflecting(uExt, u, Ng)
	case "one_sided_extrapolation":
		if err := fillGhostsOneSided(uExt, u, Ng, degree); err != nil {
			return nil, err
		}
	case "prescribed":
		if opts.Prescribe == nil {
			return nil, newMMSErr("E_MMS_BAD_FIXTURE",
				"boundary_policy=`prescribed` requires a Prescribe callback; "+
					"callable receives (side, k) with side ∈ (\"left\", \"right\") and 1 ≤ k ≤ ghost_width")
		}
		fillGhostsPrescribed(uExt, Ng, opts.Prescribe)
	case "panel_dispatch":
		return nil, newMMSErr("E_GHOST_FILL_UNSUPPORTED",
			"boundary_policy=`panel_dispatch` not implemented for the 1D walker "+
				"(cubed-sphere only); see esm-37k follow-ups for the 2D adapter")
	default:
		return nil, newMMSErr("E_MMS_BAD_FIXTURE",
			fmt.Sprintf("unknown boundary_policy kind %q; expected one of: %v",
				kind, BoundaryPolicyKinds))
	}

	out := make([]float64, n)
	for i := 0; i < n; i++ {
		var acc float64
		for _, p := range pairs {
			acc += p.coeff * uExt[Ng+i+p.offset]
		}
		out[i] = acc
	}
	return out, nil
}

// resolveSubStencil extracts the stencil-entries list from the rule's stencil
// field. The Julia reference accepts a single list or a multi-stencil mapping;
// when a mapping is supplied SubStencil names the entry to apply.
func resolveSubStencil(stencil interface{}, subStencil string) ([]interface{}, error) {
	if list, ok := stencil.([]interface{}); ok {
		if subStencil != "" {
			return nil, newMMSErr("E_MMS_BAD_FIXTURE",
				fmt.Sprintf("`sub_stencil`=%q was requested but rule carries "+
					"a single stencil list, not a multi-stencil mapping", subStencil))
		}
		return list, nil
	}
	if m, ok := stencil.(map[string]interface{}); ok {
		if subStencil == "" {
			keys := make([]string, 0, len(m))
			for k := range m {
				keys = append(keys, k)
			}
			return nil, newMMSErr("E_MMS_BAD_FIXTURE",
				fmt.Sprintf("rule carries a multi-stencil mapping but no `sub_stencil` "+
					"name was supplied (available: %v)", keys))
		}
		v, has := m[subStencil]
		if !has {
			keys := make([]string, 0, len(m))
			for k := range m {
				keys = append(keys, k)
			}
			return nil, newMMSErr("E_MMS_BAD_FIXTURE",
				fmt.Sprintf("rule carries no `%s` sub-stencil (available: %v)",
					subStencil, keys))
		}
		list, ok := v.([]interface{})
		if !ok {
			return nil, newMMSErr("E_MMS_BAD_FIXTURE",
				fmt.Sprintf("sub-stencil %q must be an entry list, got %T", subStencil, v))
		}
		return list, nil
	}
	return nil, newMMSErr("E_MMS_BAD_FIXTURE",
		fmt.Sprintf("stencil must be a list or multi-stencil mapping, got %T", stencil))
}

// extractPolicyKind pulls the kind tag out of opts.BoundaryPolicy. Accepts a
// closed-set string or a BoundaryPolicySpec.
func extractPolicyKind(bp interface{}) (string, error) {
	switch v := bp.(type) {
	case string:
		return v, nil
	case BoundaryPolicySpec:
		if v.Kind == "" {
			return "", newMMSErr("E_MMS_BAD_FIXTURE",
				"BoundaryPolicySpec missing required `kind`")
		}
		return v.Kind, nil
	case *BoundaryPolicySpec:
		if v == nil {
			return "", newMMSErr("E_MMS_BAD_FIXTURE",
				"BoundaryPolicy is nil")
		}
		if v.Kind == "" {
			return "", newMMSErr("E_MMS_BAD_FIXTURE",
				"BoundaryPolicySpec missing required `kind`")
		}
		return v.Kind, nil
	}
	return "", newMMSErr("E_MMS_BAD_FIXTURE",
		fmt.Sprintf("BoundaryPolicy must be a string or BoundaryPolicySpec, got %T", bp))
}

// resolveExtrapolationDegree picks the polynomial degree for
// one_sided_extrapolation. Returns the spec's degree when HasDegree, else
// optDegree if positive, else 1.
func resolveExtrapolationDegree(bp interface{}, optDegree int) int {
	if spec, ok := bp.(BoundaryPolicySpec); ok && spec.HasDegree {
		return spec.Degree
	}
	if spec, ok := bp.(*BoundaryPolicySpec); ok && spec != nil && spec.HasDegree {
		return spec.Degree
	}
	if optDegree > 0 {
		return optDegree
	}
	return 1
}

// fillGhostsPeriodic wraps interior values around to the ghost cells.
func fillGhostsPeriodic(uExt []float64, u []float64, Ng int) {
	n := len(u)
	for k := 1; k <= Ng; k++ {
		uExt[Ng-k] = u[n-k]     // left ghost k mirrors interior cell n-k+1 across the period
		uExt[Ng+n+k-1] = u[k-1] // right ghost k mirrors interior cell k across the period
	}
}

// fillGhostsReflecting mirrors interior cells across the boundary face.
func fillGhostsReflecting(uExt []float64, u []float64, Ng int) {
	n := len(u)
	for k := 1; k <= Ng; k++ {
		// Mirror across the boundary face between cell 0 (ghost) and cell 1
		// (interior): ghost cell k (1 = closest to the boundary) reads
		// interior cell k.
		uExt[Ng-k] = u[k-1]
		uExt[Ng+n+k-1] = u[n-k]
	}
}

// fillGhostsOneSided extrapolates ghost cells from the interior using a
// polynomial of the given degree (0..3).
func fillGhostsOneSided(uExt []float64, u []float64, Ng, degree int) error {
	if degree < 0 || degree > 3 {
		return newMMSErr("E_MMS_BAD_FIXTURE",
			fmt.Sprintf("one_sided_extrapolation degree must be in 0..3, got %d", degree))
	}
	n := len(u)
	if n <= degree {
		return newMMSErr("E_MMS_BAD_FIXTURE",
			fmt.Sprintf("one_sided_extrapolation degree %d requires at least %d "+
				"interior cells; got %d", degree, degree+1, n))
	}
	for k := 1; k <= Ng; k++ {
		uExt[Ng-k] = extrapolateLeft(u, degree, k)
		uExt[Ng+n+k-1] = extrapolateRight(u, degree, k)
	}
	return nil
}

// extrapolateLeft fits a polynomial through the first degree+1 interior cells
// and evaluates it at virtual cell index 1-k (1-indexed, matching Julia).
func extrapolateLeft(u []float64, degree, k int) float64 {
	K := float64(k)
	switch degree {
	case 0:
		return u[0]
	case 1:
		return u[0] + K*(u[0]-u[1])
	case 2:
		// Quadratic through u[1], u[2], u[3] evaluated at i = 1 - k.
		return (1.0+1.5*K+0.5*K*K)*u[0] +
			(-2.0*K-K*K)*u[1] +
			(0.5*K+0.5*K*K)*u[2]
	}
	// degree == 3: cubic through u[1..4] at i = 1 - k.
	return (1.0+(11.0/6.0)*K+K*K+(1.0/6.0)*K*K*K)*u[0] +
		(-3.0*K-2.5*K*K-0.5*K*K*K)*u[1] +
		(1.5*K+2.0*K*K+0.5*K*K*K)*u[2] +
		((-1.0/3.0)*K-0.5*K*K-(1.0/6.0)*K*K*K)*u[3]
}

// extrapolateRight fits a polynomial through the last degree+1 interior cells
// and evaluates it at virtual cell index n+k.
func extrapolateRight(u []float64, degree, k int) float64 {
	n := len(u)
	K := float64(k)
	switch degree {
	case 0:
		return u[n-1]
	case 1:
		return u[n-1] + K*(u[n-1]-u[n-2])
	case 2:
		return (1.0+1.5*K+0.5*K*K)*u[n-1] +
			(-2.0*K-K*K)*u[n-2] +
			(0.5*K+0.5*K*K)*u[n-3]
	}
	return (1.0+(11.0/6.0)*K+K*K+(1.0/6.0)*K*K*K)*u[n-1] +
		(-3.0*K-2.5*K*K-0.5*K*K*K)*u[n-2] +
		(1.5*K+2.0*K*K+0.5*K*K*K)*u[n-3] +
		((-1.0/3.0)*K-0.5*K*K-(1.0/6.0)*K*K*K)*u[n-4]
}

// fillGhostsPrescribed invokes the caller's Prescribe callback for each ghost
// cell. The callback receives ("left"|"right", k) with k ∈ 1..Ng (1 = closest
// to the boundary).
func fillGhostsPrescribed(uExt []float64, Ng int, prescribe func(side string, k int) float64) {
	nInterior := len(uExt) - 2*Ng
	for k := 1; k <= Ng; k++ {
		uExt[Ng-k] = prescribe("left", k)
		uExt[Ng+nInterior+k-1] = prescribe("right", k)
	}
}
