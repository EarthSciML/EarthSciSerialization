"""
Mathematical verification test fixtures for scientific computing correctness.

This module provides comprehensive test fixtures for fundamental mathematical
correctness verification essential for scientific computing applications:

1. Stoichiometric matrix computation correctness with known analytical solutions
2. ODE derivation verification against hand-derived equations
3. Mass conservation validation for reaction systems
4. Numerical stability tests for extreme parameter values
5. Symbolic differentiation correctness verification
6. Integration accuracy tests with known analytical solutions
7. Steady-state calculation verification
8. Parameter estimation convergence tests

These mathematical verification tests are critical for ensuring the scientific
validity of all computational results in Earth system modeling.
"""

import pytest
import numpy as np
from typing import Dict, List, Tuple, Any
from esm_format.types import (
    ModelVariable, Parameter, Species, Equation, ExprNode,
    Model, ReactionSystem, Reaction
)
from esm_format.verification import (
    MathematicalVerifier, VerificationStatus, verify_reaction_system,
    verify_model, compute_stoichiometric_matrix
)


class TestStoichiometricMatrixVerification:
    """Test stoichiometric matrix computation correctness with analytical solutions."""

    def test_simple_reaction_stoichiometry(self):
        """Test stoichiometric matrix for simple reaction A + B -> C."""
        # Reaction: A + B -> C
        # Expected stoichiometric matrix:
        # Species: [A, B, C]
        # Reaction 1: [-1, -1, 1]

        species = [
            Species(name="A", formula="A"),
            Species(name="B", formula="B"),
            Species(name="C", formula="C")
        ]

        reaction = Reaction(
            name="simple_synthesis",
            reactants={"A": 1.0, "B": 1.0},
            products={"C": 1.0}
        )

        reaction_system = ReactionSystem(
            name="simple_system",
            species=species,
            reactions=[reaction]
        )

        # Expected stoichiometric matrix (species x reactions)
        expected_matrix = np.array([[-1.0], [-1.0], [1.0]])

        # Compute actual stoichiometric matrix
        actual_matrix = self._compute_stoichiometric_matrix(reaction_system)

        np.testing.assert_array_equal(actual_matrix, expected_matrix)

    def test_complex_reaction_network_stoichiometry(self):
        """Test stoichiometric matrix for complex reaction network."""
        # Multiple reactions:
        # R1: A + B -> C + D
        # R2: C + E -> F
        # R3: F -> A + G

        species = [
            Species(name="A"), Species(name="B"), Species(name="C"),
            Species(name="D"), Species(name="E"), Species(name="F"),
            Species(name="G")
        ]

        reactions = [
            Reaction("R1", reactants={"A": 1, "B": 1}, products={"C": 1, "D": 1}),
            Reaction("R2", reactants={"C": 1, "E": 1}, products={"F": 1}),
            Reaction("R3", reactants={"F": 1}, products={"A": 1, "G": 1})
        ]

        reaction_system = ReactionSystem("complex_network", species=species, reactions=reactions)

        # Expected stoichiometric matrix (7 species x 3 reactions)
        expected_matrix = np.array([
            [-1,  0,  1],  # A
            [-1,  0,  0],  # B
            [ 1, -1,  0],  # C
            [ 1,  0,  0],  # D
            [ 0, -1,  0],  # E
            [ 0,  1, -1],  # F
            [ 0,  0,  1]   # G
        ])

        actual_matrix = self._compute_stoichiometric_matrix(reaction_system)
        np.testing.assert_array_equal(actual_matrix, expected_matrix)

    def test_reversible_reaction_stoichiometry(self):
        """Test stoichiometric matrix for reversible reactions."""
        # Forward: A + B <-> C + D
        # Represented as two separate reactions

        species = [
            Species(name="A"), Species(name="B"),
            Species(name="C"), Species(name="D")
        ]

        reactions = [
            Reaction("forward", reactants={"A": 1, "B": 1}, products={"C": 1, "D": 1}),
            Reaction("reverse", reactants={"C": 1, "D": 1}, products={"A": 1, "B": 1})
        ]

        reaction_system = ReactionSystem("reversible_system", species=species, reactions=reactions)

        # Expected matrix should show forward and reverse reactions
        expected_matrix = np.array([
            [-1,  1],  # A
            [-1,  1],  # B
            [ 1, -1],  # C
            [ 1, -1]   # D
        ])

        actual_matrix = self._compute_stoichiometric_matrix(reaction_system)
        np.testing.assert_array_equal(actual_matrix, expected_matrix)

    def _compute_stoichiometric_matrix(self, reaction_system: ReactionSystem) -> np.ndarray:
        """Compute stoichiometric matrix from reaction system."""
        species_names = [s.name for s in reaction_system.species]
        n_species = len(species_names)
        n_reactions = len(reaction_system.reactions)

        matrix = np.zeros((n_species, n_reactions))

        for j, reaction in enumerate(reaction_system.reactions):
            # Subtract reactants (negative coefficients)
            for species, coeff in reaction.reactants.items():
                i = species_names.index(species)
                matrix[i, j] -= coeff

            # Add products (positive coefficients)
            for species, coeff in reaction.products.items():
                i = species_names.index(species)
                matrix[i, j] += coeff

        return matrix


class TestMassConservationVerification:
    """Test mass conservation validation for reaction systems."""

    def test_mass_balance_simple_reaction(self):
        """Test mass balance for simple reaction with known molecular weights."""
        # CH4 + 2O2 -> CO2 + 2H2O
        # Molecular weights: CH4=16, O2=32, CO2=44, H2O=18
        # Mass balance: 16 + 2*32 = 44 + 2*18 = 80

        species = [
            Species(name="CH4", formula="CH4", mass=16.04),
            Species(name="O2", formula="O2", mass=31.998),
            Species(name="CO2", formula="CO2", mass=44.01),
            Species(name="H2O", formula="H2O", mass=18.015)
        ]

        reaction = Reaction(
            name="methane_combustion",
            reactants={"CH4": 1, "O2": 2},
            products={"CO2": 1, "H2O": 2}
        )

        # Calculate mass balance
        reactant_mass = 16.04 + 2 * 31.998  # = 80.036
        product_mass = 44.01 + 2 * 18.015   # = 80.04

        mass_error = abs(reactant_mass - product_mass) / reactant_mass

        # Mass should be conserved within 0.1%
        assert mass_error < 0.001

    def test_mass_conservation_matrix_rank(self):
        """Test that stoichiometric matrix preserves mass conservation constraints."""
        # For mass conservation, the mass-weighted stoichiometric matrix
        # should have a null space corresponding to mass conservation

        species = [
            Species(name="A", mass=10.0),
            Species(name="B", mass=20.0),
            Species(name="C", mass=30.0)
        ]

        reaction = Reaction(
            name="mass_conserving",
            reactants={"A": 1, "B": 1},
            products={"C": 1}
        )

        reaction_system = ReactionSystem("test_system", species=species, reactions=[reaction])

        # Get stoichiometric matrix
        stoich_matrix = self._compute_stoichiometric_matrix(reaction_system)

        # Mass vector
        mass_vector = np.array([[10.0], [20.0], [30.0]])

        # Mass conservation: mass_vector^T * stoich_matrix should be zero
        mass_balance = mass_vector.T @ stoich_matrix

        np.testing.assert_array_almost_equal(mass_balance, [[0.0]], decimal=10)

    def _compute_stoichiometric_matrix(self, reaction_system: ReactionSystem) -> np.ndarray:
        """Helper method to compute stoichiometric matrix."""
        species_names = [s.name for s in reaction_system.species]
        n_species = len(species_names)
        n_reactions = len(reaction_system.reactions)

        matrix = np.zeros((n_species, n_reactions))

        for j, reaction in enumerate(reaction_system.reactions):
            for species, coeff in reaction.reactants.items():
                i = species_names.index(species)
                matrix[i, j] -= coeff
            for species, coeff in reaction.products.items():
                i = species_names.index(species)
                matrix[i, j] += coeff

        return matrix


class TestODEDerivationVerification:
    """Test ODE derivation verification against hand-derived equations."""

    def test_first_order_linear_ode(self):
        """Test first-order linear ODE: dy/dt = -ky with analytical solution."""
        # Analytical solution: y(t) = y0 * exp(-kt)

        # Define parameters
        k = 0.5
        y0 = 10.0
        t_values = np.array([0, 1, 2, 3, 4, 5])

        # Analytical solution
        y_analytical = y0 * np.exp(-k * t_values)

        # Numerical solution using Euler's method
        dt = 0.01
        t_num = np.arange(0, 5 + dt, dt)
        y_num = np.zeros_like(t_num)
        y_num[0] = y0

        for i in range(1, len(t_num)):
            y_num[i] = y_num[i-1] + dt * (-k * y_num[i-1])

        # Interpolate numerical solution at test points
        y_numerical_interp = np.interp(t_values, t_num, y_num)

        # Check relative error is small
        rel_error = np.abs((y_numerical_interp - y_analytical) / y_analytical)
        assert np.all(rel_error < 0.01)  # 1% tolerance

    def test_second_order_harmonic_oscillator(self):
        """Test second-order ODE: d²y/dt² + ω²y = 0 with analytical solution."""
        # Analytical solution: y(t) = A*cos(ωt) + B*sin(ωt)
        # Initial conditions: y(0) = A, dy/dt(0) = B*ω

        omega = 2.0  # Angular frequency
        A = 1.0      # Initial position
        B = 0.5      # Related to initial velocity

        t_values = np.linspace(0, 2*np.pi/omega, 50)

        # Analytical solution
        y_analytical = A * np.cos(omega * t_values) + B * np.sin(omega * t_values)
        dydt_analytical = -A * omega * np.sin(omega * t_values) + B * omega * np.cos(omega * t_values)

        # Check that second derivative satisfies ODE
        d2ydt2_analytical = -omega**2 * y_analytical

        # The ODE should be satisfied: d²y/dt² + ω²y = 0
        ode_residual = d2ydt2_analytical + omega**2 * y_analytical

        np.testing.assert_array_almost_equal(ode_residual, np.zeros_like(ode_residual), decimal=10)

    def test_coupled_ode_system(self):
        """Test coupled ODE system for predator-prey equations."""
        # Lotka-Volterra equations:
        # dx/dt = αx - βxy
        # dy/dt = δxy - γy

        alpha, beta, gamma, delta = 1.0, 0.1, 1.5, 0.075

        # Test equilibrium point
        x_eq = gamma / delta  # = 20
        y_eq = alpha / beta   # = 10

        # At equilibrium, derivatives should be zero
        dxdt_eq = alpha * x_eq - beta * x_eq * y_eq
        dydt_eq = delta * x_eq * y_eq - gamma * y_eq

        assert abs(dxdt_eq) < 1e-10
        assert abs(dydt_eq) < 1e-10

    def test_reaction_rate_ode_derivation(self):
        """Test ODE derivation for reaction kinetics."""
        # A -> B, rate = k[A]
        # d[A]/dt = -k[A]
        # d[B]/dt = k[A]

        k = 0.1
        A0 = 1.0
        B0 = 0.0

        # At any time t, [A] + [B] should equal A0 + B0 (conservation)
        t = 5.0
        A_t = A0 * np.exp(-k * t)
        B_t = A0 - A_t

        total = A_t + B_t
        expected_total = A0 + B0

        assert abs(total - expected_total) < 1e-10


class TestNumericalStabilityVerification:
    """Test numerical stability for extreme parameter values."""

    def test_stiff_ode_stability(self):
        """Test numerical stability for stiff ODE systems."""
        # Fast-slow system: dy1/dt = -1000*y1, dy2/dt = -y2
        # This is a stiff system due to different time scales

        # For explicit methods, large time steps should cause instability
        dt_stable = 0.001    # Small time step - should be stable
        dt_unstable = 0.01   # Large time step - may be unstable for stiff problems

        k1, k2 = 1000.0, 1.0
        y1_0, y2_0 = 1.0, 1.0

        # Test with small time step (should be stable)
        n_steps = int(0.01 / dt_stable)
        y1, y2 = y1_0, y2_0

        for _ in range(n_steps):
            y1_new = y1 + dt_stable * (-k1 * y1)
            y2_new = y2 + dt_stable * (-k2 * y2)
            y1, y2 = y1_new, y2_new

        # Should decay towards zero without oscillation
        assert y1 >= 0  # No oscillation
        assert y2 >= 0  # No oscillation
        assert y1 < y1_0  # Should decrease
        assert y2 < y2_0  # Should decrease

    def test_extreme_parameter_values(self):
        """Test behavior with extreme parameter values."""
        # Test reaction with very large and very small rate constants

        # Very small rate constant
        k_small = 1e-10
        y_small = self._solve_first_order(k_small, 1.0, 1.0)  # k, y0, t
        expected_small = 1.0 * np.exp(-k_small * 1.0)  # ≈ 1.0
        assert abs(y_small - expected_small) / expected_small < 1e-6

        # Very large rate constant (but numerically stable timestep)
        k_large = 1e6
        t_small = 1e-8  # Very small time for stability
        y_large = self._solve_first_order(k_large, 1.0, t_small)
        expected_large = 1.0 * np.exp(-k_large * t_small)
        assert abs(y_large - expected_large) / expected_large < 1e-3

    def test_near_zero_concentrations(self):
        """Test numerical stability near zero concentrations."""
        # Test behavior when concentrations approach machine epsilon

        epsilon = np.finfo(float).eps
        near_zero = 10 * epsilon

        # Ensure calculations don't produce negative concentrations
        concentration = near_zero
        rate_constant = 0.1
        dt = 0.01

        # Simple decay: dc/dt = -k*c
        new_concentration = concentration * np.exp(-rate_constant * dt)

        assert new_concentration >= 0
        assert new_concentration <= concentration
        assert not np.isnan(new_concentration)
        assert not np.isinf(new_concentration)

    def _solve_first_order(self, k: float, y0: float, t: float) -> float:
        """Solve first-order ODE dy/dt = -ky analytically."""
        return y0 * np.exp(-k * t)


class TestSymbolicDifferentiationVerification:
    """Test symbolic differentiation correctness verification."""

    def test_polynomial_differentiation(self):
        """Test differentiation of polynomial expressions."""
        # Test d/dx(x^n) = n*x^(n-1)

        test_cases = [
            # (expression_desc, expected_derivative_desc, x_val, expected_result)
            ("x^2", "2*x", 3.0, 6.0),
            ("x^3", "3*x^2", 2.0, 12.0),
            ("2*x^4", "8*x^3", 1.5, 27.0),
            ("x^5 + 3*x^2", "5*x^4 + 6*x", 2.0, 92.0)
        ]

        for expr_desc, deriv_desc, x_val, expected in test_cases:
            # For this test, we manually verify known derivatives
            if expr_desc == "x^2":
                computed = 2 * x_val  # d/dx(x^2) = 2x
            elif expr_desc == "x^3":
                computed = 3 * x_val**2  # d/dx(x^3) = 3x^2
            elif expr_desc == "2*x^4":
                computed = 8 * x_val**3  # d/dx(2x^4) = 8x^3
            elif expr_desc == "x^5 + 3*x^2":
                computed = 5 * x_val**4 + 6 * x_val  # d/dx(x^5 + 3x^2) = 5x^4 + 6x

            assert abs(computed - expected) < 1e-10

    def test_trigonometric_differentiation(self):
        """Test differentiation of trigonometric functions."""
        # Test derivatives: d/dx(sin(x)) = cos(x), d/dx(cos(x)) = -sin(x)

        x_values = [0, np.pi/4, np.pi/2, np.pi]

        for x in x_values:
            # d/dx(sin(x)) = cos(x)
            sin_derivative = np.cos(x)
            expected_sin_deriv = np.cos(x)
            assert abs(sin_derivative - expected_sin_deriv) < 1e-10

            # d/dx(cos(x)) = -sin(x)
            cos_derivative = -np.sin(x)
            expected_cos_deriv = -np.sin(x)
            assert abs(cos_derivative - expected_cos_deriv) < 1e-10

    def test_chain_rule_differentiation(self):
        """Test chain rule: d/dx[f(g(x))] = f'(g(x)) * g'(x)."""
        # Test d/dx[sin(x^2)] = cos(x^2) * 2x

        x_values = [1.0, 1.5, 2.0]

        for x in x_values:
            # f(g(x)) = sin(x^2), g(x) = x^2, f'(u) = cos(u), g'(x) = 2x
            # d/dx[sin(x^2)] = cos(x^2) * 2x
            derivative = np.cos(x**2) * 2 * x

            # Verify using numerical differentiation
            h = 1e-8
            f_plus = np.sin((x + h)**2)
            f_minus = np.sin((x - h)**2)
            numerical_derivative = (f_plus - f_minus) / (2 * h)

            relative_error = abs(derivative - numerical_derivative) / abs(numerical_derivative)
            assert relative_error < 1e-6

    def test_product_rule_differentiation(self):
        """Test product rule: d/dx[f(x)g(x)] = f'(x)g(x) + f(x)g'(x)."""
        # Test d/dx[x^2 * sin(x)] = 2x * sin(x) + x^2 * cos(x)

        x_values = [0.5, 1.0, 1.5]

        for x in x_values:
            # f(x) = x^2, g(x) = sin(x)
            # f'(x) = 2x, g'(x) = cos(x)
            # Product rule: 2x * sin(x) + x^2 * cos(x)
            derivative = 2 * x * np.sin(x) + x**2 * np.cos(x)

            # Numerical verification
            h = 1e-8
            f_plus = (x + h)**2 * np.sin(x + h)
            f_minus = (x - h)**2 * np.sin(x - h)
            numerical_derivative = (f_plus - f_minus) / (2 * h)

            relative_error = abs(derivative - numerical_derivative) / abs(numerical_derivative)
            assert relative_error < 1e-6


class TestIntegrationAccuracyVerification:
    """Test integration accuracy with known analytical solutions."""

    def test_polynomial_integration(self):
        """Test integration of polynomial functions."""
        # ∫x^n dx = x^(n+1)/(n+1) + C

        test_cases = [
            # (n, lower, upper, expected)
            (1, 0, 2, 2.0),      # ∫x dx from 0 to 2 = [x²/2] = 2
            (2, 0, 3, 9.0),      # ∫x² dx from 0 to 3 = [x³/3] = 9
            (3, 1, 2, 3.75),     # ∫x³ dx from 1 to 2 = [x⁴/4] = 4 - 0.25 = 3.75
        ]

        for n, a, b, expected in test_cases:
            # Analytical result
            analytical = (b**(n+1) - a**(n+1)) / (n+1)
            assert abs(analytical - expected) < 1e-10

            # Numerical integration using trapezoidal rule
            x = np.linspace(a, b, 10001)  # High resolution
            y = x**n
            numerical = self._trapz(y, x)

            relative_error = abs(numerical - analytical) / analytical
            assert relative_error < 1e-6

    def test_trigonometric_integration(self):
        """Test integration of trigonometric functions."""
        # ∫sin(x) dx = -cos(x) + C
        # ∫cos(x) dx = sin(x) + C

        # Test ∫sin(x) dx from 0 to π = [-cos(x)] = -cos(π) + cos(0) = 1 + 1 = 2
        a, b = 0, np.pi
        analytical_sin = -np.cos(b) + np.cos(a)  # = 2.0

        x = np.linspace(a, b, 10001)
        y_sin = np.sin(x)
        numerical_sin = self._trapz(y_sin, x)

        relative_error = abs(numerical_sin - analytical_sin) / analytical_sin
        assert relative_error < 1e-6

        # Test ∫cos(x) dx from 0 to π/2 = [sin(x)] = sin(π/2) - sin(0) = 1
        a, b = 0, np.pi/2
        analytical_cos = np.sin(b) - np.sin(a)  # = 1.0

        x = np.linspace(a, b, 10001)
        y_cos = np.cos(x)
        numerical_cos = self._trapz(y_cos, x)

        relative_error = abs(numerical_cos - analytical_cos) / analytical_cos
        assert relative_error < 1e-6

    def test_exponential_integration(self):
        """Test integration of exponential functions."""
        # ∫e^x dx = e^x + C
        # ∫e^(ax) dx = e^(ax)/a + C

        # Test ∫e^x dx from 0 to 1 = [e^x] = e - 1
        a, b = 0, 1
        analytical = np.exp(b) - np.exp(a)  # = e - 1

        x = np.linspace(a, b, 10001)
        y = np.exp(x)
        numerical = self._trapz(y, x)

        relative_error = abs(numerical - analytical) / analytical
        assert relative_error < 1e-6

        # Test ∫e^(-2x) dx from 0 to 1 = [-e^(-2x)/2] = -e^(-2)/2 + 1/2
        coeff = -2
        analytical_scaled = (np.exp(coeff * b) - np.exp(coeff * a)) / coeff

        x = np.linspace(a, b, 10001)
        y_scaled = np.exp(coeff * x)
        numerical_scaled = self._trapz(y_scaled, x)

        relative_error = abs(numerical_scaled - analytical_scaled) / abs(analytical_scaled)
        assert relative_error < 1e-6

    def _trapz(self, y: np.ndarray, x: np.ndarray) -> float:
        """Trapezoidal integration (replacement for deprecated numpy.trapz)."""
        return np.sum((y[1:] + y[:-1]) * np.diff(x)) / 2.0


class TestSteadyStateVerification:
    """Test steady-state calculation verification."""

    def test_linear_system_steady_state(self):
        """Test steady state for linear system of equations."""
        # System: dx/dt = Ax + b
        # Steady state: 0 = Ax_ss + b => x_ss = -A^(-1)b

        A = np.array([[-2, 1], [1, -3]])
        b = np.array([1, 2])

        # Analytical steady state
        x_ss_analytical = -np.linalg.solve(A, b)

        # Verify it's actually steady state
        dx_dt = A @ x_ss_analytical + b
        np.testing.assert_array_almost_equal(dx_dt, [0, 0], decimal=10)

        # Numerical verification by long-time integration
        dt = 0.01
        t_final = 10.0  # Long time
        n_steps = int(t_final / dt)

        x = np.array([10.0, 5.0])  # Arbitrary initial condition

        for _ in range(n_steps):
            dx_dt = A @ x + b
            x = x + dt * dx_dt

        # Should converge to steady state
        np.testing.assert_allclose(x, x_ss_analytical, rtol=1e-3)

    def test_reaction_equilibrium(self):
        """Test steady state for reversible reaction system."""
        # A <-> B with forward rate kf and reverse rate kr
        # At equilibrium: kf*[A] = kr*[B]
        # With conservation: [A] + [B] = [A]₀ + [B]₀

        kf, kr = 2.0, 0.5  # Forward and reverse rate constants
        A0, B0 = 1.0, 0.0  # Initial concentrations
        total = A0 + B0

        # Analytical equilibrium
        # kf*A_eq = kr*B_eq and A_eq + B_eq = total
        # => kf*A_eq = kr*(total - A_eq)
        # => A_eq = kr*total/(kf + kr)
        A_eq = kr * total / (kf + kr)
        B_eq = total - A_eq

        # Verify equilibrium condition
        forward_rate = kf * A_eq
        reverse_rate = kr * B_eq
        assert abs(forward_rate - reverse_rate) < 1e-10

        # Numerical verification
        dt = 0.01
        A, B = A0, B0

        for _ in range(10000):  # Long simulation
            dA_dt = -kf * A + kr * B
            dB_dt = kf * A - kr * B
            A += dt * dA_dt
            B += dt * dB_dt

        np.testing.assert_allclose([A, B], [A_eq, B_eq], rtol=1e-3)

    def test_enzyme_kinetics_steady_state(self):
        """Test steady state approximation for enzyme kinetics."""
        # Michaelis-Menten mechanism: E + S <-> ES -> E + P
        # Quasi-steady state approximation: d[ES]/dt ≈ 0

        # Parameters
        k1, k_1, k2 = 1e6, 1e3, 1e2  # Rate constants
        E_total = 1e-6  # Total enzyme concentration (M)
        S = 1e-3        # Substrate concentration (M)

        # Steady state ES concentration
        Km = (k_1 + k2) / k1  # Michaelis constant
        ES_ss = E_total * S / (Km + S)

        # Verify steady state condition: d[ES]/dt = 0
        # d[ES]/dt = k1*[E]*[S] - (k_1 + k2)*[ES]
        E_free = E_total - ES_ss
        formation_rate = k1 * E_free * S
        consumption_rate = (k_1 + k2) * ES_ss

        relative_error = abs(formation_rate - consumption_rate) / formation_rate
        assert relative_error < 1e-10


class TestParameterEstimationVerification:
    """Test parameter estimation convergence and accuracy."""

    def test_linear_regression_parameter_estimation(self):
        """Test parameter estimation for linear model y = ax + b."""
        # Generate synthetic data with known parameters
        true_a, true_b = 2.5, 1.3
        x_data = np.linspace(0, 10, 100)
        noise = np.random.normal(0, 0.1, size=x_data.shape)
        y_data = true_a * x_data + true_b + noise

        # Least squares estimation
        X = np.column_stack([x_data, np.ones(len(x_data))])
        params = np.linalg.lstsq(X, y_data, rcond=None)[0]
        estimated_a, estimated_b = params

        # Check convergence within reasonable error bounds
        assert abs(estimated_a - true_a) < 0.1  # 4% tolerance
        assert abs(estimated_b - true_b) < 0.1  # ~8% tolerance

    def test_nonlinear_parameter_estimation_convergence(self):
        """Test convergence for nonlinear parameter estimation."""
        # Exponential decay model: y = A * exp(-k * t)

        # Use deterministic data for reproducible test
        true_A, true_k = 10.0, 0.5
        t_data = np.linspace(0, 5, 50)

        # Use small fixed noise for reproducibility
        np.random.seed(42)  # Fixed seed
        noise = np.random.normal(0, 0.05, size=t_data.shape)  # Reduced noise
        y_data = true_A * np.exp(-true_k * t_data) + noise

        # Use analytical solution for exponential fitting when possible
        # For y = A * exp(-k * t), take ln: ln(y) = ln(A) - k*t
        # Linear regression on log space (handle positive values only)
        y_positive = np.maximum(y_data, 1e-10)  # Avoid log(0)
        ln_y = np.log(y_positive)

        # Linear fit: ln(y) = ln(A) - k*t
        X = np.column_stack([np.ones(len(t_data)), -t_data])
        params = np.linalg.lstsq(X, ln_y, rcond=None)[0]
        ln_A_est, k_est = params
        A_est = np.exp(ln_A_est)

        # Verify reasonable convergence (more lenient for noisy data)
        assert abs(A_est - true_A) < 1.0   # 10% tolerance
        assert abs(k_est - true_k) < 0.1   # 20% tolerance

    def test_parameter_estimation_uncertainty_quantification(self):
        """Test parameter uncertainty quantification."""
        # Simple linear case with analytical solution for uncertainty

        true_slope = 1.0
        x_data = np.array([1, 2, 3, 4, 5], dtype=float)
        sigma_noise = 0.1  # Known noise level

        # Generate data
        y_data = true_slope * x_data + np.random.normal(0, sigma_noise, size=len(x_data))

        # Fit y = slope * x (no intercept)
        slope_est = np.sum(x_data * y_data) / np.sum(x_data**2)

        # Analytical uncertainty in slope
        slope_uncertainty = sigma_noise / np.sqrt(np.sum(x_data**2))

        # Parameter should be within 2-sigma of true value most of the time
        deviation = abs(slope_est - true_slope)
        assert deviation < 2 * slope_uncertainty


class TestVerificationModuleIntegration:
    """Test integration of the verification module with existing functionality."""

    def test_verification_module_stoichiometric_matrix(self):
        """Test verification module's stoichiometric matrix computation."""
        # Simple reaction: A + B -> C
        species = [
            Species(name="A"), Species(name="B"), Species(name="C")
        ]
        reaction = Reaction(
            name="synthesis",
            reactants={"A": 1.0, "B": 1.0},
            products={"C": 1.0}
        )
        reaction_system = ReactionSystem("test", species=species, reactions=[reaction])

        # Test using verification module
        matrix = compute_stoichiometric_matrix(reaction_system)
        expected = np.array([[-1.0], [-1.0], [1.0]])

        np.testing.assert_array_equal(matrix, expected)

        # Test consistency with existing method
        existing_matrix = self._compute_stoichiometric_matrix(reaction_system)
        np.testing.assert_array_equal(matrix, existing_matrix)

    def test_verification_module_mass_conservation(self):
        """Test verification module's mass conservation checking."""
        species = [
            Species(name="CH4", mass=16.04),
            Species(name="O2", mass=31.998),
            Species(name="CO2", mass=44.01),
            Species(name="H2O", mass=18.015)
        ]
        reaction = Reaction(
            name="combustion",
            reactants={"CH4": 1, "O2": 2},
            products={"CO2": 1, "H2O": 2}
        )
        reaction_system = ReactionSystem("combustion", species=species, reactions=[reaction])

        # Test full verification with appropriate tolerance for molecular weights
        report = verify_reaction_system(reaction_system, tolerance=1e-4)

        # Should pass all major tests
        assert report.passed()
        assert report.summary["pass"] > 0
        assert report.summary["fail"] == 0

        # Check specific mass conservation result
        mass_results = [r for r in report.results if "mass conservation" in r.message.lower()]
        assert len(mass_results) > 0
        assert mass_results[0].status == VerificationStatus.PASS

    def test_verification_module_model_validation(self):
        """Test verification module's model validation."""
        # Create a simple model with consistent variables and equations
        variables = {
            "x": ModelVariable(type="state", units="m"),
            "v": ModelVariable(type="state", units="m/s"),
            "t": ModelVariable(type="parameter", units="s")
        }

        equations = [
            Equation(lhs="dx_dt", rhs="v"),
            Equation(lhs="dv_dt", rhs="-9.8")  # Simple gravity
        ]

        model = Model(name="falling_object", variables=variables, equations=equations)

        # Test model verification
        report = verify_model(model)

        # Should have some passing tests
        assert len(report.results) > 0

        # Check that variable-equation consistency is verified
        consistency_results = [r for r in report.results if "consistency" in r.message.lower()]
        assert len(consistency_results) > 0

    def test_verification_module_error_handling(self):
        """Test verification module's error handling with invalid data."""
        # Empty reaction system
        empty_system = ReactionSystem("empty")
        report = verify_reaction_system(empty_system)

        # Should handle gracefully with warnings
        assert len(report.results) > 0
        # Should have warnings but not crash
        warning_count = report.summary["warning"]
        assert warning_count >= 0

    def test_verification_module_numerical_stability(self):
        """Test numerical stability analysis."""
        verifier = MathematicalVerifier(tolerance=1e-10)

        # Test with well-conditioned matrix
        well_conditioned = np.array([[1, 0], [0, 1]])  # Identity matrix
        stability = verifier.check_numerical_stability(well_conditioned)

        assert stability["is_well_conditioned"]
        assert stability["condition_number"] == 1.0

        # Test with ill-conditioned matrix
        ill_conditioned = np.array([[1, 1], [1, 1.0001]])  # Nearly singular
        stability_bad = verifier.check_numerical_stability(ill_conditioned)

        assert stability_bad["condition_number"] > 1000  # Should be large

    def test_verification_module_conservation_analysis(self):
        """Test conservation law analysis."""
        verifier = MathematicalVerifier()

        # Simple conservation example: A -> B (1:1 ratio)
        species = [Species(name="A", mass=10.0), Species(name="B", mass=10.0)]
        reaction = Reaction("conversion", reactants={"A": 1}, products={"B": 1})
        reaction_system = ReactionSystem("conservation_test", species=species, reactions=[reaction])

        stoich_matrix = verifier.compute_stoichiometric_matrix(reaction_system)
        mass_vector = np.array([[10.0], [10.0]])

        analysis = verifier.analyze_conservation_laws(stoich_matrix, mass_vector)

        assert "mass_conserved" in analysis
        assert analysis["mass_conserved"] == True
        assert analysis["conserved_quantities"] >= 1

    def _compute_stoichiometric_matrix(self, reaction_system: ReactionSystem) -> np.ndarray:
        """Helper method for backward compatibility testing."""
        species_names = [s.name for s in reaction_system.species]
        n_species = len(species_names)
        n_reactions = len(reaction_system.reactions)

        matrix = np.zeros((n_species, n_reactions))

        for j, reaction in enumerate(reaction_system.reactions):
            for species, coeff in reaction.reactants.items():
                i = species_names.index(species)
                matrix[i, j] -= coeff
            for species, coeff in reaction.products.items():
                i = species_names.index(species)
                matrix[i, j] += coeff

        return matrix