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


def derive_odes(system: ReactionSystem) -> Model:
    """
    Derive ODEs from a reaction system using mass action kinetics.

    Generates a system of ordinary differential equations from a reaction network
    based on the stoichiometry and rate laws. Handles source reactions (null
    substrates) and sink reactions (null products).

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

    # Create species concentration variables
    species_names = [species.name for species in system.species]
    variables = {}

    # Add state variables for species concentrations
    for species in system.species:
        variables[species.name] = ModelVariable(
            type='state',
            units=species.units,
            description=f"Concentration of {species.name}",
        )

    # Add parameter variables
    for param in system.parameters:
        variables[param.name] = ModelVariable(
            type='parameter',
            units=param.units,
            description=param.description,
            default=param.value if isinstance(param.value, (int, float)) else None,
            expression=param.value if not isinstance(param.value, (int, float)) else None,
        )

    # Generate ODE equations using mass action kinetics
    equations = []

    # Initialize rate of change for each species
    species_rates = {name: 0 for name in species_names}

    for reaction in system.reactions:
        # Build rate expression using mass action kinetics
        # Rate = k * [reactant1]^coeff1 * [reactant2]^coeff2 * ...

        if reaction.rate_constant is None:
            raise ValueError(f"Reaction {reaction.name} must have a rate constant")

        rate_expr = reaction.rate_constant

        # Add reactant terms (mass action kinetics)
        for reactant, coeff in reaction.reactants.items():
            if reactant not in species_names:
                raise ValueError(f"Reactant {reactant} not found in species list")

            # For mass action: rate *= [reactant]^coeff
            if coeff == 1:
                # Simple multiplication
                rate_expr = _multiply_expressions(rate_expr, reactant)
            else:
                # Power term
                power_expr = _power_expression(reactant, coeff)
                rate_expr = _multiply_expressions(rate_expr, power_expr)

        # Apply stoichiometric coefficients to species rates
        # For each species, d[species]/dt += (product_coeff - reactant_coeff) * rate

        for species_name in species_names:
            net_stoich_coeff = 0

            # Subtract reactant coefficient (consumed)
            if species_name in reaction.reactants:
                net_stoich_coeff -= reaction.reactants[species_name]

            # Add product coefficient (produced)
            if species_name in reaction.products:
                net_stoich_coeff += reaction.products[species_name]

            if net_stoich_coeff != 0:
                # Add this reaction's contribution to species rate
                contribution = _multiply_expressions(net_stoich_coeff, rate_expr)
                species_rates[species_name] = _add_expressions(species_rates[species_name], contribution)

    # Create differential equations
    for species_name in species_names:
        if species_rates[species_name] != 0:  # Only create equations for species with non-zero rates
            # d[species]/dt = rate_expression
            lhs = ExprNode(op="D", args=[species_name], wrt="t")
            equations.append(Equation(lhs=lhs, rhs=species_rates[species_name]))

    # Handle constraint equations (algebraic equations)
    # These would be derived from conservation laws or equilibrium assumptions
    # For now, we don't add any constraint equations - they would be handled
    # separately based on the specific system requirements

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