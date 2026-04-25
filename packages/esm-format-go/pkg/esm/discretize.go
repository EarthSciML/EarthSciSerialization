// Discretization pipeline per discretization RFC §11 (gt-gbs2).
//
// Mirrors the Julia reference implementation in
// packages/EarthSciSerialization.jl/src/discretize.jl. DAE classification
// and the RFC §12 binding contract are out of scope for this binding and
// tracked separately.
//
// The public entry point is [Discretize] which walks a parsed ESM
// document and emits a discretized ESM:
//
//  1. Canonicalize all expressions (§5.4).
//  2. Resolve model-level boundary conditions into a synthetic `bc` op so
//     they flow through the same rule engine as interior equations.
//  3. Apply the rule engine (§5.2) to every equation RHS and every BC
//     value with a max-pass budget.
//  4. Re-canonicalize the rewritten ASTs.
//  5. Check for unrewritten PDE ops (§11 Step 7) — error or
//     passthrough-annotate depending on StrictUnrewritten.
//  6. Record `metadata.discretized_from` provenance.

package esm

import (
	"bytes"
	"encoding/json"
	"fmt"
)

// DiscretizeOptions configures the §11 pipeline.
type DiscretizeOptions struct {
	// MaxPasses is the per-expression rule-engine budget (§5.2.5). A
	// non-positive value uses DefaultMaxPasses.
	MaxPasses int
	// StrictUnrewritten controls what happens when a rewritten expression
	// still carries a PDE op: true (default) raises
	// E_UNREWRITTEN_PDE_OP; false stamps `passthrough: true` on the
	// offending equation/BC and retains it verbatim.
	StrictUnrewritten bool
}

// DefaultDiscretizeOptions returns the default pipeline configuration:
// max_passes=DefaultMaxPasses, strict_unrewritten=true.
func DefaultDiscretizeOptions() DiscretizeOptions {
	return DiscretizeOptions{
		MaxPasses:         DefaultMaxPasses,
		StrictUnrewritten: true,
	}
}

// Discretize runs the RFC §11 discretization pipeline on a parsed ESM
// document represented as a generic JSON map. Returns a new map; the
// input is not mutated.
//
// `esm` is the parsed ESM payload produced by JSON decoding (use
// encoding/json with UseNumber, or the lossless [LoadAsMap] helper).
// Errors are *RuleEngineError with stable codes per RFC §5.2 / §11.
func Discretize(esm map[string]interface{}, opts DiscretizeOptions) (map[string]interface{}, error) {
	if opts.MaxPasses <= 0 {
		opts.MaxPasses = DefaultMaxPasses
	}

	out := deepNativeMap(esm)

	topRules, err := loadRulesFromAny(out["rules"])
	if err != nil {
		return nil, err
	}

	ctx := buildDiscretizeContext(out)

	if models, ok := out["models"].(map[string]interface{}); ok {
		for mname, mraw := range models {
			model, ok := mraw.(map[string]interface{})
			if !ok {
				continue
			}
			if err := discretizeModel(mname, model, topRules, ctx, opts); err != nil {
				return nil, err
			}
			models[mname] = model
		}
	}

	recordDiscretizedFrom(out)
	return out, nil
}

// ============================================================================
// Rule context assembly (grids + variables)
// ============================================================================

func buildDiscretizeContext(esm map[string]interface{}) RuleContext {
	ctx := NewRuleContext()

	if gridsRaw, ok := esm["grids"].(map[string]interface{}); ok {
		for gname, graw := range gridsRaw {
			ctx.Grids[gname] = extractGridMeta(graw)
		}
	}

	if models, ok := esm["models"].(map[string]interface{}); ok {
		for _, mraw := range models {
			mobj, ok := mraw.(map[string]interface{})
			if !ok {
				continue
			}
			mgrid := stringOrEmpty(mobj["grid"])
			vars, ok := mobj["variables"].(map[string]interface{})
			if !ok {
				continue
			}
			for vname, vraw := range vars {
				vobj, ok := vraw.(map[string]interface{})
				if !ok {
					continue
				}
				meta := VariableMeta{Grid: mgrid}
				if shape, ok := vobj["shape"].([]interface{}); ok {
					ss := make([]string, 0, len(shape))
					for _, s := range shape {
						if str, ok := s.(string); ok {
							ss = append(ss, str)
						}
					}
					meta.Shape = ss
					meta.HasShape = true
				}
				if loc, ok := vobj["location"].(string); ok {
					meta.Location = loc
				}
				ctx.Variables[vname] = meta
			}
		}
	}

	return ctx
}

func extractGridMeta(graw interface{}) GridMeta {
	meta := GridMeta{}
	gobj, ok := graw.(map[string]interface{})
	if !ok {
		return meta
	}
	dims, ok := gobj["dimensions"].([]interface{})
	if !ok {
		return meta
	}
	for _, d := range dims {
		dobj, ok := d.(map[string]interface{})
		if !ok {
			continue
		}
		name, _ := dobj["name"].(string)
		if name == "" {
			continue
		}
		meta.SpatialDims = append(meta.SpatialDims, name)
		if p, ok := dobj["periodic"].(bool); ok && p {
			meta.PeriodicDims = append(meta.PeriodicDims, name)
		}
		if sp, ok := dobj["spacing"].(string); ok && (sp == "nonuniform" || sp == "stretched") {
			meta.NonuniformDims = append(meta.NonuniformDims, name)
		}
	}
	return meta
}

// ============================================================================
// Model-level pipeline
// ============================================================================

func discretizeModel(mname string, model map[string]interface{},
	topRules []Rule, ctx RuleContext, opts DiscretizeOptions) error {

	localRules, err := loadRulesFromAny(model["rules"])
	if err != nil {
		return err
	}
	var rules []Rule
	if len(localRules) == 0 {
		rules = topRules
	} else {
		rules = make([]Rule, 0, len(topRules)+len(localRules))
		rules = append(rules, topRules...)
		rules = append(rules, localRules...)
	}

	mp := lookupMaxPasses(model, opts.MaxPasses)

	if eqns, ok := model["equations"].([]interface{}); ok {
		for i, eqnAny := range eqns {
			eqn, ok := eqnAny.(map[string]interface{})
			if !ok {
				continue
			}
			path := fmt.Sprintf("models.%s.equations[%d]", mname, i)
			if err := discretizeEquation(path, eqn, rules, ctx, mp, opts.StrictUnrewritten); err != nil {
				return err
			}
			eqns[i] = eqn
		}
	}

	if bcs, ok := model["boundary_conditions"].(map[string]interface{}); ok {
		for bcName, bcAny := range bcs {
			bc, ok := bcAny.(map[string]interface{})
			if !ok {
				continue
			}
			path := fmt.Sprintf("models.%s.boundary_conditions.%s", mname, bcName)
			if err := discretizeBC(path, bc, rules, ctx, mp, opts.StrictUnrewritten); err != nil {
				return err
			}
			bcs[bcName] = bc
		}
	}
	return nil
}

func lookupMaxPasses(model map[string]interface{}, defaultMP int) int {
	rc, ok := model["rules_config"].(map[string]interface{})
	if !ok {
		return defaultMP
	}
	switch v := rc["max_passes"].(type) {
	case int:
		return v
	case int64:
		return int(v)
	case float64:
		if v == float64(int(v)) {
			return int(v)
		}
	case json.Number:
		if i, err := v.Int64(); err == nil {
			return int(i)
		}
	}
	return defaultMP
}

// ============================================================================
// Per-equation / per-BC rewrite
// ============================================================================

func discretizeEquation(path string, eqn map[string]interface{},
	rules []Rule, ctx RuleContext, maxPasses int, strict bool) error {

	passthrough := asBool(eqn["passthrough"])

	if rhsRaw, has := eqn["rhs"]; has {
		out, newPT, err := rewriteOrPassthrough(
			path+".rhs", rhsRaw, rules, ctx, maxPasses, strict, passthrough)
		if err != nil {
			return err
		}
		eqn["rhs"] = out
		if newPT && !passthrough {
			eqn["passthrough"] = true
		}
	}
	if lhsRaw, has := eqn["lhs"]; has {
		out, err := canonicalizeLHSValue(lhsRaw)
		if err != nil {
			return err
		}
		eqn["lhs"] = out
	}
	return nil
}

func discretizeBC(path string, bc map[string]interface{},
	rules []Rule, ctx RuleContext, maxPasses int, strict bool) error {

	passthrough := asBool(bc["passthrough"])
	variable := stringOrEmpty(bc["variable"])
	kind := stringOrEmpty(bc["kind"])
	side := stringOrEmpty(bc["side"])
	valueRaw, hasValue := bc["value"]

	// Step 1: try matching a `bc` rule pattern (§9.2 — synthetic wrapper).
	// The wrapper is `bc(variable[, value])`; `kind` / `side` are recorded
	// as sibling map fields for parity with the Julia reference but are
	// not consumed by the expression parser (rules match on op + args).
	rewrittenViaBCRule := false
	if variable != "" && kind != "" && len(rules) > 0 {
		wrapperMap := map[string]interface{}{
			"op":   "bc",
			"args": []interface{}{variable},
			"kind": kind,
		}
		if side != "" {
			wrapperMap["side"] = side
		}
		if hasValue {
			args := wrapperMap["args"].([]interface{})
			wrapperMap["args"] = append(args, valueRaw)
		}

		bcExpr, err := parseExprForRewrite(wrapperMap)
		if err != nil {
			return err
		}
		canonBC, err := Canonicalize(bcExpr)
		if err != nil {
			return err
		}
		rewriteOut, err := Rewrite(canonBC, rules, ctx, maxPasses)
		if err != nil {
			return err
		}
		node, isNode := asExprNode(rewriteOut)
		if !(isNode && node.Op == "bc") {
			final, err := Canonicalize(rewriteOut)
			if err != nil {
				return err
			}
			if hasPDEOp(final) && !passthrough {
				if strict {
					op := firstPDEOp(final)
					return newRuleErr("E_UNREWRITTEN_PDE_OP",
						fmt.Sprintf("%s.value still contains PDE op '%s' after rewrite; "+
							"annotate the BC with 'passthrough: true' to opt out", path, op))
				}
				bc["passthrough"] = true
			}
			bc["value"] = serializeExprToJSON(final)
			rewrittenViaBCRule = true
		}
	}

	// Step 2: default path — canonicalize `value` and run the rule engine.
	if !rewrittenViaBCRule && hasValue {
		out, newPT, err := rewriteOrPassthrough(
			path+".value", valueRaw, rules, ctx, maxPasses, strict, passthrough)
		if err != nil {
			return err
		}
		bc["value"] = out
		if newPT && !passthrough {
			bc["passthrough"] = true
		}
	}
	return nil
}

// rewriteOrPassthrough canonicalizes + rewrites + re-canonicalizes an
// expression. Returns (jsonValue, needsPassthroughStamp, err).
func rewriteOrPassthrough(path string, valueRaw interface{}, rules []Rule,
	ctx RuleContext, maxPasses int, strict, passthrough bool) (interface{}, bool, error) {

	expr, err := parseExprForRewrite(valueRaw)
	if err != nil {
		return nil, false, err
	}
	canon0, err := Canonicalize(expr)
	if err != nil {
		return nil, false, err
	}
	var rewritten Expression
	if len(rules) == 0 {
		rewritten = canon0
	} else {
		rewritten, err = Rewrite(canon0, rules, ctx, maxPasses)
		if err != nil {
			return nil, false, err
		}
	}
	canon1, err := Canonicalize(rewritten)
	if err != nil {
		return nil, false, err
	}
	if passthrough {
		return serializeExprToJSON(canon1), false, nil
	}
	if hasPDEOp(canon1) {
		if strict {
			op := firstPDEOp(canon1)
			return nil, false, newRuleErr("E_UNREWRITTEN_PDE_OP",
				fmt.Sprintf("%s still contains PDE op '%s' after rewrite; "+
					"annotate the equation/BC with 'passthrough: true' to opt out", path, op))
		}
		return serializeExprToJSON(canon1), true, nil
	}
	return serializeExprToJSON(canon1), false, nil
}

func canonicalizeLHSValue(raw interface{}) (interface{}, error) {
	expr, err := parseExprForRewrite(raw)
	if err != nil {
		return nil, err
	}
	c, err := Canonicalize(expr)
	if err != nil {
		return nil, err
	}
	return serializeExprToJSON(c), nil
}

// ============================================================================
// Parse/serialize bridges between JSON-tree form and Expression AST
// ============================================================================

// parseExprForRewrite converts a JSON-decoded value (map/slice/primitive) to
// an Expression AST suitable for Canonicalize / Rewrite.
func parseExprForRewrite(v interface{}) (Expression, error) {
	return parseExprValue(normalizeExprInput(v))
}

// normalizeExprInput normalizes json.Number tokens inside a decoded tree so
// that parseExprValue sees int64/float64 per §5.4.6. It returns a structurally
// identical tree (maps/slices are mutated in place; primitives converted).
func normalizeExprInput(v interface{}) interface{} {
	switch x := v.(type) {
	case json.Number:
		return normalizeJSONNumber(x)
	case map[string]interface{}:
		out := make(map[string]interface{}, len(x))
		for k, val := range x {
			out[k] = normalizeExprInput(val)
		}
		return out
	case []interface{}:
		out := make([]interface{}, len(x))
		for i, e := range x {
			out[i] = normalizeExprInput(e)
		}
		return out
	}
	return v
}

// serializeExprToJSON converts a canonicalized Expression back to a
// JSON-tree value (primitives + map[string]interface{} for ExprNode).
// The result round-trips through encoding/json and the canonical emitter.
func serializeExprToJSON(e Expression) interface{} {
	switch v := e.(type) {
	case nil:
		return nil
	case int64, float64, string, bool:
		return v
	case int:
		return int64(v)
	case ExprNode:
		return exprNodeToJSON(v)
	case *ExprNode:
		return exprNodeToJSON(*v)
	}
	return e
}

func exprNodeToJSON(n ExprNode) map[string]interface{} {
	out := map[string]interface{}{
		"op": n.Op,
	}
	args := make([]interface{}, len(n.Args))
	for i, a := range n.Args {
		args[i] = serializeExprToJSON(a)
	}
	out["args"] = args
	if n.Wrt != nil {
		out["wrt"] = *n.Wrt
	}
	if n.Dim != nil {
		out["dim"] = *n.Dim
	}
	if n.Name != nil {
		out["name"] = *n.Name
	}
	if n.Value != nil {
		out["value"] = n.Value
	}
	return out
}

// ============================================================================
// PDE-op scan (§11 Step 7)
// ============================================================================

var discretizePDEOps = map[string]struct{}{
	"grad": {}, "div": {}, "laplacian": {}, "D": {}, "bc": {},
}

func hasPDEOp(e Expression) bool {
	return firstPDEOp(e) != ""
}

func firstPDEOp(e Expression) string {
	node, ok := asExprNode(e)
	if !ok {
		return ""
	}
	if _, found := discretizePDEOps[node.Op]; found {
		return node.Op
	}
	for _, a := range node.Args {
		if op := firstPDEOp(a); op != "" {
			return op
		}
	}
	return ""
}

// ============================================================================
// Rules loading
// ============================================================================

func loadRulesFromAny(raw interface{}) ([]Rule, error) {
	if raw == nil {
		return nil, nil
	}
	switch raw.(type) {
	case []interface{}, map[string]interface{}:
		rules, err := parseRulesValue(normalizeExprInput(raw))
		if err != nil {
			return nil, err
		}
		return rules, nil
	}
	return nil, nil
}

// ============================================================================
// Metadata provenance
// ============================================================================

func recordDiscretizedFrom(esm map[string]interface{}) {
	meta, ok := esm["metadata"].(map[string]interface{})
	if !ok {
		meta = map[string]interface{}{}
	}
	provenance := map[string]interface{}{}
	if name, ok := meta["name"].(string); ok {
		provenance["name"] = name
	}
	meta["discretized_from"] = provenance

	switch tags := meta["tags"].(type) {
	case []interface{}:
		seen := false
		for _, t := range tags {
			if s, ok := t.(string); ok && s == "discretized" {
				seen = true
				break
			}
		}
		if !seen {
			meta["tags"] = append(tags, "discretized")
		}
	default:
		meta["tags"] = []interface{}{"discretized"}
	}

	esm["metadata"] = meta
}

// ============================================================================
// Deep copy + small helpers
// ============================================================================

// deepNativeMap returns a deep copy of a JSON-shaped map with numeric
// literals normalized to int64 / float64 per §5.4.6.
func deepNativeMap(m map[string]interface{}) map[string]interface{} {
	out := make(map[string]interface{}, len(m))
	for k, v := range m {
		out[k] = deepNative(v)
	}
	return out
}

func deepNative(v interface{}) interface{} {
	switch x := v.(type) {
	case nil:
		return nil
	case map[string]interface{}:
		out := make(map[string]interface{}, len(x))
		for k, val := range x {
			out[k] = deepNative(val)
		}
		return out
	case []interface{}:
		out := make([]interface{}, len(x))
		for i, e := range x {
			out[i] = deepNative(e)
		}
		return out
	case json.Number:
		return normalizeJSONNumber(x)
	}
	return v
}

func stringOrEmpty(v interface{}) string {
	s, _ := v.(string)
	return s
}

func asBool(v interface{}) bool {
	switch x := v.(type) {
	case bool:
		return x
	case string:
		return x == "true" || x == "True" || x == "TRUE"
	}
	return false
}

// ============================================================================
// JSON helpers for top-level document ingestion
// ============================================================================

// CanonicalDocJSON emits a discretized ESM document (or any JSON-tree value)
// as canonical JSON per RFC §5.4.6: sorted object keys at every level,
// minified (no inter-token whitespace), and canonical float literals
// (trailing `.0` for integer-valued magnitudes, lowercase `e` exponents).
func CanonicalDocJSON(doc interface{}) ([]byte, error) {
	return marshalCanonical(doc, false)
}

// LoadAsMap parses an ESM JSON document as a generic map preserving
// numeric int/float distinctions per §5.4.6. This is the preferred input
// form for Discretize since it does not require the strongly-typed
// EsmFile struct to understand every field (notably `rules`).
func LoadAsMap(data []byte) (map[string]interface{}, error) {
	dec := json.NewDecoder(bytes.NewReader(data))
	dec.UseNumber()
	var v interface{}
	if err := dec.Decode(&v); err != nil {
		return nil, fmt.Errorf("ESM decode: %w", err)
	}
	m, ok := v.(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("ESM decode: top-level value is not a JSON object")
	}
	return deepNativeMap(m), nil
}
