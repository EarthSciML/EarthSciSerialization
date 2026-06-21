"""Build-time value-invention front-door (Python binding).

Port of the Julia reference ``value_invention.jl`` (bead ess-3lj.1 → ess-3lj.2);
RFC ``semiring-faq-unified-ir`` §6.1 (cadence-partition) / §5.5 (determinism) /
§7.3 (edge enumeration); ``CONFORMANCE_SPEC.md`` §5.5 / §5.7.

A ``kind:"derived"`` index set whose ``from_faq`` names a value-invention
aggregate (an ``aggregate`` with ``distinct:true``, or whose body / ``key`` is
``skolem`` / ``rank``) is materialised here, ONCE at setup, off the per-step hot
path — the §6.1 CONST/DISCRETE materialisation point. The aggregate's keys are
evaluated over the build-time const-array factors and run through the
:mod:`earthsci_toolkit.relational` engine (skolem / distinct, §5.5 determinism);
the distinct set's cardinality is handed to the index-set resolver as the dense
extent ``[1, n]`` — exactly as the ``intersect_polygon`` clip-ring case resolves
a derived set from its materialised ring (§8.1), now generalised to the
relational engine. The value-invention outputs run off the per-step hot path and
are dropped from the ODE.

The pass runs on the RAW JSON model document (``model["models"][name]``), not the
typed IR: the value-invention vocabulary (the aggregate ``key``, the ``distinct``
flag) lives in fields the typed ``ExprNode`` does not consume (mirrors
:mod:`earthsci_toolkit.cadence`, which walks raw JSON for the same reason). The
materialised members are **byte-identical** across the Julia / Rust / Python
bindings (the M3 determinism goldens) because every emitted key is the canonical
Skolem tuple in §5.5.1 sorted total order.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

import numpy as np

from . import cadence
from . import relational


class ValueInventionError(Exception):
    """A value-invention build-time materialisation error (the Python analog of
    Julia's ``TreeWalkError`` value-invention codes)."""


# The relational body ops that mark a value-invention output (excluded from the
# ODE): mirrors Julia ``_VI_BODY_OPS``.
_VI_BODY_OPS = ("skolem", "rank", "distinct")


# --------------------------------------------------------------------------- #
# Detection — classify raw aggregate nodes (mirror of _vi_node_kind / _vi_detect)
# --------------------------------------------------------------------------- #


def _vi_node_kind(node: Any) -> str:
    """Classify a raw aggregate node's value-invention role.

    - ``"producer"`` — ``distinct:true`` (an index-set-producing aggregate;
      materialises a derived index set via ``from_faq``).
    - ``"map"``      — a per-element map whose body / key is ``skolem`` (e.g.
      ``src_bin[i] = skolem("bin", floor(...), floor(...))``): a value-invention
      buffer the producer's ``join`` / ``key`` references.
    - ``"exclude"``  — another value-invention output (e.g. a ``rank`` dense-id
      buffer) dropped from the ODE but needing no setup materialisation.
    - ``"none"``     — an ordinary numeric aggregate.
    """
    if not isinstance(node, Mapping):
        return "none"
    if node.get("op") != "aggregate":
        return "none"
    if node.get("distinct", False) is True:
        return "producer"
    body = node.get("expr")
    if isinstance(body, Mapping):
        bop = body.get("op")
        if bop == "skolem":
            return "map"
        if bop in _VI_BODY_OPS:
            return "exclude"
    key = node.get("key")
    if isinstance(key, Mapping) and key.get("op") == "skolem":
        return "map"
    return "none"


def _vi_lhs_base(lhs: Any) -> Optional[str]:
    """Base variable name written by a raw LHS node: ``name``,
    ``{op:index,args:[name,…]}`` or ``{op:D,args:[name,…]}``. ``None`` if
    unrecognised."""
    if isinstance(lhs, str):
        return lhs
    if isinstance(lhs, Mapping):
        op = lhs.get("op")
        if op in ("index", "D"):
            args = lhs.get("args") or []
            if args:
                return _vi_lhs_base(args[0])
    return None


def _vi_model_assignments(model_json: Mapping[str, Any]) -> List[Tuple[Any, Any]]:
    """Every (lhs, rhs) value-expression pair in a raw model: the equation list
    plus the ``expression`` of each observed variable."""
    out: List[Tuple[Any, Any]] = []
    for eq in model_json.get("equations", []) or []:
        out.append((eq.get("lhs"), eq.get("rhs")))
    for vname, v in (model_json.get("variables", {}) or {}).items():
        if isinstance(v, Mapping):
            expr = v.get("expression")
            if expr is not None:
                out.append((vname, expr))
    return out


@dataclass
class _Detection:
    has_vi: bool
    vi_var_names: Set[str]
    maps: List[Tuple[str, Any]]
    producers: List[Tuple[str, Any]]


def _vi_detect(model_json: Mapping[str, Any]) -> _Detection:
    """Scan a raw model for value-invention assignments. ``vi_var_names`` is the
    set of LHS variables produced by skolem/distinct/rank (excluded from the ODE,
    as the geometry clip-ring vars are); ``maps`` / ``producers`` are
    ``(lhs_base, node)`` pairs to materialise."""
    vi_var_names: Set[str] = set()
    maps: List[Tuple[str, Any]] = []
    producers: List[Tuple[str, Any]] = []
    for lhs, rhs in _vi_model_assignments(model_json):
        kind = _vi_node_kind(rhs)
        if kind == "none":
            continue
        base = _vi_lhs_base(lhs)
        if base is None:
            continue
        vi_var_names.add(base)  # every value-invention output leaves the ODE
        if kind == "producer":
            producers.append((base, rhs))
        elif kind == "map":
            maps.append((base, rhs))
    has_vi = bool(maps) or bool(producers)
    return _Detection(has_vi=has_vi, vi_var_names=vi_var_names, maps=maps, producers=producers)


# --------------------------------------------------------------------------- #
# Build-time evaluation context (mirror of _ViCtx)
# --------------------------------------------------------------------------- #


@dataclass
class _ViCtx:
    const_arrays: Dict[str, np.ndarray]
    params: Dict[str, float]
    index_sets: Dict[str, Any]
    variables: Dict[str, Any]
    # materialised map var → {output-index value → key value}
    maps: Dict[str, Dict[Any, Any]] = field(default_factory=dict)


def _vi_key_int(x: Any) -> int:
    """Coerce a build-time numeric to an exact integer relational key component
    (§5.5.1 rule 1: no floats in keys). A non-integral float is a misuse — fail
    loudly rather than emit a non-deterministic key."""
    if isinstance(x, bool):
        # ``bool`` is an ``int`` subclass; a boolean key component is 0/1.
        return int(x)
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        if not float(x).is_integer():
            raise ValueInventionError(
                f"value-invention key component {x!r} is not integer-valued; "
                f"relational keys must be integer / categorical IDs "
                f"(CONFORMANCE_SPEC.md §5.5.1 rule 1)"
            )
        return int(x)
    raise ValueInventionError(f"non-numeric key component {x!r}")


def _vi_param(ctx: _ViCtx, name: str) -> float:
    """Resolve a scalar parameter value (dx/dy/atol …) from overrides-or-default."""
    if name in ctx.params:
        return ctx.params[name]
    v = ctx.variables.get(name)
    if isinstance(v, Mapping):
        d = v.get("default")
        if d is not None:
            return float(d)
    raise ValueInventionError(
        f"value-invention scalar parameter {name!r} has no override or default"
    )


def _vi_eval(node: Any, ctx: _ViCtx, bindings: Dict[str, Any]) -> Any:
    """Evaluate a raw value-invention sub-expression. Returns an int / float /
    bool / str tag / tuple key, depending on the op."""
    if isinstance(node, bool):
        return node
    if isinstance(node, (int, np.integer)):
        return int(node)
    if isinstance(node, (float, np.floating)):
        return float(node)
    if isinstance(node, str):
        if node in bindings:
            return bindings[node]  # bound range symbol
        if node in ctx.const_arrays:
            return node  # bare factor name (used by index)
        v = ctx.variables.get(node)
        if isinstance(v, Mapping) and v.get("type") == "parameter":
            return _vi_param(ctx, node)  # scalar parameter
        return node  # relation tag ("edge"/"bin"/"pair")
    if isinstance(node, Mapping):
        op = node.get("op")
        args = node.get("args") or []
        if op == "index":
            return _vi_index(node, ctx, bindings)
        if op == "skolem":
            return _vi_skolem(node, ctx, bindings)
        if op == "true":
            return True
        if op == "false":
            return False
        if op == "floor":
            return int(np.floor(float(_vi_eval(args[0], ctx, bindings))))
        if op == "ceil":
            return int(np.ceil(float(_vi_eval(args[0], ctx, bindings))))
        if op == "/":
            return float(_vi_eval(args[0], ctx, bindings)) / float(_vi_eval(args[1], ctx, bindings))
        if op == "*":
            acc = 1.0
            for a in args:
                acc *= float(_vi_eval(a, ctx, bindings))
            return acc
        if op == "+":
            return sum(float(_vi_eval(a, ctx, bindings)) for a in args)
        if op == "-":
            if len(args) == 1:
                return -float(_vi_eval(args[0], ctx, bindings))
            return float(_vi_eval(args[0], ctx, bindings)) - float(_vi_eval(args[1], ctx, bindings))
        if op in ("<", ">", "<=", ">=", "==", "!="):
            a = float(_vi_eval(args[0], ctx, bindings))
            b = float(_vi_eval(args[1], ctx, bindings))
            if op == "<":
                return a < b
            if op == ">":
                return a > b
            if op == "<=":
                return a <= b
            if op == ">=":
                return a >= b
            if op == "==":
                return a == b
            return a != b
        raise ValueInventionError(
            f"value-invention build-time evaluator does not support op {op!r}"
        )
    raise ValueInventionError(f"unevaluable value-invention node {node!r}")


def _vi_index(node: Mapping[str, Any], ctx: _ViCtx, bindings: Dict[str, Any]) -> float:
    """``index(factor, i, …)``: gather from a const-array factor (1-based). The
    factor is build-time data supplied in ``const_arrays``."""
    args = node.get("args") or []
    name = args[0]
    if not isinstance(name, str) or name not in ctx.const_arrays:
        raise ValueInventionError(
            f"value-invention index target {name!r} must be a const-array factor"
        )
    arr = ctx.const_arrays[name]
    zero_idx = tuple(int(_vi_eval(a, ctx, bindings)) - 1 for a in args[1:])
    return arr[zero_idx]


def _vi_skolem(node: Mapping[str, Any], ctx: _ViCtx, bindings: Dict[str, Any]) -> Any:
    """``skolem(tag?, c1, c2, …)`` → the canonical key tuple. A leading STRING
    literal is the relation tag (the relation name) and is NOT part of the
    emitted key — this is what makes the materialised set byte-identical to the
    M3 determinism golden (edges ``[[1,2],…]``, candidate pairs ``(i,j)``), which
    carry no tag. The remaining components are exact integer IDs (§5.5.1 rule 4).
    A single component degrades to a scalar key."""
    comps = [_vi_eval(a, ctx, bindings) for a in (node.get("args") or [])]
    if comps and isinstance(comps[0], str):
        comps = comps[1:]  # strip the relation tag
    key = tuple(_vi_key_int(c) for c in comps)
    if len(key) == 1:
        return key[0]
    return key


# --------------------------------------------------------------------------- #
# Range resolution (mirror of _vi_order_syms / _vi_range_values / _vi_enumerate)
# --------------------------------------------------------------------------- #


def _vi_order_syms(ranges: Mapping[str, Any]) -> List[str]:
    """Order range symbols so a ragged range's ``of`` parents precede it (a stable
    topological order over the per-symbol ``of`` dependency)."""
    syms = list(ranges.keys())
    ordered: List[str] = []
    remaining = list(syms)
    while remaining:
        progressed = False
        for s in list(remaining):
            of = (ranges[s] or {}).get("of") or []
            if all((p in ordered) or (p not in syms) for p in of):
                ordered.append(s)
                remaining.remove(s)
                progressed = True
        if not progressed:
            raise ValueInventionError(
                f"value-invention ranges have a cyclic `of` dependency: {remaining}"
            )
    return ordered


def _vi_range_values(spec: Mapping[str, Any], ctx: _ViCtx, bindings: Dict[str, Any]) -> List[Any]:
    """The element values a range symbol binds to. interval/categorical → 1-based
    positions; ragged → the MEMBER values gathered from the set's ``values``
    factor sliced by its ``offsets`` factor (so a range symbol over
    ``face_vertices`` binds to the vertex IDs of the parent face, §5.2)."""
    frm = spec.get("from")
    iset = ctx.index_sets.get(frm)
    if iset is None:
        raise ValueInventionError(
            f"value-invention range references undeclared index set {frm!r}"
        )
    kind = iset.get("kind")
    if kind == "interval":
        return list(range(1, int(iset["size"]) + 1))
    if kind == "categorical":
        return list(range(1, len(iset.get("members") or []) + 1))
    if kind == "ragged":
        of = spec.get("of") or []
        if not of:
            raise ValueInventionError(
                f"ragged value-invention range {frm!r} needs an `of` parent"
            )
        parent = int(bindings[of[0]])
        offs = ctx.const_arrays[iset["offsets"]]
        vals = ctx.const_arrays[iset["values"]]
        nmem = int(offs[parent - 1])
        return [_vi_key_int(vals[parent - 1, l - 1]) for l in range(1, nmem + 1)]
    raise ValueInventionError(
        f"value-invention range over index set kind {kind!r} is unsupported"
    )


def _vi_enumerate(ranges: Mapping[str, Any], ctx: _ViCtx, cb) -> None:
    """Enumerate every full binding of an aggregate's ``ranges``, calling
    ``cb(bindings)`` at each leaf (bindings is reused — copy if retained)."""
    syms = _vi_order_syms(ranges)
    bindings: Dict[str, Any] = {}

    def rec(k: int) -> None:
        if k >= len(syms):
            cb(bindings)
            return
        s = syms[k]
        for v in _vi_range_values(ranges[s], ctx, bindings):
            bindings[s] = v
            rec(k + 1)
        bindings.pop(s, None)

    rec(0)


# --------------------------------------------------------------------------- #
# Materialisation (mirror of _vi_join_* / _vi_materialize_* )
# --------------------------------------------------------------------------- #


def _vi_join_index_sym(vname: str, producer_ranges: Mapping[str, Any], ctx: _ViCtx) -> str:
    """The index range symbol of a join-key variable within the producer's
    ranges: the producer range whose ``from`` equals the variable's (1-D) shape
    index set."""
    v = ctx.variables.get(vname)
    if v is None:
        raise ValueInventionError(f"join references unknown variable {vname!r}")
    shape = v.get("shape") or []
    if len(shape) != 1:
        raise ValueInventionError(
            f"value-invention join key {vname!r} must be a 1-D buffer; shape={shape}"
        )
    target = shape[0]
    for sym, spec in producer_ranges.items():
        if (spec or {}).get("from") == target:
            return sym
    raise ValueInventionError(
        f"no producer range binds the index set {target!r} of join key {vname!r}"
    )


def _vi_join_ok(join: Sequence[Any], producer_ranges: Mapping[str, Any],
                ctx: _ViCtx, bindings: Dict[str, Any]) -> bool:
    """True iff every ``join.on`` key-column pair compares equal at this binding
    (the value-equality equi-join gate, §5.3); each key is a materialised map
    buffer."""
    for clause in join:
        for pair in (clause.get("on") or []):
            lname, rname = pair[0], pair[1]
            ls = _vi_join_index_sym(lname, producer_ranges, ctx)
            rs = _vi_join_index_sym(rname, producer_ranges, ctx)
            lval = ctx.maps[lname][bindings[ls]]
            rval = ctx.maps[rname][bindings[rs]]
            if lval != rval:
                return False
    return True


def _vi_materialize_map(ctx: _ViCtx, vname: str, node: Mapping[str, Any]) -> Dict[Any, Any]:
    """Materialise a per-element value-invention map var → {output-index → value}."""
    output_idx = node.get("output_idx") or []
    if len(output_idx) != 1:
        raise ValueInventionError(
            f"value-invention map {vname!r} must have a single output index; got {output_idx}"
        )
    body = node.get("expr")
    if body is None:
        raise ValueInventionError(f"value-invention map {vname!r} has no `expr` body")
    out: Dict[Any, Any] = {}
    sym = str(output_idx[0])

    def visit(bindings: Dict[str, Any]) -> None:
        out[bindings[sym]] = _vi_eval(body, ctx, bindings)

    _vi_enumerate(node.get("ranges") or {}, ctx, visit)
    ctx.maps[vname] = out
    return out


def _vi_materialize_producer(ctx: _ViCtx, node: Mapping[str, Any]) -> List[Any]:
    """Materialise an index-set-producing aggregate → the distinct member set
    (§5.5 sorted total order, via the relational engine). Returns the member
    list."""
    key = node.get("key")
    if key is None:
        raise ValueInventionError(
            "value-invention producer aggregate requires a `key` (§5.5)"
        )
    ranges = node.get("ranges") or {}
    filt = node.get("filter")
    join = node.get("join")
    members: List[Any] = []

    def visit(bindings: Dict[str, Any]) -> None:
        if filt is not None:
            fv = _vi_eval(filt, ctx, bindings)
            if not (fv is True or (isinstance(fv, (int, float)) and not isinstance(fv, bool) and fv > 0)):
                return
        if join is not None and not _vi_join_ok(join, ranges, ctx, bindings):
            return
        members.append(_vi_skolem(key, ctx, bindings))

    _vi_enumerate(ranges, ctx, visit)
    return relational.distinct(members)


def _vi_classification_model(model_json: Mapping[str, Any],
                             maps: Sequence[Tuple[str, Any]]) -> Mapping[str, Any]:
    """A model copy whose value-invention MAP vars are re-typed to their body's
    cadence class (``const``→parameter, ``discrete``→discrete), so a producer
    joining on a map buffer classifies by the buffer's true (input-derived)
    cadence rather than the seed of its declared ``state`` kind (§6.1). A
    ``continuous`` body is left unchanged so the §5.7 guard still rejects
    state-dependent topology."""
    if not maps:
        return model_json
    variables = dict(model_json.get("variables", {}) or {})
    for vname, node in maps:
        if vname not in variables:
            continue
        body = node.get("expr")
        if body is None:
            continue
        bcls = cadence.classify(body, model_json)
        newtype = "parameter" if bcls == "const" else ("discrete" if bcls == "discrete" else None)
        if newtype is None:
            continue
        v = dict(variables[vname])
        v["type"] = newtype
        variables[vname] = v
    out = dict(model_json)
    out["variables"] = variables
    return out


# --------------------------------------------------------------------------- #
# Public entrypoint
# --------------------------------------------------------------------------- #


@dataclass
class ValueInventionResult:
    """Result of :func:`materialize_value_invention`.

    - ``extents`` — ``from_faq`` producer id → derived index-set cardinality (the
      dense extent ``[1, n]`` the resolver consumes).
    - ``members`` — ``from_faq`` producer id → the distinct member tuples in
      §5.5.1 sorted order (for byte-identity assertions).
    - ``vi_var_names`` — value-invention LHS vars to drop from the ODE.
    """

    extents: Dict[str, int] = field(default_factory=dict)
    members: Dict[str, List[Any]] = field(default_factory=dict)
    vi_var_names: Set[str] = field(default_factory=set)


def materialize_value_invention(
    model_json: Mapping[str, Any],
    const_arrays: Optional[Mapping[str, Any]] = None,
    params: Optional[Mapping[str, Any]] = None,
) -> ValueInventionResult:
    """Run the build-time value-invention engine over a raw model document.

    ``const_arrays`` supplies the build-time factor arrays (the connectivity /
    coordinates the keys are computed from); ``params`` supplies scalar parameter
    overrides. A producer that classifies CONTINUOUS is rejected (§5.7 guard 2).

    A no-op (empty result) for a model with no skolem/distinct/rank node — the
    evaluator front-door then behaves byte-identically to before.
    """
    const_arrays = const_arrays or {}
    params = params or {}
    det = _vi_detect(model_json)
    result = ValueInventionResult(vi_var_names=set(det.vi_var_names))
    if not det.has_vi:
        return result

    ctx = _ViCtx(
        const_arrays={str(k): np.asarray(v, dtype=float) for k, v in const_arrays.items()},
        params={str(k): float(v) for k, v in params.items()},
        index_sets=dict(model_json.get("index_sets", {}) or {}),
        variables=dict(model_json.get("variables", {}) or {}),
    )

    # Maps first (a producer's join / key may reference them).
    for vname, node in det.maps:
        _vi_materialize_map(ctx, vname, node)

    # Cadence classification model: re-type each map var to its body's class so
    # the §5.7 guard 2 below classifies a producer that joins on it correctly (a
    # CONST-derived bin map passes; a genuinely state-dependent one still
    # classifies CONTINUOUS → reject).
    cls_model = _vi_classification_model(model_json, det.maps)

    # ``from_faq`` id → derived index-set name (so we only materialise producers a
    # derived set actually names; geometry producers are handled elsewhere).
    faq_to_set: Dict[str, str] = {}
    for sname, iset in ctx.index_sets.items():
        if not isinstance(iset, Mapping) or iset.get("kind") != "derived":
            continue
        faq = iset.get("from_faq")
        if faq is not None:
            faq_to_set[str(faq)] = str(sname)

    for _, node in det.producers:
        node_id = node.get("id")
        if node_id is None:
            raise ValueInventionError(
                "value-invention producer aggregate requires an `id` naming it for `from_faq`"
            )
        node_id = str(node_id)
        if node_id not in faq_to_set:
            continue  # no derived set names this producer
        # §5.7 guard 2: a relational node may not run on the hot path.
        cls = cadence.classify(node, cls_model)
        if cls == "continuous":
            raise ValueInventionError(
                f"value-invention producer {node_id!r} classifies CONTINUOUS — it may not "
                f"run per step (RFC §5.7 guard 2); its inputs must be CONST/DISCRETE"
            )
        mem = _vi_materialize_producer(ctx, node)
        result.members[node_id] = mem
        result.extents[node_id] = len(mem)

    return result
