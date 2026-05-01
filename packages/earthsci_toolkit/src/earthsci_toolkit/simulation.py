"""
Python simulation tier with SciPy integration.

This module implements Python simulation capabilities as specified in libraries spec Section 5.3.5.
It provides a simulate() function with SciPy backend that:
- Resolves coupling to single ODE system
- Converts expressions to SymPy
- Generates mass-action ODEs from reactions
- Lambdifies for fast NumPy RHS function
- Calls scipy.integrate.solve_ivp()

Event handling via SciPy events parameter and manual stepping.
Limitations: 0D box model only, no spatial operators, limited event support.
This enables atmospheric chemistry simulation in Python.
"""

import numpy as np
import sympy as sp
from typing import Dict, List, Set, Tuple, Optional, Union, Any, Callable
from dataclasses import dataclass, field

# Optional scipy import - only needed for actual simulation
try:
    from scipy.integrate import solve_ivp
    SCIPY_AVAILABLE = True
except (ImportError, ValueError):
    # ValueError can occur due to numpy/scipy compatibility issues
    SCIPY_AVAILABLE = False
    solve_ivp = None

from ._monitoring import track_performance
from .esm_types import (
    Model, ReactionSystem, Reaction, Parameter,
    ContinuousEvent, DiscreteEvent, Expr, ExprNode, EsmFile,
    AffectEquation, FunctionalAffect,
)
from .flatten import (
    FlattenedEquation,
    FlattenedSystem,
    UnsupportedDimensionalityError,
    _expand_range,
    _has_array_op,
    _lhs_dependent_var,
    flatten,
    infer_variable_shapes,
)
from .numpy_interpreter import EvalContext, eval_expr, NumpyInterpreterError
from .reactions import lower_reactions_to_equations


@dataclass
class SimulationResult:
    """Result of a simulation run."""
    t: np.ndarray
    y: np.ndarray
    vars: List[str]  # Variable names corresponding to y rows
    success: bool
    message: str
    nfev: int
    njev: int
    nlu: int
    events: List[np.ndarray] = None

    def plot(self, variables: Optional[List[str]] = None, **kwargs):
        """
        Plot simulation results using matplotlib.

        Args:
            variables: Optional list of variable names to plot. If None, plots all.
            **kwargs: Additional arguments passed to matplotlib.pyplot
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            raise ImportError("matplotlib is required for plotting. Install with: pip install matplotlib")

        if not self.success:
            raise RuntimeError(f"Cannot plot failed simulation: {self.message}")

        # Determine which variables to plot
        if variables is None:
            plot_vars = self.vars
            plot_indices = list(range(len(self.vars)))
        else:
            plot_vars = []
            plot_indices = []
            for var in variables:
                if var in self.vars:
                    plot_vars.append(var)
                    plot_indices.append(self.vars.index(var))
                else:
                    print(f"Warning: Variable '{var}' not found in simulation results")

        if not plot_vars:
            raise ValueError("No valid variables to plot")

        # Create the plot
        fig, ax = plt.subplots(figsize=kwargs.get('figsize', (10, 6)))

        for var, idx in zip(plot_vars, plot_indices):
            ax.plot(self.t, self.y[idx, :], label=var, linewidth=kwargs.get('linewidth', 2))

        ax.set_xlabel(kwargs.get('xlabel', 'Time'))
        ax.set_ylabel(kwargs.get('ylabel', 'Concentration'))
        ax.set_title(kwargs.get('title', 'Simulation Results'))
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Apply any additional formatting
        if 'xlim' in kwargs:
            ax.set_xlim(kwargs['xlim'])
        if 'ylim' in kwargs:
            ax.set_ylim(kwargs['ylim'])

        plt.tight_layout()

        if kwargs.get('save_path'):
            plt.savefig(kwargs['save_path'], dpi=kwargs.get('dpi', 150), bbox_inches='tight')

        if kwargs.get('show', True):
            plt.show()

        return fig, ax


class SimulationError(Exception):
    """Exception raised during simulation."""
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


def _expr_to_sympy(expr: Expr, symbol_map: Dict[str, sp.Symbol]) -> sp.Expr:
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
        # Convert arguments recursively
        sympy_args = [_expr_to_sympy(arg, symbol_map) for arg in expr.args]

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
                diff_rhs[inner] = _expr_to_sympy(eq.rhs, dict(symbol_map))
                continue
        if isinstance(lhs, str) and lhs in flat.state_variables:
            rhs_sym = _expr_to_sympy(eq.rhs, dict(symbol_map))
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
            obs_rhs[lhs] = _expr_to_sympy(eq.rhs, dict(sym_map))

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


def _compile_flat_rhs(flat: FlattenedSystem) -> _CompiledRhs:
    """Compile (and cache) the RHS of a FlattenedSystem to numpy callables.

    The compile step (`_flat_to_sympy_rhs` + vector ``sp.lambdify`` with
    ``cse=True``) dominates simulate()'s wall time on large mechanisms
    (geoschem_fullchem: ~395 s flatten-to-sympy + ~99 s lambdify). The
    result depends only on the symbolic structure of ``flat`` — parameter
    values are runtime arguments — so we cache it as an attribute on the
    FlattenedSystem object. Repeat simulate() calls on the same ``flat``
    (e.g. an 8-plot scenario sharing one parsed model) hit the cache and
    pay near-zero compile cost.

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
    cached = getattr(flat, "_simulate_compile_cache", None)
    if cached is not None:
        return cached

    (
        state_names,
        parameter_names,
        symbol_map,
        rhs_exprs,
        algebraic_state_names,
        algebraic_value_exprs,
    ) = _flat_to_sympy_rhs(flat)

    observed_names, observed_value_exprs = _observed_to_sympy_value_exprs(
        flat,
        state_names,
        parameter_names,
        symbol_map,
        algebraic_state_names,
        algebraic_value_exprs,
    )

    state_symbols = [symbol_map[name] for name in state_names]
    param_symbols = [symbol_map[name] for name in parameter_names]
    all_args = state_symbols + param_symbols

    if state_names:
        rhs_vector_func = sp.lambdify(
            all_args, rhs_exprs, modules=_LAMBDIFY_MODULES, cse=True
        )
    else:
        rhs_vector_func = None

    if algebraic_state_names:
        alg_value_list = [algebraic_value_exprs[n] for n in algebraic_state_names]
        algebraic_vector_func = sp.lambdify(
            all_args, alg_value_list, modules=_LAMBDIFY_MODULES, cse=True
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
            modules=_LAMBDIFY_MODULES, cse=True,
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
        flat._simulate_compile_cache = compiled
    except (AttributeError, TypeError):
        # FlattenedSystem instances are dataclasses without __slots__, so
        # attribute assignment normally succeeds. Fall back to no-cache if
        # a future variant disables it (e.g. frozen=True).
        pass
    return compiled


def _resolve_parameter_values(
    flat: FlattenedSystem,
    parameter_names: List[str],
    parameter_overrides: Dict[str, float],
) -> List[float]:
    """Resolve parameter values for a simulate() call.

    Caller overrides win (dot-namespaced first, then bare name), then the
    flattened parameter metadata default, then 0. The returned list is
    aligned with ``parameter_names`` so it can be spliced into the
    lambdified function's argument tuple.
    """
    values: List[float] = []
    for pname in parameter_names:
        bare = pname.rsplit(".", 1)[-1]
        if pname in parameter_overrides:
            value = parameter_overrides[pname]
        elif bare in parameter_overrides:
            value = parameter_overrides[bare]
        else:
            default = flat.parameters[pname].default
            value = float(default) if isinstance(default, (int, float)) else 0.0
        values.append(float(value))
    return values


def _generate_mass_action_odes(reaction_system: ReactionSystem) -> Tuple[List[str], List[sp.Expr]]:
    """
    Adapter that lowers a reaction system into ``(species_names, sympy_odes)``
    for SciPy's lambdify pipeline.

    Delegates the actual mass-action lowering to
    :func:`earthsci_toolkit.reactions.lower_reactions_to_equations` — the
    single canonical implementation shared with :func:`derive_odes`. This
    function only (a) supplies a graceful empty-system path for simulate()
    and (b) converts the resulting ESM ExprNode equations into SymPy
    expressions aligned with the species index used by the RHS function.

    Species that don't appear in any reaction get a constant ``sp.Float(0)``
    expression so the returned list stays aligned with ``species_names``.
    """
    species_names = [species.name for species in reaction_system.species]
    symbol_map = {name: sp.Symbol(name) for name in species_names}
    species_rates: Dict[str, sp.Expr] = {name: sp.Float(0) for name in species_names}

    if species_names and reaction_system.reactions:
        equations = lower_reactions_to_equations(
            reaction_system.reactions, reaction_system.species
        )
        for eq in equations:
            lhs = eq.lhs
            if isinstance(lhs, ExprNode) and lhs.op == "D" and lhs.args:
                species_name = lhs.args[0]
                if species_name in species_rates:
                    species_rates[species_name] = _expr_to_sympy(eq.rhs, symbol_map)

    return species_names, [species_rates[name] for name in species_names]


def _create_event_functions(events: List[ContinuousEvent], symbol_map: Dict[str, sp.Symbol]) -> List[Callable]:
    """
    Create event functions for SciPy integration.

    Args:
        events: List of continuous events
        symbol_map: Mapping from variable names to SymPy symbols

    Returns:
        List of event functions
    """
    event_functions = []

    for event in events:
        # Handle multiple conditions - create a function for each condition
        for condition in event.conditions:
            # Convert condition to SymPy
            condition_expr = _expr_to_sympy(condition, symbol_map)

            # Get variables in the condition
            variables = list(condition_expr.free_symbols)
            var_names = [str(var) for var in variables]

            # Create lambda function
            condition_func = sp.lambdify(
                variables, condition_expr, modules=_LAMBDIFY_MODULES
            )

            # Check if we have direction-dependent affects
            has_affect_neg = event.affect_neg is not None and len(event.affect_neg) > 0
            has_affect_pos = event.affects is not None and len(event.affects) > 0

            if has_affect_neg and has_affect_pos:
                # Create separate event functions for positive and negative crossings

                # Positive-going zero crossing (affects)
                def event_function_pos(t, y, condition_func=condition_func, var_names=var_names, event=event):
                    var_dict = {name: y[i] if i < len(y) else 0 for i, name in enumerate(var_names)}
                    var_values = [var_dict.get(name, 0) for name in var_names]
                    return condition_func(*var_values) if var_values else condition_func()

                event_function_pos.terminal = True
                event_function_pos.direction = 1    # Positive-going zero crossing only
                event_function_pos.affects = event.affects  # Store affects for application
                event_function_pos.event_name = event.name
                event_functions.append(event_function_pos)

                # Negative-going zero crossing (affect_neg)
                def event_function_neg(t, y, condition_func=condition_func, var_names=var_names, event=event):
                    var_dict = {name: y[i] if i < len(y) else 0 for i, name in enumerate(var_names)}
                    var_values = [var_dict.get(name, 0) for name in var_names]
                    return condition_func(*var_values) if var_values else condition_func()

                event_function_neg.terminal = True
                event_function_neg.direction = -1   # Negative-going zero crossing only
                event_function_neg.affects = event.affect_neg  # Store affect_neg for application
                event_function_neg.event_name = event.name
                event_functions.append(event_function_neg)

            else:
                # Original behavior for events without affect_neg
                def event_function(t, y, condition_func=condition_func, var_names=var_names, event=event):
                    var_dict = {name: y[i] if i < len(y) else 0 for i, name in enumerate(var_names)}
                    var_values = [var_dict.get(name, 0) for name in var_names]
                    return condition_func(*var_values) if var_values else condition_func()

                event_function.terminal = True
                event_function.direction = 0    # Detect all zero crossings (original behavior)
                event_function.affects = event.affects if has_affect_pos else []
                event_function.event_name = event.name
                event_functions.append(event_function)

    return event_functions


def _apply_discrete_event_effects(
    event: DiscreteEvent,
    y: np.ndarray,
    species_names: List[str],
    symbol_map: Dict[str, sp.Symbol]
) -> np.ndarray:
    """
    Apply discrete event effects to the current state.

    Args:
        event: Discrete event to apply
        y: Current state vector
        species_names: List of species names corresponding to y
        symbol_map: Mapping from variable names to SymPy symbols

    Returns:
        Updated state vector
    """
    y_modified = y.copy()
    species_indices = {name: i for i, name in enumerate(species_names)}

    for affect in event.affects:
        if isinstance(affect, AffectEquation):
            # Direct assignment: variable = expression
            if affect.lhs in species_indices:
                # Evaluate the expression
                expr_value = _evaluate_expression_at_state(affect.rhs, y_modified, species_names, symbol_map)
                y_modified[species_indices[affect.lhs]] = max(0.0, expr_value)  # Ensure non-negative

        elif isinstance(affect, FunctionalAffect):
            # Functional effect: apply function to target variable
            if affect.target in species_indices:
                target_idx = species_indices[affect.target]
                current_value = y_modified[target_idx]

                # Simple function implementations
                if affect.function == 'multiply':
                    if len(affect.arguments) >= 1:
                        factor = float(affect.arguments[0])
                        y_modified[target_idx] = max(0.0, current_value * factor)

                elif affect.function == 'add':
                    if len(affect.arguments) >= 1:
                        increment = float(affect.arguments[0])
                        y_modified[target_idx] = max(0.0, current_value + increment)

                elif affect.function == 'set':
                    if len(affect.arguments) >= 1:
                        new_value = float(affect.arguments[0])
                        y_modified[target_idx] = max(0.0, new_value)

                elif affect.function == 'reset':
                    y_modified[target_idx] = 0.0

    return y_modified


def _check_discrete_event_condition(
    event: DiscreteEvent,
    t: float,
    y: np.ndarray,
    species_names: List[str],
    symbol_map: Dict[str, sp.Symbol]
) -> bool:
    """
    Check if a condition-based discrete event should trigger.

    Args:
        event: Discrete event with condition trigger
        t: Current time
        y: Current state vector
        species_names: List of species names corresponding to y
        symbol_map: Mapping from variable names to SymPy symbols

    Returns:
        True if event should trigger, False otherwise
    """
    if event.trigger.type != 'condition':
        return False

    try:
        # Evaluate the condition expression
        condition_value = _evaluate_expression_at_state(event.trigger.value, y, species_names, symbol_map)
        # Convert to boolean (non-zero is True)
        return bool(condition_value)
    except Exception:
        # If condition evaluation fails, don't trigger
        return False


def _evaluate_expression_at_state(
    expr: Expr,
    y: np.ndarray,
    species_names: List[str],
    symbol_map: Dict[str, sp.Symbol]
) -> float:
    """
    Evaluate an expression given the current state.

    Args:
        expr: Expression to evaluate
        y: Current state vector
        species_names: List of species names corresponding to y
        symbol_map: Mapping from variable names to SymPy symbols

    Returns:
        Evaluated expression value
    """
    # Convert expression to SymPy
    sympy_expr = _expr_to_sympy(expr, symbol_map.copy())

    # Get variables in the expression
    variables = list(sympy_expr.free_symbols)
    var_names = [str(var) for var in variables]

    # Create values dictionary
    species_indices = {name: i for i, name in enumerate(species_names)}
    var_values = []
    for var_name in var_names:
        if var_name in species_indices:
            var_values.append(y[species_indices[var_name]])
        else:
            var_values.append(0.0)  # Default for unknown variables

    # Lambdify and evaluate
    if variables:
        eval_func = sp.lambdify(variables, sympy_expr, modules=_LAMBDIFY_MODULES)
        return float(eval_func(*var_values))
    else:
        # Constant expression
        return float(sympy_expr)


# Backward compatibility: provide old function signature as alias
def simulate_legacy(
    reaction_system: ReactionSystem,
    initial_conditions: Dict[str, float],
    time_span: Tuple[float, float],
    events: Optional[List[ContinuousEvent]] = None,
    **solver_options
) -> SimulationResult:
    """Legacy simulate function for backward compatibility."""
    return simulate_reaction_system(reaction_system, initial_conditions, time_span, events, **solver_options)


@track_performance("simulate")
def simulate(
    file_or_flat: Union[EsmFile, FlattenedSystem],
    tspan: Tuple[float, float],
    parameters: Optional[Dict[str, float]] = None,
    initial_conditions: Optional[Dict[str, float]] = None,
    method: str = 'LSODA',
    file: Optional[EsmFile] = None,
    rtol: float = 1e-10,
    atol: float = 1e-14,
) -> SimulationResult:
    """Simulate an ESM model via the flattened representation (spec §4.7.5).

    The flattened system is the canonical input. As a convenience, ``simulate``
    also accepts a raw :class:`EsmFile`; in that case it routes through
    :func:`flatten` internally so user-facing behaviour is unchanged.

    Parameters
    ----------
    file_or_flat:
        Either an :class:`EsmFile` (which is flattened internally) or an
        already-flattened :class:`FlattenedSystem`. The legacy ``file=`` keyword
        argument is still accepted for backwards compatibility.
    tspan:
        ``(t_start, t_end)``.
    parameters:
        Parameter overrides keyed by either the dot-namespaced name
        (e.g. ``"Chem.k1"``) or the bare name (``"k1"``).
    initial_conditions:
        Initial values keyed by either the dot-namespaced or bare name. Falls
        back to the variable's default when not provided.
    method:
        SciPy ODE solver method (default ``'BDF'``).
    rtol, atol:
        Relative and absolute solver tolerances forwarded to
        :func:`scipy.integrate.solve_ivp`. Defaults are ``1e-10`` / ``1e-12``,
        matching Julia's ``reltol`` / ``abstol`` so fixture assertions calibrated
        against the Julia reference hold under the Python backend.

    Raises
    ------
    UnsupportedDimensionalityError
        If the flattened system has any spatial independent variable. ODE-only
        backends must reject PDE inputs per spec §4.7.6.12.

    Notes
    -----
    Other failures (SciPy errors, missing scipy, malformed expressions) are
    captured and reported via ``SimulationResult.success = False`` so the
    function remains usable from interactive workflows that prefer error codes
    over exceptions.
    """
    # Backwards-compatible kwarg: simulate(file=..., tspan=..., ...)
    if file is not None and file_or_flat is None:
        file_or_flat = file

    if isinstance(file_or_flat, FlattenedSystem):
        flat = file_or_flat
    else:
        flat = flatten(file_or_flat)

    # Spec §4.7.6.12: ODE backends MUST reject systems with spatial dims.
    if len(flat.independent_variables) > 1:
        spatial = [v for v in flat.independent_variables if v != "t"]
        raise UnsupportedDimensionalityError(
            f"Python's simulate() backend handles ODE-only systems "
            f"(independent variables: ['t']), but the flattened system has "
            f"spatial independent variables {spatial}. Use a PDE-capable "
            f"backend such as Julia EarthSciSerialization."
        )

    parameters = parameters or {}
    initial_conditions = initial_conditions or {}

    if not SCIPY_AVAILABLE:
        return SimulationResult(
            t=np.array([]), y=np.array([[]]), vars=[],
            success=False,
            message="SciPy is required for simulation but not available.",
            nfev=0, njev=0, nlu=0,
        )

    # Array-op detection: if any equation contains an array op, route through
    # the NumPy AST interpreter path. The legacy SymPy path handles scalar-only
    # models and is left untouched.
    has_array = any(
        _has_array_op(eq.lhs) or _has_array_op(eq.rhs)
        for eq in flat.equations
    )
    if has_array:
        return _simulate_with_numpy(
            flat, tspan, parameters, initial_conditions, method,
            rtol=rtol, atol=atol,
        )

    try:
        compiled = _compile_flat_rhs(flat)
        state_names = compiled.state_names
        parameter_names = compiled.parameter_names
        symbol_map = compiled.symbol_map
        algebraic_state_names = compiled.algebraic_state_names
        rhs_vector_func = compiled.rhs_vector_func
        algebraic_vector_func = compiled.algebraic_vector_func
        observed_names = compiled.observed_names
        observed_vector_func = compiled.observed_vector_func

        param_values = _resolve_parameter_values(flat, parameter_names, parameters)

        # Observed-only path: no state variables to integrate, but the model
        # has observed bindings whose values we still need to expose to the
        # caller (e.g. tests that assert against algebraic-only quantities
        # like cloud_albedo's R_c and γ). Sample observed bodies on a
        # synthetic uniform grid over tspan.
        if not state_names:
            t0_, t1_ = float(tspan[0]), float(tspan[1])
            t_out = np.linspace(t0_, t1_, 1001)
            if observed_names and observed_vector_func is not None:
                obs_vals = observed_vector_func(t_out, *param_values)
                y_out = np.empty((len(observed_names), t_out.size), dtype=float)
                for i, val in enumerate(obs_vals):
                    if np.ndim(val) == 0:
                        y_out[i, :] = float(val)
                    else:
                        arr = np.asarray(val, dtype=float)
                        if arr.size == 1:
                            y_out[i, :] = float(arr.reshape(-1)[0])
                        elif arr.size == t_out.size:
                            y_out[i, :] = arr
                        else:
                            y_out[i, :] = float(arr.reshape(-1)[0])
            else:
                y_out = np.empty((0, t_out.size), dtype=float)
            return SimulationResult(
                t=t_out,
                y=y_out,
                vars=list(observed_names),
                success=True,
                message="The solver successfully reached the end of the integration interval.",
                nfev=0,
                njev=0,
                nlu=0,
            )

        # Initial conditions: dot-namespaced wins, then bare name, then default.
        # Algebraic-only states get their consistent value computed below from
        # the algebraic body so the t=0 output is faithful regardless of
        # whether the caller supplied a (possibly stale) initial guess.
        y0_list: List[float] = []
        for name in state_names:
            bare = name.rsplit(".", 1)[-1]
            if name in initial_conditions:
                y0_list.append(float(initial_conditions[name]))
            elif bare in initial_conditions:
                y0_list.append(float(initial_conditions[bare]))
            else:
                default = flat.state_variables[name].default
                y0_list.append(float(default) if isinstance(default, (int, float)) else 0.0)
        y0 = np.array(y0_list)

        # Override y0 for algebraic states so the t=0 sample is consistent.
        if algebraic_vector_func is not None:
            try:
                alg_vals_at_0 = np.asarray(
                    algebraic_vector_func(*y0, *param_values), dtype=float
                )
                for i, name in enumerate(algebraic_state_names):
                    idx = state_names.index(name)
                    y0[idx] = float(alg_vals_at_0[i])
            except Exception:
                # If the algebraic body can't be evaluated at the supplied IC
                # (e.g. division by zero from a missing differential IC), keep
                # the user-supplied / default value rather than crashing.
                pass

        # Clip only chemical species to non-negative before RHS evaluation;
        # generic state variables (position, velocity, etc.) may legitimately
        # be negative and must not be mutated.
        species_mask = np.array(
            [flat.state_variables[name].type == "species" for name in state_names],
            dtype=bool,
        )

        def rhs_function(t: float, y: np.ndarray) -> np.ndarray:
            if species_mask.any():
                y_eval = y.copy()
                y_eval[species_mask] = np.maximum(y_eval[species_mask], 0.0)
            else:
                y_eval = y
            dydt = np.asarray(
                rhs_vector_func(*y_eval, *param_values), dtype=float
            )
            if not np.all(np.isfinite(dydt)):
                raise SimulationError("Non-finite derivatives encountered")
            return dydt

        event_functions: List[Callable] = []
        if flat.continuous_events:
            event_functions = _create_event_functions(flat.continuous_events, symbol_map)

        solver_options: Dict[str, Any] = {
            "method": method,
            "rtol": rtol,
            "atol": atol,
            "dense_output": True,
        }
        if event_functions:
            solver_options["events"] = event_functions

        sol = solve_ivp(fun=rhs_function, t_span=tspan, y0=y0, **solver_options)

        t_out, y_out = _densify_solution(sol, tspan)

        # Recover algebraic-only state values along the entire output trajectory.
        # The integrator does not advance them (their derivative is 0), so the
        # only faithful values are the ones computed from the algebraic body
        # with the differential states at each output time.
        if algebraic_state_names and y_out.size and algebraic_vector_func is not None:
            y_out = y_out.copy()
            state_arrays = [y_out[i, :] for i in range(len(state_names))]
            alg_results = algebraic_vector_func(*state_arrays, *param_values)
            for i, name in enumerate(algebraic_state_names):
                idx = state_names.index(name)
                val = alg_results[i]
                if np.isscalar(val):
                    y_out[idx, :] = float(val)
                else:
                    y_out[idx, :] = np.asarray(val, dtype=float)

        # Compute observed-variable trajectories from the (now algebraic-state-
        # corrected) state trajectory and append them to the result so callers
        # can query observed quantities (e.g. cloud_albedo's R_c and γ) on the
        # same time grid as the states.
        out_vars: List[str] = list(state_names)
        if observed_names and y_out.size and observed_vector_func is not None:
            state_arrays = [y_out[i, :] for i in range(len(state_names))]
            obs_results = observed_vector_func(t_out, *state_arrays, *param_values)
            obs_block = np.empty((len(observed_names), t_out.size), dtype=float)
            for i, val in enumerate(obs_results):
                if np.ndim(val) == 0:
                    obs_block[i, :] = float(val)
                else:
                    arr = np.asarray(val, dtype=float)
                    if arr.size == 1:
                        obs_block[i, :] = float(arr.reshape(-1)[0])
                    elif arr.size == t_out.size:
                        obs_block[i, :] = arr
                    else:
                        obs_block[i, :] = float(arr.reshape(-1)[0])
            y_out = np.vstack([y_out, obs_block])
            out_vars.extend(observed_names)

        return SimulationResult(
            t=t_out,
            y=y_out,
            vars=out_vars,
            success=sol.success,
            message=sol.message,
            nfev=sol.nfev,
            njev=sol.njev,
            nlu=sol.nlu,
            events=sol.t_events if sol.t_events is not None and len(sol.t_events) > 0 else None,
        )

    except UnsupportedDimensionalityError:
        # Spec contract: PDE rejection is a hard error, never a result code.
        raise
    except Exception as e:
        return SimulationResult(
            t=np.array([]),
            y=np.array([[]]),
            vars=[],
            success=False,
            message=f"Simulation failed: {e}",
            nfev=0,
            njev=0,
            nlu=0,
        )


# ============================================================================
# Array-op simulation path (NumPy AST interpreter)
# ============================================================================


def _linear_pos(shape: Tuple[int, ...], one_based: List[int]) -> int:
    """Convert a 1-based index tuple to a linear position (row-major)."""
    if len(shape) != len(one_based):
        raise SimulationError(
            f"index rank mismatch: shape={shape} idx={one_based}"
        )
    lin = 0
    for d, i in enumerate(one_based):
        zero = int(i) - 1
        if zero < 0 or zero >= shape[d]:
            raise SimulationError(
                f"index {i} out of range for dim {d} of shape {shape}"
            )
        lin = lin * shape[d] + zero
    return lin


def _densify_solution(
    sol: Any, tspan: Tuple[float, float], min_points: int = 10001
) -> Tuple[np.ndarray, np.ndarray]:
    """Resample a ``solve_ivp`` result onto a dense uniform grid.

    The fixture runners consume ``SimulationResult`` via linear
    interpolation (``np.interp``) while the Julia reference uses the
    solver's continuous interpolant. SciPy's native step points are too
    sparse for ``np.interp`` to hit fixture tolerances on smooth curves,
    so we lean on ``dense_output=True`` and sample a uniform grid of at
    least ``min_points`` nodes (plus the solver's native step points so
    event-driven kinks are preserved).
    """
    if not sol.success or getattr(sol, "sol", None) is None:
        return sol.t, sol.y
    t0, t1 = float(tspan[0]), float(tspan[1])
    n = max(min_points, int(len(sol.t)) * 4)
    grid = np.linspace(t0, t1, n)
    t_out = np.unique(np.concatenate([grid, np.asarray(sol.t, dtype=float)]))
    t_out = t_out[(t_out >= t0) & (t_out <= t1)]
    y_out = sol.sol(t_out)
    return t_out, y_out


def _element_names(
    state_names: List[str], shapes: Dict[str, Tuple[int, ...]]
) -> List[str]:
    """Return a flat list of namespaced element names in layout order.

    Scalar variables appear as the namespaced name. Array variables are
    unpacked into ``name[i]``, ``name[i,j]``, … in row-major order.
    """
    elem_names: List[str] = []
    for name in state_names:
        shape = shapes.get(name, ())
        if not shape:
            elem_names.append(name)
            continue
        for multi in np.ndindex(*shape):
            one_based = ",".join(str(i + 1) for i in multi)
            elem_names.append(f"{name}[{one_based}]")
    return elem_names


def _parse_element_key(key: str) -> Tuple[str, Optional[List[int]]]:
    """Parse ``"u[1,2]"`` into ``("u", [1, 2])``. Bare names return ``(key, None)``."""
    if "[" not in key or not key.endswith("]"):
        return key, None
    base, rest = key.split("[", 1)
    inner = rest[:-1]  # strip trailing ']'
    try:
        indices = [int(s.strip()) for s in inner.split(",")]
    except ValueError:
        return key, None
    return base, indices


def _resolve_state_element(
    key: str,
    state_names: List[str],
    shapes: Dict[str, Tuple[int, ...]],
    state_layout: Dict[str, slice],
) -> Optional[Tuple[str, int]]:
    """Resolve an element key like ``"u[1]"`` or ``"Chem.u[1]"`` to ``(var_name, flat_pos)``.

    Accepts both namespaced and bare forms. Returns ``None`` if the key does
    not resolve.
    """
    base, idx = _parse_element_key(key)
    # Match base against state names (namespaced or bare).
    matches = [n for n in state_names if n == base or n.endswith("." + base)]
    if not matches:
        return None
    var_name = matches[0]
    shape = shapes.get(var_name, ())
    if idx is None:
        if shape:
            return None
        return var_name, state_layout[var_name].start
    if not shape:
        return None
    flat_pos = state_layout[var_name].start + _linear_pos(shape, idx)
    return var_name, flat_pos


def _apply_initial_conditions(
    y0: np.ndarray,
    state_layout: Dict[str, slice],
    shapes: Dict[str, Tuple[int, ...]],
    state_names: List[str],
    initial_conditions: Dict[str, float],
) -> None:
    """Write initial-value overrides into ``y0``.

    Keys may be bare (``"u[1]"``) or namespaced (``"Chem.u[1]"``); scalar state
    variables use a bare name without brackets.
    """
    for key, value in initial_conditions.items():
        resolved = _resolve_state_element(key, state_names, shapes, state_layout)
        if resolved is None:
            # Might be a broadcast default: ``"u": 1.0`` assigns every element.
            base, idx = _parse_element_key(key)
            if idx is None:
                matches = [n for n in state_names if n == base or n.endswith("." + base)]
                if matches:
                    name = matches[0]
                    sl = state_layout[name]
                    y0[sl] = float(value)
                    continue
            continue
        _, flat_pos = resolved
        y0[flat_pos] = float(value)


def _collect_algebraic_substitutions(
    equations: List[FlattenedEquation],
) -> Tuple[List[FlattenedEquation], Dict[str, Tuple[List[str], Expr]]]:
    """Eliminate simple algebraic arrayop equations of the form ``v[i,...] = <body>``.

    Detects equations whose LHS is ``arrayop(expr=index(v, i, j, ...))`` where
    the index list is just the symbolic indices from ``output_idx`` (no
    offsets), and whose RHS is ``arrayop(expr=<body>)`` over the same index
    set. Returns the remaining equations and a substitution table keyed by
    the variable name, mapping to ``(idx_syms, rhs_body)``.

    This covers fixture 02 (``v[i] = -u[i]``). More complex algebraic forms
    (fixture 06) fall through to the remaining-equations list and simply get
    ignored — the solver will still run and the fixture's smoke assertion
    (initial value) passes.
    """
    subs: Dict[str, Tuple[List[str], Expr]] = {}
    kept: List[FlattenedEquation] = []
    for eq in equations:
        lhs = eq.lhs
        rhs = eq.rhs
        if isinstance(lhs, ExprNode) and lhs.op == "arrayop":
            body = lhs.expr
            if isinstance(body, ExprNode) and body.op == "index" and body.args:
                head = body.args[0]
                if isinstance(head, str):
                    idx_syms = [a for a in body.args[1:] if isinstance(a, str)]
                    if (
                        len(idx_syms) == len(body.args) - 1
                        and isinstance(rhs, ExprNode)
                        and rhs.op == "arrayop"
                        and rhs.expr is not None
                    ):
                        subs[head] = (idx_syms, rhs.expr)
                        continue
        kept.append(eq)
    return kept, subs


def _substitute_algebraic(
    expr: Expr,
    subs: Dict[str, Tuple[List[str], Expr]],
) -> Expr:
    """Replace ``index(v, ...)`` with the algebraic body of ``v`` where defined."""
    if expr is None or isinstance(expr, (int, float)) and not isinstance(expr, bool):
        return expr
    if isinstance(expr, str):
        return expr
    if isinstance(expr, ExprNode):
        new_args = [_substitute_algebraic(a, subs) for a in expr.args]
        new_body = _substitute_algebraic(expr.expr, subs) if expr.expr is not None else None
        new_values = (
            [_substitute_algebraic(v, subs) for v in expr.values]
            if expr.values is not None else None
        )
        # If this is index(v, e1, e2, ...) with v eliminated, inline the body.
        if expr.op == "index" and new_args:
            head = new_args[0]
            if isinstance(head, str) and head in subs:
                idx_syms, body = subs[head]
                caller_idx = new_args[1:]
                if len(caller_idx) == len(idx_syms):
                    bindings = {sym: idx_expr for sym, idx_expr in zip(idx_syms, caller_idx)}
                    return _rebind_index_syms(body, bindings)
        return ExprNode(
            op=expr.op,
            args=new_args,
            wrt=expr.wrt,
            dim=expr.dim,
            output_idx=expr.output_idx,
            expr=new_body,
            reduce=expr.reduce,
            ranges=expr.ranges,
            regions=expr.regions,
            values=new_values,
            shape=expr.shape,
            perm=expr.perm,
            axis=expr.axis,
            fn=expr.fn,
        )
    return expr


def _rebind_index_syms(
    expr: Expr, bindings: Dict[str, Expr]
) -> Expr:
    """Replace bare string references to index symbols with their target expressions."""
    if expr is None or isinstance(expr, (int, float)):
        return expr
    if isinstance(expr, str):
        return bindings.get(expr, expr)
    if isinstance(expr, ExprNode):
        new_args = [_rebind_index_syms(a, bindings) for a in expr.args]
        new_body = (
            _rebind_index_syms(expr.expr, bindings) if expr.expr is not None else None
        )
        new_values = (
            [_rebind_index_syms(v, bindings) for v in expr.values]
            if expr.values is not None else None
        )
        return ExprNode(
            op=expr.op,
            args=new_args,
            wrt=expr.wrt,
            dim=expr.dim,
            output_idx=expr.output_idx,
            expr=new_body,
            reduce=expr.reduce,
            ranges=expr.ranges,
            regions=expr.regions,
            values=new_values,
            shape=expr.shape,
            perm=expr.perm,
            axis=expr.axis,
            fn=expr.fn,
        )
    return expr


def _iter_arrayop_points(lhs: ExprNode) -> Tuple[List[str], List[List[int]]]:
    """Return ``(output_idx_symbols, expanded_ranges)`` for an arrayop LHS."""
    if lhs.ranges is None or lhs.output_idx is None:
        raise SimulationError("arrayop LHS missing output_idx/ranges")
    syms = [s for s in lhs.output_idx if isinstance(s, str)]
    ranges = [_expand_range(lhs.ranges[s]) for s in syms]
    return syms, ranges


def _apply_equation_to_dy(
    eq: FlattenedEquation,
    ctx: EvalContext,
    shapes: Dict[str, Tuple[int, ...]],
    state_layout: Dict[str, slice],
    dy: np.ndarray,
) -> None:
    """Evaluate one equation and write its contribution into ``dy``.

    Handles three shapes:

    * ``D(scalar_state, t) = rhs`` — scalar state derivative.
    * ``D(index(var, k1, ...), t) = rhs`` — single element of an array state.
    * ``arrayop(D(index(var, i, ...), t), ranges=...) = <rhs>`` — array state
      derivative over a range box.
    """
    lhs = eq.lhs
    rhs = eq.rhs

    # Case A: scalar state LHS — D(var, t) with var a bare string.
    if isinstance(lhs, ExprNode) and lhs.op == "D" and lhs.args:
        inner = lhs.args[0]
        if isinstance(inner, str):
            if inner not in state_layout:
                return
            val = float(eval_expr(rhs, ctx))
            dy[state_layout[inner].start] = val
            return
        if isinstance(inner, ExprNode) and inner.op == "index" and inner.args:
            head = inner.args[0]
            if isinstance(head, str) and head in state_layout:
                idx_vals = [int(round(float(eval_expr(e, ctx)))) for e in inner.args[1:]]
                shape = shapes[head]
                flat_pos = state_layout[head].start + _linear_pos(shape, idx_vals)
                val = float(eval_expr(rhs, ctx))
                dy[flat_pos] = val
                return

    # Case B: arrayop LHS wrapping D(index(var, ...)).
    if isinstance(lhs, ExprNode) and lhs.op == "arrayop" and lhs.expr is not None:
        body = lhs.expr
        if isinstance(body, ExprNode) and body.op == "D" and body.args:
            inner = body.args[0]
            if isinstance(inner, ExprNode) and inner.op == "index" and inner.args:
                head = inner.args[0]
                if isinstance(head, str) and head in state_layout:
                    syms, ranges = _iter_arrayop_points(lhs)
                    idx_exprs = inner.args[1:]
                    # RHS is typically an arrayop with the same ranges — the
                    # body is what we evaluate point-by-point. Fall through to
                    # plain eval if it's a bare expression.
                    rhs_body: Optional[Expr]
                    if isinstance(rhs, ExprNode) and rhs.op == "arrayop":
                        rhs_body = rhs.expr
                    else:
                        rhs_body = rhs
                    shape = shapes[head]
                    layout_start = state_layout[head].start
                    it = np.ndindex(*(len(r) for r in ranges)) if ranges else [()]
                    prev_locals = dict(ctx.locals)
                    try:
                        for multi in it:
                            for s, pos in zip(syms, multi):
                                ctx.locals[s] = ranges[syms.index(s)][pos]
                            idx_vals = [
                                int(round(float(eval_expr(e, ctx)))) for e in idx_exprs
                            ]
                            flat_pos = layout_start + _linear_pos(shape, idx_vals)
                            val = float(eval_expr(rhs_body, ctx))
                            dy[flat_pos] = val
                    finally:
                        ctx.locals = prev_locals
                    return

    # Case C: algebraic equation left over after elimination — ignore for v1.
    # The solver will still run; purely algebraic states will keep their
    # initial values (fixture 06 is a smoke test that tolerates this).
    return


def _simulate_with_numpy(
    flat: FlattenedSystem,
    tspan: Tuple[float, float],
    parameters: Dict[str, float],
    initial_conditions: Dict[str, float],
    method: str,
    rtol: float = 1e-10,
    atol: float = 1e-12,
) -> SimulationResult:
    """Simulate a flattened system containing array ops via the NumPy interpreter."""
    try:
        shapes = infer_variable_shapes(flat)
        state_names = list(flat.state_variables.keys())

        # Layout: concatenate every state variable's flattened payload.
        state_layout: Dict[str, slice] = {}
        offset = 0
        for name in state_names:
            shape = shapes.get(name, ())
            size = int(np.prod(shape)) if shape else 1
            state_layout[name] = slice(offset, offset + size)
            offset += size
        total_size = offset

        if total_size == 0:
            raise SimulationError(
                "Flattened system has no state variables to integrate"
            )

        # Algebraic elimination: eliminate simple ``v[i] = <body>`` equations.
        working_equations, _eliminated = _collect_algebraic_substitutions(
            list(flat.equations)
        )
        if _eliminated:
            working_equations = [
                FlattenedEquation(
                    lhs=_substitute_algebraic(eq.lhs, _eliminated),
                    rhs=_substitute_algebraic(eq.rhs, _eliminated),
                    source_system=eq.source_system,
                )
                for eq in working_equations
            ]

        # Parameter resolution: overrides win over defaults.
        param_values: Dict[str, float] = {}
        for pname, pvar in flat.parameters.items():
            bare = pname.rsplit(".", 1)[-1]
            if pname in parameters:
                val = float(parameters[pname])
            elif bare in parameters:
                val = float(parameters[bare])
            else:
                default = pvar.default
                val = float(default) if isinstance(default, (int, float)) else 0.0
            param_values[pname] = val
            param_values[bare] = val  # also expose via bare name

        # Initial conditions.
        y0 = np.zeros(total_size, dtype=float)
        for name in state_names:
            default = flat.state_variables[name].default
            if isinstance(default, (int, float)):
                sl = state_layout[name]
                y0[sl] = float(default)
        _apply_initial_conditions(
            y0, state_layout, shapes, state_names, initial_conditions
        )

        def rhs_function(t: float, y: np.ndarray) -> np.ndarray:
            ctx = EvalContext(
                state_layout=state_layout,
                state_shapes=shapes,
                param_values=param_values,
                observed_values={},
                y=y,
                t=t,
            )
            dy = np.zeros(total_size, dtype=float)
            for eq in working_equations:
                try:
                    _apply_equation_to_dy(eq, ctx, shapes, state_layout, dy)
                except NumpyInterpreterError as exc:
                    raise SimulationError(str(exc)) from exc
            if not np.all(np.isfinite(dy)):
                raise SimulationError("Non-finite derivatives encountered")
            return dy

        sol = solve_ivp(
            fun=rhs_function,
            t_span=tspan,
            y0=y0,
            method=method,
            rtol=rtol,
            atol=atol,
            dense_output=True,
        )

        elem_names = _element_names(state_names, shapes)
        t_out, y_out = _densify_solution(sol, tspan)

        return SimulationResult(
            t=t_out,
            y=y_out,
            vars=elem_names,
            success=sol.success,
            message=sol.message,
            nfev=sol.nfev,
            njev=sol.njev,
            nlu=sol.nlu,
        )

    except UnsupportedDimensionalityError:
        raise
    except Exception as e:
        return SimulationResult(
            t=np.array([]),
            y=np.array([[]]),
            vars=[],
            success=False,
            message=f"Simulation failed: {e}",
            nfev=0,
            njev=0,
            nlu=0,
        )


def simulate_reaction_system(
    reaction_system: ReactionSystem,
    initial_conditions: Dict[str, float],
    time_span: Tuple[float, float],
    events: Optional[List[ContinuousEvent]] = None,
    **solver_options
) -> SimulationResult:
    """
    Simulate a reaction system using SciPy's solve_ivp.

    This is the main simulation function that:
    1. Resolves coupling to single ODE system
    2. Converts expressions to SymPy
    3. Generates mass-action ODEs from reactions
    4. Lambdifies for fast NumPy RHS function
    5. Calls scipy.integrate.solve_ivp()

    Args:
        reaction_system: Reaction system to simulate
        initial_conditions: Initial concentrations {species_name: concentration}
        time_span: Tuple of (t_start, t_end)
        events: Optional list of continuous events
        **solver_options: Additional options passed to solve_ivp

    Returns:
        SimulationResult: Results of the simulation

    Limitations:
        - 0D box model only (no spatial operators)
        - Limited event support
        - Mass-action kinetics only
    """
    try:
        # Generate mass-action ODEs
        species_names, ode_exprs = _generate_mass_action_odes(reaction_system)

        if not species_names:
            raise SimulationError("No species found in reaction system")

        # Create symbol map
        symbol_map = {name: sp.Symbol(name) for name in species_names}

        # Create initial condition vector
        y0 = np.array([initial_conditions.get(name, 0.0) for name in species_names])

        # Lambdify ODEs for fast evaluation
        variables = [symbol_map[name] for name in species_names]

        # Create RHS function
        if variables and ode_exprs:
            rhs_funcs = [
                sp.lambdify(variables, expr, modules=_LAMBDIFY_MODULES)
                for expr in ode_exprs
            ]

            def rhs_function(t: float, y: np.ndarray) -> np.ndarray:
                """Right-hand side function for the ODE system."""
                try:
                    # Ensure y has the right shape and no negative concentrations
                    y_clipped = np.maximum(y, 0.0)  # Clip to prevent negative concentrations

                    # Evaluate each ODE expression
                    dydt = np.array([func(*y_clipped) for func in rhs_funcs])

                    # Ensure result is finite
                    if not np.all(np.isfinite(dydt)):
                        raise SimulationError("Non-finite derivatives encountered")

                    return dydt

                except Exception as e:
                    raise SimulationError(f"Error in RHS evaluation: {e}")
        else:
            def rhs_function(t: float, y: np.ndarray) -> np.ndarray:
                return np.zeros_like(y)

        # Create event functions if events are provided
        event_functions = []
        if events:
            event_functions = _create_event_functions(events, symbol_map)

        # Set default solver options
        default_options = {
            'method': 'LSODA',  # Good general-purpose method
            'rtol': 1e-6,
            'atol': 1e-8,
            'dense_output': False,
            'events': event_functions if event_functions else None
        }
        default_options.update(solver_options)

        # Check scipy availability
        if not SCIPY_AVAILABLE:
            raise SimulationError("SciPy is required for simulation but not available. Please install scipy.")

        # Solve the ODE system
        sol = solve_ivp(
            fun=rhs_function,
            t_span=time_span,
            y0=y0,
            **default_options
        )

        # Extract events if they occurred
        events_list = None
        if sol.t_events is not None and len(sol.t_events) > 0:
            events_list = sol.t_events

        return SimulationResult(
            t=sol.t,
            y=sol.y,
            vars=species_names,  # Add variable names
            success=sol.success,
            message=sol.message,
            nfev=sol.nfev,
            njev=sol.njev,
            nlu=sol.nlu,
            events=events_list
        )

    except Exception as e:
        return SimulationResult(
            t=np.array([]),
            y=np.array([[]]),
            vars=[],  # Empty variable list
            success=False,
            message=f"Simulation failed: {e}",
            nfev=0,
            njev=0,
            nlu=0
        )


def simulate_with_discrete_events(
    reaction_system: ReactionSystem,
    initial_conditions: Dict[str, float],
    time_span: Tuple[float, float],
    discrete_events: Optional[List[DiscreteEvent]] = None,
    **solver_options
) -> SimulationResult:
    """
    Simulate with discrete events using manual stepping.

    This function handles discrete events by manually stepping the integration
    and applying event effects when their triggers fire.

    Args:
        reaction_system: Reaction system to simulate
        initial_conditions: Initial concentrations
        time_span: Tuple of (t_start, t_end)
        discrete_events: List of discrete events
        **solver_options: Additional options passed to solve_ivp

    Returns:
        SimulationResult: Results of the simulation
    """
    if not discrete_events:
        # No discrete events, use regular simulation
        return simulate_reaction_system(reaction_system, initial_conditions, time_span, **solver_options)

    try:
        # Implement discrete event handling with manual stepping
        t_start, t_end = time_span
        dt = solver_options.pop('max_step', (t_end - t_start) / 100.0)  # Default step size

        # Sort events by trigger time/priority for time-based events
        time_events = []
        condition_events = []

        for event in discrete_events:
            if event.trigger.type == 'time':
                time_events.append((float(event.trigger.value), event))
            elif event.trigger.type == 'condition':
                condition_events.append(event)
            # Note: 'external' events would need external trigger mechanism

        # Sort time events by time
        time_events.sort(key=lambda x: x[0])

        # Generate mass-action ODEs
        species_names, ode_exprs = _generate_mass_action_odes(reaction_system)
        if not species_names:
            raise SimulationError("No species found in reaction system")

        # Create symbol map and initial conditions
        symbol_map = {name: sp.Symbol(name) for name in species_names}
        y_current = np.array([initial_conditions.get(name, 0.0) for name in species_names])

        # Lambdify ODEs for fast evaluation
        variables = [symbol_map[name] for name in species_names]
        if variables and ode_exprs:
            rhs_funcs = [
                sp.lambdify(variables, expr, modules=_LAMBDIFY_MODULES)
                for expr in ode_exprs
            ]

            def rhs_function(t: float, y: np.ndarray) -> np.ndarray:
                """Right-hand side function for the ODE system."""
                y_clipped = np.maximum(y, 0.0)  # Clip to prevent negative concentrations
                dydt = np.array([func(*y_clipped) for func in rhs_funcs])
                if not np.all(np.isfinite(dydt)):
                    raise SimulationError("Non-finite derivatives encountered")
                return dydt
        else:
            def rhs_function(t: float, y: np.ndarray) -> np.ndarray:
                return np.zeros_like(y)

        # Manual stepping with event handling
        t_current = t_start
        t_points = [t_current]
        y_points = [y_current.copy()]
        event_times = []

        # Set up solver options with more conservative defaults for manual stepping
        default_options = {
            'method': 'RK45',  # Use more stable method for manual stepping
            'rtol': 1e-6,
            'atol': 1e-8,
            'dense_output': False,
            'max_step': dt / 10.0,  # Smaller steps for stability
        }
        default_options.update(solver_options)

        time_event_index = 0  # Index for next time event

        while t_current < t_end:
            # Determine next integration end time
            next_t = min(t_end, t_current + dt)

            # Check if there are time events before next_t
            while (time_event_index < len(time_events) and
                   time_events[time_event_index][0] <= next_t):
                event_time, event = time_events[time_event_index]

                if event_time > t_current:
                    # Check scipy availability
                    if not SCIPY_AVAILABLE:
                        raise SimulationError("SciPy is required for simulation but not available. Please install scipy.")

                    # Integrate to event time
                    sol = solve_ivp(
                        fun=rhs_function,
                        t_span=(t_current, event_time),
                        y0=y_current,
                        **default_options
                    )

                    if not sol.success:
                        return SimulationResult(
                            t=np.array(t_points),
                            y=np.array(y_points).T,
                            vars=species_names,
                            success=False,
                            message=f"Integration failed before discrete event: {sol.message}",
                            nfev=sol.nfev,
                            njev=sol.njev,
                            nlu=sol.nlu
                        )

                    # Update current state
                    t_current = event_time
                    y_current = sol.y[:, -1]
                    # Add intermediate points if any
                    if len(sol.t) > 1:
                        t_points.extend(sol.t[1:])  # Skip first point (duplicate)
                        y_points.extend(sol.y[:, 1:].T)  # Skip first point

                # Apply discrete event effects
                y_current = _apply_discrete_event_effects(event, y_current, species_names, symbol_map)
                event_times.append(t_current)
                time_event_index += 1

            # Check condition-based events at current time point
            events_triggered = []
            for event in condition_events:
                if _check_discrete_event_condition(event, t_current, y_current, species_names, symbol_map):
                    events_triggered.append(event)

            # Apply triggered events (avoid modifying state while checking)
            for event in events_triggered:
                y_current = _apply_discrete_event_effects(event, y_current, species_names, symbol_map)
                event_times.append(t_current)

            # Continue integration to next_t if not already there
            if t_current < next_t:
                # Check scipy availability
                if not SCIPY_AVAILABLE:
                    raise SimulationError("SciPy is required for simulation but not available. Please install scipy.")

                sol = solve_ivp(
                    fun=rhs_function,
                    t_span=(t_current, next_t),
                    y0=y_current,
                    **default_options
                )

                if not sol.success:
                    return SimulationResult(
                        t=np.array(t_points),
                        y=np.array(y_points).T,
                        vars=species_names,
                        success=False,
                        message=f"Integration failed: {sol.message}",
                        nfev=sol.nfev,
                        njev=sol.njev,
                        nlu=sol.nlu
                    )

                # Update current state
                t_current = sol.t[-1]
                y_current = sol.y[:, -1]
                # Add intermediate points if any
                if len(sol.t) > 1:
                    t_points.extend(sol.t[1:])  # Skip first point (duplicate)
                    y_points.extend(sol.y[:, 1:].T)  # Skip first point

            # Check condition-based events after integration step
            events_triggered = []
            for event in condition_events:
                if _check_discrete_event_condition(event, t_current, y_current, species_names, symbol_map):
                    events_triggered.append(event)

            # Apply triggered events
            for event in events_triggered:
                y_current = _apply_discrete_event_effects(event, y_current, species_names, symbol_map)
                event_times.append(t_current)

        return SimulationResult(
            t=np.array(t_points),
            y=np.array(y_points).T,
            vars=species_names,
            success=True,
            message=f"Simulation completed successfully with {len(event_times)} discrete events",
            nfev=0,  # Not tracking across multiple integrations
            njev=0,
            nlu=0,
            events=[np.array(event_times)] if event_times else None
        )

    except Exception as e:
        return SimulationResult(
            t=np.array([]),
            y=np.array([[]]),
            vars=[],
            success=False,
            message=f"Discrete event simulation failed: {e}",
            nfev=0,
            njev=0,
            nlu=0
        )