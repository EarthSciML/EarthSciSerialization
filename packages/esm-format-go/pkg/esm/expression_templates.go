package esm

import (
	"bytes"
	"encoding/json"
	"fmt"
	"regexp"
	"sort"
	"strconv"
)

// applyExpressionTemplateOp is the AST op kind for template references
// (RFC v2 §5.2 / docs/content/rfcs/ast-expression-templates.md).
const applyExpressionTemplateOp = "apply_expression_template"

// expandExpressionTemplates rewrites the raw JSON string by:
//   - Removing every `expression_templates` block from inside each model /
//     reaction_system component;
//   - Replacing every `apply_expression_template` op-node anywhere in the
//     same component with the substituted template body.
//
// Templates are component-local and not shared across subsystems
// (RFC v2 §5.3.4). The function rejects any file that uses
// expression_templates / apply_expression_template while declaring
// `esm: < 0.4.0`. Returns the rewritten JSON bytes ready for downstream
// schema validation and Unmarshal.
func expandExpressionTemplates(jsonStr string) ([]byte, error) {
	// UseNumber preserves the JSON wire form (int vs float) for every
	// number — required by discretization RFC §5.4.1. json.Marshal of a
	// json.Number writes the original token verbatim, so the round-trip
	// here cannot widen "1" to "1.0" or strip ".0" from "1.0".
	var root map[string]any
	dec := json.NewDecoder(bytes.NewReader([]byte(jsonStr)))
	dec.UseNumber()
	if err := dec.Decode(&root); err != nil {
		return nil, fmt.Errorf("expression_templates pre-expand: %w", err)
	}

	hasUse := scanForApplyTemplate(root)
	hasBlock := false
	for _, section := range []string{"models", "reaction_systems"} {
		comps, ok := root[section].(map[string]any)
		if !ok {
			continue
		}
		for _, c := range comps {
			cm, _ := c.(map[string]any)
			if cm == nil {
				continue
			}
			if t, ok := cm["expression_templates"].(map[string]any); ok && len(t) > 0 {
				hasBlock = true
				break
			}
		}
		if hasBlock {
			break
		}
	}
	if hasUse || hasBlock {
		v, ok := root["esm"].(string)
		if !ok || !esmVersionAtLeast(v, 0, 4, 0) {
			return nil, fmt.Errorf(
				"expression_templates / apply_expression_template require esm: 0.4.0 or later (file declares esm: %q)",
				v,
			)
		}
	}

	for _, section := range []string{"models", "reaction_systems"} {
		comps, ok := root[section].(map[string]any)
		if !ok {
			continue
		}
		// Iterate over components in deterministic order for reproducibility.
		names := make([]string, 0, len(comps))
		for n := range comps {
			names = append(names, n)
		}
		sort.Strings(names)
		for _, n := range names {
			cm, _ := comps[n].(map[string]any)
			if cm == nil {
				continue
			}
			if err := expandInComponent(cm); err != nil {
				return nil, err
			}
		}
	}

	out, err := json.Marshal(root)
	if err != nil {
		return nil, fmt.Errorf("expression_templates post-expand marshal: %w", err)
	}
	return out, nil
}

func expandInComponent(component map[string]any) error {
	tmplsRaw := component["expression_templates"]
	delete(component, "expression_templates")
	templates := map[string]map[string]any{}
	if tm, ok := tmplsRaw.(map[string]any); ok {
		for name, t := range tm {
			if td, ok := t.(map[string]any); ok {
				templates[name] = td
			}
		}
	}
	if len(templates) > 0 {
		for k, v := range component {
			if k == "subsystems" {
				continue
			}
			rewritten, err := expandWalk(v, templates)
			if err != nil {
				return err
			}
			component[k] = rewritten
		}
	}
	subs, _ := component["subsystems"].(map[string]any)
	for _, sub := range subs {
		sm, _ := sub.(map[string]any)
		if sm == nil {
			continue
		}
		if _, isRef := sm["ref"]; isRef {
			continue
		}
		if err := expandInComponent(sm); err != nil {
			return err
		}
	}
	return nil
}

func expandWalk(node any, templates map[string]map[string]any) (any, error) {
	switch v := node.(type) {
	case map[string]any:
		if op, _ := v["op"].(string); op == applyExpressionTemplateOp {
			return expandApplyNode(v, templates)
		}
		out := make(map[string]any, len(v))
		for k, x := range v {
			rx, err := expandWalk(x, templates)
			if err != nil {
				return nil, err
			}
			out[k] = rx
		}
		return out, nil
	case []any:
		out := make([]any, len(v))
		for i, x := range v {
			rx, err := expandWalk(x, templates)
			if err != nil {
				return nil, err
			}
			out[i] = rx
		}
		return out, nil
	default:
		return v, nil
	}
}

func expandApplyNode(node map[string]any, templates map[string]map[string]any) (any, error) {
	name, _ := node["name"].(string)
	template, ok := templates[name]
	if !ok {
		return nil, fmt.Errorf("apply_expression_template references unknown template %q", name)
	}
	paramsRaw, _ := template["params"].([]any)
	params := make([]string, 0, len(paramsRaw))
	for _, p := range paramsRaw {
		if s, ok := p.(string); ok {
			params = append(params, s)
		}
	}
	bindings, _ := node["bindings"].(map[string]any)
	if bindings == nil {
		return nil, fmt.Errorf("apply_expression_template %q missing 'bindings' object", name)
	}
	for _, p := range params {
		if _, ok := bindings[p]; !ok {
			return nil, fmt.Errorf("apply_expression_template %q missing binding %q", name, p)
		}
	}
	for k := range bindings {
		found := false
		for _, p := range params {
			if k == p {
				found = true
				break
			}
		}
		if !found {
			return nil, fmt.Errorf("apply_expression_template %q has unknown binding %q", name, k)
		}
	}
	return substituteTemplateBody(deepCloneJSON(template["body"]), bindings), nil
}

func substituteTemplateBody(body any, bindings map[string]any) any {
	switch v := body.(type) {
	case string:
		if b, ok := bindings[v]; ok {
			return deepCloneJSON(b)
		}
		return v
	case map[string]any:
		out := make(map[string]any, len(v))
		for k, x := range v {
			switch k {
			case "args", "values":
				if arr, ok := x.([]any); ok {
					rs := make([]any, len(arr))
					for i, a := range arr {
						rs[i] = substituteTemplateBody(a, bindings)
					}
					out[k] = rs
				} else {
					out[k] = x
				}
			case "expr":
				out[k] = substituteTemplateBody(x, bindings)
			default:
				out[k] = x
			}
		}
		return out
	case []any:
		out := make([]any, len(v))
		for i, x := range v {
			out[i] = substituteTemplateBody(x, bindings)
		}
		return out
	default:
		return v
	}
}

func deepCloneJSON(v any) any {
	switch x := v.(type) {
	case map[string]any:
		out := make(map[string]any, len(x))
		for k, val := range x {
			out[k] = deepCloneJSON(val)
		}
		return out
	case []any:
		out := make([]any, len(x))
		for i, val := range x {
			out[i] = deepCloneJSON(val)
		}
		return out
	default:
		return v
	}
}

func scanForApplyTemplate(node any) bool {
	switch v := node.(type) {
	case map[string]any:
		if op, _ := v["op"].(string); op == applyExpressionTemplateOp {
			return true
		}
		for _, x := range v {
			if scanForApplyTemplate(x) {
				return true
			}
		}
	case []any:
		for _, x := range v {
			if scanForApplyTemplate(x) {
				return true
			}
		}
	}
	return false
}

var esmVersionRe = regexp.MustCompile(`^(\d+)\.(\d+)\.(\d+)$`)

func esmVersionAtLeast(v string, ma, mi, pa int) bool {
	m := esmVersionRe.FindStringSubmatch(v)
	if m == nil {
		return false
	}
	a, _ := strconv.Atoi(m[1])
	b, _ := strconv.Atoi(m[2])
	c, _ := strconv.Atoi(m[3])
	if a != ma {
		return a > ma
	}
	if b != mi {
		return b > mi
	}
	return c >= pa
}
