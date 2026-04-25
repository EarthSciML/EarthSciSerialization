"""
Closed function registry — Python implementation (esm-tzp / esm-4ia).

Implements the spec-defined closed function set from esm-spec §9.2:

* ``datetime.year``, ``month``, ``day``, ``hour``, ``minute``, ``second``,
  ``day_of_year``, ``julian_day``, ``is_leap_year`` — proleptic-Gregorian
  calendar decomposition of an IEEE-754 ``binary64`` UTC scalar
  (seconds since the Unix epoch, no leap-second consultation).
* ``interp.searchsorted`` — 1-based search-into-sorted-array (Julia's
  ``searchsortedfirst`` semantics with explicit out-of-range / NaN /
  duplicate behavior pinned by spec).

The set is **closed**: callers MUST reject any ``fn``-op ``name`` outside this
list (diagnostic ``unknown_closed_function``). This module provides:

- :func:`closed_function_names` — the public closed-set as a ``set[str]``.
- :func:`evaluate_closed_function` — dispatch entry point used by the
  expression evaluators (``expression.py``, ``numpy_interpreter.py``).
- :func:`lower_enums` — load-time pass that resolves every ``enum`` op in an
  :class:`EsmFile` to a ``const`` integer per esm-spec §9.3.
- :class:`ClosedFunctionError` — error type carrying spec-defined diagnostic
  codes (``unknown_closed_function``, ``closed_function_overflow``,
  ``searchsorted_non_monotonic``, ``closed_function_arity``,
  ``searchsorted_nan_in_table``).

Calendar arithmetic uses Python's stdlib :mod:`datetime` with the
proleptic-Gregorian default; the v0.3.0 spec contract forbids leap-second
consultation, which :class:`datetime.datetime` already honors.
``datetime.julian_day`` is computed via the Fliegel–van Flandern (1968)
integer formula plus the fractional-day offset, giving ≤ 1 ulp agreement
with the spec reference computation.
"""

from __future__ import annotations

import math
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Sequence, Union

from .esm_types import EsmFile, ExprNode, Equation, Model, ReactionSystem


# ============================================================
# Errors
# ============================================================


class ClosedFunctionError(Exception):
    """Raised when the closed function registry contract is violated.

    The ``code`` attribute carries one of the stable diagnostic codes pinned
    by esm-spec §9.1–§9.2:

    - ``unknown_closed_function`` — ``fn``-op ``name`` is not in the v0.3.0 set.
    - ``closed_function_arity`` — wrong number of arguments for the named function.
    - ``closed_function_overflow`` — integer-typed result would overflow Int32.
    - ``searchsorted_non_monotonic`` — ``xs`` is not non-decreasing.
    - ``searchsorted_nan_in_table`` — ``xs`` contains a NaN entry.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"ClosedFunctionError({code}): {message}")
        self.code = code
        self.message = message


# ============================================================
# Closed function set
# ============================================================


_CLOSED_FUNCTION_NAMES: frozenset = frozenset({
    "datetime.year",
    "datetime.month",
    "datetime.day",
    "datetime.hour",
    "datetime.minute",
    "datetime.second",
    "datetime.day_of_year",
    "datetime.julian_day",
    "datetime.is_leap_year",
    "interp.searchsorted",
})


def closed_function_names() -> frozenset:
    """Return the v0.3.0 closed function set.

    Bindings MUST reject any ``fn``-op ``name`` not in this set. The set is
    intentionally narrow; new entries require a spec rev (esm-spec §9.1).
    """
    return _CLOSED_FUNCTION_NAMES


# Int32 boundaries — the spec pins integer outputs to signed 32-bit.
_INT32_MIN = -(1 << 31)
_INT32_MAX = (1 << 31) - 1


def _check_int32(name: str, v: int) -> int:
    if v < _INT32_MIN or v > _INT32_MAX:
        raise ClosedFunctionError(
            "closed_function_overflow",
            f"{name}: result {v} overflows Int32",
        )
    return v


def _expect_arity(name: str, args: Sequence[Any], n: int) -> None:
    if len(args) != n:
        raise ClosedFunctionError(
            "closed_function_arity",
            f"{name} expects {n} argument(s), got {len(args)}",
        )


def _to_datetime(t_utc: Any) -> datetime:
    """Convert a UTC scalar (seconds since Unix epoch) to a tz-aware datetime.

    Uses ``datetime.fromtimestamp(..., tz=timezone.utc)`` which honors the
    proleptic-Gregorian calendar and (per the spec contract) does not consult
    leap seconds.
    """
    seconds = float(t_utc)
    if not math.isfinite(seconds):
        raise ClosedFunctionError(
            "closed_function_arity",
            f"datetime.*: t_utc must be finite, got {seconds}",
        )
    # `datetime.fromtimestamp(..., tz=utc)` accepts negative values for
    # pre-epoch times on all supported platforms (CPython implements its own
    # proleptic-Gregorian arithmetic and does not delegate to libc gmtime).
    return datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)


def _trunc_div(a: int, b: int) -> int:
    """Truncated integer division (rounds toward zero), C/Julia ÷ semantics.

    Python's ``//`` is floor division — it disagrees with the C-style
    semantics the Fliegel–van Flandern (1968) formula assumes whenever the
    dividend is negative (e.g. ``(M − 14)`` for ``M ∈ [1, 12]``). Misusing
    ``//`` here produces JDN values that drift by 1–2 days from the spec.
    """
    q, r = divmod(a, b)
    if r != 0 and (a < 0) != (b < 0):
        q += 1
    return q


def _datetime_julian_day(t_utc: float) -> float:
    """Fliegel–van Flandern (1968) integer JDN + fractional-day offset.

    Returns a Float64 with ≤ 1 ulp agreement to the spec reference
    computation. The only floating-point operation in the inner formula is
    the final divide by 86400 (one rounded operation).
    """
    dt = _to_datetime(t_utc)
    y, m, d = dt.year, dt.month, dt.day
    a = _trunc_div(m - 14, 12)
    jdn = (
        _trunc_div(1461 * (y + 4800 + a), 4)
        + _trunc_div(367 * (m - 2 - 12 * a), 12)
        - _trunc_div(3 * _trunc_div(y + 4900 + a, 100), 4)
        + d
        - 32075
    )
    # JDN counts noon-to-noon; convert time-of-day seconds (since 00:00 UTC)
    # to a fractional offset relative to noon. The spec pins this offset as
    # `(time_of_day_seconds − 43200) / 86400` (esm-spec §9.2.1).
    seconds_in_day = math.fmod(float(t_utc), 86400.0)
    if seconds_in_day < 0:
        seconds_in_day += 86400.0
    return float(jdn) + (seconds_in_day - 43200.0) / 86400.0


def _is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


# Cumulative day-of-year for the start of each month (1-based; index 0 = Jan).
_DOY_CUMULATIVE_NORMAL = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
_DOY_CUMULATIVE_LEAP = (0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335)


def _day_of_year(dt: datetime) -> int:
    table = _DOY_CUMULATIVE_LEAP if _is_leap_year(dt.year) else _DOY_CUMULATIVE_NORMAL
    return table[dt.month - 1] + dt.day


def _interp_searchsorted(name: str, x: float, xs: Any) -> int:
    """``interp.searchsorted`` per esm-spec §9.2.2.

    1-based, left-side bias (smallest ``i`` with ``xs[i] ≥ x``); out-of-range
    below → 1, above → ``N+1``; NaN ``x`` → ``N+1``; NaN entries in ``xs``
    raise; non-monotonic ``xs`` raises.
    """
    if not isinstance(xs, (list, tuple)):
        raise ClosedFunctionError(
            "closed_function_arity",
            f"{name}: xs argument must be an array (got {type(xs).__name__})",
        )
    n = len(xs)
    if n == 0:
        # Empty table — extends "above-range → N+1" to N=0; the only consistent
        # extension that composes with `index`.
        return 1
    # Validate monotonicity + NaN-in-table once per call.
    prev = float("nan")
    for i, raw in enumerate(xs):
        v = float(raw)
        if math.isnan(v):
            raise ClosedFunctionError(
                "searchsorted_nan_in_table",
                f"{name}: xs[{i + 1}] is NaN; NaN entries in xs are forbidden",
            )
        if i > 0 and v < prev:
            raise ClosedFunctionError(
                "searchsorted_non_monotonic",
                f"{name}: xs is not non-decreasing (xs[{i + 1}]={v} < xs[{i}]={prev})",
            )
        prev = v
    # NaN x → N+1 (treated as "greater than every finite element").
    if math.isnan(x):
        return _check_int32(name, n + 1)
    # Linear scan for the smallest 1-based index with xs[i] ≥ x. The spec
    # mandates left-side bias on duplicates.
    for i in range(n):
        if float(xs[i]) >= x:
            return _check_int32(name, i + 1)
    return _check_int32(name, n + 1)


# ============================================================
# Dispatch
# ============================================================


def evaluate_closed_function(name: str, args: Sequence[Any]) -> Union[int, float]:
    """Dispatch a closed function call.

    ``name`` is the dotted-module spec name (e.g. ``"datetime.julian_day"``);
    ``args`` is a sequence of evaluated argument values. Integer-typed
    results are returned as :class:`int` (range-checked to Int32);
    float-typed results are :class:`float`.

    For ``interp.searchsorted`` the second argument MUST be the table (a
    list/tuple of numeric values) — the caller is responsible for extracting
    the array from a ``const``-op AST node before invoking this function.

    Raises :class:`ClosedFunctionError` on contract violations.
    """
    if name not in _CLOSED_FUNCTION_NAMES:
        raise ClosedFunctionError(
            "unknown_closed_function",
            f"`fn` name `{name}` is not in the v0.3.0 closed function "
            f"registry (esm-spec §9.2). Adding a primitive requires a spec rev.",
        )

    if name == "datetime.year":
        _expect_arity(name, args, 1)
        return _check_int32(name, _to_datetime(args[0]).year)
    if name == "datetime.month":
        _expect_arity(name, args, 1)
        return _to_datetime(args[0]).month
    if name == "datetime.day":
        _expect_arity(name, args, 1)
        return _to_datetime(args[0]).day
    if name == "datetime.hour":
        _expect_arity(name, args, 1)
        return _to_datetime(args[0]).hour
    if name == "datetime.minute":
        _expect_arity(name, args, 1)
        return _to_datetime(args[0]).minute
    if name == "datetime.second":
        _expect_arity(name, args, 1)
        return _to_datetime(args[0]).second
    if name == "datetime.day_of_year":
        _expect_arity(name, args, 1)
        return _day_of_year(_to_datetime(args[0]))
    if name == "datetime.julian_day":
        _expect_arity(name, args, 1)
        return _datetime_julian_day(float(args[0]))
    if name == "datetime.is_leap_year":
        _expect_arity(name, args, 1)
        return 1 if _is_leap_year(_to_datetime(args[0]).year) else 0
    if name == "interp.searchsorted":
        _expect_arity(name, args, 2)
        return _interp_searchsorted(name, float(args[0]), args[1])
    # Should be unreachable — `name in _CLOSED_FUNCTION_NAMES` covered above.
    raise ClosedFunctionError(
        "unknown_closed_function",
        f"internal: `fn` name `{name}` is in the registry but has no dispatch arm",
    )


# ============================================================
# `const` argument extraction
# ============================================================


def extract_const_array(node: Any) -> List[Any]:
    """Extract a const-op array argument as a flat Python list.

    The closed function ``interp.searchsorted`` takes an inline ``const``
    array as its second argument (see esm-spec §9.2.2). Evaluators need to
    pass the raw array — not a per-element-evaluated value — to the closed
    function dispatch. This helper unwraps ``{op: "const", value: [...]}``.
    """
    if isinstance(node, ExprNode) and node.op == "const":
        return list(node.value or [])
    if isinstance(node, (list, tuple)):
        return list(node)
    raise ClosedFunctionError(
        "closed_function_arity",
        "interp.searchsorted: xs argument must be an inline `const` array",
    )


# ============================================================
# Enum lowering — esm-spec §9.3
# ============================================================


def lower_enums(file: EsmFile) -> EsmFile:
    """Walk every expression tree in ``file`` and replace each ``enum`` op
    with a ``const`` integer per the file's ``enums`` block.

    After this pass runs, no ``enum``-op nodes remain in the in-memory
    representation.

    Validation (esm-spec §9.3):

    - An ``enum`` op naming an undeclared enum raises :class:`ValueError`
      with code ``unknown_enum``.
    - An ``enum`` op naming a symbol not declared under that enum raises
      with code ``unknown_enum_symbol``.

    Mutates ``file`` in place; returns the file for convenience.
    """
    enums: Dict[str, Dict[str, int]] = file.enums or {}
    for model in file.models.values():
        _lower_model(model, enums)
    for rs in file.reaction_systems.values():
        _lower_reaction_system(rs, enums)
    return file


def _lower_model(model: Model, enums: Dict[str, Dict[str, int]]) -> None:
    for vname, var in list(model.variables.items()):
        if var.expression is not None:
            new_expr = _lower_expr(var.expression, enums)
            if new_expr is not var.expression:
                model.variables[vname] = replace(var, expression=new_expr)
    new_eqs: List[Equation] = []
    for eq in model.equations:
        new_eqs.append(Equation(
            lhs=_lower_expr(eq.lhs, enums),
            rhs=_lower_expr(eq.rhs, enums),
            _comment=eq._comment,
        ))
    model.equations[:] = new_eqs
    new_init: List[Equation] = []
    for eq in model.initialization_equations:
        new_init.append(Equation(
            lhs=_lower_expr(eq.lhs, enums),
            rhs=_lower_expr(eq.rhs, enums),
            _comment=eq._comment,
        ))
    model.initialization_equations[:] = new_init
    for sub in model.subsystems.values():
        _lower_model(sub, enums)


def _lower_reaction_system(rs: ReactionSystem, enums: Dict[str, Dict[str, int]]) -> None:
    for r in rs.reactions:
        if r.rate_constant is not None:
            r.rate_constant = _lower_expr(r.rate_constant, enums)
    for sub in rs.subsystems.values():
        _lower_reaction_system(sub, enums)


def _lower_expr(node: Any, enums: Dict[str, Dict[str, int]]) -> Any:
    if not isinstance(node, ExprNode):
        return node
    if node.op == "enum":
        if len(node.args) != 2 or not all(isinstance(a, str) for a in node.args):
            raise ValueError(
                f"`enum` op expects exactly 2 string args (enum_name, symbol_name); "
                f"got {len(node.args)}: {node.args}"
            )
        enum_name, symbol_name = node.args[0], node.args[1]
        if enum_name not in enums:
            raise ValueError(
                f"unknown_enum: enum `{enum_name}` is not declared in the file's "
                f"`enums` block"
            )
        mapping = enums[enum_name]
        if symbol_name not in mapping:
            raise ValueError(
                f"unknown_enum_symbol: symbol `{symbol_name}` is not declared "
                f"under enum `{enum_name}`"
            )
        return ExprNode(op="const", args=[], value=mapping[symbol_name])
    # Recurse — rebuild only if a child changed.
    new_args = [_lower_expr(a, enums) for a in node.args]
    body = _lower_expr(node.expr, enums) if node.expr is not None else None
    new_values = (
        [_lower_expr(v, enums) for v in node.values]
        if node.values is not None
        else None
    )
    changed = (
        any(a is not b for a, b in zip(new_args, node.args))
        or body is not node.expr
        or (new_values is not None and any(
            a is not b for a, b in zip(new_values, node.values)
        ))
    )
    if not changed:
        return node
    return replace(node, args=new_args, expr=body, values=new_values)
