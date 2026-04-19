"""
Reaction system analysis and ODE generation functions.

This module provides functions to:
1. Generate ODE systems from reaction systems using mass action kinetics
2. Compute stoichiometric matrices for reaction networks
3. Handle substrate and product matrices separately
"""

import numpy as np
import sympy as sp
from typing import Dict, List, Optional, Set, Tuple

from .esm_types import ReactionSystem, Reaction, Species, Model, ModelVariable, Equation, Expr, ExprNode
from .expression import to_sympy, from_sympy


def lower_reactions_to_equations(
    reactions: List[Reaction],
    species: List[Species],
) -> List[Equation]:
    """
    Lower a list of reactions into ODE equations using mass-action kinetics.

    Canonical mass-action helper shared by :func:`derive_odes` (which wraps the
    result in a :class:`Model`) and the SciPy simulation path in
    ``simulation.py`` (which converts these equations to SymPy for lambdify).
    Mirrors the single-implementation pattern used by the Rust and Julia
    toolkits — there is exactly one mass-action lowering in Python.

    Builds ``d[species]/dt = sum_r net_stoich(species, r) * rate(r)`` expressions
    using ESM :class:`ExprNode` trees (not SymPy), so the output is directly
    usable by any consumer that handles the ESM expression AST.

    Args:
        reactions: List of reactions in the system.
        species: List of species in the system. Used for both ordering and
            validation (reactants referencing unknown species are rejected).

    Returns:
        List of :class:`Equation` objects of the form
        ``D(species, t) = rhs``. Only species with non-zero net rates are
        included; species that don't participate in any reaction are omitted.

    Raises:
        ValueError: If any reaction has no rate_constant, or references a
            reactant that isn't in the species list.
    """
    species_names = [s.name for s in species]
    species_rates: Dict[str, Expr] = {name: 0 for name in species_names}

    for reaction in reactions:
        if reaction.rate_constant is None:
            raise ValueError(f"Reaction {reaction.name} must have a rate constant")

        for reactant in reaction.reactants:
            if reactant not in species_names:
                raise ValueError(f"Reactant {reactant} not found in species list")

        # The schema's ``rate`` field is a full rate expression, not a bare
        # coefficient. If the user already wrote ``k*A*B`` we must NOT multiply
        # by substrates again (that yields ``k*A^2*B^2``). Mirror Julia's
        # ``mass_action_rate`` and Rust's ``enhance_rate_with_mass_action``:
        # detect whether the rate already references any substrate and, if so,
        # treat it as the full rate law; otherwise apply mass-action expansion.
        rate_expr: Expr = reaction.rate_constant
        substrate_names = list(reaction.reactants.keys())
        rate_has_substrate = any(
            _expr_contains_var(rate_expr, name) for name in substrate_names
        )

        if not rate_has_substrate:
            for reactant, coeff in reaction.reactants.items():
                if coeff == 1:
                    rate_expr = _multiply_expressions(rate_expr, reactant)
                else:
                    power_expr = _power_expression(reactant, coeff)
                    rate_expr = _multiply_expressions(rate_expr, power_expr)

        # Apply net stoichiometry (product_coeff - reactant_coeff) to species rates.
        for species_name in species_names:
            net_stoich_coeff = 0
            if species_name in reaction.reactants:
                net_stoich_coeff -= reaction.reactants[species_name]
            if species_name in reaction.products:
                net_stoich_coeff += reaction.products[species_name]

            if net_stoich_coeff != 0:
                contribution = _multiply_expressions(net_stoich_coeff, rate_expr)
                species_rates[species_name] = _add_expressions(
                    species_rates[species_name], contribution
                )

    equations: List[Equation] = []
    for species_name in species_names:
        if species_rates[species_name] != 0:
            lhs = ExprNode(op="D", args=[species_name], wrt="t")
            equations.append(Equation(lhs=lhs, rhs=species_rates[species_name]))

    return equations


def derive_odes(system: ReactionSystem) -> Model:
    """
    Derive ODEs from a reaction system using mass action kinetics.

    Thin wrapper around :func:`lower_reactions_to_equations` that bundles the
    resulting equations with a ``variables`` dict (state variables for species,
    parameter variables for rate constants) into a :class:`Model`. Handles
    source reactions (null substrates) and sink reactions (null products).

    Args:
        system: ReactionSystem containing species, reactions, and parameters

    Returns:
        Model: Mathematical model with ODE equations for each species

    Raises:
        ValueError: If system is empty or contains invalid reactions
    """
    if not system.species:
        raise ValueError("ReactionSystem must contain at least one species")

    if not system.reactions:
        raise ValueError("ReactionSystem must contain at least one reaction")

    variables: Dict[str, ModelVariable] = {}

    for species in system.species:
        variables[species.name] = ModelVariable(
            type='state',
            units=species.units,
            description=f"Concentration of {species.name}",
        )

    for param in system.parameters:
        variables[param.name] = ModelVariable(
            type='parameter',
            units=param.units,
            description=param.description,
            default=param.value if isinstance(param.value, (int, float)) else None,
            expression=param.value if not isinstance(param.value, (int, float)) else None,
        )

    equations = lower_reactions_to_equations(system.reactions, system.species)

    return Model(
        name=f"{system.name}_odes",
        variables=variables,
        equations=equations,
        metadata={
            "derived_from": system.name,
            "generation_method": "mass_action_kinetics"
        }
    )


def stoichiometric_matrix(system: ReactionSystem) -> np.ndarray:
    """
    Compute the net stoichiometric matrix for a reaction system.

    The stoichiometric matrix S is defined such that S[i,j] gives the net
    stoichiometric coefficient of species i in reaction j. Negative values
    indicate reactants (consumed), positive values indicate products (formed).

    Args:
        system: ReactionSystem containing species and reactions

    Returns:
        np.ndarray: Stoichiometric matrix with shape (n_species, n_reactions)
                   where S[i,j] = net stoichiometric coefficient of species i in reaction j

    Raises:
        ValueError: If system is empty
    """
    if not system.species or not system.reactions:
        return np.array([])

    species_names = [s.name for s in system.species]
    n_species = len(species_names)
    n_reactions = len(system.reactions)

    matrix = np.zeros((n_species, n_reactions))

    for j, reaction in enumerate(system.reactions):
        for i, species_name in enumerate(species_names):
            net_coeff = 0

            # Subtract reactant coefficient (negative contribution)
            if species_name in reaction.reactants:
                net_coeff -= reaction.reactants[species_name]

            # Add product coefficient (positive contribution)
            if species_name in reaction.products:
                net_coeff += reaction.products[species_name]

            matrix[i, j] = net_coeff

    return matrix


def substrate_matrix(system: ReactionSystem) -> np.ndarray:
    """
    Compute the substrate (reactant) stoichiometric matrix.

    The substrate matrix gives only the reactant stoichiometric coefficients.
    All entries are non-negative, with S[i,j] giving the coefficient of
    species i as a reactant in reaction j.

    Args:
        system: ReactionSystem containing species and reactions

    Returns:
        np.ndarray: Substrate matrix with shape (n_species, n_reactions)
                   where S[i,j] = reactant coefficient of species i in reaction j
    """
    if not system.species or not system.reactions:
        return np.array([])

    species_names = [s.name for s in system.species]
    n_species = len(species_names)
    n_reactions = len(system.reactions)

    matrix = np.zeros((n_species, n_reactions))

    for j, reaction in enumerate(system.reactions):
        for i, species_name in enumerate(species_names):
            if species_name in reaction.reactants:
                matrix[i, j] = reaction.reactants[species_name]

    return matrix


def product_matrix(system: ReactionSystem) -> np.ndarray:
    """
    Compute the product stoichiometric matrix.

    The product matrix gives only the product stoichiometric coefficients.
    All entries are non-negative, with P[i,j] giving the coefficient of
    species i as a product in reaction j.

    Args:
        system: ReactionSystem containing species and reactions

    Returns:
        np.ndarray: Product matrix with shape (n_species, n_reactions)
                   where P[i,j] = product coefficient of species i in reaction j
    """
    if not system.species or not system.reactions:
        return np.array([])

    species_names = [s.name for s in system.species]
    n_species = len(species_names)
    n_reactions = len(system.reactions)

    matrix = np.zeros((n_species, n_reactions))

    for j, reaction in enumerate(system.reactions):
        for i, species_name in enumerate(species_names):
            if species_name in reaction.products:
                matrix[i, j] = reaction.products[species_name]

    return matrix


# Helper functions for expression manipulation

def _multiply_expressions(expr1: Expr, expr2: Expr) -> Expr:
    """Multiply two expressions."""
    if expr1 == 0:
        return 0
    if expr2 == 0:
        return 0
    if expr1 == 1:
        return expr2
    if expr2 == 1:
        return expr1

    return ExprNode(op="*", args=[expr1, expr2])


def _add_expressions(expr1: Expr, expr2: Expr) -> Expr:
    """Add two expressions."""
    if expr1 == 0:
        return expr2
    if expr2 == 0:
        return expr1

    return ExprNode(op="+", args=[expr1, expr2])


def _power_expression(base: Expr, exponent: float) -> Expr:
    """Create a power expression."""
    if exponent == 1:
        return base
    if exponent == 0:
        return 1

    return ExprNode(op="^", args=[base, exponent])


def _expr_contains_var(expr: Expr, name: str) -> bool:
    """Return True if the Expr tree references a bare variable ``name``."""
    if isinstance(expr, str):
        return expr == name
    if isinstance(expr, ExprNode):
        for arg in expr.args:
            if _expr_contains_var(arg, name):
                return True
    return False