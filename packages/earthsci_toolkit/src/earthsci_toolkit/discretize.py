"""Discretization pipeline per discretization RFC §11 (gt-gbs2).

The public entry point is :func:`discretize`, which walks a parsed ESM
document and emits a discretized ESM:

  1. Canonicalize all expressions (§5.4).
  2. Resolve model-level boundary conditions into a synthetic ``bc`` op
     so they flow through the same rule engine as interior equations.
  3. Apply the rule engine (§5.2) to every equation RHS and every BC
     value with a max-pass budget.
  4. Re-canonicalize the rewritten ASTs.
  5. Check for unrewritten PDE ops (§11 Step 7) — error or
     passthrough-annotate depending on ``strict_unrewritten``.
  6. Record ``metadata.discretized_from`` provenance.

Scheme-expansion of ``use:<scheme>`` rules (§7.2.1), cross-grid
``regrid`` wrapping, and the RFC §12 DAE binding contract are out of
scope here.

Mirrors ``packages/EarthSciSerialization.jl/src/discretize.jl`` at
commit ``5849c525`` (gt-gbs2). Acceptance criterion is parity with the
Julia reference on the shared conformance fixtures.
"""

from __future__ import annotations

import copy
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from .canonicalize import canonicalize
from .esm_types import Expr, ExprNode
from .parse import _parse_expression
from .rule_engine import (
    Rule,
    RuleContext,
    RuleEngineError,
    parse_rules,
    rewrite,
)
from .serialize import _serialize_expression


_PDE_OPS = frozenset({"grad", "div", "laplacian", "D", "bc"})


def discretize(
    esm: Mapping[str, Any],
    *,
    max_passes: int = 32,
    strict_unrewritten: bool = True,
) -> Dict[str, Any]:
    """Run the RFC §11 discretization pipeline on an ESM document.

    ``esm`` is the parsed ESM payload as a mapping (the form produced by
    decoding JSON with the stdlib). The function returns a new dict; the
    input is not mutated.

    Parameters
    ----------
    esm:
        The ESM document to discretize.
    max_passes:
        Per-expression rule-engine budget (§5.2.5). Default 32.
    strict_unrewritten:
        When ``True`` (default), a rewritten expression that still
        carries a PDE op (``grad``, ``div``, ``laplacian``, ``D``,
        ``bc``) raises :class:`RuleEngineError` with code
        ``E_UNREWRITTEN_PDE_OP``. When ``False``, the offending
        equation or BC is instead marked ``passthrough: true`` and the
        rewritten form is retained verbatim.

    Returns
    -------
    dict
        The discretized ESM. ``metadata.discretized_from`` is set to a
        provenance sub-object carrying the input's ``metadata.name``;
        the ``"discretized"`` tag is appended to ``metadata.tags``.
    """
    if not isinstance(esm, Mapping):
        raise TypeError(
            f"discretize: input must be a JSON object / mapping; got {type(esm).__name__}"
        )

    out: Dict[str, Any] = copy.deepcopy(dict(esm))

    top_rules = _load_rules(out.get("rules"))
    ctx = _build_rule_context(out)

    models = out.get("models")
    if isinstance(models, Mapping):
        for mname, mraw in list(models.items()):
            model = dict(mraw) if isinstance(mraw, Mapping) else mraw
            if isinstance(model, dict):
                _discretize_model(
                    str(mname), model, top_rules, ctx, max_passes, strict_unrewritten
                )
                models[mname] = model  # type: ignore[index]

    _record_discretized_from(out)
    return out


# ============================================================================
# Rule-context assembly (grids + variables)
# ============================================================================


def _build_rule_context(esm: Mapping[str, Any]) -> RuleContext:
    grids: Dict[str, Dict[str, Any]] = {}
    grids_raw = esm.get("grids")
    if isinstance(grids_raw, Mapping):
        for gname, graw in grids_raw.items():
            grids[str(gname)] = _extract_grid_meta(graw)

    variables: Dict[str, Dict[str, Any]] = {}
    models = esm.get("models")
    if isinstance(models, Mapping):
        for _mname, mraw in models.items():
            if not isinstance(mraw, Mapping):
                continue
            mgrid = mraw.get("grid")
            mgrid_str = str(mgrid) if isinstance(mgrid, str) else None
            vars_raw = mraw.get("variables")
            if not isinstance(vars_raw, Mapping):
                continue
            for vname, vraw in vars_raw.items():
                if not isinstance(vraw, Mapping):
                    continue
                meta: Dict[str, Any] = {}
                if mgrid_str is not None:
                    meta["grid"] = mgrid_str
                shape = vraw.get("shape")
                if shape is not None:
                    meta["shape"] = shape
                loc = vraw.get("location")
                if loc is not None:
                    meta["location"] = str(loc)
                variables[str(vname)] = meta
    return RuleContext(grids=grids, variables=variables)


def _extract_grid_meta(graw: Any) -> Dict[str, Any]:
    meta: Dict[str, Any] = {}
    if not isinstance(graw, Mapping):
        return meta
    dims_raw = graw.get("dimensions")
    if isinstance(dims_raw, Sequence) and not isinstance(dims_raw, (str, bytes)):
        spatial: List[str] = []
        periodic: List[str] = []
        nonuniform: List[str] = []
        for d in dims_raw:
            if not isinstance(d, Mapping):
                continue
            name = d.get("name")
            if name is None:
                continue
            name_s = str(name)
            spatial.append(name_s)
            if d.get("periodic") is True:
                periodic.append(name_s)
            spacing = d.get("spacing")
            if isinstance(spacing, str) and spacing in ("nonuniform", "stretched"):
                nonuniform.append(name_s)
        meta["spatial_dims"] = spatial
        meta["periodic_dims"] = periodic
        meta["nonuniform_dims"] = nonuniform
    return meta


# ============================================================================
# Model-level pipeline
# ============================================================================


def _discretize_model(
    mname: str,
    model: Dict[str, Any],
    top_rules: List[Rule],
    ctx: RuleContext,
    max_passes: int,
    strict_unrewritten: bool,
) -> None:
    local_rules_raw = model.get("rules")
    local_rules = _load_rules(local_rules_raw)
    rules = top_rules if not local_rules else list(top_rules) + list(local_rules)

    mp = _lookup_max_passes(model, max_passes)

    eqns = model.get("equations")
    if isinstance(eqns, list):
        for i, eqn_any in enumerate(eqns):
            if not isinstance(eqn_any, Mapping):
                continue
            eqn = dict(eqn_any)
            _discretize_equation(
                f"models.{mname}.equations[{i}]",
                eqn,
                rules,
                ctx,
                mp,
                strict_unrewritten,
            )
            eqns[i] = eqn

    bcs = model.get("boundary_conditions")
    if isinstance(bcs, Mapping):
        for bc_name, bc_any in list(bcs.items()):
            if not isinstance(bc_any, Mapping):
                continue
            bc = dict(bc_any)
            _discretize_bc(
                f"models.{mname}.boundary_conditions.{bc_name}",
                bc,
                rules,
                ctx,
                mp,
                strict_unrewritten,
            )
            bcs[bc_name] = bc  # type: ignore[index]


def _lookup_max_passes(model: Mapping[str, Any], default: int) -> int:
    rules_meta = model.get("rules_config")
    if isinstance(rules_meta, Mapping):
        mp = rules_meta.get("max_passes")
        if isinstance(mp, int) and not isinstance(mp, bool):
            return mp
    return default


# ============================================================================
# Per-equation / per-BC rewrite
# ============================================================================


def _discretize_equation(
    path: str,
    eqn: Dict[str, Any],
    rules: Sequence[Rule],
    ctx: RuleContext,
    max_passes: int,
    strict_unrewritten: bool,
) -> None:
    passthrough = _as_bool(eqn.get("passthrough", False))

    def _set_passthrough(v: bool) -> None:
        eqn["passthrough"] = v

    if "rhs" in eqn:
        eqn["rhs"] = _rewrite_or_passthrough(
            f"{path}.rhs",
            eqn["rhs"],
            rules,
            ctx,
            max_passes,
            strict_unrewritten,
            passthrough,
            _set_passthrough,
        )
    if "lhs" in eqn:
        eqn["lhs"] = _canonicalize_value(eqn["lhs"])


def _discretize_bc(
    path: str,
    bc: Dict[str, Any],
    rules: Sequence[Rule],
    ctx: RuleContext,
    max_passes: int,
    strict_unrewritten: bool,
) -> None:
    passthrough = _as_bool(bc.get("passthrough", False))

    def _set_passthrough(v: bool) -> None:
        bc["passthrough"] = v

    variable = bc.get("variable")
    kind = bc.get("kind")
    side = bc.get("side")
    value_raw = bc.get("value")

    rewritten_via_bc_rule = False
    if (
        isinstance(variable, str)
        and isinstance(kind, str)
        and rules
    ):
        wrapper: Dict[str, Any] = {
            "op": "bc",
            "args": [variable],
            "kind": kind,
        }
        if isinstance(side, str):
            wrapper["side"] = side
        if value_raw is not None:
            wrapper["args"].append(value_raw)
        bc_expr = _parse_expression(wrapper)
        rewrite_out = rewrite(canonicalize(bc_expr), rules, ctx, max_passes=max_passes)
        if not (isinstance(rewrite_out, ExprNode) and rewrite_out.op == "bc"):
            final = canonicalize(rewrite_out)
            if _has_pde_op(final) and not passthrough:
                if strict_unrewritten:
                    op = _first_pde_op(final)
                    raise RuleEngineError(
                        "E_UNREWRITTEN_PDE_OP",
                        f"{path}.value still contains PDE op '{op}' after rewrite; "
                        f"annotate the BC with 'passthrough: true' to opt out",
                    )
                bc["passthrough"] = True
            bc["value"] = _serialize_expression(final)
            rewritten_via_bc_rule = True

    if not rewritten_via_bc_rule and value_raw is not None:
        bc["value"] = _rewrite_or_passthrough(
            f"{path}.value",
            value_raw,
            rules,
            ctx,
            max_passes,
            strict_unrewritten,
            passthrough,
            _set_passthrough,
        )


def _rewrite_or_passthrough(
    path: str,
    value_raw: Any,
    rules: Sequence[Rule],
    ctx: RuleContext,
    max_passes: int,
    strict_unrewritten: bool,
    passthrough: bool,
    set_passthrough: Callable[[bool], None],
) -> Any:
    expr = _parse_expression(value_raw)
    canon0 = canonicalize(expr)
    rewritten = canon0 if not rules else rewrite(canon0, rules, ctx, max_passes=max_passes)
    canon1 = canonicalize(rewritten)
    if passthrough:
        return _serialize_expression(canon1)
    if _has_pde_op(canon1):
        if strict_unrewritten:
            op = _first_pde_op(canon1)
            raise RuleEngineError(
                "E_UNREWRITTEN_PDE_OP",
                f"{path} still contains PDE op '{op}' after rewrite; "
                f"annotate the equation/BC with 'passthrough: true' to opt out",
            )
        set_passthrough(True)
    return _serialize_expression(canon1)


def _canonicalize_value(value_raw: Any) -> Any:
    expr = _parse_expression(value_raw)
    return _serialize_expression(canonicalize(expr))


# ============================================================================
# Leftover-PDE-op scan (RFC §11 Step 7)
# ============================================================================


def _has_pde_op(e: Expr) -> bool:
    return _first_pde_op(e) is not None


def _first_pde_op(e: Expr) -> Optional[str]:
    if isinstance(e, ExprNode):
        if e.op in _PDE_OPS:
            return e.op
        for a in e.args:
            r = _first_pde_op(a)
            if r is not None:
                return r
    return None


# ============================================================================
# Rule loading (permissive: accept array form or keyed-object form)
# ============================================================================


def _load_rules(raw: Any) -> List[Rule]:
    if raw is None:
        return []
    if not isinstance(raw, (list, Mapping)):
        return []
    if not raw:
        return []
    return parse_rules(raw)


# ============================================================================
# Misc helpers
# ============================================================================


def _as_bool(x: Any) -> bool:
    if isinstance(x, bool):
        return x
    if isinstance(x, str):
        return x.lower() == "true"
    if x is None:
        return False
    return x is True


# ============================================================================
# Metadata: discretized_from provenance
# ============================================================================


def _record_discretized_from(esm: Dict[str, Any]) -> None:
    meta_raw = esm.get("metadata")
    if isinstance(meta_raw, dict):
        meta = meta_raw
    elif isinstance(meta_raw, Mapping):
        meta = dict(meta_raw)
    else:
        meta = {}

    src_name = meta.get("name")
    provenance: Dict[str, Any] = {}
    if src_name is not None:
        provenance["name"] = str(src_name)
    meta["discretized_from"] = provenance

    tags = meta.get("tags")
    if isinstance(tags, list):
        if "discretized" not in (str(t) for t in tags):
            tags.append("discretized")
    else:
        meta["tags"] = ["discretized"]

    esm["metadata"] = meta
