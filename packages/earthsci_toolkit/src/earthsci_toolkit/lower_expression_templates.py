"""Load-time expansion pass for `apply_expression_template` AST ops.

esm-spec §9.6, docs/rfcs/ast-expression-templates.md, esm-giy.

Walks each ``models.<m>`` and ``reaction_systems.<rs>`` block; if an
``expression_templates`` entry is present, every
``apply_expression_template`` node anywhere in that component's
expressions is replaced by the substituted template body. After the
pass, the file's expression trees contain no ``apply_expression_template``
nodes and no ``expression_templates`` blocks — downstream consumers see
only normal Expression ASTs (Option A round-trip).

Operates on the pre-coercion JSON dict view, so it must run after
schema validation but before ``_parse_esm_data``.
"""
from __future__ import annotations

import copy
import re
from typing import Any, Iterable

APPLY_OP = "apply_expression_template"


class ExpressionTemplateError(Exception):
    """Raised when expression-template expansion fails.

    The ``code`` attribute carries one of the stable diagnostic codes:
    ``apply_expression_template_unknown_template``,
    ``apply_expression_template_bindings_mismatch``,
    ``apply_expression_template_recursive_body``,
    ``apply_expression_template_invalid_declaration``,
    ``apply_expression_template_version_too_old``.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"[{code}] {message}")
        self.code = code


def _is_object(v: Any) -> bool:
    return isinstance(v, dict)


def _is_array(v: Any) -> bool:
    return isinstance(v, list)


def _assert_no_nested_apply(body: Any, template_name: str, path: str) -> None:
    if _is_array(body):
        for i, child in enumerate(body):
            _assert_no_nested_apply(child, template_name, f"{path}/{i}")
        return
    if _is_object(body):
        if body.get("op") == APPLY_OP:
            raise ExpressionTemplateError(
                "apply_expression_template_recursive_body",
                f"expression_templates.{template_name}: body contains nested "
                f"'apply_expression_template' at {path}; templates MUST NOT call "
                "other templates",
            )
        for k, v in body.items():
            _assert_no_nested_apply(v, template_name, f"{path}/{k}")


def _validate_templates(templates: dict, scope: str) -> None:
    for name, decl in templates.items():
        if not _is_object(decl):
            raise ExpressionTemplateError(
                "apply_expression_template_invalid_declaration",
                f"{scope}.expression_templates.{name}: entry must be an object "
                "with params + body",
            )
        params = decl.get("params")
        if not isinstance(params, list) or len(params) == 0:
            raise ExpressionTemplateError(
                "apply_expression_template_invalid_declaration",
                f"{scope}.expression_templates.{name}: 'params' must be a "
                "non-empty array of strings",
            )
        seen: set[str] = set()
        for p in params:
            if not isinstance(p, str) or not p:
                raise ExpressionTemplateError(
                    "apply_expression_template_invalid_declaration",
                    f"{scope}.expression_templates.{name}: param names must "
                    "be non-empty strings",
                )
            if p in seen:
                raise ExpressionTemplateError(
                    "apply_expression_template_invalid_declaration",
                    f"{scope}.expression_templates.{name}: param '{p}' is "
                    "declared twice",
                )
            seen.add(p)
        if "body" not in decl:
            raise ExpressionTemplateError(
                "apply_expression_template_invalid_declaration",
                f"{scope}.expression_templates.{name}: 'body' is required",
            )
        _assert_no_nested_apply(decl["body"], name, "/body")
        # ``match`` (optional) turns the entry into an auto-applied rewrite rule.
        # It must be a pattern Expression (a bare-metavar string or an op node);
        # a body re-introducing this pattern is rejected later as
        # ``rewrite_rule_nonterminating`` (see _build_match_rules).
        if "match" in decl:
            match = decl["match"]
            if not (isinstance(match, str) or _is_object(match)):
                raise ExpressionTemplateError(
                    "apply_expression_template_invalid_declaration",
                    f"{scope}.expression_templates.{name}: 'match' must be a "
                    "pattern Expression (a metavariable string or an op node)",
                )
            _assert_no_nested_apply(match, name, "/match")


def _substitute(body: Any, bindings: dict[str, Any]) -> Any:
    """Pure structural substitution: every bare-string occurrence of a bound
    metavariable in ``body`` is replaced by a deep copy of its bound AST/literal.

    This is the single substitution primitive of the rewrite engine — it
    instantiates both explicit ``apply_expression_template`` bodies (metavars
    bound from ``bindings``) and auto-applied ``match``-rule bodies (metavars
    bound by structural matching).
    """
    if isinstance(body, str):
        if body in bindings:
            return copy.deepcopy(bindings[body])
        return body
    if _is_array(body):
        return [_substitute(c, bindings) for c in body]
    if _is_object(body):
        return {k: _substitute(v, bindings) for k, v in body.items()}
    return body


# --- match-rule machinery (auto-applied rewrite rules, esm-spec §9.6) ---------
#
# A MatchRule pairs a pattern Expression with a replacement body. ``params`` are
# the metavariables: a param appearing in an operand/``args`` position binds to
# the matched sub-AST; a param in a scalar field (``dim``, ``side``, ...) binds
# to the matched literal. The same ``_match`` recursion handles both positions.

class MatchRule:
    __slots__ = ("name", "pattern", "params", "body")

    def __init__(self, name: str, pattern: Any, params: set, body: Any) -> None:
        self.name = name
        self.pattern = pattern
        self.params = params
        self.body = body


def _merge_bindings(acc: dict, new: dict) -> bool:
    """Merge ``new`` into ``acc``; a repeated metavariable must bind structurally
    equal sub-ASTs. Returns False on a conflicting re-bind."""
    for k, v in new.items():
        if k in acc:
            if acc[k] != v:
                return False
        else:
            acc[k] = v
    return True


def _match(pattern: Any, node: Any, params: set):
    """Structurally match ``pattern`` against ``node``. Returns a dict of
    metavariable bindings on success, or ``None`` on failure. A bare-string
    pattern that is a param is a wildcard binding to whatever ``node`` is;
    otherwise literals must compare equal and dict/list shapes must agree."""
    if isinstance(pattern, str):
        if pattern in params:
            return {pattern: node}
        return {} if (isinstance(node, str) and node == pattern) else None
    if isinstance(pattern, bool):
        return {} if (isinstance(node, bool) and node == pattern) else None
    if isinstance(pattern, (int, float)):
        # bool is a subclass of int; keep True/1 distinct from a numeric literal.
        if isinstance(node, bool):
            return None
        return {} if (isinstance(node, (int, float)) and node == pattern) else None
    if _is_array(pattern):
        if not _is_array(node) or len(node) != len(pattern):
            return None
        acc: dict = {}
        for p, n in zip(pattern, node):
            b = _match(p, n, params)
            if b is None or not _merge_bindings(acc, b):
                return None
        return acc
    if _is_object(pattern):
        if not _is_object(node):
            return None
        acc = {}
        for k, pv in pattern.items():
            if k not in node:
                return None
            b = _match(pv, node[k], params)
            if b is None or not _merge_bindings(acc, b):
                return None
        return acc
    # None or any other scalar: exact equality.
    return {} if node == pattern else None


def _pattern_occurs(tree: Any, pattern: Any, params: set) -> bool:
    """True if ``pattern`` structurally matches any node within ``tree`` (the
    node itself or any descendant) — the non-termination test for a rule whose
    ``body`` re-introduces its own ``match`` pattern."""
    if _match(pattern, tree, params) is not None:
        return True
    if _is_array(tree):
        return any(_pattern_occurs(c, pattern, params) for c in tree)
    if _is_object(tree):
        return any(_pattern_occurs(v, pattern, params) for v in tree.values())
    return False


def _build_match_rules(templates: dict, scope: str) -> list:
    """Collect the ``match``-carrying templates as auto-applied rewrite rules,
    in declaration order. Rejects a rule whose ``body`` re-introduces its own
    pattern with ``rewrite_rule_nonterminating`` (esm-spec §9.6.3)."""
    rules: list = []
    for name, decl in templates.items():
        if "match" not in decl:
            continue
        pattern = decl["match"]
        params = set(decl["params"])
        body = decl["body"]
        if _pattern_occurs(body, pattern, params):
            raise ExpressionTemplateError(
                "rewrite_rule_nonterminating",
                f"{scope}.expression_templates.{name}: the rewrite rule's body "
                "re-introduces its own match pattern; single-pass rewriting "
                "(no re-scan) would not terminate",
            )
        rules.append(MatchRule(name, pattern, params, body))
    return rules


def _expand_apply(node: dict, templates: dict, match_rules: list, scope: str) -> Any:
    name = node.get("name")
    if not isinstance(name, str) or not name:
        raise ExpressionTemplateError(
            "apply_expression_template_invalid_declaration",
            f"{scope}: apply_expression_template node missing or empty 'name'",
        )
    decl = templates.get(name)
    if decl is None:
        raise ExpressionTemplateError(
            "apply_expression_template_unknown_template",
            f"{scope}: apply_expression_template references undeclared "
            f"template '{name}'",
        )
    bindings = node.get("bindings")
    if not _is_object(bindings):
        raise ExpressionTemplateError(
            "apply_expression_template_bindings_mismatch",
            f"{scope}: apply_expression_template '{name}' missing 'bindings' "
            "object",
        )
    declared = set(decl["params"])
    provided = set(bindings.keys())
    for p in decl["params"]:
        if p not in provided:
            raise ExpressionTemplateError(
                "apply_expression_template_bindings_mismatch",
                f"{scope}: apply_expression_template '{name}' missing binding "
                f"for param '{p}'",
            )
    for p in provided:
        if p not in declared:
            raise ExpressionTemplateError(
                "apply_expression_template_bindings_mismatch",
                f"{scope}: apply_expression_template '{name}' supplies unknown "
                f"param '{p}'",
            )
    # Bottom-up: rewrite each binding (which may itself contain apply nodes or
    # match-triggering ops) before substituting into the body. The substituted
    # body is NOT re-scanned (single-pass, §9.6.3).
    resolved = {
        k: _rewrite_node(v, templates, match_rules, scope)
        for k, v in bindings.items()
    }
    return _substitute(decl["body"], resolved)


def _rewrite_node(node: Any, templates: dict, match_rules: list, scope: str) -> Any:
    """The single bottom-up rewrite pass (esm-spec §9.6).

    Children are rewritten first; then, at the current node, explicit
    ``apply_expression_template`` ops are expanded and auto-applied ``match``
    rules are tried in declaration order — the first rule that matches fires and
    its instantiated body replaces the node WITHOUT being re-scanned.
    """
    if _is_array(node):
        return [_rewrite_node(c, templates, match_rules, scope) for c in node]
    if _is_object(node):
        if node.get("op") == APPLY_OP:
            return _expand_apply(node, templates, match_rules, scope)
        rewritten = {
            k: _rewrite_node(v, templates, match_rules, scope)
            for k, v in node.items()
        }
        for rule in match_rules:
            binds = _match(rule.pattern, rewritten, rule.params)
            if binds is not None:
                return _substitute(rule.body, binds)
        return rewritten
    return node


def _find_apply_paths(view: Any, path: str = "") -> list[str]:
    hits: list[str] = []

    def visit(v: Any, p: str) -> None:
        if _is_array(v):
            for i, child in enumerate(v):
                visit(child, f"{p}/{i}")
            return
        if _is_object(v):
            if v.get("op") == APPLY_OP:
                hits.append(p)
            for k, child in v.items():
                visit(child, f"{p}/{k}")

    visit(view, path)
    return hits


def reject_expression_templates_pre_v04(view: Any) -> None:
    """Reject template constructs in files declaring esm < 0.4.0.

    Mirrors the equivalent TS / Julia / Rust / Go checks for
    cross-binding-uniform diagnostics.
    """
    if not _is_object(view):
        return
    esm = view.get("esm")
    if not isinstance(esm, str):
        return
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", esm)
    if not m:
        return
    major, minor = int(m.group(1)), int(m.group(2))
    if not (major == 0 and minor < 4):
        return

    offences: list[str] = []
    for compkind in ("models", "reaction_systems"):
        comps = view.get(compkind)
        if not _is_object(comps):
            continue
        for cname, comp in comps.items():
            if _is_object(comp) and "expression_templates" in comp:
                offences.append(f"/{compkind}/{cname}/expression_templates")
    offences.extend(_find_apply_paths(view))

    if offences:
        raise ExpressionTemplateError(
            "apply_expression_template_version_too_old",
            f"expression_templates / apply_expression_template require esm >= "
            f"0.4.0; file declares {esm}. Offending paths: {', '.join(offences)}",
        )


def _has_match_rules(file: dict) -> bool:
    """True if any component declares an ``expression_templates`` entry carrying
    a ``match`` (i.e. an auto-applied rewrite rule that fires without an explicit
    ``apply_expression_template`` invocation)."""
    for compkind in ("models", "reaction_systems"):
        comps = file.get(compkind)
        if not _is_object(comps):
            continue
        for comp in comps.values():
            tplraw = _is_object(comp) and comp.get("expression_templates")
            if _is_object(tplraw) and any(
                _is_object(d) and "match" in d for d in tplraw.values()
            ):
                return True
    return False


def lower_expression_templates(file: dict) -> dict:
    """Run the single load-time rewrite pass (esm-spec §9.6) over `file`.

    One bottom-up pass per component expands explicit
    ``apply_expression_template`` ops and auto-applies the component's
    ``match`` rewrite rules in template declaration order (replacements are not
    re-scanned); the ``expression_templates`` blocks are then stripped. Returns
    a new dict (does not mutate input).

    Pre-condition: the input has been schema-validated.
    """
    reject_expression_templates_pre_v04(file)

    if not _is_object(file):
        return file

    out = copy.deepcopy(file)
    # Nothing to do unless something triggers the engine: an explicit apply op
    # somewhere, or a component declaring a ``match`` rewrite rule.
    if not _find_apply_paths(out) and not _has_match_rules(out):
        return _strip_expression_templates(out)

    for compkind in ("models", "reaction_systems"):
        comps = out.get(compkind)
        if not _is_object(comps):
            continue
        for cname, comp in comps.items():
            if not _is_object(comp):
                continue
            tplraw = comp.get("expression_templates")
            templates: dict[str, Any] = {}
            match_rules: list = []
            if _is_object(tplraw):
                for tname, tdecl in tplraw.items():
                    templates[tname] = tdecl
                _validate_templates(templates, f"{compkind}.{cname}")
                match_rules = _build_match_rules(templates, f"{compkind}.{cname}")
            for k in list(comp.keys()):
                if k == "expression_templates":
                    continue
                comp[k] = _rewrite_node(
                    comp[k], templates, match_rules, f"{compkind}.{cname}.{k}"
                )
            comp.pop("expression_templates", None)

    leftover = _find_apply_paths(out)
    if leftover:
        raise ExpressionTemplateError(
            "apply_expression_template_unknown_template",
            f"apply_expression_template ops remain after expansion at: "
            f"{', '.join(leftover)} — likely referenced from a component lacking "
            "an expression_templates block",
        )
    return out


def _strip_expression_templates(file: dict) -> dict:
    for compkind in ("models", "reaction_systems"):
        comps = file.get(compkind)
        if not _is_object(comps):
            continue
        for comp in comps.values():
            if _is_object(comp):
                comp.pop("expression_templates", None)
    return file
