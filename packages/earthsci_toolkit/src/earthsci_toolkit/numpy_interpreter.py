"""
NumPy AST interpreter for array/tensor expression nodes.

This module provides a recursive evaluator for the ESM expression AST that
returns NumPy scalars or ndarrays. It is the Python counterpart of the Rust
``ndarray`` runtime and the Julia ``SymbolicUtils.ArrayOp`` path, and is used
by :mod:`earthsci_toolkit.simulation` when the flattened system contains any
array op (``arrayop``, ``makearray``, ``index``, ``broadcast``, ``reshape``,
``transpose``, ``concat``).

Design notes
------------
- The evaluator is driven by a tiny context containing the current state,
  parameters, observed values, and the flat-state layout (``{name: slice}``
  plus ``{name: shape}``). It views slices of the flat state vector as
  ndarrays of the appropriate shape.
- Index symbols inside an ``arrayop`` body are threaded through a ``locals``
  dict. The body is evaluated once per point in the output box; results are
  assembled into an output ndarray.
- For simple contraction bodies (``index(A, i, k) * index(B, k, j)`` with
  ``j``, ``k`` implicit / reduced) we fall through to the generic nested loop.
  An ``np.einsum`` fast path could be added later — the public API stays the
  same either way.
- Shapes are 1-based to match the schema's Julia heritage. When reading an
  element ``u[i]`` we subtract 1 from the declared integer index.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np

from .esm_types import Expr, ExprNode


Shape = Tuple[int, ...]


@dataclass
class EvalContext:
    """Runtime data passed to each recursive evaluation step."""

    state_layout: Dict[str, slice]
    state_shapes: Dict[str, Shape]
    param_values: Dict[str, float]
    observed_values: Dict[str, float]
    y: np.ndarray
    t: float
    locals: Dict[str, int] = field(default_factory=dict)


class NumpyInterpreterError(Exception):
    """Raised when an expression cannot be evaluated by the NumPy interpreter."""


def _as_array(x: Any) -> np.ndarray:
    if isinstance(x, np.ndarray):
        return x
    return np.asarray(x, dtype=float)


def _view_state_array(name: str, ctx: EvalContext) -> np.ndarray:
    """Return an ndarray view of ``name`` into the flat state vector."""
    sl = ctx.state_layout[name]
    shape = ctx.state_shapes[name]
    data = ctx.y[sl]
    if shape == ():
        return np.asarray(float(data[0]))
    return data.reshape(shape, order="C")


def _resolve_symbol(name: str, ctx: EvalContext) -> Union[float, np.ndarray]:
    """Resolve a bare name reference."""
    if name in ctx.locals:
        return float(ctx.locals[name])
    if name == "t":
        return float(ctx.t)
    if name in ctx.state_layout:
        return _view_state_array(name, ctx)
    if name in ctx.param_values:
        return float(ctx.param_values[name])
    if name in ctx.observed_values:
        return float(ctx.observed_values[name])
    try:
        return float(name)
    except Exception:
        raise NumpyInterpreterError(f"Unresolved symbol: {name!r}")


_SCALAR_FUNCS: Dict[str, Callable] = {
    "exp": np.exp,
    "log": np.log,
    "log10": np.log10,
    "sqrt": np.sqrt,
    "abs": np.abs,
    "sin": np.sin,
    "cos": np.cos,
    "tan": np.tan,
    "asin": np.arcsin,
    "acos": np.arccos,
    "atan": np.arctan,
    "floor": np.floor,
    "ceil": np.ceil,
    "sign": np.sign,
}


def _broadcast_fn(fn: str) -> Callable:
    table = {
        "+": np.add,
        "-": np.subtract,
        "*": np.multiply,
        "/": np.true_divide,
        "^": np.power,
        "**": np.power,
        "min": np.minimum,
        "max": np.maximum,
    }
    if fn not in table:
        raise NumpyInterpreterError(f"Unsupported broadcast fn: {fn}")
    return table[fn]


def eval_expr(expr: Expr, ctx: EvalContext) -> Union[float, np.ndarray]:
    """Recursively evaluate an ESM expression against ``ctx``.

    Returns a Python float for scalar results or a numpy ndarray for
    array-valued sub-expressions.
    """
    if isinstance(expr, (int, float)) and not isinstance(expr, bool):
        return float(expr)
    if isinstance(expr, bool):
        return float(expr)
    if isinstance(expr, str):
        return _resolve_symbol(expr, ctx)
    if not isinstance(expr, ExprNode):
        raise NumpyInterpreterError(f"Cannot evaluate expression of type {type(expr).__name__}")

    op = expr.op
    # --- scalar arithmetic / elementwise ---
    if op == "+":
        if not expr.args:
            return 0.0
        vals = [eval_expr(a, ctx) for a in expr.args]
        acc = vals[0]
        for v in vals[1:]:
            acc = acc + v
        return acc
    if op == "-":
        vals = [eval_expr(a, ctx) for a in expr.args]
        if len(vals) == 1:
            return -vals[0]
        acc = vals[0]
        for v in vals[1:]:
            acc = acc - v
        return acc
    if op == "*":
        if not expr.args:
            return 1.0
        vals = [eval_expr(a, ctx) for a in expr.args]
        acc = vals[0]
        for v in vals[1:]:
            acc = acc * v
        return acc
    if op == "/":
        if len(expr.args) != 2:
            raise NumpyInterpreterError("/ expects 2 args")
        a = eval_expr(expr.args[0], ctx)
        b = eval_expr(expr.args[1], ctx)
        return a / b
    if op in ("^", "**"):
        if len(expr.args) != 2:
            raise NumpyInterpreterError("^ expects 2 args")
        a = eval_expr(expr.args[0], ctx)
        b = eval_expr(expr.args[1], ctx)
        return a ** b
    if op in _SCALAR_FUNCS:
        if len(expr.args) != 1:
            raise NumpyInterpreterError(f"{op} expects 1 arg")
        v = eval_expr(expr.args[0], ctx)
        return _SCALAR_FUNCS[op](v)
    if op == "min":
        vals = [eval_expr(a, ctx) for a in expr.args]
        return np.minimum.reduce(vals) if len(vals) > 1 else vals[0]
    if op == "max":
        vals = [eval_expr(a, ctx) for a in expr.args]
        return np.maximum.reduce(vals) if len(vals) > 1 else vals[0]
    if op == "ifelse":
        if len(expr.args) != 3:
            raise NumpyInterpreterError("ifelse expects 3 args")
        cond = eval_expr(expr.args[0], ctx)
        a = eval_expr(expr.args[1], ctx)
        b = eval_expr(expr.args[2], ctx)
        return np.where(cond, a, b)
    if op in (">", "<", ">=", "<=", "==", "!="):
        if len(expr.args) != 2:
            raise NumpyInterpreterError(f"{op} expects 2 args")
        a = eval_expr(expr.args[0], ctx)
        b = eval_expr(expr.args[1], ctx)
        ops = {
            ">": np.greater,
            "<": np.less,
            ">=": np.greater_equal,
            "<=": np.less_equal,
            "==": np.equal,
            "!=": np.not_equal,
        }
        return ops[op](a, b).astype(float)
    if op == "D":
        # D() should have been routed out at the equation level. If we see it
        # here (e.g. inside an expression), treat it as evaluating the inner
        # expression — this is only reachable when the LHS contains D(...) and
        # simulation extracts what it's differentiating.
        if expr.args:
            return eval_expr(expr.args[0], ctx)
        return 0.0

    # --- array ops ---
    if op == "index":
        return _eval_index(expr, ctx)
    if op == "arrayop":
        return _eval_arrayop(expr, ctx)
    if op == "makearray":
        return _eval_makearray(expr, ctx)
    if op == "broadcast":
        return _eval_broadcast(expr, ctx)
    if op == "reshape":
        return _eval_reshape(expr, ctx)
    if op == "transpose":
        return _eval_transpose(expr, ctx)
    if op == "concat":
        return _eval_concat(expr, ctx)

    raise NumpyInterpreterError(f"Unsupported op in NumPy interpreter: {op!r}")


def _eval_index(expr: ExprNode, ctx: EvalContext) -> Union[float, np.ndarray]:
    if not expr.args:
        raise NumpyInterpreterError("index requires at least 1 arg (the array)")
    arr_val = eval_expr(expr.args[0], ctx)
    idxs = [eval_expr(a, ctx) for a in expr.args[1:]]
    if not isinstance(arr_val, np.ndarray):
        # Scalar passed through: if no indices, return it; otherwise that's an error.
        if not idxs:
            return float(arr_val)
        raise NumpyInterpreterError("index applied to scalar value")
    # 1-based -> 0-based.
    zero_idx = tuple(int(round(float(i))) - 1 for i in idxs)
    if len(zero_idx) != arr_val.ndim:
        # Allow row-level access on a 2D array with a single index (returns a row).
        # Otherwise treat as error.
        raise NumpyInterpreterError(
            f"index got {len(zero_idx)} indices for array of shape {arr_val.shape}"
        )
    return float(arr_val[zero_idx])


def _eval_arrayop(expr: ExprNode, ctx: EvalContext) -> np.ndarray:
    """Evaluate an arrayop body over its output index box.

    Returns an ndarray whose shape is the cartesian product of the ranges for
    each symbolic index in ``output_idx``. Reduction (``reduce``) over index
    symbols that appear in the body but not in ``output_idx`` is supported
    for the default sum reducer; a future fast path can lift common uniform
    contractions to ``np.einsum``.
    """
    if expr.expr is None:
        raise NumpyInterpreterError("arrayop requires an 'expr' body")
    output_idx = list(expr.output_idx or [])
    ranges = expr.ranges or {}

    out_syms: List[str] = [s for s in output_idx if isinstance(s, str)]
    for s in out_syms:
        if s not in ranges:
            raise NumpyInterpreterError(
                f"arrayop output index {s!r} has no declared range"
            )

    from .flatten import _expand_range  # local import to avoid cycle
    out_ranges = [_expand_range(ranges[s]) for s in out_syms]
    out_shape = tuple(len(r) for r in out_ranges)

    # Collect reduction indices (appear in ranges but not in output_idx).
    reduce_syms: List[str] = [s for s in ranges.keys() if s not in out_syms]
    red_ranges = [_expand_range(ranges[s]) for s in reduce_syms]
    reducer = expr.reduce or "+"

    out = np.zeros(out_shape, dtype=float)
    it = np.ndindex(*out_shape) if out_shape else [()]
    for multi_idx in it:
        local_binding: Dict[str, int] = {}
        for s, pos in zip(out_syms, multi_idx):
            local_binding[s] = out_ranges[out_syms.index(s)][pos]
        if not reduce_syms:
            prev = dict(ctx.locals)
            ctx.locals.update(local_binding)
            try:
                v = eval_expr(expr.expr, ctx)
            finally:
                ctx.locals = prev
            out[multi_idx] = float(v)
        else:
            acc: Optional[float] = None
            prev = dict(ctx.locals)
            try:
                ctx.locals.update(local_binding)
                for red_point in _cartesian(red_ranges):
                    for s, v in zip(reduce_syms, red_point):
                        ctx.locals[s] = v
                    val = float(eval_expr(expr.expr, ctx))
                    acc = _reduce_step(reducer, acc, val)
            finally:
                ctx.locals = prev
            out[multi_idx] = acc if acc is not None else 0.0
    return out


def _cartesian(lists: List[List[int]]) -> List[Tuple[int, ...]]:
    if not lists:
        return [()]
    result: List[Tuple[int, ...]] = [()]
    for lst in lists:
        result = [prev + (x,) for prev in result for x in lst]
    return result


def _reduce_step(op: str, acc: Optional[float], val: float) -> float:
    if acc is None:
        return val
    if op == "+":
        return acc + val
    if op == "*":
        return acc * val
    if op == "max":
        return max(acc, val)
    if op == "min":
        return min(acc, val)
    raise NumpyInterpreterError(f"Unsupported reduce: {op}")


def _eval_makearray(expr: ExprNode, ctx: EvalContext) -> np.ndarray:
    """Build a dense array from a list of region/value pairs."""
    regions = expr.regions or []
    values = expr.values or []
    if len(regions) != len(values):
        raise NumpyInterpreterError(
            f"makearray: regions/values length mismatch ({len(regions)} vs {len(values)})"
        )
    if not regions:
        raise NumpyInterpreterError("makearray requires at least one region")

    # Infer output shape from the union of region bounding boxes.
    ndim = len(regions[0])
    shape = [0] * ndim
    for region in regions:
        if len(region) != ndim:
            raise NumpyInterpreterError("makearray regions have inconsistent ndim")
        for d, (lo, hi) in enumerate(region):
            if hi > shape[d]:
                shape[d] = int(hi)
    out = np.zeros(tuple(shape), dtype=float)
    for region, value_expr in zip(regions, values):
        v = eval_expr(value_expr, ctx)
        slicer = tuple(slice(int(lo) - 1, int(hi)) for lo, hi in region)
        if isinstance(v, np.ndarray):
            out[slicer] = v
        else:
            out[slicer] = float(v)
    return out


def _eval_broadcast(expr: ExprNode, ctx: EvalContext) -> np.ndarray:
    """Element-wise combine operands under Julia-style broadcasting.

    Julia left-aligns shapes when broadcasting (trailing 1s are added to
    shorter shapes), whereas NumPy right-aligns. To match the Julia binding's
    semantics we pad every operand's shape with trailing 1s to the maximum
    rank, then combine via NumPy's own broadcasting. A ``(3,) .+ (1,3)``
    pair becomes ``(3,1) .+ (1,3) = (3,3)``.
    """
    fn_name = expr.fn or "+"
    fn = _broadcast_fn(fn_name)
    vals = [eval_expr(a, ctx) for a in expr.args]
    if not vals:
        raise NumpyInterpreterError("broadcast requires at least 1 arg")
    arrs = [_as_array(v) for v in vals]
    max_ndim = max(a.ndim for a in arrs) if arrs else 0
    aligned: List[np.ndarray] = []
    for a in arrs:
        if a.ndim < max_ndim:
            new_shape = list(a.shape) + [1] * (max_ndim - a.ndim)
            aligned.append(a.reshape(new_shape))
        else:
            aligned.append(a)
    result = aligned[0]
    for a in aligned[1:]:
        result = fn(result, a)
    return np.asarray(result, dtype=float)


def _eval_reshape(expr: ExprNode, ctx: EvalContext) -> np.ndarray:
    if not expr.args:
        raise NumpyInterpreterError("reshape requires at least 1 arg")
    v = eval_expr(expr.args[0], ctx)
    arr = _as_array(v)
    shape = expr.shape or []
    concrete_shape: List[int] = []
    for s in shape:
        if isinstance(s, int):
            concrete_shape.append(s)
        else:
            raise NumpyInterpreterError(
                f"reshape symbolic shape {s!r} not supported in NumPy interpreter"
            )
    # Julia uses column-major; NumPy is row-major by default. Use Fortran
    # ordering to match the Julia binding's reshape semantics.
    return np.asarray(arr, dtype=float).reshape(concrete_shape, order="F")


def _eval_transpose(expr: ExprNode, ctx: EvalContext) -> np.ndarray:
    if not expr.args:
        raise NumpyInterpreterError("transpose requires 1 arg")
    v = eval_expr(expr.args[0], ctx)
    arr = _as_array(v)
    if expr.perm is not None:
        return np.transpose(arr, axes=list(expr.perm))
    if arr.ndim <= 1:
        return arr.reshape(1, -1) if arr.ndim == 1 else arr
    return np.transpose(arr)


def _eval_concat(expr: ExprNode, ctx: EvalContext) -> np.ndarray:
    if not expr.args:
        raise NumpyInterpreterError("concat requires at least 1 arg")
    arrs = [np.atleast_1d(_as_array(eval_expr(a, ctx))) for a in expr.args]
    axis = expr.axis if expr.axis is not None else 0
    return np.concatenate(arrs, axis=axis)


def expr_contains_array_op(expr: Expr) -> bool:
    """Return True if ``expr`` contains any array op node."""
    if expr is None or isinstance(expr, (int, float, str)):
        return False
    if isinstance(expr, ExprNode):
        if expr.op in {
            "arrayop", "makearray", "index", "broadcast",
            "reshape", "transpose", "concat",
        }:
            return True
        for a in expr.args:
            if expr_contains_array_op(a):
                return True
        if expr.expr is not None and expr_contains_array_op(expr.expr):
            return True
        if expr.values is not None:
            for v in expr.values:
                if expr_contains_array_op(v):
                    return True
    return False
