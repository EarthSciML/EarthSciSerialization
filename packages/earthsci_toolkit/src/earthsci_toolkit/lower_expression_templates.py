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


def _substitute(body: Any, bindings: dict[str, Any]) -> Any:
    if isinstance(body, str):
        if body in bindings:
            return copy.deepcopy(bindings[body])
        return body
    if _is_array(body):
        return [_substitute(c, bindings) for c in body]
    if _is_object(body):
        return {k: _substitute(v, bindings) for k, v in body.items()}
    return body


def _expand_apply(node: dict, templates: dict, scope: str) -> Any:
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
    resolved = {k: _walk(v, templates, scope) for k, v in bindings.items()}
    return _substitute(decl["body"], resolved)


def _walk(node: Any, templates: dict, scope: str) -> Any:
    if _is_array(node):
        return [_walk(c, templates, scope) for c in node]
    if _is_object(node):
        if node.get("op") == APPLY_OP:
            return _expand_apply(node, templates, scope)
        return {k: _walk(v, templates, scope) for k, v in node.items()}
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


def lower_expression_templates(file: dict) -> dict:
    """Expand all apply_expression_template ops in `file` and strip the
    expression_templates blocks. Returns a new dict (does not mutate input).

    Pre-condition: the input has been schema-validated.
    """
    reject_expression_templates_pre_v04(file)

    if not _is_object(file):
        return file

    apply_paths = _find_apply_paths(file)
    out = copy.deepcopy(file)
    if not apply_paths:
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
            if _is_object(tplraw):
                for tname, tdecl in tplraw.items():
                    templates[tname] = tdecl
                _validate_templates(templates, f"{compkind}.{cname}")
            for k in list(comp.keys()):
                if k == "expression_templates":
                    continue
                comp[k] = _walk(comp[k], templates, f"{compkind}.{cname}.{k}")
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
