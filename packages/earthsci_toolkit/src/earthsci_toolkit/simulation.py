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
from typing import Dict, List, Tuple, Optional, Union, Any, Callable
from dataclasses import dataclass

# Optional scipy import - only needed for actual simulation
try:
    from scipy.integrate import solve_ivp
    SCIPY_AVAILABLE = True
except (ImportError, ValueError):
    # ValueError can occur due to numpy/scipy compatibility issues
    SCIPY_AVAILABLE = False
    solve_ivp = None

from .esm_types import (
    Model, ReactionSystem, Reaction, Parameter,
    ContinuousEvent, DiscreteEvent, Expr, ExprNode, EsmFile,
    AffectEquation, FunctionalAffect,
)
from .flatten import (
    FlattenedSystem,
    UnsupportedDimensionalityError,
    _lhs_dependent_var,
    flatten,
)
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


def _expr_to_sympy(expr: Expr, symbol_map: Dict[str, sp.Symbol]) -> sp.Expr:
    """
    Convert ESM Expr to SymPy expression.

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
                # Create a new symbol if not found
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
        elif expr.op == '^' or expr.op == '**':
            if len(sympy_args) != 2:
                raise SimulationError(f"Power requires exactly 2 arguments, got {len(sympy_args)}")
            return sympy_args[0] ** sympy_args[1]
        elif expr.op == 'exp':
            if len(sympy_args) != 1:
                raise SimulationError(f"Exponential requires exactly 1 argument, got {len(sympy_args)}")
            return sp.exp(sympy_args[0])
        elif expr.op == 'log':
            if len(sympy_args) != 1:
                raise SimulationError(f"Logarithm requires exactly 1 argument, got {len(sympy_args)}")
            return sp.log(sympy_args[0])
        elif expr.op == 'sin':
            if len(sympy_args) != 1:
                raise SimulationError(f"Sine requires exactly 1 argument, got {len(sympy_args)}")
            return sp.sin(sympy_args[0])
        elif expr.op == 'cos':
            if len(sympy_args) != 1:
                raise SimulationError(f"Cosine requires exactly 1 argument, got {len(sympy_args)}")
            return sp.cos(sympy_args[0])
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
    parameter_overrides: Dict[str, float],
) -> Tuple[List[str], List[sp.Expr], Dict[str, sp.Symbol]]:
    """Build the SymPy ODE RHS expressions from a FlattenedSystem.

    Returns
    -------
    state_names:
        Dot-namespaced state variable names in the order they appear in the
        result vector.
    rhs_exprs:
        Per-state SymPy expression for ``dy_i/dt``. State variables without an
        equation default to ``0``.
    symbol_map:
        Mapping from namespaced variable name to SymPy symbol (for use by event
        functions and parameter substitution).
    """
    state_names = list(flat.state_variables.keys())
    parameter_names = list(flat.parameters.keys())

    symbol_map: Dict[str, sp.Symbol] = {}
    for name in state_names + parameter_names:
        symbol_map[name] = sp.Symbol(name)

    state_to_rhs: Dict[str, sp.Expr] = {}
    for eq in flat.equations:
        dep = _lhs_dependent_var(eq.lhs)
        if dep is None:
            continue
        if dep in flat.state_variables:
            state_to_rhs[dep] = _expr_to_sympy(eq.rhs, dict(symbol_map))

    rhs_exprs: List[sp.Expr] = []
    for name in state_names:
        rhs_exprs.append(state_to_rhs.get(name, sp.Float(0)))

    # Resolve parameter values: caller overrides win, then defaults from the
    # flattened parameter metadata, then 0.
    param_subs: Dict[sp.Symbol, float] = {}
    for pname in parameter_names:
        bare = pname.rsplit(".", 1)[-1]
        if pname in parameter_overrides:
            value = parameter_overrides[pname]
        elif bare in parameter_overrides:
            value = parameter_overrides[bare]
        else:
            default = flat.parameters[pname].default
            value = float(default) if isinstance(default, (int, float)) else 0.0
        param_subs[symbol_map[pname]] = sp.Float(value)

    if param_subs:
        rhs_exprs = [
            (expr.subs(param_subs) if hasattr(expr, "subs") else expr)
            for expr in rhs_exprs
        ]

    return state_names, rhs_exprs, symbol_map


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
            condition_func = sp.lambdify(variables, condition_expr, 'numpy')

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
        eval_func = sp.lambdify(variables, sympy_expr, 'numpy')
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


def simulate(
    file_or_flat: Union[EsmFile, FlattenedSystem],
    tspan: Tuple[float, float],
    parameters: Optional[Dict[str, float]] = None,
    initial_conditions: Optional[Dict[str, float]] = None,
    method: str = 'BDF',
    file: Optional[EsmFile] = None,
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

    try:
        state_names, rhs_exprs, symbol_map = _flat_to_sympy_rhs(flat, parameters)

        if not state_names:
            raise SimulationError(
                "Flattened system has no state variables to integrate"
            )

        # Initial conditions: dot-namespaced wins, then bare name, then default.
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

        state_symbols = [symbol_map[name] for name in state_names]
        rhs_funcs = [sp.lambdify(state_symbols, expr, "numpy") for expr in rhs_exprs]

        def rhs_function(t: float, y: np.ndarray) -> np.ndarray:
            y_clipped = np.maximum(y, 0.0)
            dydt = np.array([func(*y_clipped) for func in rhs_funcs])
            if not np.all(np.isfinite(dydt)):
                raise SimulationError("Non-finite derivatives encountered")
            return dydt

        event_functions: List[Callable] = []
        if flat.continuous_events:
            event_functions = _create_event_functions(flat.continuous_events, symbol_map)

        solver_options: Dict[str, Any] = {
            "method": method,
            "rtol": 1e-6,
            "atol": 1e-8,
            "dense_output": False,
        }
        if event_functions:
            solver_options["events"] = event_functions

        sol = solve_ivp(fun=rhs_function, t_span=tspan, y0=y0, **solver_options)

        return SimulationResult(
            t=sol.t,
            y=sol.y,
            vars=state_names,
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
            rhs_funcs = [sp.lambdify(variables, expr, 'numpy') for expr in ode_exprs]

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
            rhs_funcs = [sp.lambdify(variables, expr, 'numpy') for expr in ode_exprs]

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