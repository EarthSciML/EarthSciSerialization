"""Generic, GDD-driven spatial (method-of-lines) discretization — the Python
"PDE-op scan" deferred by :mod:`earthsci_toolkit.discretize`, mirroring the
Julia Path-A pipeline (ESD ``build_ode_problem`` → ``EarthSciSerialization.discretize``).

Design principle (no per-rule code): a **Grid Discretization Descriptor** maps
each spatial operator to a catalog rule —

    {"discretizations": {"grad": {<rule>}, "d2": {<rule>}, ...},
     "grids": {<domain>: {"spatial": {<dim>: {"grid_spacing": ...}}}}}

The pass walks every equation (state PDE *and* observed, e.g.
``psi_x = grad(psi, x)``) and, for each spatial-operator node, applies the
*GDD-selected* rule via :func:`earthsci_toolkit.rule_engine.rewrite`. Selection
is data, not code: adding a stencil to the catalog and naming it in a GDD is
sufficient — no edit here. There is no operator special-casing (no ``grad_norm``
/ Godunov branch); a level-set ``|∇ψ|`` discretizes because its component factors
into ``grad`` observeds, and whatever ``grad`` rule the GDD selects (centered,
``upwind_1st``, …) is applied to each.

Scope of this module: Cartesian uniform grids; ``grad`` / ``d2`` (atomic) and
``laplacian`` (expanded to per-dimension ``d2``); ``dirichlet`` / ``zero_gradient``
BCs lowered to ``makearray`` ghost regions. BC-as-declarative-rules and
non-uniform / curvilinear grids remain follow-ups (the Julia binding covers them).
"""

from __future__ import annotations

import copy
import itertools
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dataclasses import replace

from .rule_engine import parse_rule, rewrite, _parse_expr
from .canonicalize import canonicalize
from .esm_types import ExprNode


class SpatialDiscretizeError(Exception):
    """Raised when a PDE component cannot be discretized under the given GDD."""


def flattened_to_esm(flat: Any, domains: Dict[str, Any],
                     name: str = "Flattened",
                     boundary_conditions: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Adapt a :class:`FlattenedSystem` (the output of ``earthsci_toolkit.flatten``)
    into a single-model ``.esm`` dict that :func:`spatial_discretize` consumes.

    This is the join between coupling resolution and discretization: ``flatten``
    resolves ``param_to_var`` and other coupling (e.g. a 0-D Rothermel spread
    rate substituted into the level-set's ``R_0``); this adapter exposes the
    resolved equation set on the PDE domain so the spatial pass can lower it.
    ``domains`` is the coupled file's ``domains`` block (re-used verbatim).
    ``boundary_conditions`` carries the PDE model's BCs (``flatten`` does not
    preserve them); without them the spatial pass falls back to Dirichlet
    defaults and mis-sizes the grid.
    """
    # flatten() dot-namespaces names (e.g. "LevelSet.psi"); a dot in an array
    # state name breaks simulate()'s element expansion, so sanitize "." -> "_"
    # consistently across variable declarations and equation references.
    rename = {n: n.replace(".", "_")
              for n in (*flat.state_variables, *flat.observed_variables, *flat.parameters)}

    def _rename(node):
        return _map_expr(node, lambda x: rename.get(x, x) if isinstance(x, str) else x)

    variables: Dict[str, Any] = {}
    for n, v in flat.state_variables.items():
        variables[rename[n]] = {"type": "state", "units": v.units or "1"}
    for n, v in flat.observed_variables.items():
        variables[rename[n]] = {"type": "observed", "units": v.units or "1"}
    for n, v in flat.parameters.items():
        variables[rename[n]] = {"type": "parameter", "units": v.units or "1",
                                "default": v.default if v.default is not None else 0.0}
    equations = [{"lhs": _rename(_to_json(e.lhs)), "rhs": _rename(_to_json(e.rhs))}
                 for e in flat.equations]
    model: Dict[str, Any] = {"domain": next(iter(domains)), "system_kind": "pde",
                             "variables": variables, "equations": equations}
    if boundary_conditions:
        model["boundary_conditions"] = boundary_conditions
    return {
        "esm": "0.5.0", "metadata": {"name": name}, "domains": domains,
        "models": {name: model},
    }


# --- GDD rule resolution (the generic selection mechanism) -------------------
def _resolve_rule(op: str, entry: Any) -> Any:
    """Turn a GDD ``discretizations[op]`` entry into a parsed Rule.

    Accepts an inline rule object (``{applies_to|pattern, replacement, ...}``),
    a single-rule wrapper ``{"discretizations": {name: rule}}``, or a
    ``{"ref": path}`` pointing at an ESD catalog JSON file.
    """
    if isinstance(entry, dict) and "ref" in entry:
        data = json.loads(Path(entry["ref"]).read_text())
        (name, spec), = data["discretizations"].items()
        spec = dict(spec)
    elif isinstance(entry, dict) and "discretizations" in entry:
        (name, spec), = entry["discretizations"].items()
        spec = dict(spec)
    elif isinstance(entry, dict):
        spec, name = dict(entry), op
    else:
        raise SpatialDiscretizeError(f"GDD entry for {op!r} is not a rule")
    if "applies_to" in spec and "pattern" not in spec:
        spec["pattern"] = spec.pop("applies_to")
    return parse_rule(spec, name=name)


def _gdd_rules(gdd: Dict[str, Any]) -> Dict[str, Any]:
    return {op: _resolve_rule(op, entry)
            for op, entry in (gdd.get("discretizations") or {}).items()}


# --- AST plumbing (shared, content-free) -------------------------------------
_CHILD_KEYS = ("args", "values")


def _map_expr(node: Any, fn) -> Any:
    if isinstance(node, dict):
        new = dict(node)
        for k in _CHILD_KEYS:
            if isinstance(new.get(k), list):
                new[k] = [_map_expr(a, fn) for a in new[k]]
        if new.get("expr") is not None:
            new["expr"] = _map_expr(new["expr"], fn)
        return fn(new)
    if isinstance(node, list):
        return [_map_expr(a, fn) for a in node]
    return fn(node)


def _to_json(e: Any) -> Any:
    if isinstance(e, ExprNode):
        d: Dict[str, Any] = {"op": e.op}
        if e.args is not None:
            d["args"] = [_to_json(a) for a in e.args]
        # scalar / list / dict metadata fields carried verbatim
        for f in ("wrt", "dim", "fn", "output_idx", "reduce", "ranges", "regions",
                  "shape", "perm", "axis", "name", "value", "var", "semiring",
                  "distinct", "join", "id", "manifold", "handler_id", "table", "output"):
            v = getattr(e, f, None)
            if v is not None:
                d[f] = v
        # expression-valued fields recurse
        for f in ("expr", "lower", "upper", "filter", "key"):
            v = getattr(e, f, None)
            if v is not None:
                d[f] = _to_json(v)
        if e.values is not None:
            d["values"] = [_to_json(x) for x in e.values]
        if getattr(e, "table_axes", None) is not None:
            d["table_axes"] = {k: _to_json(v) for k, v in e.table_axes.items()}
        return d
    return e


def _subst_symbol(node: Any, name: str, value: Any) -> Any:
    return _map_expr(node, lambda n: value if n == name else n)


def _canon_for_match(node: Any) -> Any:
    """Canonical form used for composite-rule pattern matching.

    Normalizes integer-valued floats to ints (so ``^2.0`` and ``^2`` match) and
    canonicalizes (RFC §5.4 — sorts commutative ``+``/``*`` operands), so a
    composite rule (e.g. the Godunov ``sqrt(grad²+grad²)`` norm) matches the real
    component regardless of exponent representation or operand order. Applied to
    both the expression and the rule pattern, so structural matching aligns.
    """
    nums = _map_expr(node, lambda n: int(n)
                     if isinstance(n, float) and float(n).is_integer() else n)
    return _to_json(canonicalize(_parse_expr(nums)))


def _lift_index_to_nd(body: Any, state: str, dim: str, dims: List[str]) -> Any:
    if len(dims) == 1:
        return body
    pos = dims.index(dim)

    def f(n):
        if (isinstance(n, dict) and n.get("op") == "index"
                and n.get("args") and n["args"][0] == state and len(n["args"]) == 2):
            k = n["args"][1]
            return {"op": "index", "args": [state] + [(k if i == pos else d)
                                                       for i, d in enumerate(dims)]}
        return n
    return _map_expr(body, f)


def _expand_laplacian(expr: Any, dims: List[str]) -> Any:
    def f(n):
        if isinstance(n, dict) and n.get("op") == "laplacian":
            u = n["args"][0]
            terms = [{"op": "d2", "args": [u], "dim": d} for d in dims]
            return terms[0] if len(terms) == 1 else {"op": "+", "args": terms}
        return n
    return _map_expr(expr, f)


_ATOMIC_OPS = ("grad", "d2")


def _apply_gdd_rules(expr: Any, rules: Dict[str, Any], dims: List[str],
                     dx_by_dim: Dict[str, float]) -> Any:
    """Lower spatial operators using the GDD-selected rules.

    Composite rules (GDD keys other than the atomic ``grad`` / ``d2``, e.g. a
    ``grad_norm`` Godunov rule whose ``applies_to`` matches ``sqrt(grad²+grad²)``)
    are applied to the whole expression first via the rule engine — they fire
    wherever their multi-node pattern matches and emit a ready N-D pointwise body
    (uniform-grid ``dx``). Atomic per-dimension rules then lower any remaining
    ``grad`` / ``d2`` nodes (extract the 1-D stencil body and lift it to N-D).
    """
    composite = [r for op, r in rules.items()
                 if op not in _ATOMIC_OPS and op != "laplacian"]
    if composite:
        # canonicalize expr + patterns so 2 vs 2.0 and operand order don't block
        # the multi-node match against the real component form.
        expr = _canon_for_match(expr)
        composite = [replace(r, pattern=_parse_expr(_canon_for_match(_to_json(r.pattern))))
                     for r in composite]
        expr = _to_json(rewrite(_parse_expr(expr), composite))
        # canonicalize emits its internal `neg` for unary minus; restore the
        # wire op `-` so the discretized document validates.
        expr = _map_expr(expr, lambda n: {"op": "-", "args": n["args"]}
                         if isinstance(n, dict) and n.get("op") == "neg" else n)
        dxs = set(dx_by_dim.values())
        if len(dxs) > 1:
            raise SpatialDiscretizeError(
                "composite (norm-level) stencil rules assume a uniform grid "
                f"spacing; got {sorted(dxs)}")
        expr = _subst_symbol(expr, "dx", float(next(iter(dxs))))

    atomic = {op: rules[op] for op in _ATOMIC_OPS if op in rules}

    def f(n):
        if not (isinstance(n, dict) and n.get("op") in atomic):
            return n
        op = n["op"]
        operand = n["args"][0]
        if not isinstance(operand, str):
            raise SpatialDiscretizeError(
                f"{op} operand must be a bare field (got {operand!r}); inline a "
                "named observed instead")
        dim = n.get("dim")
        if dim not in dx_by_dim:
            raise SpatialDiscretizeError(f"{op} over unknown spatial dim {dim!r}")
        lowered = rewrite(_parse_expr(n), [atomic[op]])
        if lowered.expr is None:
            raise SpatialDiscretizeError(f"rule for {op!r} did not lower to a body")
        body = _subst_symbol(_to_json(lowered.expr), "dx", float(dx_by_dim[dim]))
        return _lift_index_to_nd(body, operand, dim, dims)
    return _map_expr(expr, f)


# --- boundary conditions -> ghost regions ------------------------------------
_BC_ALIAS = {"zero_gradient": "neumann", "constant": "dirichlet"}
_DEFAULT_BC = {"kind": "dirichlet", "value": 0.0}


def _split_side(side: str, dims: List[str]) -> Tuple[Optional[str], Optional[str]]:
    for end, suffix in (("low", "min"), ("high", "max")):
        if side.endswith(suffix) and side[:-len(suffix)] in dims:
            return side[:-len(suffix)], end
    return None, None


def _bcs_by_side(model, domain, dims) -> Dict[Tuple[str, str], Dict[str, Any]]:
    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for bc in (model.get("boundary_conditions") or {}).values():
        dim, end = _split_side(str(bc.get("side", "")), dims)
        if dim is not None:
            out[(dim, end)] = {"kind": _BC_ALIAS.get(bc.get("kind"), bc.get("kind", "dirichlet")),
                               "value": float(bc.get("value", 0.0))}
    for bc in domain.get("boundary_conditions", []) or []:
        kind = _BC_ALIAS.get(bc.get("type"), bc.get("type", "dirichlet"))
        value = float(bc.get("value", 0.0))
        for d in bc.get("dimensions", []):
            for end in ("low", "high"):
                out.setdefault((d, end), {"kind": kind, "value": value})
    return out


def _bc(bc_by_side, dim, end):
    return bc_by_side.get((dim, end), _DEFAULT_BC)


def _grid_sizes(domain, dims, bc_by_side) -> Dict[str, Tuple[int, float]]:
    out: Dict[str, Tuple[int, float]] = {}
    spatial = domain.get("spatial") or {}
    for name in dims:
        spec = spatial[name]
        n_points = int(round((spec["max"] - spec["min"]) / spec["grid_spacing"])) + 1
        drop = sum(1 for end in ("low", "high")
                   if _bc(bc_by_side, name, end)["kind"] in ("dirichlet", "constant"))
        out[name] = (n_points - drop, float(spec["grid_spacing"]))
    return out


def _affine_offset(sub: Any, dim: str) -> Optional[int]:
    """If ``sub`` is an affine index ``dim`` / ``dim ± k`` (in the canonical
    ``{op:"+", args:[dim, k]}`` form or its ``-``/operand-swapped variants),
    return the integer offset ``k`` (0 for a bare ``dim``); else ``None``."""
    if sub == dim:
        return 0
    if isinstance(sub, dict) and sub.get("op") in ("+", "-"):
        args = sub.get("args") or []
        if len(args) == 2:
            a, b = args
            if sub["op"] == "+":
                if a == dim and isinstance(b, (int, float)) and not isinstance(b, bool):
                    return int(b)
                if b == dim and isinstance(a, (int, float)) and not isinstance(a, bool):
                    return int(a)
            elif sub["op"] == "-" and a == dim and isinstance(b, (int, float)) \
                    and not isinstance(b, bool):
                return -int(b)
    return None


def _halo_by_dim(body: Any, state: str, dims: List[str]) -> Dict[str, int]:
    """Largest absolute stencil offset on ``state`` per spatial dim — the ghost
    halo width each boundary needs (1 for a centred 2nd-order / Godunov stencil,
    2 for WENO5, etc.)."""
    halo = {d: 0 for d in dims}

    def f(n):
        if (isinstance(n, dict) and n.get("op") == "index"
                and n.get("args") and n["args"][0] == state):
            subs = n["args"][1:]
            if len(subs) == len(dims):
                for pos, d in enumerate(dims):
                    k = _affine_offset(subs[pos], d)
                    if k is not None:
                        halo[d] = max(halo[d], abs(k))
        return n
    _map_expr(body, f)
    return halo


def _ghost_subst_cell(expr, state, pos, ndim, cell, n, bc_kind, bc_value, dim):
    """Substitute out-of-range ghost accesses for one concrete boundary cell.

    For an ``index(state, …)`` whose subscript along ``pos`` is affine in ``dim``
    (offset ``k``), the resolved index at this cell is ``cell + k``; when that
    falls outside ``[1, n]`` it is a ghost: replaced by the Dirichlet/constant
    value, or (Neumann / zero-gradient) by the nearest in-range cell. Matching
    the canonical ``{+,[dim,k]}`` affine form fixes the long-standing low-side
    miss (the old ``{-,[dim,1]}`` target never matched ``{+,[dim,-1]}``), and the
    per-cell resolution generalizes from a 1-cell to an N-cell halo."""
    def f(node):
        if (isinstance(node, dict) and node.get("op") == "index"
                and node.get("args") and node["args"][0] == state):
            subs = node["args"][1:]
            if len(subs) == ndim:
                k = _affine_offset(subs[pos], dim)
                if k is not None:
                    resolved = cell + k
                    if resolved < 1 or resolved > n:
                        if bc_kind in ("dirichlet", "constant"):
                            return float(bc_value)
                        new = list(subs)
                        new[pos] = min(max(resolved, 1), n)   # clamp to boundary cell
                        return {"op": "index", "args": [state] + new}
        return node
    return _map_expr(expr, f)


def _make_regions(interior, state, dims, sizes, bc_by_side):
    """Carve the index box into an interior region plus per-cell boundary
    regions of the stencil's halo width, applying ghost substitution per cell.

    The interior body covers the full box first; boundary cells (depth ``1..h``
    from each side, ``h`` = stencil halo) overwrite it last-wins. A 1-cell halo
    reproduces the original 3^D layout; wider stencils (WENO) get a width-``h``
    band on each side, so a ``±h`` access never reads past the domain edge."""
    ndim = len(dims)
    halo = _halo_by_dim(interior, state, dims)

    # Per-dim position options: a DISJOINT interior band [h+1, n-h] plus the
    # low/high boundary cells (depth 1..h each side). Disjoint (not the full
    # box) so an interior ``±h`` access never reaches a domain edge — the
    # vectorized evaluator can slice it directly, and boundary cells carry the
    # ghost-substituted bodies. h=0 dims keep the full [1, n] band.
    dim_opts: List[List[Tuple[Any, Tuple[int, int]]]] = []
    for dim in dims:
        n = sizes[dim][0]
        h = min(halo[dim], n)
        opts: List[Tuple[Any, Tuple[int, int]]] = []
        if n - h >= h + 1:                              # non-empty interior band
            opts.append(("I", (h + 1, n - h)))
        for p in range(1, h + 1):                       # low cells 1..h
            opts.append((("low", p), (p, p)))
        for p in range(max(h + 1, n - h + 1), n + 1):   # high cells, no overlap with low
            opts.append((("high", p), (p, p)))
        if not opts:                                    # degenerate (n==0); keep full box
            opts = [("I", (1, n))]
        dim_opts.append(opts)

    combos = sorted(
        itertools.product(*[range(len(o)) for o in dim_opts]),
        key=lambda c: sum(1 for pos, i in enumerate(c) if dim_opts[pos][i][0] != "I"))

    regions, values = [], []
    for combo in combos:
        rng, value = [], copy.deepcopy(interior)
        for pos in range(ndim):
            tag, (lo, hi) = dim_opts[pos][combo[pos]]
            rng.append([lo, hi])
            if tag != "I":
                side, cell = tag
                n = sizes[dims[pos]][0]
                b = _bc(bc_by_side, dims[pos], side)
                value = _ghost_subst_cell(value, state, pos, ndim, cell, n,
                                          b["kind"], b["value"], dims[pos])
        regions.append(rng)
        values.append(value)
    return regions, values


def _observed_exprs(model: Dict[str, Any]) -> Dict[str, Any]:
    """Collect inline-able algebraic definitions (name -> expression).

    Covers the variable-level ``expression`` form (e.g. the level-set's
    ``psi_x = grad(psi, x)``) and **any** algebraic equation whose LHS is a bare
    variable name — regardless of the variable's declared ``type``. The latter is
    essential for observed-only components like RothermelFireSpread, whose 27
    algebraic unknowns are typed ``state`` but defined by ``var = expr`` (no time
    derivative); they must be inlined, not left as undefined states.
    """
    obs: Dict[str, Any] = {}
    for name, v in model.get("variables", {}).items():
        if v.get("type") == "observed" and v.get("expression") is not None:
            obs[name] = v["expression"]
    for eq in model.get("equations", []):
        lhs = eq.get("lhs")
        if isinstance(lhs, str):              # algebraic definition: var = expr
            obs[lhs] = eq["rhs"]
    return obs


def _resolve_observed(name, raw, cache, stack):
    if name in cache:
        return cache[name]
    if name in stack:
        raise SpatialDiscretizeError(f"cyclic observed dependency at {name!r}")
    resolved = _inline_observeds(raw[name], raw, cache, stack | {name})
    cache[name] = resolved
    return resolved


def _inline_observeds(expr, raw, cache, stack):
    """Substitute observed-variable names with their (recursively resolved)
    expressions, so spatial operators surface inline for discretization."""
    def f(n):
        if isinstance(n, str) and n in raw:
            return _resolve_observed(n, raw, cache, stack)
        return n
    return _map_expr(expr, f)


def _lhs_state(lhs, state_names) -> Optional[str]:
    if isinstance(lhs, dict) and lhs.get("op") == "D" and lhs.get("args"):
        a = lhs["args"][0]
        if isinstance(a, str) and a in state_names:
            return a
        if isinstance(a, dict) and a.get("op") == "index" and a["args"][0] in state_names:
            return a["args"][0]
    return None


def spatial_discretize(esm: Dict[str, Any], gdd: Dict[str, Any]) -> Dict[str, Any]:
    """Return a spatially-discretized copy of ``esm`` under the GDD.

    Each model with a spatial domain has its GDD-mapped spatial operators lowered
    to ArrayOp stencils (with ghost-region BCs), yielding an ODE system runnable
    by :func:`earthsci_toolkit.simulate`. Rule selection is entirely the GDD's —
    this function contains no stencil coefficients and no operator special-cases.
    """
    rules = _gdd_rules(gdd)
    out = copy.deepcopy(esm)
    domains = out.get("domains", {})
    for model in out.get("models", {}).values():
        dom = model.get("domain")
        if not dom or dom not in domains:
            continue
        domain = domains[dom]
        dims = list((domain.get("spatial") or {}).keys())
        if not dims:
            continue
        bc_by_side = _bcs_by_side(model, domain, dims)
        sizes = _grid_sizes(domain, dims, bc_by_side)
        ranges = {d: [1, sizes[d][0]] for d in dims}
        dx_by_dim = {d: sizes[d][1] for d in dims}

        state_names = [n for n, v in model.get("variables", {}).items()
                       if v.get("type") == "state"]
        for n in state_names:
            model["variables"][n]["shape"] = list(dims)

        # Observed spatial sub-expressions (e.g. psi_x = grad(psi,x)) are inlined
        # into each state PDE's RHS so their operators discretize in place; the
        # observed variables are then dropped from the discretized model.
        obs_raw = _observed_exprs(model)
        obs_cache: Dict[str, Any] = {}

        new_eqs = []
        for eq in model.get("equations", []):
            state = _lhs_state(eq["lhs"], state_names)
            if state is None:
                continue  # observed/algebraic defn — folded in by inlining
            inlined = _inline_observeds(eq["rhs"], obs_raw, obs_cache, set())
            rhs = _apply_gdd_rules(_expand_laplacian(inlined, dims), rules, dims, dx_by_dim)
            regions, values = _make_regions(rhs, state, dims, sizes, bc_by_side)
            new_eqs.append({
                "lhs": {"op": "arrayop", "args": [], "output_idx": list(dims),
                        "expr": {"op": "D", "args": [{"op": "index", "args": [state] + list(dims)}],
                                 "wrt": "t"}, "ranges": ranges},
                "rhs": {"op": "arrayop", "args": [], "output_idx": list(dims),
                        "expr": {"op": "index", "args": [{"op": "makearray", "args": [],
                                 "regions": regions, "values": values}] + list(dims)},
                        "ranges": ranges},
            })
        model["equations"] = new_eqs
        model["variables"] = {n: v for n, v in model["variables"].items()
                              if n not in obs_raw}
        model["system_kind"] = "ode"
        model.pop("domain", None)
    return out
