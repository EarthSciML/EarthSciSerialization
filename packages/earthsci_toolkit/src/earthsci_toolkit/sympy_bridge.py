"""SymPy bridge for the Python simulation tier.

Bridges ESM AST expressions to SymPy and compiles them to NumPy callables
via :func:`sympy.lambdify`. This module owns:

* :class:`_ess_numeric_abs` — the ``sp.Abs`` workaround that keeps
  lambdified RHS expressions in pure-real form (esm-5gk).
* :func:`_expr_to_sympy` — ESM ``Expr`` → SymPy expression.
* :func:`_flat_to_sympy_rhs` / :func:`_observed_to_sympy_value_exprs` —
  build per-state / per-observed SymPy expressions from a
  :class:`FlattenedSystem` with scalar algebraic-equation elimination.
* :class:`_CompiledRhs` and :func:`_compile_flat_rhs` — the lambdify +
  CSE compile that dominates ``simulate()`` wall time on large mechanisms.

``simulation.py`` imports from this module and handles the SciPy
``solve_ivp`` wiring, event handling, and array-op interpreter path.
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set, Tuple

import numpy as np
import sympy as sp

from .esm_types import Expr, ExprNode
from .flatten import FlattenedSystem
from .numpy_interpreter import (
    UnreachableSpatialOperatorError,
    _INTERP_CONST_ARG_POSITIONS,
)


class SimulationError(Exception):
    """Exception raised during the SymPy bridge or simulation.

    Defined here (rather than in ``simulation.py``) because the bridge
    itself raises it for malformed expressions and cyclic algebraic
    equations. ``simulation.py`` re-exports the name to keep the public
    ``earthsci_toolkit.simulation.SimulationError`` symbol stable.
    """
    pass


class _ess_numeric_abs(sp.Function):
    """``|x|`` with construction-time canonical rewrites disabled (esm-5gk).

    SymPy's ``sp.Abs.eval`` applies decompositions like
    ``Abs(exp(z) * w) → exp(re(z)) * Abs(w)`` and ``Abs(0.41**((log(N*T**(-8))
    - C)**2 + 1)) → 0.41**((log|...|**2 - arg(...)**2)/log10**2 + 1)``
    whenever the inner expression's domain cannot be proven real. Those
    decompositions look mathematically equivalent on the positive real
    branch but the ``log|...|**2 * arg(...)**2`` cross term in the second
    one evaluates to ``inf * 0 = NaN`` whenever a species concentration
    touches 0 — exactly the cse=False non-finite-derivative failure on
    geoschem_fullchem this whole bead targets.

    A subclass of :class:`sympy.Function` with a strictly numeric
    ``.eval`` rule sidesteps the decomposition entirely:

    * Symbolic argument → returns ``None`` from ``eval``, leaving an
      opaque ``_ess_numeric_abs(arg)`` node in the tree. SymPy never
      reasons about modulus/phase of the inner expression, so the
      complex-domain rewrites cannot fire.
    * Numeric argument (``Float``/``Integer``/``Rational``) → returns
      the literal absolute value, so substitution-based evaluation
      (e.g. tests doing ``expr.subs(x, 3.5)``) keeps working.

    At lambdify time we pass ``modules=[{"_ess_numeric_abs": numpy.abs},
    "numpy"]``, so the opaque calls resolve to ``numpy.abs`` on real
    floats — correct for any sign of the runtime argument. This is why
    the fix is sign-agnostic: it makes no positivity assumption about
    state or parameters and stays correct on models whose state goes
    negative.

    Class of risk this addresses: ``sp.Abs.eval`` is the SymPy operator
    whose canonical rewrites produced the chemistry-fatal decomposition
    path (``Abs(exp(z)*w)``, ``Abs(b**z)`` chains). If a future SymPy
    version adds a new rewrite-on-eval to another operator
    (``sign``, ``floor``, ``ceiling``, etc.) that emits ``re``/``im``/
    ``arg`` on real-but-symbolically-unprovable inputs, the same
    opacity treatment may need to be extended to that operator. Audit
    by checking ``inspect.getsource`` of a lambdified RHS on a fresh
    model that uses the suspected operator and grepping for ``real(``,
    ``imag(``, ``angle(``.
    """

    @classmethod
    def eval(cls, arg):
        if arg.is_number and getattr(arg, "is_real", None):
            return abs(arg)
        return None


# Module-mapping handed to every ``sp.lambdify`` call in this module so
# the ``_ess_numeric_abs`` calls emitted by ``_expr_to_sympy`` resolve to
# ``numpy.abs`` at runtime.
_LAMBDIFY_MODULES = [{"_ess_numeric_abs": np.abs}, "numpy"]


def _make_fn_closure(
    closed_name: str,
    arity: int,
    const_args: Dict[int, List],
    sym_positions: List[int],
) -> Callable:
    """Build a closure for an ``fn`` op with const-array args baked in.

    ``closed_name`` is the closed-function-registry name (e.g.
    ``"interp.bilinear"``). ``const_args`` maps positional index → list (the
    table/axis tensor extracted from a ``const``-op AST node at compile
    time). ``sym_positions`` lists the positions whose values come from the
    symbolic call site; the returned closure receives these in order from
    the lambdified RHS at runtime.

    The closure handles both scalar and array runtime inputs so that the
    same compiled callable is reusable both inside the integrator's RHS
    (called with scalar state/time per step) and in the observed-vector
    pass (called once with arrays over the output time grid).
    """
    from .registered_functions import evaluate_closed_function

    captured_consts = dict(const_args)
    captured_positions = list(sym_positions)

    def closure(*sym_vals):
        arrs = [np.asarray(v, dtype=float) for v in sym_vals]
        any_array = any(a.ndim > 0 for a in arrs)
        if not any_array:
            full_args: List = [None] * arity
            for pos, val in captured_consts.items():
                full_args[pos] = val
            for k, pos in enumerate(captured_positions):
                full_args[pos] = float(arrs[k])
            return float(evaluate_closed_function(closed_name, full_args))
        if arrs:
            shape = np.broadcast_shapes(*(a.shape for a in arrs))
        else:
            shape = ()
        broadcast = [np.broadcast_to(a, shape) for a in arrs]
        out = np.empty(shape, dtype=float)
        for idx in np.ndindex(*shape) if shape else [()]:
            full_args = [None] * arity
            for pos, val in captured_consts.items():
                full_args[pos] = val
            for k, pos in enumerate(captured_positions):
                full_args[pos] = float(broadcast[k][idx])
            out[idx] = float(evaluate_closed_function(closed_name, full_args))
        return out

    return closure


def _expr_to_sympy(
    expr: Expr,
    symbol_map: Dict[str, sp.Symbol],
    fn_registry: Optional[Dict[str, Callable]] = None,
) -> sp.Expr:
    """
    Convert ESM Expr to SymPy expression.

    The ``'abs'`` op is converted to a placeholder
    :class:`sympy.Function` rather than :class:`sympy.Abs` so SymPy's
    construction-time canonical rewrites for absolute value do not fire
    (esm-5gk). See ``_ess_numeric_abs`` for the full rationale; in
    short, ``sp.Abs`` over a product of ``exp``/``log``/rational-power
    composites decomposes into a complex-domain form whose
    ``log|x|**2 * arg(x)**2`` term evaluates to ``inf*0 = NaN`` at any
    boundary value (e.g. species concentration of 0). The placeholder
    :class:`sympy.Function` has no ``.eval``, so the decomposition cannot
    fire and the lambdified RHS stays in pure-real form.

    Args:
        expr: Expression to convert
        symbol_map: Mapping from variable names to SymPy symbols

    Returns:
        SymPy expression
    """
    if isinstance(expr, (int, float)):
        return sp.Float(expr)
    elif isinstance(expr, str):
        if expr in symbol_map:
            return symbol_map[expr]
        else:
            # Try to parse as a number
            try:
                return sp.Float(float(expr))
            except ValueError:
                # Create a new symbol if not found.
                symbol_map[expr] = sp.Symbol(expr)
                return symbol_map[expr]
    elif isinstance(expr, ExprNode):
        # Spatial differential operators must be rewritten by ESD
        # discretization rules into `arrayop` AST before reaching the
        # SymPy/lambdify simulator path. Encountering one here means the
        # canonical pipeline broke; surface it instead of letting SymPy
        # invent a symbolic placeholder. (esm-i7b)
        if expr.op in ('grad', 'div', 'laplacian'):
            raise UnreachableSpatialOperatorError(expr.op)

        # `const` (inline literal value, esm-spec §9.2 / §9.5). Scalar
        # literals are inlined as ``sp.Float``. Array-valued ``const`` nodes
        # are only meaningful as inline tables for ``interp.*`` calls (per
        # esm-spec §9.2) and are extracted at the enclosing ``fn`` node;
        # encountering one outside that context indicates a malformed AST
        # for the SymPy/lambdify backend (the array-op path uses the NumPy
        # interpreter instead).
        if expr.op == 'const':
            v = expr.value
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                return sp.Float(v)
            raise SimulationError(
                "array-valued `const` op outside `fn` is not supported by "
                "the SymPy backend; inline-const tables MUST appear as the "
                "table/axis arg of an `interp.*` `fn` call (esm-spec §9.2)"
            )

        # `fn` (closed function registry call, esm-spec §9.2). Emitted as
        # an opaque ``sp.Function`` so SymPy treats the call as an
        # uninterpreted symbolic node — no derivative, no algebraic
        # simplification — mirroring the Julia binding's
        # ``@register_symbolic`` treatment that keeps ``interp.*`` opaque
        # to ``structural_simplify``. Inline-``const`` table/axis args
        # listed in ``_INTERP_CONST_ARG_POSITIONS`` are extracted at
        # compile time and baked into a closure registered under a
        # uniquified name so that distinct call sites with different
        # tables map to distinct opaque functions.
        if expr.op == 'fn':
            if fn_registry is None:
                raise SimulationError(
                    "`fn` op encountered but no fn registry was provided to "
                    "`_expr_to_sympy`. Callers that lambdify expressions "
                    "containing `fn` calls MUST thread an `fn_registry` dict "
                    "through compilation so the closures resolve at runtime."
                )
            if expr.name is None:
                raise SimulationError("`fn` op missing required `name` field")
            const_positions = set(_INTERP_CONST_ARG_POSITIONS.get(expr.name, ()))
            const_args: Dict[int, List] = {}
            sym_positions: List[int] = []
            sym_args: List[sp.Expr] = []
            for i, a in enumerate(expr.args):
                if (
                    i in const_positions
                    and isinstance(a, ExprNode)
                    and a.op == "const"
                ):
                    const_args[i] = list(a.value or [])
                else:
                    sym_args.append(_expr_to_sympy(a, symbol_map, fn_registry))
                    sym_positions.append(i)
            opaque_name = f"_ess_fn_{len(fn_registry)}"
            fn_registry[opaque_name] = _make_fn_closure(
                expr.name, len(expr.args), const_args, sym_positions,
            )
            return sp.Function(opaque_name)(*sym_args)

        # Convert arguments recursively
        sympy_args = [_expr_to_sympy(arg, symbol_map, fn_registry) for arg in expr.args]

        # Handle different operations
        if expr.op == '+':
            return sum(sympy_args) if sympy_args else 0
        elif expr.op == '-':
            if len(sympy_args) == 1:
                return -sympy_args[0]
            elif len(sympy_args) == 2:
                return sympy_args[0] - sympy_args[1]
            else:
                raise SimulationError(f"Invalid number of arguments for subtraction: {len(sympy_args)}")
        elif expr.op == '*':
            result = 1
            for arg in sympy_args:
                result *= arg
            return result
        elif expr.op == '/':
            if len(sympy_args) != 2:
                raise SimulationError(f"Division requires exactly 2 arguments, got {len(sympy_args)}")
            return sympy_args[0] / sympy_args[1]
        elif expr.op in ('^', '**', 'pow'):
            if len(sympy_args) != 2:
                raise SimulationError(f"Power requires exactly 2 arguments, got {len(sympy_args)}")
            base, exp_arg = sympy_args
            # SymPy treats ``x**Float(2.0)`` as a non-integer rational power
            # (``exp(2.0*log(x))``) which forces the lambdified RHS into
            # complex-domain code paths (``re(...)``, ``im(...)``,
            # ``angle(...)``) under cse=False — even when ``x`` is provably
            # real. Integer-valued Float exponents from ESM JSON (``"2.0"``,
            # ``"3.0"``) are by author intent integer powers, so canonicalize
            # them to ``sp.Integer`` and keep sympy on its real-domain
            # simplification path. See esm-5gk for the geoschem_fullchem
            # non-finite-derivative failure this prevents.
            if (
                isinstance(exp_arg, sp.Float)
                and exp_arg.is_finite
                and float(exp_arg) == int(exp_arg)
            ):
                exp_arg = sp.Integer(int(exp_arg))
            return base ** exp_arg
        elif expr.op == 'exp':
            if len(sympy_args) != 1:
                raise SimulationError(f"Exponential requires exactly 1 argument, got {len(sympy_args)}")
            return sp.exp(sympy_args[0])
        elif expr.op == 'log':
            if len(sympy_args) != 1:
                raise SimulationError(f"Logarithm requires exactly 1 argument, got {len(sympy_args)}")
            return sp.log(sympy_args[0])
        elif expr.op == 'log10':
            if len(sympy_args) != 1:
                raise SimulationError(f"log10 requires exactly 1 argument, got {len(sympy_args)}")
            return sp.log(sympy_args[0], 10)
        elif expr.op == 'sqrt':
            if len(sympy_args) != 1:
                raise SimulationError(f"sqrt requires exactly 1 argument, got {len(sympy_args)}")
            return sp.sqrt(sympy_args[0])
        elif expr.op == 'abs':
            if len(sympy_args) != 1:
                raise SimulationError(f"abs requires exactly 1 argument, got {len(sympy_args)}")
            # See ``_ess_numeric_abs`` definition — using ``sp.Abs`` here
            # would trigger the construction-time decomposition that
            # esm-5gk fixes.
            return _ess_numeric_abs(sympy_args[0])
        elif expr.op == 'sign':
            if len(sympy_args) != 1:
                raise SimulationError(f"sign requires exactly 1 argument, got {len(sympy_args)}")
            return sp.sign(sympy_args[0])
        elif expr.op == 'floor':
            if len(sympy_args) != 1:
                raise SimulationError(f"floor requires exactly 1 argument, got {len(sympy_args)}")
            return sp.floor(sympy_args[0])
        elif expr.op == 'ceil':
            if len(sympy_args) != 1:
                raise SimulationError(f"ceil requires exactly 1 argument, got {len(sympy_args)}")
            return sp.ceiling(sympy_args[0])
        elif expr.op == 'min':
            if not sympy_args:
                raise SimulationError("min requires at least 1 argument")
            return sp.Min(*sympy_args)
        elif expr.op == 'max':
            if not sympy_args:
                raise SimulationError("max requires at least 1 argument")
            return sp.Max(*sympy_args)
        elif expr.op == 'sin':
            if len(sympy_args) != 1:
                raise SimulationError(f"Sine requires exactly 1 argument, got {len(sympy_args)}")
            return sp.sin(sympy_args[0])
        elif expr.op == 'cos':
            if len(sympy_args) != 1:
                raise SimulationError(f"Cosine requires exactly 1 argument, got {len(sympy_args)}")
            return sp.cos(sympy_args[0])
        elif expr.op == 'tan':
            if len(sympy_args) != 1:
                raise SimulationError(f"tan requires exactly 1 argument, got {len(sympy_args)}")
            return sp.tan(sympy_args[0])
        elif expr.op == 'asin':
            if len(sympy_args) != 1:
                raise SimulationError(f"asin requires exactly 1 argument, got {len(sympy_args)}")
            return sp.asin(sympy_args[0])
        elif expr.op == 'acos':
            if len(sympy_args) != 1:
                raise SimulationError(f"acos requires exactly 1 argument, got {len(sympy_args)}")
            return sp.acos(sympy_args[0])
        elif expr.op == 'atan':
            if len(sympy_args) != 1:
                raise SimulationError(f"atan requires exactly 1 argument, got {len(sympy_args)}")
            return sp.atan(sympy_args[0])
        elif expr.op == 'atan2':
            if len(sympy_args) != 2:
                raise SimulationError(f"atan2 requires exactly 2 arguments, got {len(sympy_args)}")
            return sp.atan2(sympy_args[0], sympy_args[1])
        elif expr.op == 'ifelse':
            if len(sympy_args) != 3:
                raise SimulationError(f"ifelse requires exactly 3 arguments, got {len(sympy_args)}")
            return sp.Piecewise((sympy_args[1], sympy_args[0]), (sympy_args[2], True))
        elif expr.op == 'and':
            if len(sympy_args) < 2:
                raise SimulationError(f"and requires at least 2 arguments, got {len(sympy_args)}")
            return sp.And(*sympy_args)
        elif expr.op == 'or':
            if len(sympy_args) < 2:
                raise SimulationError(f"or requires at least 2 arguments, got {len(sympy_args)}")
            return sp.Or(*sympy_args)
        elif expr.op == 'not':
            if len(sympy_args) != 1:
                raise SimulationError(f"not requires exactly 1 argument, got {len(sympy_args)}")
            return sp.Not(sympy_args[0])
        elif expr.op == '>':
            if len(sympy_args) != 2:
                raise SimulationError(f"Greater than requires exactly 2 arguments, got {len(sympy_args)}")
            return sp.StrictGreaterThan(sympy_args[0], sympy_args[1])
        elif expr.op == '<':
            if len(sympy_args) != 2:
                raise SimulationError(f"Less than requires exactly 2 arguments, got {len(sympy_args)}")
            return sp.StrictLessThan(sympy_args[0], sympy_args[1])
        elif expr.op == '>=':
            if len(sympy_args) != 2:
                raise SimulationError(f"Greater than or equal requires exactly 2 arguments, got {len(sympy_args)}")
            return sp.GreaterThan(sympy_args[0], sympy_args[1])
        elif expr.op == '<=':
            if len(sympy_args) != 2:
                raise SimulationError(f"Less than or equal requires exactly 2 arguments, got {len(sympy_args)}")
            return sp.LessThan(sympy_args[0], sympy_args[1])
        elif expr.op == '==':
            if len(sympy_args) != 2:
                raise SimulationError(f"Equality requires exactly 2 arguments, got {len(sympy_args)}")
            return sp.Eq(sympy_args[0], sympy_args[1])
        elif expr.op == '!=':
            if len(sympy_args) != 2:
                raise SimulationError(f"Inequality requires exactly 2 arguments, got {len(sympy_args)}")
            return sp.Ne(sympy_args[0], sympy_args[1])
        else:
            raise SimulationError(f"Unsupported operation: {expr.op}")
    else:
        raise SimulationError(f"Unsupported expression type: {type(expr)}")


def _flat_to_sympy_rhs(
    flat: FlattenedSystem,
    fn_registry: Optional[Dict[str, Callable]] = None,
) -> Tuple[
    List[str],
    List[str],
    Dict[str, sp.Symbol],
    List[sp.Expr],
    List[str],
    Dict[str, sp.Expr],
]:
    """Build the SymPy ODE RHS expressions from a FlattenedSystem.

    Performs scalar algebraic-equation elimination as part of construction:
    equations of the form ``v = <body>`` (where ``v`` is a state variable
    that has no corresponding ``D(v, t) = …`` differential equation) are
    treated as observed/algebraic. Each algebraic body is symbolically
    substituted into every other algebraic body and into every differential
    RHS, so the integrator's RHS depends only on differential states and
    parameters. This is the scalar equivalent of MTK's ``structural_simplify``
    and is required for models like ``diameter_growth`` where ``A`` and
    ``I_D`` are algebraically defined alongside an ODE for ``D_p``.

    Parameter values are NOT inlined — parameter symbols remain free in
    ``rhs_exprs`` and ``algebraic_value_exprs`` so the symbolic form (and
    its lambdified counterpart) can be cached and reused across multiple
    simulate() calls with different parameter overrides. The caller passes
    parameter values to the lambdified function as runtime arguments
    (see :func:`_compile_flat_rhs`).

    Returns
    -------
    state_names:
        Dot-namespaced state variable names in the order they appear in the
        result vector.
    parameter_names:
        Dot-namespaced parameter names in the order their symbols appear in
        the lambdified function's parameter argument slots.
    symbol_map:
        Mapping from namespaced variable name to SymPy symbol (for use by
        event functions and parameter binding).
    rhs_exprs:
        Per-state SymPy expression for ``dy_i/dt``. Differential states get
        their (algebraic-substituted) derivative; algebraic-only states get
        ``0`` — the integrator does not advance them, and their values are
        recovered at output time by evaluating ``algebraic_value_exprs``.
    algebraic_state_names:
        Subset of ``state_names`` whose values are determined algebraically
        rather than by integration.
    algebraic_value_exprs:
        Per-algebraic-state SymPy expression for the variable's value
        (already substituted so it depends only on differential states and
        free parameter symbols).

    Observed variables (``flat.observed_variables``) are not handled here
    — see :func:`_observed_to_sympy_value_exprs` for the parallel pass that
    builds their value expressions from the same equation list.

    Raises
    ------
    SimulationError
        If the algebraic equations form a cycle (including self-reference).
    """
    state_names = list(flat.state_variables.keys())
    parameter_names = list(flat.parameters.keys())

    symbol_map: Dict[str, sp.Symbol] = {}
    for name in state_names + parameter_names:
        symbol_map[name] = sp.Symbol(name)

    # Classify equations: differential (D(var, t) = …) vs algebraic (var = …).
    diff_rhs: Dict[str, sp.Expr] = {}
    alg_rhs: Dict[str, sp.Expr] = {}
    for eq in flat.equations:
        lhs = eq.lhs
        if isinstance(lhs, ExprNode) and lhs.op == "D" and lhs.args:
            inner = lhs.args[0]
            if isinstance(inner, str) and inner in flat.state_variables:
                diff_rhs[inner] = _expr_to_sympy(
                    eq.rhs, dict(symbol_map), fn_registry,
                )
                continue
        if isinstance(lhs, str) and lhs in flat.state_variables:
            rhs_sym = _expr_to_sympy(eq.rhs, dict(symbol_map), fn_registry)
            if lhs in alg_rhs:
                # Same-system DAE: a previous equation already defines this
                # variable. Treat ``lhs = rhs_sym`` as an algebraic constraint
                # on a different unbound state variable that appears in the
                # RHS. This is the scalar analogue of MTK's alias-elimination
                # pass and is required for equilibrium models that author
                # K = f(T) alongside K = product([H+], [OH-]).
                free_states = []
                seen_states: Set[str] = set()
                for s in rhs_sym.free_symbols:
                    nm = str(s)
                    if (
                        nm in flat.state_variables
                        and nm not in alg_rhs
                        and nm not in diff_rhs
                        and nm != lhs
                        and nm not in seen_states
                    ):
                        free_states.append(s)
                        seen_states.add(nm)
                if len(free_states) >= 1:
                    target = free_states[0]
                    target_name = str(target)
                    try:
                        solutions = sp.solve(
                            sp.Eq(symbol_map[lhs], rhs_sym), target,
                        )
                    except Exception:
                        solutions = []
                    if solutions:
                        alg_rhs[target_name] = sp.sympify(solutions[0])
                        continue
                # No unbound state variable on the RHS — the equation is
                # either a redundant restatement or a genuine contradiction.
                # Skip it; downstream output will surface any inconsistency.
                continue
            alg_rhs[lhs] = rhs_sym
            continue
        # Other LHS shapes (e.g. array ops) are handled by the NumPy path.

    # If a state has both an ODE and an algebraic equation, the ODE wins — the
    # system is overdetermined and we must pick one consistent interpretation.
    for name in list(alg_rhs.keys()):
        if name in diff_rhs:
            del alg_rhs[name]

    algebraic_state_names = [n for n in state_names if n in alg_rhs]

    # Topologically sort algebraic vars by their direct dependence on each
    # other. Detect cycles (including self-reference) and raise with the
    # offending chain so authors can fix the model.
    alg_deps: Dict[str, List[str]] = {}
    alg_set = set(algebraic_state_names)
    for n in algebraic_state_names:
        free = getattr(alg_rhs[n], "free_symbols", set()) or set()
        alg_deps[n] = [str(s) for s in free if str(s) in alg_set]

    sorted_alg: List[str] = []
    visited: Set[str] = set()
    in_progress: Set[str] = set()

    def _topo_visit(name: str, path: List[str]) -> None:
        if name in visited:
            return
        if name in in_progress:
            cycle = path[path.index(name):] + [name]
            raise SimulationError(
                "Cyclic algebraic equations detected: "
                + " -> ".join(cycle)
            )
        in_progress.add(name)
        for dep in alg_deps[name]:
            _topo_visit(dep, path + [name])
        in_progress.discard(name)
        visited.add(name)
        sorted_alg.append(name)

    for n in algebraic_state_names:
        _topo_visit(n, [])

    # Substitute earlier-sorted algebraic bodies into later ones, so each
    # alg_rhs[n] ends up expressed only in terms of differential states and
    # parameters.
    for n in sorted_alg:
        deps_subs = {symbol_map[d]: alg_rhs[d] for d in alg_deps[n]}
        if deps_subs:
            alg_rhs[n] = alg_rhs[n].subs(deps_subs, simultaneous=False)

    # Substitute the (now fully-resolved) algebraic bodies into every
    # differential RHS. The integrator's RHS no longer references any
    # algebraic state symbol.
    full_alg_subs = {symbol_map[k]: alg_rhs[k] for k in algebraic_state_names}
    if full_alg_subs:
        for k in list(diff_rhs.keys()):
            diff_rhs[k] = diff_rhs[k].subs(full_alg_subs, simultaneous=False)

    rhs_exprs: List[sp.Expr] = []
    for name in state_names:
        if name in diff_rhs:
            rhs_exprs.append(diff_rhs[name])
        else:
            # Algebraic states and unassigned states get a zero derivative.
            # Algebraic states are recovered at output time from alg_rhs.
            rhs_exprs.append(sp.Float(0))

    return (
        state_names,
        parameter_names,
        symbol_map,
        rhs_exprs,
        algebraic_state_names,
        alg_rhs,
    )


def _observed_to_sympy_value_exprs(
    flat: FlattenedSystem,
    state_names: List[str],
    parameter_names: List[str],
    symbol_map: Dict[str, sp.Symbol],
    algebraic_state_names: List[str],
    algebraic_value_exprs: Dict[str, sp.Expr],
    fn_registry: Optional[Dict[str, Callable]] = None,
) -> Tuple[List[str], Dict[str, sp.Expr]]:
    """Build SymPy value expressions for ``flat.observed_variables``.

    Mirrors the algebraic-state pass in :func:`_flat_to_sympy_rhs`: equations
    whose LHS is an observed variable are collected, topologically sorted by
    their dependence on each other, and folded so each body depends only on
    differential states and parameters. Algebraic-state bodies (already
    substituted to the same closed form) are folded in too.

    This is a separate function from :func:`_flat_to_sympy_rhs` to keep the
    latter's tuple-return shape stable for external callers (the EarthSciModels
    inline-test runner pre-populates ``flat._simulate_compile_cache`` by
    unpacking the original 6-tuple — adding observed there would break that
    contract).

    Returns
    -------
    observed_names:
        Observed variables that have an algebraic body, in input order.
    observed_value_exprs:
        Per-observed SymPy expression for the variable's value, depending only
        on differential-state symbols and free parameter symbols.
    """
    observed_names_all = list(flat.observed_variables.keys())
    if not observed_names_all:
        return [], {}

    # Extend the symbol map with observed-variable symbols so substitution
    # between observed bodies works without name collisions.
    sym_map = dict(symbol_map)
    for name in observed_names_all:
        if name not in sym_map:
            sym_map[name] = sp.Symbol(name)

    obs_rhs: Dict[str, sp.Expr] = {}
    for eq in flat.equations:
        lhs = eq.lhs
        if isinstance(lhs, str) and lhs in flat.observed_variables:
            obs_rhs[lhs] = _expr_to_sympy(eq.rhs, dict(sym_map), fn_registry)

    observed_with_eq = [n for n in observed_names_all if n in obs_rhs]
    if not observed_with_eq:
        return [], {}

    # Topologically sort observed vars by their direct dependence on each
    # other; detect cycles (including self-reference).
    obs_deps: Dict[str, List[str]] = {}
    obs_set = set(observed_with_eq)
    for n in observed_with_eq:
        free = getattr(obs_rhs[n], "free_symbols", set()) or set()
        obs_deps[n] = [str(s) for s in free if str(s) in obs_set]

    sorted_obs: List[str] = []
    obs_visited: Set[str] = set()
    obs_in_progress: Set[str] = set()

    def _obs_topo_visit(name: str, path: List[str]) -> None:
        if name in obs_visited:
            return
        if name in obs_in_progress:
            cycle = path[path.index(name):] + [name]
            raise SimulationError(
                "Cyclic observed equations detected: "
                + " -> ".join(cycle)
            )
        obs_in_progress.add(name)
        for dep in obs_deps[name]:
            _obs_topo_visit(dep, path + [name])
        obs_in_progress.discard(name)
        obs_visited.add(name)
        sorted_obs.append(name)

    for n in observed_with_eq:
        _obs_topo_visit(n, [])

    full_alg_subs = {
        sym_map[k]: algebraic_value_exprs[k] for k in algebraic_state_names
    }
    for n in sorted_obs:
        if full_alg_subs:
            obs_rhs[n] = obs_rhs[n].subs(full_alg_subs, simultaneous=False)
        deps_subs = {sym_map[d]: obs_rhs[d] for d in obs_deps[n]}
        if deps_subs:
            obs_rhs[n] = obs_rhs[n].subs(deps_subs, simultaneous=False)

    return observed_with_eq, obs_rhs


@dataclass
class _CompiledRhs:
    """Cached, parametric RHS for a FlattenedSystem.

    Both ``rhs_vector_func`` and ``algebraic_vector_func`` are produced by
    :func:`sympy.lambdify` with ``cse=True``, sharing CSE across the full
    state vector instead of one lambdify-per-expression. Each function takes
    state symbols followed by parameter symbols (in the orders given by
    ``state_names`` / ``parameter_names``) so a single compile is reusable
    across simulate() calls with different parameter overrides.
    """

    state_names: List[str]
    parameter_names: List[str]
    symbol_map: Dict[str, sp.Symbol]
    algebraic_state_names: List[str]
    rhs_vector_func: Optional[Callable]
    algebraic_vector_func: Optional[Callable]
    observed_names: List[str] = field(default_factory=list)
    observed_vector_func: Optional[Callable] = None


def _compile_flat_rhs(flat: FlattenedSystem, cse: bool = True) -> _CompiledRhs:
    """Compile (and cache) the RHS of a FlattenedSystem to numpy callables.

    The compile step (`_flat_to_sympy_rhs` + vector ``sp.lambdify`` with
    ``cse=True``) dominates simulate()'s wall time on large mechanisms
    (geoschem_fullchem: ~395 s flatten-to-sympy + ~99 s lambdify). The
    result depends only on the symbolic structure of ``flat`` — parameter
    values are runtime arguments — so we cache it as an attribute on the
    FlattenedSystem object. Repeat simulate() calls on the same ``flat``
    (e.g. an 8-plot scenario sharing one parsed model) hit the cache and
    pay near-zero compile cost.

    Parameters
    ----------
    flat:
        The flattened system to compile.
    cse:
        Forwarded to :func:`sympy.lambdify` for the rhs / algebraic / observed
        functions. ``True`` (default) shares common subexpressions across the
        full vector, which is the production setting and dominates simulate()
        cost-wise. ``False`` disables CSE — useful for diagnostics that need
        to bypass SymPy's construction-time canonical rewrites (e.g. the
        ``cse=False`` non-finite-derivative regression captured by esm-5gk).
        Compiles for ``cse=True`` and ``cse=False`` are cached independently
        on ``flat`` so flipping the flag does not invalidate the other.

    Notes
    -----
    Systems with zero state variables are supported when at least one
    observed variable has an algebraic body — ``rhs_vector_func`` is then
    ``None`` and only ``observed_vector_func`` is populated. simulate()
    handles this case by skipping the integrator and sampling the observed
    bodies on a synthetic time grid (cloud_albedo.esm and friends, where
    every variable lands as an observed binding after MTK-style scalar
    elimination).
    """
    # cse=True keeps the legacy cache attribute name so external callers
    # (notably the EarthSciModels inline-test runner pre-population path
    # documented above _observed_to_sympy_value_exprs) continue to work.
    cache_attr = "_simulate_compile_cache" if cse else "_simulate_compile_cache_no_cse"
    cached = getattr(flat, cache_attr, None)
    if cached is not None:
        return cached

    # ``fn_registry`` collects opaque-function closures emitted by
    # ``_expr_to_sympy`` for ``fn`` op nodes (closed function registry calls,
    # esm-spec §9.2). Inline-``const`` table/axis args are baked into each
    # closure at compile time; the lambdified RHS dispatches by the unique
    # ``_ess_fn_<seq>`` name, so we hand the registry to ``sp.lambdify`` as
    # an additional module dict. fastjx.esm and any other model with
    # ``interp.linear`` / ``interp.bilinear`` observed bodies routes through
    # this path.
    fn_registry: Dict[str, Callable] = {}

    (
        state_names,
        parameter_names,
        symbol_map,
        rhs_exprs,
        algebraic_state_names,
        algebraic_value_exprs,
    ) = _flat_to_sympy_rhs(flat, fn_registry)

    observed_names, observed_value_exprs = _observed_to_sympy_value_exprs(
        flat,
        state_names,
        parameter_names,
        symbol_map,
        algebraic_state_names,
        algebraic_value_exprs,
        fn_registry,
    )

    # Differential and algebraic RHS expressions may reference observed
    # variables by their dot-namespaced name (e.g. ``D(FastJX.NO2) = ... *
    # FastJX.j_NO2`` where ``FastJX.j_NO2`` is observed). ``_expr_to_sympy``
    # creates such references as on-the-fly ``sp.Symbol`` instances because
    # observed names are not in ``symbol_map``; if we hand those expressions
    # straight to ``sp.lambdify`` the dotted names are printed literally
    # (``FastJX.j_NO2``) and Python parses them as attribute access on a
    # nonexistent ``FastJX`` module — the ``NameError: name 'FastJX' is not
    # defined`` reported in esm-4id. Substitute the (already fully-resolved)
    # observed bodies in so the lambdified RHS depends only on differential
    # state and parameter symbols, all of which appear in ``all_args`` and
    # are dummy-renamed by ``lambdify`` for safe code emission.
    if observed_names:
        observed_subs = {
            sp.Symbol(name): observed_value_exprs[name]
            for name in observed_names
        }
        rhs_exprs = [
            expr.subs(observed_subs, simultaneous=False)
            for expr in rhs_exprs
        ]
        if algebraic_state_names:
            algebraic_value_exprs = {
                k: v.subs(observed_subs, simultaneous=False)
                for k, v in algebraic_value_exprs.items()
            }

    state_symbols = [symbol_map[name] for name in state_names]
    param_symbols = [symbol_map[name] for name in parameter_names]
    all_args = state_symbols + param_symbols

    # If any ``fn`` op closures were registered, prepend them to the lambdify
    # modules list so SymPy's code printer emits ``_ess_fn_<seq>(args)`` that
    # resolves to our closure. Module-list entries take precedence in order,
    # and the per-compile dict is harmless (empty) when no fn ops appear.
    lambdify_modules = (
        [fn_registry, *_LAMBDIFY_MODULES] if fn_registry else _LAMBDIFY_MODULES
    )

    if state_names:
        rhs_vector_func = sp.lambdify(
            all_args, rhs_exprs, modules=lambdify_modules, cse=cse
        )
    else:
        rhs_vector_func = None

    if algebraic_state_names:
        alg_value_list = [algebraic_value_exprs[n] for n in algebraic_state_names]
        algebraic_vector_func = sp.lambdify(
            all_args, alg_value_list, modules=lambdify_modules, cse=cse
        )
    else:
        algebraic_vector_func = None

    if observed_names:
        obs_value_list = [observed_value_exprs[n] for n in observed_names]
        # Observed bodies may legitimately reference the independent
        # variable ``t`` (e.g. an analytical-solution observed in
        # python_scipy_integration.esm: ``c0 * exp(-k*t)``). State and
        # parameter symbols stay anonymous in ``rhs_vector_func`` /
        # ``algebraic_vector_func`` because the integrator never feeds
        # ``t`` into their bodies, but observed evaluation happens at the
        # output time grid where ``t`` is a real value the caller must be
        # able to bind. Plumbing ``t`` here keeps the runner generic
        # without per-equation dispatch.
        t_symbol = sp.Symbol("t")
        observed_vector_func = sp.lambdify(
            [t_symbol, *all_args], obs_value_list,
            modules=lambdify_modules, cse=cse,
        )
    else:
        observed_vector_func = None

    compiled = _CompiledRhs(
        state_names=state_names,
        parameter_names=parameter_names,
        symbol_map=symbol_map,
        algebraic_state_names=algebraic_state_names,
        rhs_vector_func=rhs_vector_func,
        algebraic_vector_func=algebraic_vector_func,
        observed_names=observed_names,
        observed_vector_func=observed_vector_func,
    )
    try:
        setattr(flat, cache_attr, compiled)
    except (AttributeError, TypeError):
        # FlattenedSystem instances are dataclasses without __slots__, so
        # attribute assignment normally succeeds. Fall back to no-cache if
        # a future variant disables it (e.g. frozen=True).
        pass
    return compiled
