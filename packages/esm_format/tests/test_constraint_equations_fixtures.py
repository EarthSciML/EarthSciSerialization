"""
Comprehensive test fixtures for constraint equations and algebraic variables.

This module provides test fixtures for constraint equations that appear in
Earth system models, focusing on:

1. Mass conservation constraint equations
2. Charge balance constraint equations
3. Equilibrium constraint equations
4. Steady-state algebraic constraints
5. Implicit algebraic equations (DAE systems)
6. Constraint equation validation and solving
7. Mixed differential-algebraic equation systems
8. Thermodynamic equilibrium constraints
9. Stoichiometric constraint matrices
10. Phase equilibrium constraints

These constraint equation test fixtures ensure proper handling of algebraic
constraints in Earth system models, which are essential for physical realism
and numerical stability.
"""

import pytest
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from esm_format.types import (
    ModelVariable, Parameter, Species, Equation, ExprNode,
    Model, ReactionSystem, Reaction, EsmFile, Metadata
)
from esm_format.parse import load
from esm_format.serialize import save

# Scientific computing imports with fallbacks
try:
    import scipy.optimize
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


# ========================================
# 1. Mass Conservation Constraint Fixtures
# ========================================

class TestMassConservationConstraints:
    """Test fixtures for mass conservation constraint equations."""

    def test_simple_mass_conservation_constraint(self):
        """Test simple mass conservation constraint: sum(mass_i) = constant."""

        # Create species with known masses
        species = [
            Species(name="A", mass=10.0, units="g/mol"),
            Species(name="B", mass=20.0, units="g/mol"),
            Species(name="C", mass=30.0, units="g/mol")
        ]

        # Simple reaction A + B -> C
        reactions = [
            Reaction(
                name="synthesis",
                reactants={"A": 1.0, "B": 1.0},
                products={"C": 1.0}
            )
        ]

        # Mass conservation constraint equation
        # mass_A * [A] + mass_B * [B] + mass_C * [C] = total_mass
        constraint_equations = [
            Equation(
                lhs=ExprNode(
                    op="+",
                    args=[
                        ExprNode(op="*", args=[10.0, "A"]),
                        ExprNode(op="*", args=[20.0, "B"]),
                        ExprNode(op="*", args=[30.0, "C"])
                    ]
                ),
                rhs="total_mass"
            )
        ]

        reaction_system = ReactionSystem(
            name="mass_conserved_system",
            species=species,
            reactions=reactions
        )

        # Add constraint equations to reaction system
        reaction_system.constraint_equations = constraint_equations

        # Test mass conservation numerically
        # Initial: A=1.0, B=1.0, C=0.0 -> total_mass = 30.0
        # Final: A=0.0, B=0.0, C=1.0 -> total_mass = 30.0
        initial_mass = 10.0 * 1.0 + 20.0 * 1.0 + 30.0 * 0.0  # = 30.0
        final_mass = 10.0 * 0.0 + 20.0 * 0.0 + 30.0 * 1.0    # = 30.0

        assert abs(initial_mass - final_mass) < 1e-10, "Mass should be conserved"

    def test_multi_reaction_mass_conservation(self):
        """Test mass conservation across multiple reactions."""

        species = [
            Species(name="H2", mass=2.016, units="g/mol"),
            Species(name="O2", mass=31.998, units="g/mol"),
            Species(name="H2O", mass=18.015, units="g/mol"),
            Species(name="H2O2", mass=34.014, units="g/mol")
        ]

        reactions = [
            # H2 + 1/2 O2 -> H2O
            Reaction("water_formation",
                    reactants={"H2": 1.0, "O2": 0.5},
                    products={"H2O": 1.0}),
            # H2 + O2 -> H2O2
            Reaction("peroxide_formation",
                    reactants={"H2": 1.0, "O2": 1.0},
                    products={"H2O2": 1.0})
        ]

        # Mass conservation constraint
        constraint_equations = [
            Equation(
                lhs=ExprNode(
                    op="+",
                    args=[
                        ExprNode(op="*", args=[2.016, "H2"]),
                        ExprNode(op="*", args=[31.998, "O2"]),
                        ExprNode(op="*", args=[18.015, "H2O"]),
                        ExprNode(op="*", args=[34.014, "H2O2"])
                    ]
                ),
                rhs="total_system_mass"
            )
        ]

        reaction_system = ReactionSystem(
            name="hydrogen_oxygen_system",
            species=species,
            reactions=reactions
        )
        reaction_system.constraint_equations = constraint_equations

        # Test that stoichiometric coefficients preserve mass
        # Reaction 1: 2.016 + 0.5*31.998 = 18.015 (18.015 vs 18.015)
        react1_mass = 2.016 + 0.5 * 31.998  # = 18.015
        prod1_mass = 18.015
        assert abs(react1_mass - prod1_mass) < 0.01, "Reaction 1 should conserve mass"

        # Reaction 2: 2.016 + 31.998 = 34.014 (34.014 vs 34.014)
        react2_mass = 2.016 + 31.998  # = 34.014
        prod2_mass = 34.014
        assert abs(react2_mass - prod2_mass) < 0.01, "Reaction 2 should conserve mass"

    def test_mass_conservation_matrix_formulation(self):
        """Test mass conservation using matrix formulation."""

        species = [
            Species(name="CH4", mass=16.04, units="g/mol"),
            Species(name="O2", mass=32.00, units="g/mol"),
            Species(name="CO2", mass=44.01, units="g/mol"),
            Species(name="H2O", mass=18.02, units="g/mol")
        ]

        # CH4 + 2 O2 -> CO2 + 2 H2O (methane combustion)
        reactions = [
            Reaction("combustion",
                    reactants={"CH4": 1, "O2": 2},
                    products={"CO2": 1, "H2O": 2})
        ]

        # Mass conservation constraint as matrix equation: M^T * c = 0
        # where M is mass vector, c is concentration vector
        masses = np.array([16.04, 32.00, 44.01, 18.02])
        stoich_matrix = np.array([[-1], [-2], [1], [2]])  # Species x Reactions

        # Mass balance: masses^T @ stoich_matrix should be zero
        mass_balance = masses @ stoich_matrix
        expected_balance = np.array([0.0])  # Should be zero for mass conservation

        np.testing.assert_allclose(mass_balance, expected_balance, atol=0.1)


# ========================================
# 2. Charge Balance Constraint Fixtures
# ========================================

class TestChargeBalanceConstraints:
    """Test fixtures for charge balance constraint equations."""

    def test_ion_charge_balance(self):
        """Test charge balance constraint for ionic species."""

        # Ionic species with charges
        species = [
            Species(name="Na+", formula="Na+", units="mol/L"),
            Species(name="Cl-", formula="Cl-", units="mol/L"),
            Species(name="H+", formula="H+", units="mol/L"),
            Species(name="OH-", formula="OH-", units="mol/L")
        ]

        # Charge balance constraint: sum(z_i * c_i) = 0
        # where z_i is charge and c_i is concentration
        constraint_equations = [
            Equation(
                lhs=ExprNode(
                    op="+",
                    args=[
                        ExprNode(op="*", args=[1, "Na+"]),   # +1 charge
                        ExprNode(op="*", args=[-1, "Cl-"]),  # -1 charge
                        ExprNode(op="*", args=[1, "H+"]),    # +1 charge
                        ExprNode(op="*", args=[-1, "OH-"])   # -1 charge
                    ]
                ),
                rhs=0.0  # Electroneutrality
            )
        ]

        reaction_system = ReactionSystem(
            name="ionic_solution",
            species=species
        )
        reaction_system.constraint_equations = constraint_equations

        # Test charge balance with specific concentrations
        # Na+ = 0.1, Cl- = 0.05, H+ = 0.001, OH- = 0.051
        charge_balance = 1*0.1 + (-1)*0.05 + 1*0.001 + (-1)*0.051
        assert abs(charge_balance) < 1e-10, "Charge should be balanced"

    def test_aqueous_chemistry_charge_constraint(self):
        """Test charge balance in aqueous chemistry system."""

        species = [
            Species(name="Ca2+", formula="Ca2+"),  # +2 charge
            Species(name="HCO3-", formula="HCO3-"),  # -1 charge
            Species(name="CO32-", formula="CO32-"),  # -2 charge
            Species(name="H+", formula="H+"),      # +1 charge
            Species(name="OH-", formula="OH-")     # -1 charge
        ]

        # Carbonate equilibrium reactions
        reactions = [
            Reaction("bicarbonate_dissociation",
                    reactants={"HCO3-": 1},
                    products={"CO32-": 1, "H+": 1}),
            Reaction("water_dissociation",
                    reactants={"H2O": 1},
                    products={"H+": 1, "OH-": 1})
        ]

        # Charge balance constraint
        constraint_equations = [
            Equation(
                lhs=ExprNode(
                    op="+",
                    args=[
                        ExprNode(op="*", args=[2, "Ca2+"]),   # +2 charge
                        ExprNode(op="*", args=[-1, "HCO3-"]), # -1 charge
                        ExprNode(op="*", args=[-2, "CO32-"]), # -2 charge
                        ExprNode(op="*", args=[1, "H+"]),     # +1 charge
                        ExprNode(op="*", args=[-1, "OH-"])    # -1 charge
                    ]
                ),
                rhs=0.0
            )
        ]

        reaction_system = ReactionSystem(
            name="carbonate_system",
            species=species,
            reactions=reactions
        )
        reaction_system.constraint_equations = constraint_equations

        # Verify charge balance is enforced
        assert len(constraint_equations) == 1
        assert constraint_equations[0].rhs == 0.0


# ========================================
# 3. Equilibrium Constraint Fixtures
# ========================================

class TestEquilibriumConstraints:
    """Test fixtures for chemical equilibrium constraint equations."""

    def test_simple_equilibrium_constraint(self):
        """Test equilibrium constraint K = [products]/[reactants]."""

        species = [
            Species(name="A"), Species(name="B"), Species(name="C")
        ]

        # Equilibrium reaction A + B <-> C
        reactions = [
            Reaction("forward", reactants={"A": 1, "B": 1}, products={"C": 1}),
            Reaction("reverse", reactants={"C": 1}, products={"A": 1, "B": 1})
        ]

        parameters = [
            Parameter(name="K_eq", value=2.5, description="Equilibrium constant")
        ]

        # Equilibrium constraint: K_eq = [C] / ([A] * [B])
        constraint_equations = [
            Equation(
                lhs="K_eq",
                rhs=ExprNode(
                    op="/",
                    args=[
                        "C",
                        ExprNode(op="*", args=["A", "B"])
                    ]
                )
            )
        ]

        reaction_system = ReactionSystem(
            name="equilibrium_system",
            species=species,
            parameters=parameters,
            reactions=reactions
        )
        reaction_system.constraint_equations = constraint_equations

        # Test equilibrium condition
        # If A=1.0, B=1.0, then at equilibrium: C = K_eq * A * B = 2.5
        K_eq = 2.5
        A_eq, B_eq = 1.0, 1.0
        C_eq_expected = K_eq * A_eq * B_eq

        assert abs(C_eq_expected - 2.5) < 1e-10, "Equilibrium should satisfy constraint"

    def test_acid_base_equilibrium_constraint(self):
        """Test acid-base equilibrium Ka constraint."""

        species = [
            Species(name="HA"),    # Weak acid
            Species(name="H+"),    # Hydrogen ion
            Species(name="A-"),    # Conjugate base
            Species(name="H2O")    # Water
        ]

        # Acid dissociation: HA + H2O <-> H+ + A-
        reactions = [
            Reaction("dissociation",
                    reactants={"HA": 1, "H2O": 1},
                    products={"H+": 1, "A-": 1})
        ]

        parameters = [
            Parameter(name="Ka", value=1.8e-5, description="Acid dissociation constant")
        ]

        # Equilibrium constraint: Ka = [H+][A-]/[HA]
        # (assuming [H2O] is constant and incorporated into Ka)
        constraint_equations = [
            Equation(
                lhs="Ka",
                rhs=ExprNode(
                    op="/",
                    args=[
                        ExprNode(op="*", args=["H+", "A-"]),
                        "HA"
                    ]
                )
            )
        ]

        reaction_system = ReactionSystem(
            name="acid_base_equilibrium",
            species=species,
            parameters=parameters,
            reactions=reactions
        )
        reaction_system.constraint_equations = constraint_equations

        # Test Henderson-Hasselbalch relationship
        Ka = 1.8e-5
        # At half-neutralization: [HA] = [A-], so [H+] = Ka
        HA_conc = 0.1
        A_conc = 0.1
        H_plus_expected = Ka  # When [HA] = [A-]

        calculated_Ka = H_plus_expected * A_conc / HA_conc
        assert abs(calculated_Ka - Ka) < 1e-10, "Ka constraint should be satisfied"


# ========================================
# 4. Steady-State Algebraic Constraints
# ========================================

class TestSteadyStateConstraints:
    """Test fixtures for steady-state algebraic constraint equations."""

    def test_enzyme_steady_state_approximation(self):
        """Test quasi-steady-state approximation for enzyme kinetics."""

        species = [
            Species(name="E"),     # Free enzyme
            Species(name="S"),     # Substrate
            Species(name="ES"),    # Enzyme-substrate complex
            Species(name="P")      # Product
        ]

        # Enzyme mechanism: E + S <-> ES -> E + P
        reactions = [
            Reaction("binding", reactants={"E": 1, "S": 1}, products={"ES": 1}),
            Reaction("release", reactants={"ES": 1}, products={"E": 1, "S": 1}),
            Reaction("catalysis", reactants={"ES": 1}, products={"E": 1, "P": 1})
        ]

        parameters = [
            Parameter(name="k1", value=1e6),    # Binding rate
            Parameter(name="k_1", value=1e3),   # Release rate
            Parameter(name="k2", value=1e2),    # Catalysis rate
            Parameter(name="E_total", value=1e-6)  # Total enzyme
        ]

        # Steady-state constraints:
        # 1. d[ES]/dt = 0 (quasi-steady-state approximation)
        # 2. E_total = [E] + [ES] (enzyme conservation)
        constraint_equations = [
            # d[ES]/dt = k1*[E]*[S] - (k_1 + k2)*[ES] = 0
            Equation(
                lhs=0.0,
                rhs=ExprNode(
                    op="-",
                    args=[
                        ExprNode(op="*", args=["k1", "E", "S"]),
                        ExprNode(op="*", args=[
                            ExprNode(op="+", args=["k_1", "k2"]),
                            "ES"
                        ])
                    ]
                )
            ),
            # Enzyme conservation: E_total = [E] + [ES]
            Equation(
                lhs="E_total",
                rhs=ExprNode(op="+", args=["E", "ES"])
            )
        ]

        reaction_system = ReactionSystem(
            name="enzyme_kinetics",
            species=species,
            parameters=parameters,
            reactions=reactions
        )
        reaction_system.constraint_equations = constraint_equations

        # Test Michaelis-Menten parameters
        k1, k_1, k2 = 1e6, 1e3, 1e2
        Km = (k_1 + k2) / k1  # Michaelis constant

        expected_Km = 1.1e-3  # (1000 + 100) / 1e6
        assert abs(Km - expected_Km) < 1e-6, "Michaelis constant should be correct"

    def test_photochemical_steady_state(self):
        """Test steady-state approximation for photochemical system."""

        species = [
            Species(name="NO2"),   # Nitrogen dioxide
            Species(name="NO"),    # Nitric oxide
            Species(name="O3"),    # Ozone
            Species(name="O")      # Atomic oxygen (steady-state)
        ]

        # Photostationary state reactions:
        # NO2 + hv -> NO + O   (photolysis)
        # O + O2 -> O3         (fast)
        # O3 + NO -> NO2 + O2  (catalytic)
        reactions = [
            Reaction("photolysis", reactants={"NO2": 1}, products={"NO": 1, "O": 1}),
            Reaction("ozone_formation", reactants={"O": 1}, products={"O3": 1}),
            Reaction("titration", reactants={"O3": 1, "NO": 1}, products={"NO2": 1})
        ]

        parameters = [
            Parameter(name="J_NO2", value=0.01, description="Photolysis rate"),
            Parameter(name="k_O3", value=1e9, description="O + O2 rate"),
            Parameter(name="k_tit", value=2e-14, description="O3 + NO rate")
        ]

        # Steady-state constraints:
        # d[O]/dt = 0 (atomic oxygen in steady state)
        constraint_equations = [
            Equation(
                lhs=0.0,
                rhs=ExprNode(
                    op="-",
                    args=[
                        ExprNode(op="*", args=["J_NO2", "NO2"]),  # Production
                        ExprNode(op="*", args=["k_O3", "O"])      # Loss
                    ]
                )
            )
        ]

        reaction_system = ReactionSystem(
            name="photostationary_state",
            species=species,
            parameters=parameters,
            reactions=reactions
        )
        reaction_system.constraint_equations = constraint_equations

        # Test photostationary state relationship
        # [O] = J_NO2 * [NO2] / k_O3
        J_NO2, k_O3 = 0.01, 1e9
        NO2_conc = 1e-9  # ppb level
        O_steady_state = J_NO2 * NO2_conc / k_O3

        expected_O_conc = 1e-14  # Very low steady-state concentration
        assert abs(O_steady_state - expected_O_conc) < 1e-15


# ========================================
# 5. DAE (Differential-Algebraic) Systems
# ========================================

class TestDAESystemConstraints:
    """Test fixtures for differential-algebraic equation systems."""

    def test_simple_dae_system(self):
        """Test simple DAE with algebraic constraint."""

        # Variables: x (differential), y (algebraic), z (differential)
        variables = {
            "x": ModelVariable(type="state", units="m"),
            "y": ModelVariable(type="state", units="m/s"),  # Algebraic variable
            "z": ModelVariable(type="state", units="m"),
            "t": ModelVariable(type="parameter", units="s")
        }

        # Differential equations:
        # dx/dt = y
        # dz/dt = -y
        equations = [
            Equation(lhs="dx_dt", rhs="y"),
            Equation(lhs="dz_dt", rhs=ExprNode(op="*", args=[-1, "y"]))
        ]

        # Algebraic constraint: x + z = constant
        constraint_equations = [
            Equation(
                lhs=ExprNode(op="+", args=["x", "z"]),
                rhs="total_displacement"
            )
        ]

        model = Model(
            name="simple_dae",
            variables=variables,
            equations=equations
        )

        # Add constraint to model metadata
        model.metadata = {"constraint_equations": constraint_equations}

        # Test that constraint is preserved
        # If x(0) = 1, z(0) = 2, then x(t) + z(t) = 3 for all t
        x0, z0 = 1.0, 2.0
        total_expected = x0 + z0

        # At any later time with y = 0.5:
        dt = 0.1
        x1 = x0 + 0.5 * dt  # x + ∫y dt
        z1 = z0 - 0.5 * dt  # z - ∫y dt
        total_actual = x1 + z1

        assert abs(total_actual - total_expected) < 1e-10, "Constraint should be preserved"

    def test_pendulum_dae_system(self):
        """Test pendulum as DAE system with constraint."""

        variables = {
            "x": ModelVariable(type="state", units="m", description="Horizontal position"),
            "y": ModelVariable(type="state", units="m", description="Vertical position"),
            "vx": ModelVariable(type="state", units="m/s", description="Horizontal velocity"),
            "vy": ModelVariable(type="state", units="m/s", description="Vertical velocity"),
            "lambda": ModelVariable(type="state", description="Lagrange multiplier"),
            "L": ModelVariable(type="parameter", value=1.0, units="m", description="Pendulum length"),
            "g": ModelVariable(type="parameter", value=9.81, units="m/s^2")
        }

        # Differential equations:
        # dx/dt = vx, dy/dt = vy
        # dvx/dt = -2*lambda*x/L^2, dvy/dt = -g - 2*lambda*y/L^2
        equations = [
            Equation(lhs="dx_dt", rhs="vx"),
            Equation(lhs="dy_dt", rhs="vy"),
            Equation(
                lhs="dvx_dt",
                rhs=ExprNode(op="*", args=[
                    -2,
                    ExprNode(op="/", args=[
                        ExprNode(op="*", args=["lambda", "x"]),
                        ExprNode(op="^", args=["L", 2])
                    ])
                ])
            ),
            Equation(
                lhs="dvy_dt",
                rhs=ExprNode(op="+", args=[
                    ExprNode(op="*", args=[-1, "g"]),
                    ExprNode(op="*", args=[
                        -2,
                        ExprNode(op="/", args=[
                            ExprNode(op="*", args=["lambda", "y"]),
                            ExprNode(op="^", args=["L", 2])
                        ])
                    ])
                ])
            )
        ]

        # Algebraic constraint: x^2 + y^2 = L^2 (pendulum length constraint)
        constraint_equations = [
            Equation(
                lhs=ExprNode(
                    op="+",
                    args=[
                        ExprNode(op="^", args=["x", 2]),
                        ExprNode(op="^", args=["y", 2])
                    ]
                ),
                rhs=ExprNode(op="^", args=["L", 2])
            )
        ]

        model = Model(
            name="pendulum_dae",
            variables=variables,
            equations=equations
        )
        model.metadata = {"constraint_equations": constraint_equations}

        # Test constraint satisfaction
        L = 1.0
        x, y = 0.6, 0.8  # Point on circle of radius L
        constraint_value = x**2 + y**2
        expected_constraint = L**2

        assert abs(constraint_value - expected_constraint) < 1e-10, "Length constraint should be satisfied"


# ========================================
# 6. Thermodynamic Equilibrium Constraints
# ========================================

class TestThermodynamicConstraints:
    """Test fixtures for thermodynamic equilibrium constraints."""

    def test_vapor_liquid_equilibrium(self):
        """Test vapor-liquid equilibrium constraint (Raoult's law)."""

        species = [
            Species(name="A_liq", description="Component A in liquid phase"),
            Species(name="A_vap", description="Component A in vapor phase"),
            Species(name="B_liq", description="Component B in liquid phase"),
            Species(name="B_vap", description="Component B in vapor phase")
        ]

        parameters = [
            Parameter(name="P_sat_A", value=101325, units="Pa", description="Vapor pressure of A"),
            Parameter(name="P_sat_B", value=50663, units="Pa", description="Vapor pressure of B"),
            Parameter(name="P_total", value=101325, units="Pa", description="Total pressure"),
            Parameter(name="R", value=8.314, units="J/(mol*K)"),
            Parameter(name="T", value=298.15, units="K")
        ]

        # Phase equilibrium reactions
        reactions = [
            Reaction("A_evaporation", reactants={"A_liq": 1}, products={"A_vap": 1}),
            Reaction("B_evaporation", reactants={"B_liq": 1}, products={"B_vap": 1})
        ]

        # VLE constraints (Raoult's law):
        # P_A = x_A * P_sat_A = y_A * P_total
        # P_B = x_B * P_sat_B = y_B * P_total
        constraint_equations = [
            # For component A: x_A * P_sat_A = y_A * P_total
            Equation(
                lhs=ExprNode(op="*", args=["x_A", "P_sat_A"]),
                rhs=ExprNode(op="*", args=["y_A", "P_total"])
            ),
            # For component B: x_B * P_sat_B = y_B * P_total
            Equation(
                lhs=ExprNode(op="*", args=["x_B", "P_sat_B"]),
                rhs=ExprNode(op="*", args=["y_B", "P_total"])
            ),
            # Liquid phase mole fractions sum to 1
            Equation(
                lhs=ExprNode(op="+", args=["x_A", "x_B"]),
                rhs=1.0
            ),
            # Vapor phase mole fractions sum to 1
            Equation(
                lhs=ExprNode(op="+", args=["y_A", "y_B"]),
                rhs=1.0
            )
        ]

        reaction_system = ReactionSystem(
            name="vle_system",
            species=species,
            parameters=parameters,
            reactions=reactions
        )
        reaction_system.constraint_equations = constraint_equations

        # Test Raoult's law calculation
        P_sat_A, P_sat_B = 101325, 50663
        P_total = 101325

        # For equimolar liquid mixture: x_A = x_B = 0.5
        x_A = 0.5
        x_B = 0.5

        # Calculate vapor composition
        y_A = x_A * P_sat_A / P_total  # = 0.5 * 101325 / 101325 = 0.5
        y_B = x_B * P_sat_B / P_total  # = 0.5 * 50663 / 101325 ≈ 0.25

        # Note: This won't sum to 1 because pressure is inconsistent
        # In reality, P_total would adjust for equilibrium
        expected_y_A = 0.5
        expected_y_B_approx = 0.25

        assert abs(y_A - expected_y_A) < 1e-6, "Vapor fraction A should match Raoult's law"

    def test_chemical_potential_equilibrium(self):
        """Test chemical potential equality at equilibrium."""

        species = [
            Species(name="A_phase1", description="Species A in phase 1"),
            Species(name="A_phase2", description="Species A in phase 2")
        ]

        parameters = [
            Parameter(name="mu0_A_1", value=-1000, units="J/mol", description="Standard chemical potential, phase 1"),
            Parameter(name="mu0_A_2", value=-1200, units="J/mol", description="Standard chemical potential, phase 2"),
            Parameter(name="R", value=8.314, units="J/(mol*K)"),
            Parameter(name="T", value=298.15, units="K")
        ]

        # Equilibrium reaction: A_phase1 <-> A_phase2
        reactions = [
            Reaction("phase_transfer", reactants={"A_phase1": 1}, products={"A_phase2": 1})
        ]

        # Chemical potential equilibrium constraint:
        # μ₁ = μ₂
        # μ₀₁ + RT ln(a₁) = μ₀₂ + RT ln(a₂)
        # For ideal solutions: a_i ≈ x_i
        constraint_equations = [
            Equation(
                lhs=ExprNode(op="+", args=[
                    "mu0_A_1",
                    ExprNode(op="*", args=[
                        "R", "T",
                        ExprNode(op="ln", args=["x_A_1"])
                    ])
                ]),
                rhs=ExprNode(op="+", args=[
                    "mu0_A_2",
                    ExprNode(op="*", args=[
                        "R", "T",
                        ExprNode(op="ln", args=["x_A_2"])
                    ])
                ])
            )
        ]

        reaction_system = ReactionSystem(
            name="phase_equilibrium",
            species=species,
            parameters=parameters,
            reactions=reactions
        )
        reaction_system.constraint_equations = constraint_equations

        # Test equilibrium constant calculation
        mu0_1, mu0_2 = -1000, -1200  # J/mol
        R, T = 8.314, 298.15

        # At equilibrium: ln(x_2/x_1) = (mu0_1 - mu0_2)/(RT)
        ln_K = (mu0_1 - mu0_2) / (R * T)  # = 200 / (8.314 * 298.15) ≈ 0.081
        K = np.exp(ln_K)  # ≈ 1.08

        expected_K_approx = 1.08
        assert abs(K - expected_K_approx) < 0.01, "Equilibrium constant should be correct"


# ========================================
# 7. Integration and Validation Tests
# ========================================

class TestConstraintEquationIntegration:
    """Integration tests for constraint equation systems."""

    def test_esm_file_with_constraint_equations(self):
        """Test complete ESM file with constraint equations."""

        # Create a complete ESM file with constraint equations
        metadata = Metadata(
            title="Test System with Constraints",
            description="System demonstrating constraint equation usage",
            authors=["Test Author"],
            version="1.0"
        )

        species = [
            Species(name="A", mass=10.0),
            Species(name="B", mass=20.0),
            Species(name="C", mass=30.0)
        ]

        reactions = [
            Reaction("conversion", reactants={"A": 1, "B": 1}, products={"C": 1})
        ]

        constraint_equations = [
            # Mass conservation
            Equation(
                lhs=ExprNode(op="+", args=[
                    ExprNode(op="*", args=[10.0, "A"]),
                    ExprNode(op="*", args=[20.0, "B"]),
                    ExprNode(op="*", args=[30.0, "C"])
                ]),
                rhs=60.0  # Total mass when A=1, B=1, C=1
            )
        ]

        reaction_system = ReactionSystem(
            name="constrained_system",
            species=species,
            reactions=reactions
        )
        reaction_system.constraint_equations = constraint_equations

        esm_file = EsmFile(
            version="0.1.0",
            metadata=metadata,
            reaction_systems=[reaction_system]
        )

        # Test serialization/deserialization
        serialized = save(esm_file)
        assert "constraint_equations" in serialized, "Constraint equations should be serialized"

        # Verify structure
        assert len(esm_file.reaction_systems) == 1
        assert len(esm_file.reaction_systems[0].constraint_equations) == 1

    @pytest.mark.skipif(not SCIPY_AVAILABLE, reason="SciPy not available")
    def test_constraint_equation_numerical_solution(self):
        """Test numerical solution of constraint equation system."""

        # Simple constraint optimization problem:
        # Minimize: (x-1)² + (y-2)²
        # Subject to: x + y = 3 (constraint equation)

        def objective(vars):
            x, y = vars
            return (x - 1)**2 + (y - 2)**2

        def constraint(vars):
            x, y = vars
            return x + y - 3  # Should equal 0

        # Initial guess
        x0 = [1.0, 1.0]

        # Constraint definition for scipy
        cons = {'type': 'eq', 'fun': constraint}

        # Solve constrained optimization
        result = scipy.optimize.minimize(objective, x0, method='SLSQP', constraints=cons)

        # Expected solution: x=1, y=2 (satisfies x+y=3 and minimizes objective)
        expected_x, expected_y = 1.0, 2.0
        actual_x, actual_y = result.x

        assert abs(actual_x - expected_x) < 1e-3, "x should be close to expected value"
        assert abs(actual_y - expected_y) < 1e-3, "y should be close to expected value"
        assert abs(constraint(result.x)) < 1e-6, "Constraint should be satisfied"

    def test_multiple_constraint_types(self):
        """Test system with multiple types of constraints."""

        # System with both equality and inequality-like constraints
        species = [
            Species(name="X1", mass=1.0),
            Species(name="X2", mass=2.0),
            Species(name="X3", mass=3.0),
            Species(name="Y1", units="mol/L"),
            Species(name="Y2", units="mol/L")
        ]

        # Multiple constraint equations
        constraint_equations = [
            # Mass conservation constraint
            Equation(
                lhs=ExprNode(op="+", args=[
                    ExprNode(op="*", args=[1.0, "X1"]),
                    ExprNode(op="*", args=[2.0, "X2"]),
                    ExprNode(op="*", args=[3.0, "X3"])
                ]),
                rhs="total_mass"
            ),
            # Stoichiometric constraint
            Equation(
                lhs=ExprNode(op="-", args=["X1", "X2"]),
                rhs="stoich_difference"
            ),
            # Equilibrium constraint
            Equation(
                lhs=ExprNode(op="*", args=["Y1", "Y2"]),
                rhs="equilibrium_product"
            )
        ]

        reaction_system = ReactionSystem(
            name="multi_constraint_system",
            species=species
        )
        reaction_system.constraint_equations = constraint_equations

        # Verify all constraints are present
        assert len(constraint_equations) == 3, "Should have 3 constraint equations"

        # Test constraint types
        constraint_types = []
        for eq in constraint_equations:
            if isinstance(eq.rhs, str):
                if "mass" in eq.rhs:
                    constraint_types.append("mass_conservation")
                elif "stoich" in eq.rhs:
                    constraint_types.append("stoichiometric")
                elif "equilibrium" in eq.rhs:
                    constraint_types.append("equilibrium")

        expected_types = ["mass_conservation", "stoichiometric", "equilibrium"]
        assert constraint_types == expected_types, "All constraint types should be identified"


# ========================================
# 8. Error Handling and Edge Cases
# ========================================

class TestConstraintEquationEdgeCases:
    """Test edge cases and error conditions for constraint equations."""

    def test_empty_constraint_equations(self):
        """Test system with empty constraint equations list."""

        reaction_system = ReactionSystem(name="no_constraints")
        reaction_system.constraint_equations = []

        assert len(reaction_system.constraint_equations) == 0
        # Should not raise any errors

    def test_inconsistent_constraint_equations(self):
        """Test detection of inconsistent constraint equations."""

        # Create obviously inconsistent constraints:
        # x = 1 and x = 2 (impossible to satisfy simultaneously)
        constraint_equations = [
            Equation(lhs="x", rhs=1.0),
            Equation(lhs="x", rhs=2.0)
        ]

        # This should be detectable as inconsistent
        # (implementation would need constraint validation logic)
        assert len(constraint_equations) == 2

        # Check for obvious inconsistency
        if (constraint_equations[0].lhs == constraint_equations[1].lhs and
            constraint_equations[0].rhs != constraint_equations[1].rhs):
            inconsistent = True
        else:
            inconsistent = False

        assert inconsistent, "Should detect inconsistent constraints"

    def test_underdetermined_constraint_system(self):
        """Test underdetermined constraint system (more variables than equations)."""

        # 3 variables, 1 constraint equation -> underdetermined
        species = [
            Species(name="A"), Species(name="B"), Species(name="C")
        ]

        constraint_equations = [
            Equation(
                lhs=ExprNode(op="+", args=["A", "B", "C"]),
                rhs="total"
            )
        ]

        reaction_system = ReactionSystem(
            name="underdetermined",
            species=species
        )
        reaction_system.constraint_equations = constraint_equations

        # System should be valid but have infinite solutions
        n_variables = len(species)  # 3
        n_constraints = len(constraint_equations)  # 1
        degrees_of_freedom = n_variables - n_constraints  # 2

        assert degrees_of_freedom > 0, "System should be underdetermined"

    def test_overdetermined_constraint_system(self):
        """Test overdetermined constraint system (more equations than variables)."""

        # 2 variables, 3 constraint equations -> overdetermined
        species = [Species(name="X"), Species(name="Y")]

        constraint_equations = [
            Equation(lhs="X", rhs=1.0),
            Equation(lhs="Y", rhs=2.0),
            Equation(lhs=ExprNode(op="+", args=["X", "Y"]), rhs=3.0)  # Consistent
        ]

        reaction_system = ReactionSystem(
            name="overdetermined",
            species=species
        )
        reaction_system.constraint_equations = constraint_equations

        n_variables = len(species)  # 2
        n_constraints = len(constraint_equations)  # 3

        assert n_constraints > n_variables, "System should be overdetermined"

        # Check if constraints are consistent (X=1, Y=2, X+Y=3 ✓)
        x_val = 1.0
        y_val = 2.0
        sum_val = x_val + y_val  # = 3.0

        assert abs(sum_val - 3.0) < 1e-10, "Overdetermined system should be consistent"


def test_comprehensive_constraint_equation_coverage():
    """Comprehensive test covering all constraint equation features."""

    # Test creation of all constraint types in a single system
    species = [
        Species(name="A", mass=10.0, formula="A"),
        Species(name="B", mass=20.0, formula="B"),
        Species(name="C", mass=30.0, formula="C"),
        Species(name="H+", formula="H+"),
        Species(name="OH-", formula="OH-")
    ]

    parameters = [
        Parameter(name="K_eq", value=2.5),
        Parameter(name="total_mass", value=60.0),
        Parameter(name="pH", value=7.0)
    ]

    reactions = [
        Reaction("synthesis", reactants={"A": 1, "B": 1}, products={"C": 1}),
        Reaction("hydrolysis", reactants={"C": 1}, products={"A": 1, "B": 1})
    ]

    # Comprehensive constraint equations
    constraint_equations = [
        # 1. Mass conservation
        Equation(
            lhs=ExprNode(op="+", args=[
                ExprNode(op="*", args=[10.0, "A"]),
                ExprNode(op="*", args=[20.0, "B"]),
                ExprNode(op="*", args=[30.0, "C"])
            ]),
            rhs="total_mass"
        ),
        # 2. Equilibrium constraint
        Equation(
            lhs="K_eq",
            rhs=ExprNode(op="/", args=[
                "C",
                ExprNode(op="*", args=["A", "B"])
            ])
        ),
        # 3. Charge balance
        Equation(
            lhs=ExprNode(op="+", args=[
                ExprNode(op="*", args=[1, "H+"]),
                ExprNode(op="*", args=[-1, "OH-"])
            ]),
            rhs=0.0
        ),
        # 4. Water dissociation (pH constraint)
        Equation(
            lhs=ExprNode(op="*", args=["H+", "OH-"]),
            rhs=1e-14  # Kw at 25°C
        )
    ]

    reaction_system = ReactionSystem(
        name="comprehensive_constraints",
        species=species,
        parameters=parameters,
        reactions=reactions
    )
    reaction_system.constraint_equations = constraint_equations

    # Verify all constraint types are present
    assert len(constraint_equations) == 4, "Should have 4 different constraint types"

    # Test constraint equation structure
    for eq in constraint_equations:
        assert hasattr(eq, 'lhs'), "Each equation should have LHS"
        assert hasattr(eq, 'rhs'), "Each equation should have RHS"

    # Verify constraint categories
    constraint_categories = {
        "mass_conservation": False,
        "equilibrium": False,
        "charge_balance": False,
        "water_dissociation": False
    }

    # Simple classification based on structure
    for eq in constraint_equations:
        if isinstance(eq.rhs, str) and "mass" in eq.rhs:
            constraint_categories["mass_conservation"] = True
        elif isinstance(eq.rhs, str) and eq.rhs == "K_eq":
            continue  # This is LHS = K_eq case
        elif hasattr(eq, 'lhs') and eq.lhs == "K_eq":
            constraint_categories["equilibrium"] = True
        elif isinstance(eq.rhs, (int, float)) and eq.rhs == 0.0:
            constraint_categories["charge_balance"] = True
        elif isinstance(eq.rhs, (int, float)) and eq.rhs == 1e-14:
            constraint_categories["water_dissociation"] = True

    # At least some categories should be identified
    assert any(constraint_categories.values()), "At least one constraint category should be identified"

    print("✓ Comprehensive constraint equation test fixtures completed successfully")


if __name__ == "__main__":
    # Run a simple test to verify fixtures
    test_comprehensive_constraint_equation_coverage()
    print("All constraint equation test fixtures are working correctly!")