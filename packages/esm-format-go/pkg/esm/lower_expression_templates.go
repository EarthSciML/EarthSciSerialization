package esm

// Load-time expansion pass for `apply_expression_template` AST ops
// (esm-spec §9.6, docs/rfcs/ast-expression-templates.md, esm-giy).
//
// Walks each `models.<m>` and `reaction_systems.<rs>` block; if an
// `expression_templates` entry is present, every `apply_expression_template`
// node anywhere in that component's expressions is replaced by the
// substituted template body. After the pass, the file's expression trees
// contain no `apply_expression_template` nodes and no `expression_templates`
// blocks — downstream consumers see only normal Expression ASTs (Option A
// round-trip).
//
// Operates on the pre-deserialization `map[string]interface{}` view, so it
// must run after schema validation but before unmarshaling into the
// `EsmFile` struct.

import (
	"encoding/json"
	"fmt"
	"regexp"
	"strconv"
	"strings"
)

const applyExpressionTemplateOp = "apply_expression_template"

// ExpressionTemplateError is the error type raised by the expression-template
// expansion pass. The Code field carries one of the stable diagnostic codes:
//
//   - apply_expression_template_unknown_template
//   - apply_expression_template_bindings_mismatch
//   - apply_expression_template_recursive_body
//   - apply_expression_template_invalid_declaration
//   - apply_expression_template_version_too_old
type ExpressionTemplateError struct {
	Code    string
	Message string
}

func (e *ExpressionTemplateError) Error() string {
	return fmt.Sprintf("[%s] %s", e.Code, e.Message)
}

func newETErr(code, msg string) *ExpressionTemplateError {
	return &ExpressionTemplateError{Code: code, Message: msg}
}

func isObject(v interface{}) bool {
	_, ok := v.(map[string]interface{})
	return ok
}

func isArray(v interface{}) bool {
	_, ok := v.([]interface{})
	return ok
}

func opOf(v interface{}) string {
	if obj, ok := v.(map[string]interface{}); ok {
		if op, ok := obj["op"].(string); ok {
			return op
		}
	}
	return ""
}

func assertNoNestedApply(body interface{}, templateName, path string) error {
	switch b := body.(type) {
	case []interface{}:
		for i, child := range b {
			if err := assertNoNestedApply(child, templateName, fmt.Sprintf("%s/%d", path, i)); err != nil {
				return err
			}
		}
	case map[string]interface{}:
		if op, ok := b["op"].(string); ok && op == applyExpressionTemplateOp {
			return newETErr(
				"apply_expression_template_recursive_body",
				fmt.Sprintf("expression_templates.%s: body contains nested 'apply_expression_template' at %s; templates MUST NOT call other templates", templateName, path),
			)
		}
		// Iterate in deterministic order for cross-language reproducibility
		// of error messages (Go map iteration is randomized).
		keys := sortedKeys(b)
		for _, k := range keys {
			if err := assertNoNestedApply(b[k], templateName, path+"/"+k); err != nil {
				return err
			}
		}
	}
	return nil
}

func validateTemplates(templates map[string]interface{}, scope string) error {
	for _, name := range sortedKeys(templates) {
		decl := templates[name]
		declObj, ok := decl.(map[string]interface{})
		if !ok {
			return newETErr(
				"apply_expression_template_invalid_declaration",
				fmt.Sprintf("%s.expression_templates.%s: entry must be an object with params + body", scope, name),
			)
		}
		paramsRaw, ok := declObj["params"].([]interface{})
		if !ok || len(paramsRaw) == 0 {
			return newETErr(
				"apply_expression_template_invalid_declaration",
				fmt.Sprintf("%s.expression_templates.%s: 'params' must be a non-empty array of strings", scope, name),
			)
		}
		seen := make(map[string]struct{})
		for _, p := range paramsRaw {
			ps, ok := p.(string)
			if !ok || ps == "" {
				return newETErr(
					"apply_expression_template_invalid_declaration",
					fmt.Sprintf("%s.expression_templates.%s: param names must be non-empty strings", scope, name),
				)
			}
			if _, exists := seen[ps]; exists {
				return newETErr(
					"apply_expression_template_invalid_declaration",
					fmt.Sprintf("%s.expression_templates.%s: param '%s' declared twice", scope, name, ps),
				)
			}
			seen[ps] = struct{}{}
		}
		body, ok := declObj["body"]
		if !ok {
			return newETErr(
				"apply_expression_template_invalid_declaration",
				fmt.Sprintf("%s.expression_templates.%s: 'body' is required", scope, name),
			)
		}
		if err := assertNoNestedApply(body, name, "/body"); err != nil {
			return err
		}
	}
	return nil
}

func deepCopyJSON(v interface{}) interface{} {
	switch x := v.(type) {
	case map[string]interface{}:
		out := make(map[string]interface{}, len(x))
		for k, val := range x {
			out[k] = deepCopyJSON(val)
		}
		return out
	case []interface{}:
		out := make([]interface{}, len(x))
		for i, val := range x {
			out[i] = deepCopyJSON(val)
		}
		return out
	default:
		return x
	}
}

func substituteParams(body interface{}, bindings map[string]interface{}) interface{} {
	switch b := body.(type) {
	case string:
		if v, ok := bindings[b]; ok {
			return deepCopyJSON(v)
		}
		return body
	case []interface{}:
		out := make([]interface{}, len(b))
		for i, c := range b {
			out[i] = substituteParams(c, bindings)
		}
		return out
	case map[string]interface{}:
		out := make(map[string]interface{}, len(b))
		for k, v := range b {
			out[k] = substituteParams(v, bindings)
		}
		return out
	default:
		return body
	}
}

func expandApply(node map[string]interface{}, templates map[string]interface{}, scope string) (interface{}, error) {
	nameRaw, ok := node["name"].(string)
	if !ok || nameRaw == "" {
		return nil, newETErr(
			"apply_expression_template_invalid_declaration",
			fmt.Sprintf("%s: apply_expression_template node missing or empty 'name'", scope),
		)
	}
	declRaw, ok := templates[nameRaw]
	if !ok {
		return nil, newETErr(
			"apply_expression_template_unknown_template",
			fmt.Sprintf("%s: apply_expression_template references undeclared template '%s'", scope, nameRaw),
		)
	}
	decl, ok := declRaw.(map[string]interface{})
	if !ok {
		return nil, newETErr(
			"apply_expression_template_invalid_declaration",
			fmt.Sprintf("%s: template '%s' declaration is not an object", scope, nameRaw),
		)
	}
	bindingsRaw, ok := node["bindings"].(map[string]interface{})
	if !ok {
		return nil, newETErr(
			"apply_expression_template_bindings_mismatch",
			fmt.Sprintf("%s: apply_expression_template '%s' missing 'bindings' object", scope, nameRaw),
		)
	}
	paramsArr, _ := decl["params"].([]interface{})
	declared := make(map[string]struct{}, len(paramsArr))
	params := make([]string, 0, len(paramsArr))
	for _, p := range paramsArr {
		if ps, ok := p.(string); ok {
			declared[ps] = struct{}{}
			params = append(params, ps)
		}
	}
	for _, p := range params {
		if _, ok := bindingsRaw[p]; !ok {
			return nil, newETErr(
				"apply_expression_template_bindings_mismatch",
				fmt.Sprintf("%s: apply_expression_template '%s' missing binding for param '%s'", scope, nameRaw, p),
			)
		}
	}
	for k := range bindingsRaw {
		if _, ok := declared[k]; !ok {
			return nil, newETErr(
				"apply_expression_template_bindings_mismatch",
				fmt.Sprintf("%s: apply_expression_template '%s' supplies unknown param '%s'", scope, nameRaw, k),
			)
		}
	}
	resolved := make(map[string]interface{}, len(bindingsRaw))
	for k, v := range bindingsRaw {
		walked, err := walkExpr(v, templates, scope)
		if err != nil {
			return nil, err
		}
		resolved[k] = walked
	}
	body := decl["body"]
	return substituteParams(body, resolved), nil
}

func walkExpr(node interface{}, templates map[string]interface{}, scope string) (interface{}, error) {
	switch n := node.(type) {
	case []interface{}:
		out := make([]interface{}, len(n))
		for i, c := range n {
			r, err := walkExpr(c, templates, scope)
			if err != nil {
				return nil, err
			}
			out[i] = r
		}
		return out, nil
	case map[string]interface{}:
		if op, ok := n["op"].(string); ok && op == applyExpressionTemplateOp {
			return expandApply(n, templates, scope)
		}
		out := make(map[string]interface{}, len(n))
		for k, v := range n {
			r, err := walkExpr(v, templates, scope)
			if err != nil {
				return nil, err
			}
			out[k] = r
		}
		return out, nil
	default:
		return node, nil
	}
}

func findApplyPaths(view interface{}, path string, hits *[]string) {
	switch v := view.(type) {
	case []interface{}:
		for i, c := range v {
			findApplyPaths(c, fmt.Sprintf("%s/%d", path, i), hits)
		}
	case map[string]interface{}:
		if op, ok := v["op"].(string); ok && op == applyExpressionTemplateOp {
			*hits = append(*hits, path)
		}
		for _, k := range sortedKeys(v) {
			findApplyPaths(v[k], path+"/"+k, hits)
		}
	}
}

var semverRe = regexp.MustCompile(`^(\d+)\.(\d+)\.(\d+)$`)

// RejectExpressionTemplatesPreV04 rejects `expression_templates` blocks and
// `apply_expression_template` ops in files declaring `esm` < 0.4.0. Mirrors
// the equivalent TS / Python / Julia / Rust checks.
func RejectExpressionTemplatesPreV04(view map[string]interface{}) error {
	if view == nil {
		return nil
	}
	esmRaw, ok := view["esm"].(string)
	if !ok {
		return nil
	}
	m := semverRe.FindStringSubmatch(esmRaw)
	if m == nil {
		return nil
	}
	major, _ := strconv.Atoi(m[1])
	minor, _ := strconv.Atoi(m[2])
	if !(major == 0 && minor < 4) {
		return nil
	}
	offences := []string{}
	for _, kind := range []string{"models", "reaction_systems"} {
		comps, ok := view[kind].(map[string]interface{})
		if !ok {
			continue
		}
		for _, cname := range sortedKeys(comps) {
			compObj, ok := comps[cname].(map[string]interface{})
			if !ok {
				continue
			}
			if _, has := compObj["expression_templates"]; has {
				offences = append(offences, fmt.Sprintf("/%s/%s/expression_templates", kind, cname))
			}
		}
	}
	findApplyPaths(view, "", &offences)
	if len(offences) > 0 {
		return newETErr(
			"apply_expression_template_version_too_old",
			fmt.Sprintf("expression_templates / apply_expression_template require esm >= 0.4.0; file declares %s. Offending paths: %s", esmRaw, strings.Join(offences, ", ")),
		)
	}
	return nil
}

// LowerExpressionTemplates expands all apply_expression_template ops in
// `view` and strips the `expression_templates` blocks. Mutates `view` in
// place.
//
// Pre-condition: the input has been schema-validated.
func LowerExpressionTemplates(view map[string]interface{}) error {
	if err := RejectExpressionTemplatesPreV04(view); err != nil {
		return err
	}
	if view == nil {
		return nil
	}
	hits := []string{}
	findApplyPaths(view, "", &hits)
	if len(hits) == 0 {
		stripExpressionTemplates(view)
		return nil
	}
	for _, kind := range []string{"models", "reaction_systems"} {
		comps, ok := view[kind].(map[string]interface{})
		if !ok {
			continue
		}
		for cname, compRaw := range comps {
			compObj, ok := compRaw.(map[string]interface{})
			if !ok {
				continue
			}
			tplRaw, _ := compObj["expression_templates"].(map[string]interface{})
			if tplRaw != nil {
				if err := validateTemplates(tplRaw, fmt.Sprintf("%s.%s", kind, cname)); err != nil {
					return err
				}
			}
			templates := tplRaw
			if templates == nil {
				templates = map[string]interface{}{}
			}
			delete(compObj, "expression_templates")
			for k, v := range compObj {
				scope := fmt.Sprintf("%s.%s.%s", kind, cname, k)
				expanded, err := walkExpr(v, templates, scope)
				if err != nil {
					return err
				}
				compObj[k] = expanded
			}
		}
	}
	leftover := []string{}
	findApplyPaths(view, "", &leftover)
	if len(leftover) > 0 {
		return newETErr(
			"apply_expression_template_unknown_template",
			fmt.Sprintf("apply_expression_template ops remain after expansion at: %s — likely referenced from a component lacking an expression_templates block", strings.Join(leftover, ", ")),
		)
	}
	return nil
}

func stripExpressionTemplates(view map[string]interface{}) {
	for _, kind := range []string{"models", "reaction_systems"} {
		comps, ok := view[kind].(map[string]interface{})
		if !ok {
			continue
		}
		for _, compRaw := range comps {
			if compObj, ok := compRaw.(map[string]interface{}); ok {
				delete(compObj, "expression_templates")
			}
		}
	}
}

// applyExpressionTemplatesToJSON rewrites a JSON document, performing the
// load-time `apply_expression_template` expansion. Returns the expanded JSON
// bytes; the input is not modified.
//
// Used by the Go binding's load path: schema validation runs against the
// original JSON, then this rewrite produces the post-expansion JSON used to
// unmarshal into the typed struct.
func applyExpressionTemplatesToJSON(jsonStr string) (string, error) {
	var view map[string]interface{}
	dec := json.NewDecoder(strings.NewReader(jsonStr))
	dec.UseNumber()
	if err := dec.Decode(&view); err != nil {
		return "", fmt.Errorf("apply_expression_template pass: %w", err)
	}
	if err := LowerExpressionTemplates(view); err != nil {
		return "", err
	}
	out, err := json.Marshal(view)
	if err != nil {
		return "", fmt.Errorf("apply_expression_template pass: re-marshal: %w", err)
	}
	return string(out), nil
}
