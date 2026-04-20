"""Rule engine per discretization RFC §5.2.

Pattern-match rewriting over the ESM expression AST with typed pattern
variables, guards, non-linear matching (via canonical equality), and a
top-down fixed-point loop with per-pass sealing of rewritten subtrees.

Mirrors ``packages/EarthSciSerialization.jl/src/rule_engine.jl`` and
``packages/earthsci-toolkit-rs/src/rule_engine.rs``; byte-identical
output on the cross-binding rule-engine conformance fixtures is the
acceptance criterion.

The MVP supports only the inline ``replacement`` form; ``use:<scheme>``
(RFC §7.2.1) is deferred.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

from .canonicalize import canonical_json, CanonicalizeError
from .esm_types import Expr, ExprNode


class RuleEngineError(Exception):
    """Error raised by the rule engine.

    ``code`` carries one of the RFC §5.2 / §11 stable error codes:

    - ``E_RULES_NOT_CONVERGED`` — fixed-point loop exceeded ``max_passes``.
    - ``E_UNREWRITTEN_PDE_OP`` — a PDE op remained after rewriting on an
      equation not annotated ``passthrough: true``.
    - ``E_SCHEME_MISMATCH`` — reserved for the ``use:`` form (not emitted
      in the MVP).
    """

    def __init__(self, code: str, message: str):
        super().__init__(f"RuleEngineError({code}): {message}")
        self.code = code
        self.message = message


@dataclass
class Guard:
    """A single constraint on pattern-variable bindings (RFC §5.2.4)."""

    name: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Rule:
    """A rewrite rule (RFC §5.2)."""

    name: str
    pattern: Expr
    replacement: Expr
    where: List[Guard] = field(default_factory=list)
    region: Optional[str] = None


@dataclass
class RuleContext:
    """Context supplied to guard evaluation (RFC §5.2.4).

    - ``grids``: per-grid metadata. Each entry may carry ``spatial_dims``,
      ``periodic_dims``, ``nonuniform_dims`` (lists of strings).
    - ``variables``: per-variable metadata. Each entry may carry ``grid``,
      ``location``, ``shape``.
    """

    grids: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    variables: Dict[str, Dict[str, Any]] = field(default_factory=dict)


# ============================================================================
# Pattern variable detection
# ============================================================================


def _is_pvar_string(x: Any) -> bool:
    return isinstance(x, str) and len(x) >= 2 and x[0] == "$"


# ============================================================================
# Match
# ============================================================================


Bindings = Dict[str, Expr]


def match_pattern(pattern: Expr, expr: Expr) -> Optional[Bindings]:
    """Attempt to match ``pattern`` against ``expr``.

    On success returns a substitution mapping each pattern-variable name
    (including the leading ``$``) to the bound value. Bare-name bindings
    (for sibling fields like ``wrt`` or ``dim``) are stored as plain
    strings. On failure returns ``None``.
    """
    return _match(pattern, expr, {})


def _match(pat: Expr, expr: Expr, b: Bindings) -> Optional[Bindings]:
    if _is_pvar_string(pat):
        return _unify(pat, expr, b)  # type: ignore[arg-type]
    if isinstance(pat, bool):
        # Python bool is an int subclass; the AST does not carry booleans.
        return None
    if isinstance(pat, int):
        return b if (isinstance(expr, int) and not isinstance(expr, bool) and expr == pat) else None
    if isinstance(pat, float):
        return b if (isinstance(expr, float) and expr == pat) else None
    if isinstance(pat, str):
        return b if (isinstance(expr, str) and expr == pat) else None
    if isinstance(pat, ExprNode):
        if not isinstance(expr, ExprNode):
            return None
        if pat.op != expr.op:
            return None
        if len(pat.args) != len(expr.args):
            return None
        b2 = _match_sibling_name(pat.wrt, expr.wrt, b)
        if b2 is None:
            return None
        b2 = _match_sibling_name(pat.dim, expr.dim, b2)
        if b2 is None:
            return None
        for pa, ea in zip(pat.args, expr.args):
            b2 = _match(pa, ea, b2)
            if b2 is None:
                return None
        return b2
    return None


def _match_sibling_name(
    pat: Optional[str], val: Optional[str], b: Bindings
) -> Optional[Bindings]:
    if pat is None:
        return b if val is None else None
    if _is_pvar_string(pat):
        if val is None:
            return None
        return _unify(pat, val, b)
    return b if (val is not None and val == pat) else None


def _unify(pname: str, candidate: Expr, b: Bindings) -> Optional[Bindings]:
    if pname in b:
        try:
            prev_json = canonical_json(b[pname])
            new_json = canonical_json(candidate)
        except CanonicalizeError:
            return None
        return b if prev_json == new_json else None
    nb = dict(b)
    nb[pname] = candidate
    return nb


# ============================================================================
# Apply bindings
# ============================================================================


def apply_bindings(template: Expr, b: Bindings) -> Expr:
    """Substitute pattern variables in ``template`` with their bound values."""
    if _is_pvar_string(template):
        if template not in b:
            raise RuleEngineError(
                "E_PATTERN_VAR_UNBOUND",
                f"pattern variable {template} is not bound",
            )
        return b[template]
    if isinstance(template, ExprNode):
        new_args = [apply_bindings(a, b) for a in template.args]
        new_wrt = _apply_name_field(template.wrt, b)
        new_dim = _apply_name_field(template.dim, b)
        return replace(template, args=new_args, wrt=new_wrt, dim=new_dim)
    return template


def _apply_name_field(field_val: Optional[str], b: Bindings) -> Optional[str]:
    if field_val is None:
        return None
    if _is_pvar_string(field_val):
        if field_val not in b:
            raise RuleEngineError(
                "E_PATTERN_VAR_UNBOUND",
                f"pattern variable {field_val} is not bound",
            )
        v = b[field_val]
        if not isinstance(v, str):
            raise RuleEngineError(
                "E_PATTERN_VAR_TYPE",
                f"pattern variable {field_val} used in name-class field must "
                f"bind a bare name",
            )
        return v
    return field_val


# ============================================================================
# Guards (§5.2.4)
# ============================================================================


def check_guards(
    guards: Sequence[Guard], bindings: Bindings, ctx: RuleContext
) -> Optional[Bindings]:
    """Evaluate a guard list left-to-right, threading bindings."""
    b: Optional[Bindings] = bindings
    for g in guards:
        b = check_guard(g, b, ctx)  # type: ignore[arg-type]
        if b is None:
            return None
    return b


def check_guard(g: Guard, b: Bindings, ctx: RuleContext) -> Optional[Bindings]:
    """Evaluate a single guard per §5.2.4."""
    name = g.name
    if name == "var_has_grid":
        return _guard_var_has_grid(g, b, ctx)
    if name == "dim_is_spatial_dim_of":
        return _guard_dim_is_spatial_dim_of(g, b, ctx)
    if name == "dim_is_periodic":
        return _guard_dim_is_periodic(g, b, ctx)
    if name == "dim_is_nonuniform":
        return _guard_dim_is_nonuniform(g, b, ctx)
    if name == "var_location_is":
        return _guard_var_location_is(g, b, ctx)
    if name == "var_shape_rank":
        return _guard_var_shape_rank(g, b, ctx)
    raise RuleEngineError(
        "E_UNKNOWN_GUARD",
        f"unknown guard: {name} (§5.2.4 closed set)",
    )


def _resolve_name(b: Bindings, key: str) -> Optional[str]:
    v = b.get(key)
    return v if isinstance(v, str) else None


def _resolve_or_mark(g: Guard, b: Bindings, field_name: str):
    """Return (value, need_bind, pvar_name)."""
    v = g.params.get(field_name)
    if v is None:
        return (None, False, None)
    s = str(v)
    if _is_pvar_string(s):
        bound = _resolve_name(b, s)
        return (bound, bound is None, s)
    return (s, False, None)


def _bind_pvar_name(b: Bindings, pvar: str, name: str) -> Bindings:
    nb = dict(b)
    nb[pvar] = name
    return nb


def _guard_var_has_grid(g: Guard, b: Bindings, ctx: RuleContext) -> Optional[Bindings]:
    pvar = str(g.params["pvar"])
    var_name = _resolve_name(b, pvar)
    if var_name is None:
        return None
    meta = ctx.variables.get(var_name)
    if meta is None:
        return None
    actual = meta.get("grid")
    if actual is None:
        return None
    wanted, need_bind, pname = _resolve_or_mark(g, b, "grid")
    if need_bind:
        return _bind_pvar_name(b, pname, actual)  # type: ignore[arg-type]
    return b if wanted == actual else None


def _dim_name_from_pvar_or_literal(g: Guard, b: Bindings) -> Optional[str]:
    pvar = str(g.params["pvar"])
    name = _resolve_name(b, pvar)
    if name is not None:
        return name
    # §9.2.1 accepts a bare string in pvar (e.g. "x") — treat as literal.
    return None if _is_pvar_string(pvar) else pvar


def _guard_dim_is_spatial_dim_of(
    g: Guard, b: Bindings, ctx: RuleContext
) -> Optional[Bindings]:
    pvar = str(g.params["pvar"])
    dim_name = _resolve_name(b, pvar)
    if dim_name is None:
        return None
    grid, _, _ = _resolve_or_mark(g, b, "grid")
    if grid is None:
        return None
    meta = ctx.grids.get(grid)
    if meta is None:
        return None
    return b if dim_name in meta.get("spatial_dims", []) else None


def _guard_dim_is_periodic(
    g: Guard, b: Bindings, ctx: RuleContext
) -> Optional[Bindings]:
    dim_name = _dim_name_from_pvar_or_literal(g, b)
    if dim_name is None:
        return None
    grid, _, _ = _resolve_or_mark(g, b, "grid")
    if grid is None:
        return None
    meta = ctx.grids.get(grid)
    if meta is None:
        return None
    return b if dim_name in meta.get("periodic_dims", []) else None


def _guard_dim_is_nonuniform(
    g: Guard, b: Bindings, ctx: RuleContext
) -> Optional[Bindings]:
    dim_name = _dim_name_from_pvar_or_literal(g, b)
    if dim_name is None:
        return None
    grid, _, _ = _resolve_or_mark(g, b, "grid")
    if grid is None:
        return None
    meta = ctx.grids.get(grid)
    if meta is None:
        return None
    return b if dim_name in meta.get("nonuniform_dims", []) else None


def _guard_var_location_is(
    g: Guard, b: Bindings, ctx: RuleContext
) -> Optional[Bindings]:
    pvar = str(g.params["pvar"])
    var_name = _resolve_name(b, pvar)
    if var_name is None:
        return None
    target = str(g.params["location"])
    meta = ctx.variables.get(var_name)
    if meta is None:
        return None
    return b if meta.get("location") == target else None


def _guard_var_shape_rank(
    g: Guard, b: Bindings, ctx: RuleContext
) -> Optional[Bindings]:
    pvar = str(g.params["pvar"])
    var_name = _resolve_name(b, pvar)
    if var_name is None:
        return None
    want = int(g.params["rank"])
    meta = ctx.variables.get(var_name)
    if meta is None:
        return None
    shape = meta.get("shape")
    if shape is None:
        return None
    return b if len(shape) == want else None


# ============================================================================
# Rewriter (§5.2.5)
# ============================================================================


def rewrite(
    expr: Expr,
    rules: Sequence[Rule],
    ctx: Optional[RuleContext] = None,
    max_passes: int = 32,
) -> Expr:
    """Run the rule engine on ``expr`` per RFC §5.2.5.

    Each pass walks top-down, the first rule whose pattern matches fires,
    the rewritten subtree is sealed for the remainder of that pass, then
    walking continues with siblings. A pass that produces no rewrites
    terminates the loop. If ``max_passes`` is reached without convergence
    the engine raises ``RuleEngineError(E_RULES_NOT_CONVERGED)``.
    """
    if ctx is None:
        ctx = RuleContext()
    current = expr
    for _ in range(max_passes):
        state = {"changed": False}
        current = _rewrite_pass(current, rules, ctx, state)
        if not state["changed"]:
            return current
    raise RuleEngineError(
        "E_RULES_NOT_CONVERGED",
        f"rule engine did not converge within {max_passes} passes",
    )


def _rewrite_pass(
    expr: Expr,
    rules: Sequence[Rule],
    ctx: RuleContext,
    state: Dict[str, bool],
) -> Expr:
    for rule in rules:
        m = match_pattern(rule.pattern, expr)
        if m is None:
            continue
        m2 = check_guards(rule.where, m, ctx)
        if m2 is None:
            continue
        new_expr = apply_bindings(rule.replacement, m2)
        state["changed"] = True
        return new_expr
    if isinstance(expr, ExprNode):
        new_args = [_rewrite_pass(a, rules, ctx, state) for a in expr.args]
        return replace(expr, args=new_args)
    return expr


# ============================================================================
# JSON loading
# ============================================================================


def _parse_expr(v: Any) -> Expr:
    if isinstance(v, ExprNode):
        return v
    if isinstance(v, bool):
        raise RuleEngineError(
            "E_RULE_PARSE",
            "booleans are not valid in expression position",
        )
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return v
    if isinstance(v, str):
        return v
    if isinstance(v, Mapping):
        if "op" not in v:
            raise RuleEngineError(
                "E_RULE_PARSE", "expression object missing 'op' field"
            )
        op = str(v["op"])
        args_raw = v.get("args", [])
        args = [_parse_expr(a) for a in args_raw]
        wrt = v.get("wrt")
        dim = v.get("dim")
        return ExprNode(
            op=op,
            args=args,
            wrt=None if wrt is None else str(wrt),
            dim=None if dim is None else str(dim),
        )
    raise RuleEngineError(
        "E_RULE_PARSE", f"cannot parse expression of type {type(v).__name__}"
    )


def _parse_guard(obj: Mapping[str, Any]) -> Guard:
    if "guard" not in obj:
        raise RuleEngineError("E_RULE_PARSE", "guard object missing 'guard' field")
    name = str(obj["guard"])
    params: Dict[str, Any] = {}
    for k, v in obj.items():
        if k == "guard":
            continue
        params[str(k)] = v
    return Guard(name=name, params=params)


def parse_rule(obj: Mapping[str, Any], name: Optional[str] = None) -> Rule:
    """Build a :class:`Rule` from a decoded JSON object."""
    if name is None:
        if "name" not in obj:
            raise RuleEngineError("E_RULE_PARSE", "rule object missing 'name'")
        name = str(obj["name"])
    if "pattern" not in obj:
        raise RuleEngineError(
            "E_RULE_PARSE", f"rule {name}: missing 'pattern' field"
        )
    pat = _parse_expr(obj["pattern"])
    if "replacement" not in obj:
        raise RuleEngineError(
            "E_RULE_REPLACEMENT_MISSING",
            f"rule {name}: MVP supports only the 'replacement' form; "
            f"'use:' rules are deferred",
        )
    repl = _parse_expr(obj["replacement"])
    where_raw = obj.get("where")
    guards = [] if where_raw is None else [_parse_guard(g) for g in where_raw]
    region_raw = obj.get("region")
    region = None if region_raw is None else str(region_raw)
    return Rule(
        name=name, pattern=pat, replacement=repl, where=guards, region=region
    )


def parse_rules(obj: Any) -> List[Rule]:
    """Parse the ``rules`` section of a model into an ordered list.

    Accepts either the JSON-object-keyed-by-name form or the JSON-array
    form per RFC §5.2.5.
    """
    if isinstance(obj, list):
        return [parse_rule(r) for r in obj]
    if isinstance(obj, Mapping):
        return [parse_rule(v, name=str(k)) for k, v in obj.items()]
    raise RuleEngineError(
        "E_RULE_PARSE",
        f"cannot parse rules section of type {type(obj).__name__}",
    )


# ============================================================================
# Unrewritten PDE op check (§11 Step 7)
# ============================================================================


_PDE_OPS = frozenset({"grad", "div", "laplacian", "D", "bc"})


def check_unrewritten_pde_ops(expr: Expr) -> None:
    """Scan for leftover PDE ops and raise if any are found."""
    found = _find_pde_op(expr)
    if found is not None:
        raise RuleEngineError(
            "E_UNREWRITTEN_PDE_OP",
            f"equation still contains PDE op '{found}' after rewrite; "
            f"annotate the equation with 'passthrough: true' to opt out",
        )


def _find_pde_op(e: Expr) -> Optional[str]:
    if isinstance(e, ExprNode):
        if e.op in _PDE_OPS:
            return e.op
        for a in e.args:
            r = _find_pde_op(a)
            if r is not None:
                return r
    return None
