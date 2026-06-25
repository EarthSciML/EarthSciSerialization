"""Discretize a spatial PDE component into an ArrayOp ODE system (method of lines).

This is the Python counterpart to the Julia binding's ``build_ode_problem``: it
turns a continuous PDE component (state fields plus equations carrying spatial
operators ``grad`` / ``d2`` / ``laplacian`` over a Cartesian uniform grid) into a
discretized system whose equations are ``arrayop`` stencils over grid-indexed
state — the form ``earthsci_toolkit.simulation.simulate`` already integrates via
its ArrayOp dispatch path.

Pipeline (single-pathway compliant — no parallel evaluator):

1. Read each PDE model's domain: spatial dimensions (``min`` / ``max`` /
   ``grid_spacing``) and boundary conditions.
2. Expand ``laplacian`` to a sum of per-dimension ``d2`` operators, then rewrite
   every ``grad`` / ``d2`` node into a centered 2nd-order pointwise stencil using
   the rule engine (``rule_engine.rewrite``). The grid spacing is baked in as a
   literal per dimension.
3. Lower boundary conditions into ``makearray`` ghost regions: an interior region
   plus, for every face / edge / corner, a region that substitutes the
   out-of-bounds neighbour read (Dirichlet → the boundary value; zero-gradient /
   Neumann → a reflected in-bounds read). Regions are emitted least-specific
   first so the ArrayOp runtime's last-wins overwrite resolves corners correctly.
4. Emit a discretized ``.esm`` document: ``state`` fields gain a ``shape`` of the
   spatial index names; each equation becomes ``D(u[idx]) = arrayop[idx](...)``.

Supported today: 1-D and N-D Cartesian uniform grids; ``dirichlet``/``constant``
and ``zero_gradient``/``neumann`` boundary conditions; ``grad`` (1st), ``d2``
(2nd), and ``laplacian`` operators. Non-uniform grids, periodic BCs, and
curvilinear families are out of scope (the Julia ``build_ode_problem`` covers
them).
"""

from __future__ import annotations

import copy
import itertools
from typing import Any, Dict, List, Optional, Tuple

from .rule_engine import parse_rule, rewrite, _parse_expr
from .esm_types import ExprNode


class DiscretizePDEError(Exception):
    """Raised when a PDE component cannot be discretized by this driver."""


# --- centered 2nd-order stencil rules (mirror ESD's finite_difference catalog) ---
_GRAD_RULE = parse_rule(
    {
        "name": "centered_2nd_grad",  # grad(u,x) -> (u[x+1]-u[x-1])/(2 dx)
        "pattern": {"op": "grad", "args": ["$u"], "dim": "$x"},
        "replacement": {
            "op": "arrayop", "output_idx": ["$x"], "args": ["$u"],
            "expr": {"op": "/", "args": [
                {"op": "-", "args": [
                    {"op": "index", "args": ["$u", {"op": "+", "args": ["$x", 1]}]},
                    {"op": "index", "args": ["$u", {"op": "-", "args": ["$x", 1]}]},
                ]},
                {"op": "*", "args": [2, "__dx__"]},
            ]},
        },
    }
)
_D2_RULE = parse_rule(
    {
        "name": "centered_2nd_d2",  # d2(u,x) -> (u[x-1]-2u[x]+u[x+1])/dx^2
        "pattern": {"op": "d2", "args": ["$u"], "dim": "$x"},
        "replacement": {
            "op": "arrayop", "output_idx": ["$x"], "args": ["$u"],
            "expr": {"op": "/", "args": [
                {"op": "+", "args": [
                    {"op": "index", "args": ["$u", {"op": "-", "args": ["$x", 1]}]},
                    {"op": "*", "args": [-2, {"op": "index", "args": ["$u", "$x"]}]},
                    {"op": "index", "args": ["$u", {"op": "+", "args": ["$x", 1]}]},
                ]},
                {"op": "*", "args": ["__dx__", "__dx__"]},
            ]},
        },
    }
)

_EXPR_CHILD_KEYS = ("args", "values")


def _map_expr(node: Any, fn) -> Any:
    """Apply ``fn`` post-order to every sub-expression of a JSON AST node.

    ``fn(node)`` is called with each node after its children are mapped; it
    returns the (possibly replaced) node. Recurses through ``args`` (list),
    ``values`` (list), and ``expr`` (single).
    """
    if isinstance(node, dict):
        new = dict(node)
        for k in _EXPR_CHILD_KEYS:
            if isinstance(new.get(k), list):
                new[k] = [_map_expr(a, fn) for a in new[k]]
        if "expr" in new and new["expr"] is not None:
            new["expr"] = _map_expr(new["expr"], fn)
        return fn(new)
    if isinstance(node, list):
        return [_map_expr(a, fn) for a in node]
    return fn(node)


def _to_json(e: Any) -> Any:
    """Serialize an ExprNode tree back to plain JSON."""
    if isinstance(e, ExprNode):
        d: Dict[str, Any] = {"op": e.op}
        if e.args is not None:
            d["args"] = [_to_json(a) for a in e.args]
        for f in ("wrt", "dim", "fn", "output_idx", "reduce", "ranges",
                  "regions", "shape", "perm", "axis"):
            v = getattr(e, f, None)
            if v is not None:
                d[f] = v
        if e.expr is not None:
            d["expr"] = _to_json(e.expr)
        if e.values is not None:
            d["values"] = [_to_json(x) for x in e.values]
        return d
    return e


def _subst_symbol(node: Any, name: str, value: Any) -> Any:
    """Replace every bare-symbol occurrence of ``name`` with ``value``."""
    def f(n):
        return value if n == name else n
    return _map_expr(node, f)


def _expand_laplacian(expr: Any, dims: List[str]) -> Any:
    def f(n):
        if isinstance(n, dict) and n.get("op") == "laplacian":
            u = n["args"][0]
            terms = [{"op": "d2", "args": [u], "dim": d} for d in dims]
            return terms[0] if len(terms) == 1 else {"op": "+", "args": terms}
        return n
    return _map_expr(expr, f)


def _lift_index_to_nd(body: Any, state: str, dim: str, dims: List[str]) -> Any:
    """Lift a 1-D stencil's single-subscript reads to the full N-D index tuple.

    The catalog stencil rules are 1-D: they emit ``index(u, x±1)``. On a field
    ``u[x, y, …]`` a derivative along ``x`` must preserve the other indices, so
    ``index(u, x±1)`` becomes ``index(u, x±1, y, …)`` with the operated subscript
    in ``dim``'s slot and bare dimension names elsewhere.
    """
    if len(dims) == 1:
        return body
    pos = dims.index(dim)

    def f(n):
        if (isinstance(n, dict) and n.get("op") == "index"
                and n.get("args") and n["args"][0] == state and len(n["args"]) == 2):
            k = n["args"][1]
            full = [state] + [(k if i == pos else d) for i, d in enumerate(dims)]
            return {"op": "index", "args": full}
        return n
    return _map_expr(body, f)


def _rewrite_spatial_ops(expr: Any, dx_by_dim: Dict[str, float],
                         dims: List[str]) -> Any:
    """Replace grad/d2 nodes with their pointwise centered stencils (post-order)."""
    def f(n):
        if isinstance(n, dict) and n.get("op") in ("grad", "d2"):
            op, dim = n["op"], n.get("dim")
            if dim not in dx_by_dim:
                raise DiscretizePDEError(f"{op} over unknown spatial dim {dim!r}")
            operand = n["args"][0]
            if not isinstance(operand, str):
                raise DiscretizePDEError(
                    f"{op} operand must be a bare state field (got {operand!r}); "
                    "nested spatial operators are out of scope for this driver"
                )
            rule = _GRAD_RULE if op == "grad" else _D2_RULE
            lowered = rewrite(_parse_expr(n), [rule])
            body = _to_json(lowered.expr)
            body = _subst_symbol(body, "__dx__", float(dx_by_dim[dim]))
            return _lift_index_to_nd(body, operand, dim, dims)
        return n
    return _map_expr(expr, f)


def _ghost_subst(expr: Any, state: str, pos: int, ndim: int, side: str,
                 bc_kind: str, bc_value: float, dim: str) -> Any:
    """Substitute the out-of-bounds neighbour read for one (dim, side) boundary."""
    target = {"op": ("+" if side == "high" else "-"), "args": [dim, 1]}

    def f(n):
        if (isinstance(n, dict) and n.get("op") == "index"
                and n.get("args") and n["args"][0] == state):
            subs = n["args"][1:]
            if len(subs) == ndim and subs[pos] == target:
                if bc_kind in ("dirichlet", "constant"):
                    return float(bc_value)
                new_subs = list(subs)
                new_subs[pos] = dim            # zero-gradient / neumann: reflect
                return {"op": "index", "args": [state] + new_subs}
        return n
    return _map_expr(expr, f)


def _spatial_dims(domain: Dict[str, Any]) -> List[str]:
    return list((domain.get("spatial") or {}).keys())


_BC_ALIAS = {"zero_gradient": "neumann", "constant": "dirichlet"}
_DEFAULT_BC = {"kind": "dirichlet", "value": 0.0}


def _bcs_by_side(model: Dict[str, Any], domain: Dict[str, Any],
                 dims: List[str]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """Map (dim, "low"|"high") -> {kind, value}, supporting both schemas.

    Model-level (v0.2.0+, preferred): ``boundary_conditions`` keyed by id, each
    ``{side: "<dim>min"|"<dim>max", kind, value?}``. Domain-level (v0.1.0,
    deprecated): ``boundary_conditions`` list of ``{type, dimensions, value?}``
    applied to both sides of each named dimension.
    """
    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    model_bcs = model.get("boundary_conditions") or {}
    if isinstance(model_bcs, dict) and model_bcs:
        for bc in model_bcs.values():
            side = str(bc.get("side", ""))
            dim, end = _split_side(side, dims)
            if dim is None:
                continue
            kind = _BC_ALIAS.get(bc.get("kind"), bc.get("kind", "dirichlet"))
            out[(dim, end)] = {"kind": kind, "value": float(bc.get("value", 0.0))}
    for bc in domain.get("boundary_conditions", []) or []:
        kind = _BC_ALIAS.get(bc.get("type"), bc.get("type", "dirichlet"))
        value = float(bc.get("value", 0.0))
        for d in bc.get("dimensions", []):
            for end in ("low", "high"):
                out.setdefault((d, end), {"kind": kind, "value": value})
    return out


def _split_side(side: str, dims: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """`"xmin"` -> ("x", "low"); `"xmax"` -> ("x", "high")."""
    for end, suffix in (("low", "min"), ("high", "max")):
        if side.endswith(suffix):
            dim = side[: -len(suffix)]
            if dim in dims:
                return dim, end
    return None, None


def _bc(bc_by_side, dim, end):
    return bc_by_side.get((dim, end), _DEFAULT_BC)


def _grid_sizes(domain: Dict[str, Any], dims: List[str], bc_by_side):
    """Per spatial dim: (N_interior, dx). A Dirichlet side drops its endpoint;
    a zero-gradient side keeps it."""
    out: Dict[str, Tuple[int, float]] = {}
    spatial = domain.get("spatial") or {}
    for name in dims:
        spec = spatial[name]
        lo, hi, dx = spec["min"], spec["max"], spec["grid_spacing"]
        n_points = int(round((hi - lo) / dx)) + 1
        drop = sum(
            1 for end in ("low", "high")
            if _bc(bc_by_side, name, end)["kind"] in ("dirichlet", "constant")
        )
        out[name] = (n_points - drop, float(dx))
    return out


def _make_regions(interior_expr: Any, state: str, dims: List[str],
                  sizes: Dict[str, Tuple[int, float]],
                  bc_by_side: Dict[Tuple[str, str], Dict[str, Any]]):
    """Build (regions, values) for a makearray over the spatial grid.

    Emits one region per element of the 3^D product over {interior, low, high}
    per dim, least-specific (fewest boundary faces) first so last-wins overwrite
    resolves corners. Each region's value substitutes ghosts for its boundary
    faces.
    """
    ndim = len(dims)
    combos = list(itertools.product(("I", "L", "H"), repeat=ndim))
    combos.sort(key=lambda c: sum(s != "I" for s in c))  # interior first

    regions: List[List[List[int]]] = []
    values: List[Any] = []
    for combo in combos:
        rng: List[List[int]] = []
        value = copy.deepcopy(interior_expr)
        for pos, (dim, s) in enumerate(zip(dims, combo)):
            n = sizes[dim][0]
            if s == "I":
                rng.append([1, n])
            elif s == "L":
                rng.append([1, 1])
                bc = _bc(bc_by_side, dim, "low")
                value = _ghost_subst(value, state, pos, ndim, "low",
                                     bc["kind"], bc["value"], dim)
            else:  # "H"
                rng.append([n, n])
                bc = _bc(bc_by_side, dim, "high")
                value = _ghost_subst(value, state, pos, ndim, "high",
                                     bc["kind"], bc["value"], dim)
        regions.append(rng)
        values.append(value)
    return regions, values


def discretize_pde(esm: Dict[str, Any]) -> Dict[str, Any]:
    """Return a discretized copy of ``esm`` (a parsed ``.esm`` dict).

    Every model that declares a spatial domain has its ``grad`` / ``d2`` /
    ``laplacian`` operators lowered to ArrayOp stencils with ghost-region BC
    handling, producing an ODE system runnable by ``simulate``.
    """
    out = copy.deepcopy(esm)
    domains = out.get("domains", {})
    for mname, model in out.get("models", {}).items():
        dom_name = model.get("domain")
        if not dom_name or dom_name not in domains:
            continue
        domain = domains[dom_name]
        dims = _spatial_dims(domain)
        if not dims:
            continue
        bc_by_side = _bcs_by_side(model, domain, dims)
        sizes = _grid_sizes(domain, dims, bc_by_side)
        ranges = {d: [1, sizes[d][0]] for d in dims}
        dx_by_dim = {d: sizes[d][1] for d in dims}

        # State fields on this domain become array-valued over the spatial dims.
        state_names = [n for n, v in model.get("variables", {}).items()
                       if v.get("type") == "state"]
        for n in state_names:
            model["variables"][n]["shape"] = list(dims)

        new_eqs = []
        for eq in model.get("equations", []):
            lhs, rhs = eq["lhs"], eq["rhs"]
            state = _lhs_state(lhs, state_names)
            if state is None:
                new_eqs.append(eq)
                continue
            # interior pointwise stencil
            rhs_e = _expand_laplacian(rhs, dims)
            interior = _rewrite_spatial_ops(rhs_e, dx_by_dim, dims)
            regions, values = _make_regions(interior, state, dims, sizes, bc_by_side)
            idx_args = [state] + list(dims)
            new_eqs.append({
                "lhs": {
                    "op": "arrayop", "args": [], "output_idx": list(dims),
                    "expr": {"op": "D",
                             "args": [{"op": "index", "args": idx_args}], "wrt": "t"},
                    "ranges": ranges,
                },
                "rhs": {
                    "op": "arrayop", "args": [], "output_idx": list(dims),
                    "expr": {"op": "index",
                             "args": [{"op": "makearray", "args": [],
                                       "regions": regions, "values": values}] + list(dims)},
                    "ranges": ranges,
                },
            })
        model["equations"] = new_eqs
        model["system_kind"] = "ode"
        model.pop("domain", None)
    return out


def _lhs_state(lhs: Dict[str, Any], state_names: List[str]) -> Optional[str]:
    """Return the state name a ``D(u)/dt`` LHS differentiates, else None."""
    n = lhs
    if isinstance(n, dict) and n.get("op") == "D" and n.get("args"):
        a = n["args"][0]
        if isinstance(a, str) and a in state_names:
            return a
        if isinstance(a, dict) and a.get("op") == "index" and a["args"][0] in state_names:
            return a["args"][0]
    return None
