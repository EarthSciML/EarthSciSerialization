#!/usr/bin/env python3
"""
Basic test for reactions.py implementation.
This is a simple verification that our implementation works correctly.
"""

import sys
import os
import numpy as np

# Add the src directory to the path so we can import our module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from esm_format import (
    ReactionSystem, Reaction, Species, Parameter,
    derive_odes, stoichiometric_matrix, substrate_matrix, product_matrix
)


def test_simple_reaction_system():
    """Test with a simple A -> B reaction."""
    print("Testing simple A -> B reaction system...")

    # Create species
    species_A = Species(name="A", units="mol/L")
    species_B = Species(name="B", units="mol/L")

    # Create parameter for rate constant
    k1 = Parameter(name="k1", value=0.1, units="1/s")

    # Create reaction: A -> B with rate k1
    reaction1 = Reaction(
        name="A_to_B",
        reactants={"A": 1.0},
        products={"B": 1.0},
        rate_constant="k1"
    )

    # Create reaction system
    system = ReactionSystem(
        name="simple_system",
        species=[species_A, species_B],
        parameters=[k1],
        reactions=[reaction1]
    )

    # Test stoichiometric matrix
    stoich_matrix = stoichiometric_matrix(system)
    print(f"Stoichiometric matrix shape: {stoich_matrix.shape}")
    print(f"Stoichiometric matrix:\n{stoich_matrix}")

    expected_stoich = np.array([[-1.0], [1.0]])  # A is consumed (-1), B is produced (+1)
    assert np.allclose(stoich_matrix, expected_stoich), f"Expected {expected_stoich}, got {stoich_matrix}"

    # Test substrate matrix
    substrate_mat = substrate_matrix(system)
    print(f"Substrate matrix:\n{substrate_mat}")

    expected_substrate = np.array([[1.0], [0.0]])  # Only A is a substrate
    assert np.allclose(substrate_mat, expected_substrate), f"Expected {expected_substrate}, got {substrate_mat}"

    # Test product matrix
    product_mat = product_matrix(system)
    print(f"Product matrix:\n{product_mat}")

    expected_product = np.array([[0.0], [1.0]])  # Only B is a product
    assert np.allclose(product_mat, expected_product), f"Expected {expected_product}, got {product_mat}"

    # Test ODE derivation
    model = derive_odes(system)
    print(f"Generated model name: {model.name}")
    print(f"Number of variables: {len(model.variables)}")
    print(f"Number of equations: {len(model.equations)}")

    # Check that we have the expected variables
    assert "A" in model.variables
    assert "B" in model.variables
    assert "k1" in model.variables

    # Check variable types
    assert model.variables["A"].type == "state"
    assert model.variables["B"].type == "state"
    assert model.variables["k1"].type == "parameter"

    print("✓ Simple reaction system test passed!")


def test_two_reaction_system():
    """Test with a more complex system: A -> B -> C"""
    print("\nTesting A -> B -> C reaction system...")

    # Create species
    species_A = Species(name="A", units="mol/L")
    species_B = Species(name="B", units="mol/L")
    species_C = Species(name="C", units="mol/L")

    # Create parameters
    k1 = Parameter(name="k1", value=0.1, units="1/s")
    k2 = Parameter(name="k2", value=0.05, units="1/s")

    # Create reactions
    reaction1 = Reaction(
        name="A_to_B",
        reactants={"A": 1.0},
        products={"B": 1.0},
        rate_constant="k1"
    )

    reaction2 = Reaction(
        name="B_to_C",
        reactants={"B": 1.0},
        products={"C": 1.0},
        rate_constant="k2"
    )

    # Create reaction system
    system = ReactionSystem(
        name="sequential_system",
        species=[species_A, species_B, species_C],
        parameters=[k1, k2],
        reactions=[reaction1, reaction2]
    )

    # Test stoichiometric matrix
    stoich_matrix = stoichiometric_matrix(system)
    print(f"Stoichiometric matrix shape: {stoich_matrix.shape}")
    print(f"Stoichiometric matrix:\n{stoich_matrix}")

    # Expected: A is consumed in reaction 1, B is produced in reaction 1 and consumed in reaction 2, C is produced in reaction 2
    expected_stoich = np.array([
        [-1.0,  0.0],  # A: consumed in reaction 1
        [ 1.0, -1.0],  # B: produced in reaction 1, consumed in reaction 2
        [ 0.0,  1.0]   # C: produced in reaction 2
    ])
    assert np.allclose(stoich_matrix, expected_stoich), f"Expected {expected_stoich}, got {stoich_matrix}"

    # Test ODE derivation
    model = derive_odes(system)
    print(f"Generated model: {model.name}")
    print(f"Number of equations: {len(model.equations)}")

    # Should have 3 state variables and 2 parameters
    assert len([v for v in model.variables.values() if v.type == "state"]) == 3
    assert len([v for v in model.variables.values() if v.type == "parameter"]) == 2

    print("✓ Two reaction system test passed!")


if __name__ == "__main__":
    test_simple_reaction_system()
    test_two_reaction_system()
    print("\n🎉 All tests passed!")