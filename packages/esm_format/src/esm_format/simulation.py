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
except ImportError:
    SCIPY_AVAILABLE = False
    solve_ivp = None

from .esm_types import (
    Model, ModelVariable, ReactionSystem, Reaction, Species, Parameter,
    ContinuousEvent, DiscreteEvent, Expr, ExprNode, EsmFile,
    AffectEquation, FunctionalAffect, CouplingType
)
from .reactions import derive_odes, stoichiometric_matrix
from .expression import to_sympy
from .coupling_graph import construct_coupling_graph, CouplingGraph


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


def _resolve_coupled_systems(file: EsmFile, parameters: Dict[str, float]) -> Tuple[List[str], List[sp.Expr]]:
    """
    Resolve coupling between multiple reaction systems and generate combined ODE system.

    Args:
        file: ESM file containing multiple reaction systems and coupling rules
        parameters: Parameter values to substitute

    Returns:
        Tuple of (species_names, ode_expressions) for the coupled system

    Raises:
        SimulationError: If coupling cannot be resolved or spatial operators are present
    """
    try:
        # Construct coupling graph to analyze dependencies
        coupling_graph = construct_coupling_graph(file)

        # Get execution order based on coupling dependencies
        execution_order = coupling_graph.get_execution_order()

        # Collect all species from all reaction systems
        all_species = {}  # name -> species object
        all_species_names = []
        species_to_system = {}  # species name -> system name

        for system_name, system in file.reaction_systems.items():
            for species in system.species:
                if species.name not in all_species:
                    all_species[species.name] = species
                    all_species_names.append(species.name)
                species_to_system[species.name] = system_name

        # Initialize combined ODE expressions (all start at 0)
        combined_ode_exprs = [sp.Float(0) for _ in all_species_names]
        species_indices = {name: i for i, name in enumerate(all_species_names)}

        # Process each reaction system
        for system_name, system in file.reaction_systems.items():
            # Update system parameters
            updated_reactions = []
            for reaction in system.reactions:
                updated_reaction = Reaction(
                    name=reaction.name,
                    reactants=reaction.reactants.copy(),
                    products=reaction.products.copy(),
                    rate_constant=parameters.get(str(reaction.rate_constant), reaction.rate_constant),
                    conditions=reaction.conditions.copy()
                )
                updated_reactions.append(updated_reaction)

            updated_system = ReactionSystem(
                name=system.name,
                species=system.species.copy(),
                parameters=system.parameters.copy(),
                reactions=updated_reactions
            )

            # Generate ODEs for this system
            system_species_names, system_ode_exprs = _generate_mass_action_odes(updated_system)

            # Add system's contributions to the combined ODEs
            for i, species_name in enumerate(system_species_names):
                if species_name in species_indices:
                    global_idx = species_indices[species_name]
                    combined_ode_exprs[global_idx] += system_ode_exprs[i]

        # Apply coupling rules
        _apply_coupling_rules(file, coupling_graph, all_species_names, combined_ode_exprs, species_indices)

        return all_species_names, combined_ode_exprs

    except Exception as e:
        raise SimulationError(f"Failed to resolve coupled systems: {e}")


def _apply_coupling_rules(
    file: EsmFile,
    coupling_graph: CouplingGraph,
    species_names: List[str],
    ode_exprs: List[sp.Expr],
    species_indices: Dict[str, int]
) -> None:
    """
    Apply coupling rules from the ESM file to modify ODE expressions.

    Args:
        file: ESM file containing coupling rules
        coupling_graph: Constructed coupling graph
        species_names: List of all species names
        ode_exprs: List of ODE expressions to modify (modified in-place)
        species_indices: Mapping from species names to indices
    """
    if not hasattr(file, 'couplings') or not file.couplings:
        return

    # Create symbol map for all species
    symbol_map = {name: sp.Symbol(name) for name in species_names}

    # Process each coupling entry
    for coupling in file.couplings:
        if coupling.coupling_type == CouplingType.VARIABLE_MAP:
            # Handle variable mapping coupling
            if coupling.from_var and coupling.to_var:
                # Extract species names from variable references
                # For now, assume direct species name mapping
                from_species = coupling.from_var.split('.')[-1]  # Get last part of scoped reference
                to_species = coupling.to_var.split('.')[-1]

                # Apply transformation if specified
                if coupling.transform and from_species in species_indices and to_species in species_indices:
                    from_idx = species_indices[from_species]
                    to_idx = species_indices[to_species]

                    # Simple linear transformation: apply factor
                    if coupling.factor and coupling.factor != 1.0:
                        # Add coupling term to target species
                        coupling_term = coupling.factor * symbol_map[from_species]
                        ode_exprs[to_idx] += coupling_term
                        # Subtract from source species to conserve mass
                        ode_exprs[from_idx] -= coupling_term

        elif coupling.coupling_type == CouplingType.COUPLE2:
            # Handle bidirectional coupling between systems
            if coupling.systems and len(coupling.systems) == 2:
                # For now, implement simple exchange coupling
                # This would need more sophisticated implementation based on connector equations
                pass

        # Other coupling types (OPERATOR_COMPOSE, etc.) would be implemented here
        # For now, focus on VARIABLE_MAP which is most common


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
        # Handle multiple conditions - create a function for each condition
        for condition in event.conditions:
            # Convert condition to SymPy
            condition_expr = _expr_to_sympy(condition, symbol_map)

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

        # Handle multiple reaction systems with coupling resolution
        if len(file.reaction_systems) == 1:
            # Single system case - existing behavior
            reaction_system = list(file.reaction_systems.values())[0]

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
        else:
            # Multiple systems case - resolve coupling
            species_names, ode_exprs = _resolve_coupled_systems(file, parameters)

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

        # Check scipy availability
        if not SCIPY_AVAILABLE:
            raise SimulationError("SciPy is required for simulation but not available. Please install scipy.")

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