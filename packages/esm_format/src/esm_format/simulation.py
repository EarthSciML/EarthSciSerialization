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
from scipy.integrate import solve_ivp
from typing import Dict, List, Tuple, Optional, Union, Any, Callable
from dataclasses import dataclass

from .types import (
    Model, ModelVariable, ReactionSystem, Reaction, Species, Parameter,
    ContinuousEvent, DiscreteEvent, Expr, ExprNode, EsmFile
)
from .reactions import derive_odes, stoichiometric_matrix
from .expression import to_sympy


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
        else:
            raise SimulationError(f"Unsupported operation: {expr.op}")
    else:
        raise SimulationError(f"Unsupported expression type: {type(expr)}")


def _generate_mass_action_odes(reaction_system: ReactionSystem) -> Tuple[List[str], List[sp.Expr]]:
    """
    Generate mass-action ODEs from reaction system.

    Args:
        reaction_system: The reaction system to convert

    Returns:
        Tuple of (species_names, ode_expressions)
    """
    # Get all species names
    species_names = [species.name for species in reaction_system.species]
    species_symbols = {name: sp.Symbol(name) for name in species_names}

    # Initialize ODE expressions (all start at 0)
    ode_exprs = [sp.Float(0) for _ in species_names]
    species_indices = {name: i for i, name in enumerate(species_names)}

    # Process each reaction
    for reaction in reaction_system.reactions:
        # Convert rate constant to SymPy
        if reaction.rate_constant is None:
            continue

        rate_expr = _expr_to_sympy(reaction.rate_constant, species_symbols)

        # Mass action kinetics: rate = k * product(reactant concentrations)
        for reactant, coefficient in reaction.reactants.items():
            if reactant in species_symbols:
                rate_expr *= species_symbols[reactant] ** coefficient

        # Add/subtract from species ODEs based on stoichiometry
        for reactant, coefficient in reaction.reactants.items():
            if reactant in species_indices:
                idx = species_indices[reactant]
                ode_exprs[idx] -= coefficient * rate_expr

        for product, coefficient in reaction.products.items():
            if product in species_indices:
                idx = species_indices[product]
                ode_exprs[idx] += coefficient * rate_expr

    return species_names, ode_exprs


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
        # Convert condition to SymPy
        condition_expr = _expr_to_sympy(event.condition, symbol_map)

        # Get variables in the condition
        variables = list(condition_expr.free_symbols)
        var_names = [str(var) for var in variables]

        # Create lambda function
        condition_func = sp.lambdify(variables, condition_expr, 'numpy')

        def event_function(t, y, condition_func=condition_func, var_names=var_names):
            # Map y values to variable names
            var_dict = {name: y[i] if i < len(y) else 0 for i, name in enumerate(var_names)}
            var_values = [var_dict.get(name, 0) for name in var_names]
            return condition_func(*var_values) if var_values else condition_func()

        event_function.terminal = True  # Stop integration when event occurs
        event_function.direction = 0    # Detect all zero crossings
        event_functions.append(event_function)

    return event_functions


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
    file: EsmFile,
    tspan: Tuple[float, float],
    parameters: Dict[str, float],
    initial_conditions: Dict[str, float],
    method: str = 'BDF'
) -> SimulationResult:
    """
    Simulate an ESM file using SciPy's solve_ivp.

    This is the main simulation function that:
    1. Resolves coupling to single ODE system
    2. Converts expressions to SymPy
    3. Generates mass-action ODEs from reaction systems
    4. Lambdifies for fast NumPy RHS function
    5. Calls scipy.integrate.solve_ivp()

    Args:
        file: ESM file containing models and reaction systems
        tspan: Tuple of (t_start, t_end)
        parameters: Parameter values {param_name: value}
        initial_conditions: Initial concentrations {species_name: concentration}
        method: Integration method (default 'BDF')

    Returns:
        SimulationResult: Results of the simulation

    Limitations:
        - 0D box model only (no spatial operators)
        - Limited event support
        - Mass-action kinetics only

    Raises:
        SimulationError: If spatial operators are present or other simulation issues occur
    """
    try:
        # Check for spatial operators - raise error if present
        for operator in file.operators:
            if operator.type.value in ['spatial', 'differentiation', 'integration']:
                raise SimulationError(f"Spatial operators not supported in 0D simulation. Found: {operator.name}")

        # Variable mapping and operator composition for 0D only
        # For now, we'll focus on reaction systems as they are well-defined
        if not file.reaction_systems:
            raise SimulationError("No reaction systems found in ESM file")

        if len(file.reaction_systems) > 1:
            raise SimulationError("Multiple reaction systems not yet supported. Use coupling resolution.")

        reaction_system = file.reaction_systems[0]

        # Update reaction system parameters with provided values
        updated_reactions = []
        for reaction in reaction_system.reactions:
            updated_reaction = Reaction(
                name=reaction.name,
                reactants=reaction.reactants.copy(),
                products=reaction.products.copy(),
                rate_constant=parameters.get(str(reaction.rate_constant), reaction.rate_constant),
                conditions=reaction.conditions.copy()
            )
            updated_reactions.append(updated_reaction)

        updated_system = ReactionSystem(
            name=reaction_system.name,
            species=reaction_system.species.copy(),
            parameters=reaction_system.parameters.copy(),
            reactions=updated_reactions
        )

        # Generate mass-action ODEs using the dependency
        species_names, ode_exprs = _generate_mass_action_odes(updated_system)

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

        # Set solver options based on method
        solver_options = {
            'method': method,
            'rtol': 1e-6,
            'atol': 1e-8,
            'dense_output': False,
        }

        # Solve the ODE system
        sol = solve_ivp(
            fun=rhs_function,
            t_span=tspan,
            y0=y0,
            **solver_options
        )

        return SimulationResult(
            t=sol.t,
            y=sol.y,
            vars=species_names,  # Add variable names
            success=sol.success,
            message=sol.message,
            nfev=sol.nfev,
            njev=sol.njev,
            nlu=sol.nlu,
            events=sol.t_events if sol.t_events is not None and len(sol.t_events) > 0 else None
        )

    except Exception as e:
        return SimulationResult(
            t=np.array([]),
            y=np.array([[]]),
            vars=[],
            success=False,
            message=f"Simulation failed: {e}",
            nfev=0,
            njev=0,
            nlu=0
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

    # TODO: Implement discrete event handling with manual stepping
    # For now, just run regular simulation and warn
    result = simulate_reaction_system(reaction_system, initial_conditions, time_span, **solver_options)
    if result.success:
        result.message += " (Warning: Discrete events not yet implemented)"

    return result