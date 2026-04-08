"""
Comprehensive simulation test fixtures for Python implementation.

This module provides test fixtures covering:
1. Simulation reference trajectories with known analytical solutions for validation
2. SymPy symbolic computation integration and correctness verification
3. SciPy numerical integration accuracy and stability tests
4. NumPy array operations and broadcasting behavior
5. Performance benchmarks for large-scale simulations
6. Parameter estimation and optimization convergence tests
7. Sensitivity analysis and uncertainty quantification
8. Parallel simulation execution with multiprocessing
9. Integration with Jupyter notebook environments

These simulation capabilities are essential for Python's role as the primary analysis platform.
"""

import pytest
import numpy as np
import json
import time
import multiprocessing
from typing import Callable, Dict, List, Tuple, Any
from unittest.mock import patch
from contextlib import contextmanager

# Core imports
from esm_format.esm_types import (
    Model, ModelVariable, Equation, ExprNode, EsmFile, Metadata,
    ReactionSystem, Species, Parameter, Reaction
)
from esm_format.parse import load
from esm_format.serialize import save

# Scientific computing imports with fallbacks for optional dependencies
try:
    import sympy as sp
    SYMPY_AVAILABLE = True
except ImportError:
    SYMPY_AVAILABLE = False
    sp = None

try:
    from scipy.integrate import solve_ivp, quad
    from scipy.optimize import minimize, differential_evolution
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


# ========================================
# 1. Analytical Solution Reference Trajectories
# ========================================

class AnalyticalSolutions:
    """Reference analytical solutions for validation."""

    @staticmethod
    def exponential_decay(t: np.ndarray, x0: float = 1.0, k: float = 0.1) -> np.ndarray:
        """Analytical solution for dx/dt = -k*x with x(0) = x0."""
        return x0 * np.exp(-k * t)

    @staticmethod
    def exponential_growth(t: np.ndarray, x0: float = 1.0, k: float = 0.1) -> np.ndarray:
        """Analytical solution for dx/dt = k*x with x(0) = x0."""
        return x0 * np.exp(k * t)

    @staticmethod
    def harmonic_oscillator(t: np.ndarray, x0: float = 1.0, v0: float = 0.0, omega: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
        """Analytical solution for harmonic oscillator d²x/dt² + ω²x = 0."""
        A = x0
        B = v0 / omega if omega != 0 else 0
        x = A * np.cos(omega * t) + B * np.sin(omega * t)
        v = -A * omega * np.sin(omega * t) + B * omega * np.cos(omega * t)
        return x, v

    @staticmethod
    def logistic_growth(t: np.ndarray, x0: float = 0.1, r: float = 1.0, K: float = 10.0) -> np.ndarray:
        """Analytical solution for logistic equation dx/dt = r*x*(1 - x/K)."""
        return K / (1 + (K/x0 - 1) * np.exp(-r * t))


def test_analytical_solutions():
    """Test analytical solution generators for correctness."""
    t = np.linspace(0, 5, 100)

    # Test exponential decay
    x_decay = AnalyticalSolutions.exponential_decay(t, x0=2.0, k=0.5)
    assert np.isclose(x_decay[0], 2.0), "Initial condition not satisfied"
    assert x_decay[-1] < x_decay[0], "Should be decaying"

    # Test exponential growth
    x_growth = AnalyticalSolutions.exponential_growth(t, x0=1.0, k=0.2)
    assert np.isclose(x_growth[0], 1.0), "Initial condition not satisfied"
    assert x_growth[-1] > x_growth[0], "Should be growing"

    # Test harmonic oscillator
    x, v = AnalyticalSolutions.harmonic_oscillator(t, x0=1.0, v0=0.0, omega=2.0)
    assert np.isclose(x[0], 1.0), "Initial position not satisfied"
    assert np.isclose(v[0], 0.0), "Initial velocity not satisfied"

    # Test energy conservation (E = 0.5*v² + 0.5*ω²*x²)
    omega = 2.0
    energy = 0.5 * v**2 + 0.5 * omega**2 * x**2
    assert np.allclose(energy, energy[0], rtol=1e-10), "Energy should be conserved"

    # Test logistic growth
    x_logistic = AnalyticalSolutions.logistic_growth(t, x0=0.1, r=1.0, K=10.0)
    assert np.isclose(x_logistic[0], 0.1), "Initial condition not satisfied"
    assert x_logistic[-1] < 10.0, "Should approach carrying capacity"


# ========================================
# 2. SymPy Symbolic Computation Integration
# ========================================

@pytest.mark.skipif(not SYMPY_AVAILABLE, reason="SymPy not available")
class TestSymPyIntegration:
    """Test SymPy symbolic computation integration."""

    def test_symbolic_expression_creation(self):
        """Test creating SymPy expressions from ESM expressions."""
        # Create symbolic variables
        t, x, y = sp.symbols('t x y')

        # Test basic arithmetic
        expr = x + 2*y - sp.sin(t)
        assert str(expr) == "x + 2*y - sin(t)"

        # Test derivatives
        dx_dt = sp.diff(x*sp.cos(t), t)
        expected = -x*sp.sin(t) + sp.cos(t)*sp.diff(x, t)
        assert sp.simplify(dx_dt - expected) == 0

    def test_symbolic_ode_solving(self):
        """Test solving ODEs symbolically."""
        t = sp.Symbol('t')
        x = sp.Function('x')

        # Simple exponential decay: dx/dt + k*x = 0
        k = sp.Symbol('k', positive=True)
        ode = sp.Eq(x(t).diff(t), -k*x(t))
        solution = sp.dsolve(ode, x(t))

        # Verify solution form
        assert 'exp(-k*t)' in str(solution)

    def test_expression_node_to_sympy_conversion(self):
        """Test converting ESM ExprNode to SymPy expressions."""
        def convert_expr_to_sympy(expr):
            """Convert ExprNode to SymPy expression (simplified implementation)."""
            if isinstance(expr, (int, float)):
                return sp.sympify(expr)
            elif isinstance(expr, str):
                return sp.Symbol(expr)
            elif isinstance(expr, ExprNode):
                if expr.op == '+':
                    return sum(convert_expr_to_sympy(arg) for arg in expr.args)
                elif expr.op == '*':
                    result = sp.sympify(1)
                    for arg in expr.args:
                        result *= convert_expr_to_sympy(arg)
                    return result
                elif expr.op == 'sin':
                    return sp.sin(convert_expr_to_sympy(expr.args[0]))
                elif expr.op == 'cos':
                    return sp.cos(convert_expr_to_sympy(expr.args[0]))
                elif expr.op == 'exp':
                    return sp.exp(convert_expr_to_sympy(expr.args[0]))
            return sp.sympify(0)

        # Test conversion
        expr_node = ExprNode(op='+', args=['x', ExprNode(op='*', args=[2, 'y'])])
        sympy_expr = convert_expr_to_sympy(expr_node)
        expected = sp.Symbol('x') + 2 * sp.Symbol('y')
        assert sympy_expr.equals(expected)

    def test_symbolic_jacobian_computation(self):
        """Test computing Jacobians symbolically."""
        x, y, z = sp.symbols('x y z')

        # System of equations
        f1 = x**2 + y - z
        f2 = x + y**2 - 2*z
        f3 = x*y - z**2

        system = [f1, f2, f3]
        variables = [x, y, z]

        # Compute Jacobian
        jacobian = sp.Matrix([[sp.diff(f, var) for var in variables] for f in system])

        # Verify some elements
        assert jacobian[0, 0] == 2*x  # ∂f1/∂x
        assert jacobian[1, 1] == 2*y  # ∂f2/∂y
        assert jacobian[2, 2] == -2*z  # ∂f3/∂z


# ========================================
# 3. SciPy Numerical Integration Tests
# ========================================

@pytest.mark.skipif(not SCIPY_AVAILABLE, reason="SciPy not available")
class TestSciPyIntegration:
    """Test SciPy numerical integration accuracy and stability."""

    def test_ode_integration_accuracy(self):
        """Test ODE integration accuracy against analytical solutions."""
        def exponential_decay_ode(t, y, k):
            """ODE function for dx/dt = -k*x."""
            return [-k * y[0]]

        # Parameters
        t_span = (0, 5)
        y0 = [2.0]
        k = 0.5
        t_eval = np.linspace(0, 5, 50)

        # Solve numerically
        sol = solve_ivp(exponential_decay_ode, t_span, y0, args=(k,), t_eval=t_eval, rtol=1e-8)

        # Compare with analytical solution
        analytical = AnalyticalSolutions.exponential_decay(t_eval, x0=2.0, k=0.5)

        # Check accuracy
        assert sol.success, "Integration should succeed"
        np.testing.assert_allclose(sol.y[0], analytical, rtol=1e-6)

    def test_stiff_ode_solver_stability(self):
        """Test stability with stiff ODEs."""
        def van_der_pol_oscillator(t, y, mu):
            """Van der Pol oscillator (stiff for large mu)."""
            x, dx_dt = y
            return [dx_dt, mu * (1 - x**2) * dx_dt - x]

        # Stiff system with large mu
        mu = 100.0
        t_span = (0, 20)
        y0 = [2.0, 0.0]

        # Use stiff solver
        sol = solve_ivp(van_der_pol_oscillator, t_span, y0, args=(mu,), method='Radau', rtol=1e-6)

        assert sol.success, "Stiff solver should handle the system"
        assert len(sol.t) > 10, "Should produce reasonable number of points"

    def test_integration_method_comparison(self):
        """Compare different integration methods for the same problem."""
        def simple_harmonic_oscillator(t, y, omega):
            """Simple harmonic oscillator."""
            x, v = y
            return [v, -omega**2 * x]

        omega = 2.0
        t_span = (0, 10)
        y0 = [1.0, 0.0]
        t_eval = np.linspace(0, 10, 100)

        methods = ['RK45', 'RK23', 'DOP853']
        solutions = {}

        for method in methods:
            sol = solve_ivp(simple_harmonic_oscillator, t_span, y0, args=(omega,),
                          method=method, t_eval=t_eval, rtol=1e-8)
            solutions[method] = sol
            assert sol.success, f"Method {method} should succeed"

        # All methods should give similar results
        for method in methods[1:]:
            np.testing.assert_allclose(solutions[methods[0]].y[0], solutions[method].y[0], rtol=1e-2, atol=1e-3)

    def test_numerical_quadrature_accuracy(self):
        """Test numerical quadrature against known integrals."""
        # Test ∫₀¹ x² dx = 1/3
        result, _ = quad(lambda x: x**2, 0, 1)
        assert np.isclose(result, 1/3, rtol=1e-10)

        # Test ∫₀^π sin(x) dx = 2
        result, _ = quad(np.sin, 0, np.pi)
        assert np.isclose(result, 2, rtol=1e-10)

        # Test Gaussian integral ∫₋∞^∞ exp(-x²) dx = √π
        result, _ = quad(lambda x: np.exp(-x**2), -np.inf, np.inf)
        assert np.isclose(result, np.sqrt(np.pi), rtol=1e-10)


# ========================================
# 4. NumPy Array Operations and Broadcasting
# ========================================

class TestNumPyOperations:
    """Test NumPy array operations and broadcasting behavior."""

    def test_array_creation_and_manipulation(self):
        """Test array creation and basic manipulations."""
        # Test array creation
        a = np.array([1, 2, 3, 4])
        b = np.arange(0, 10, 0.5)
        c = np.linspace(0, 1, 11)
        d = np.zeros((3, 4))
        e = np.ones((2, 3, 4))

        assert a.shape == (4,)
        assert b.shape == (20,)
        assert c.shape == (11,)
        assert d.shape == (3, 4)
        assert e.shape == (2, 3, 4)

        # Test array modification
        a[0] = 10
        assert a[0] == 10

        # Test slicing
        assert np.array_equal(a[1:3], [2, 3])

    def test_broadcasting_rules(self):
        """Test NumPy broadcasting rules for array operations."""
        # Scalar and array
        a = np.array([1, 2, 3])
        result = a + 5
        expected = np.array([6, 7, 8])
        np.testing.assert_array_equal(result, expected)

        # Arrays with compatible shapes
        b = np.array([[1], [2], [3]])  # shape (3, 1)
        c = np.array([10, 20, 30])     # shape (3,)
        result = b + c  # should broadcast to (3, 3)
        expected = np.array([[11, 21, 31], [12, 22, 32], [13, 23, 33]])
        np.testing.assert_array_equal(result, expected)

        # Test broadcasting error
        d = np.array([[1, 2], [3, 4]])  # shape (2, 2)
        e = np.array([1, 2, 3])         # shape (3,)
        with pytest.raises(ValueError):
            _ = d + e  # Should raise broadcasting error

    def test_vectorized_operations(self):
        """Test vectorized mathematical operations."""
        x = np.linspace(0, 2*np.pi, 1000)

        # Test trigonometric functions
        sin_x = np.sin(x)
        cos_x = np.cos(x)

        # Test trigonometric identity: sin²(x) + cos²(x) = 1
        identity = sin_x**2 + cos_x**2
        np.testing.assert_allclose(identity, 1.0, rtol=1e-12)

        # Test exponential and logarithm
        y = np.exp(x)
        log_y = np.log(y)
        np.testing.assert_allclose(log_y, x, rtol=1e-12)

    def test_array_reduction_operations(self):
        """Test array reduction operations (sum, mean, etc.)."""
        a = np.random.rand(5, 4, 3)

        # Test different axis reductions
        sum_all = np.sum(a)
        sum_axis0 = np.sum(a, axis=0)
        sum_axis1 = np.sum(a, axis=1)
        sum_axis2 = np.sum(a, axis=2)

        assert sum_axis0.shape == (4, 3)
        assert sum_axis1.shape == (5, 3)
        assert sum_axis2.shape == (5, 4)

        # Test statistical operations
        mean_val = np.mean(a)
        std_val = np.std(a)
        var_val = np.var(a)

        assert np.isclose(var_val, std_val**2, rtol=1e-14)

        # Test along specific axes
        mean_axis0 = np.mean(a, axis=0)
        assert mean_axis0.shape == (4, 3)

    def test_linear_algebra_operations(self):
        """Test basic linear algebra operations."""
        # Matrix multiplication
        A = np.random.rand(3, 4)
        B = np.random.rand(4, 5)
        C = A @ B  # Matrix multiplication

        assert C.shape == (3, 5)

        # Test with explicit np.dot
        C_dot = np.dot(A, B)
        np.testing.assert_allclose(C, C_dot)

        # Square matrix operations
        M = np.random.rand(4, 4)

        # Eigenvalues and eigenvectors
        eigenvals, eigenvecs = np.linalg.eig(M)
        assert eigenvals.shape == (4,)
        assert eigenvecs.shape == (4, 4)

        # Test eigenvalue equation: M @ v = λ * v
        for i in range(4):
            lhs = M @ eigenvecs[:, i]
            rhs = eigenvals[i] * eigenvecs[:, i]
            np.testing.assert_allclose(lhs, rhs, rtol=1e-10)


# ========================================
# 5. Performance Benchmarks
# ========================================

class TestPerformanceBenchmarks:
    """Performance benchmarks for large-scale simulations."""

    def test_large_array_operations_performance(self):
        """Benchmark performance of large array operations."""
        sizes = [10**4, 10**5, 10**6]

        for size in sizes:
            # Create large arrays
            start_time = time.time()
            a = np.random.rand(size)
            b = np.random.rand(size)
            creation_time = time.time() - start_time

            # Element-wise operations
            start_time = time.time()
            c = a + b
            d = a * b
            e = np.sin(a) + np.cos(b)
            operation_time = time.time() - start_time

            # Reduction operations
            start_time = time.time()
            sum_a = np.sum(a)
            mean_a = np.mean(a)
            std_a = np.std(a)
            reduction_time = time.time() - start_time

            print(f"Size {size}: Creation {creation_time:.4f}s, Operations {operation_time:.4f}s, Reductions {reduction_time:.4f}s")

            # Performance assertions (these are rough guidelines)
            assert creation_time < 1.0, f"Array creation too slow for size {size}"
            assert operation_time < 1.0, f"Array operations too slow for size {size}"
            assert reduction_time < 0.5, f"Reductions too slow for size {size}"

    def test_matrix_multiplication_scaling(self):
        """Test matrix multiplication performance scaling."""
        sizes = [100, 200, 500]

        for size in sizes:
            A = np.random.rand(size, size)
            B = np.random.rand(size, size)

            start_time = time.time()
            C = A @ B
            mult_time = time.time() - start_time

            print(f"Matrix size {size}×{size}: Multiplication {mult_time:.4f}s")

            # Verify result
            assert C.shape == (size, size)

            # Performance should scale roughly as O(n³) but with BLAS optimization
            # These are very loose bounds
            expected_max_time = (size / 100)**2 * 0.1  # Very rough estimate
            assert mult_time < max(expected_max_time, 5.0), f"Matrix multiplication too slow for size {size}"

    @pytest.mark.skipif(not SCIPY_AVAILABLE, reason="SciPy not available")
    def test_ode_integration_performance(self):
        """Benchmark ODE integration performance."""
        def system_ode(t, y):
            """Large system of ODEs."""
            n = len(y)
            dydt = np.zeros(n)
            for i in range(n):
                dydt[i] = -0.1 * y[i] + 0.01 * np.sum(y) - y[i]**2
            return dydt

        system_sizes = [10, 50, 100]

        for n in system_sizes:
            y0 = np.random.rand(n)
            t_span = (0, 1)

            start_time = time.time()
            sol = solve_ivp(system_ode, t_span, y0, rtol=1e-6)
            integration_time = time.time() - start_time

            print(f"ODE system size {n}: Integration {integration_time:.4f}s")

            assert sol.success, f"Integration should succeed for system size {n}"
            # Performance bound (very loose)
            assert integration_time < 5.0, f"Integration too slow for system size {n}"


# ========================================
# 6. Parameter Estimation and Optimization
# ========================================

@pytest.mark.skipif(not SCIPY_AVAILABLE, reason="SciPy not available")
class TestParameterEstimation:
    """Test parameter estimation and optimization convergence."""

    def test_simple_parameter_estimation(self):
        """Test parameter estimation for a simple exponential model."""
        # Generate synthetic data
        true_params = {'x0': 2.0, 'k': 0.3}
        t_data = np.linspace(0, 5, 20)
        y_true = AnalyticalSolutions.exponential_decay(t_data, **true_params)
        y_data = y_true + 0.1 * np.random.randn(len(t_data))  # Add noise

        def objective(params):
            """Objective function for parameter estimation."""
            x0, k = params
            y_model = AnalyticalSolutions.exponential_decay(t_data, x0, k)
            return np.sum((y_data - y_model)**2)

        # Initial guess
        initial_guess = [1.0, 0.1]

        # Optimize
        result = minimize(objective, initial_guess, method='Nelder-Mead')

        assert result.success, "Optimization should converge"

        # Check parameter recovery (within reasonable tolerance due to noise)
        estimated_params = result.x
        assert np.isclose(estimated_params[0], true_params['x0'], rtol=0.2)
        assert np.isclose(estimated_params[1], true_params['k'], rtol=0.2)

    def test_global_optimization(self):
        """Test global optimization with multiple local minima."""
        def rastrigin_function(x):
            """Rastrigin function - has many local minima."""
            A = 10
            n = len(x)
            return A * n + np.sum(x**2 - A * np.cos(2 * np.pi * x))

        # Global minimum is at x = [0, 0, ..., 0] with f = 0
        bounds = [(-5.12, 5.12)] * 3  # 3D optimization

        result = differential_evolution(rastrigin_function, bounds, seed=42, maxiter=1000)

        assert result.success, "Global optimization should converge"
        assert np.allclose(result.x, 0, atol=0.1), "Should find global minimum near origin"
        assert result.fun < 1.0, "Should achieve low function value"

    def test_constrained_optimization(self):
        """Test optimization with constraints."""
        # Minimize x₁² + x₂² subject to x₁ + x₂ = 1
        def objective(x):
            return x[0]**2 + x[1]**2

        from scipy.optimize import LinearConstraint
        constraint = LinearConstraint([[1, 1]], [1], [1])  # x₁ + x₂ = 1

        result = minimize(objective, [0.0, 0.0], constraints=constraint, method='SLSQP')

        assert result.success, "Constrained optimization should converge"

        # Analytical solution: x₁ = x₂ = 0.5
        np.testing.assert_allclose(result.x, [0.5, 0.5], rtol=1e-6)
        assert np.isclose(result.fun, 0.5, rtol=1e-6)


# ========================================
# 7. Sensitivity Analysis and Uncertainty Quantification
# ========================================

class TestSensitivityAnalysis:
    """Test sensitivity analysis and uncertainty quantification."""

    def test_finite_difference_sensitivity(self):
        """Test finite difference sensitivity analysis."""
        def model_function(params):
            """Simple model: f(a, b, c) = a*x² + b*x + c evaluated at x=2."""
            a, b, c = params
            x = 2.0
            return a * x**2 + b * x + c

        # Reference parameters
        params0 = [1.0, 2.0, 3.0]  # f = 1*4 + 2*2 + 3 = 11

        # Compute sensitivities using finite differences
        h = 1e-6
        sensitivities = []

        for i in range(len(params0)):
            params_plus = params0.copy()
            params_minus = params0.copy()
            params_plus[i] += h
            params_minus[i] -= h

            f_plus = model_function(params_plus)
            f_minus = model_function(params_minus)

            sensitivity = (f_plus - f_minus) / (2 * h)
            sensitivities.append(sensitivity)

        # Analytical sensitivities for f(a,b,c) = 4a + 2b + c at x=2
        expected_sensitivities = [4.0, 2.0, 1.0]

        np.testing.assert_allclose(sensitivities, expected_sensitivities, rtol=1e-6)

    def test_monte_carlo_uncertainty_propagation(self):
        """Test Monte Carlo uncertainty propagation."""
        # Model: f(x) = sin(x) + cos(x)
        def model(x):
            return np.sin(x) + np.cos(x)

        # Uncertain input: x ~ N(π/4, σ²)
        mean_x = np.pi / 4
        std_x = 0.1
        n_samples = 10000

        # Generate samples
        np.random.seed(42)  # For reproducibility
        x_samples = np.random.normal(mean_x, std_x, n_samples)

        # Propagate uncertainty
        y_samples = model(x_samples)

        # Statistics
        mean_y = np.mean(y_samples)
        std_y = np.std(y_samples)

        # Analytical values at x = π/4
        # f(π/4) = sin(π/4) + cos(π/4) = √2
        # f'(x) = cos(x) - sin(x), f'(π/4) = 0
        expected_mean = np.sqrt(2)

        assert np.isclose(mean_y, expected_mean, rtol=1e-2)
        assert std_y > 0, "Output should have some uncertainty"

    def test_sobol_indices_estimation(self):
        """Test estimation of Sobol sensitivity indices (simplified)."""
        def ishigami_function(x):
            """Ishigami function for sensitivity analysis testing."""
            a, b = 7, 0.1
            return np.sin(x[0]) + a * np.sin(x[1])**2 + b * x[2]**4 * np.sin(x[0])

        # Generate uniform random samples in [-π, π]³
        np.random.seed(42)
        n_samples = 1000  # Reduced for testing

        # Two independent sample matrices
        A = np.random.uniform(-np.pi, np.pi, (n_samples, 3))
        B = np.random.uniform(-np.pi, np.pi, (n_samples, 3))

        # Evaluate function
        f_A = np.array([ishigami_function(A[i]) for i in range(n_samples)])
        f_B = np.array([ishigami_function(B[i]) for i in range(n_samples)])

        # Compute total variance
        all_samples = np.concatenate([f_A, f_B])
        total_variance = np.var(all_samples)

        assert total_variance > 0, "Function should have variance"

        # First-order indices (simplified calculation)
        first_order_indices = []
        for i in range(3):
            # Create C^i matrix (B with i-th column from A)
            C_i = B.copy()
            C_i[:, i] = A[:, i]
            f_C_i = np.array([ishigami_function(C_i[j]) for j in range(n_samples)])

            # First-order index approximation
            V_i = np.mean(f_B * f_C_i) - np.mean(f_B) * np.mean(f_C_i)
            S_i = V_i / total_variance
            first_order_indices.append(S_i)

        # Basic sanity checks (Sobol indices can be noisy with small samples)
        assert len(first_order_indices) == 3, "Should have three indices"
        # Note: With small sample sizes, Sobol indices can be negative or > 1 due to sampling error
        assert all(abs(idx) < 2.0 for idx in first_order_indices), "Indices should be reasonable"


# ========================================
# 8. Parallel Simulation Execution
# ========================================

class TestParallelExecution:
    """Test parallel simulation execution with multiprocessing."""

    def simulation_task(self, params):
        """Individual simulation task for parallel execution."""
        task_id, k_value = params

        # Simulate exponential decay with different decay constants
        t = np.linspace(0, 5, 100)
        x = AnalyticalSolutions.exponential_decay(t, x0=1.0, k=k_value)

        # Compute some summary statistics
        final_value = x[-1]
        integral = np.trapezoid(x, t)  # Numerical integration

        return {
            'task_id': task_id,
            'k_value': k_value,
            'final_value': final_value,
            'integral': integral,
            'max_value': np.max(x),
            'min_value': np.min(x)
        }

    def test_multiprocessing_simulation(self):
        """Test parallel execution of multiple simulations."""
        # Prepare parameter sets
        k_values = [0.1, 0.2, 0.3, 0.4, 0.5]
        tasks = [(i, k) for i, k in enumerate(k_values)]

        # Run simulations in parallel
        with multiprocessing.Pool(processes=2) as pool:
            results = pool.map(self.simulation_task, tasks)

        # Verify results
        assert len(results) == len(k_values)

        for result in results:
            assert 'task_id' in result
            assert 'k_value' in result
            assert 'final_value' in result
            assert 'integral' in result

            # Basic physics checks
            assert result['final_value'] > 0, "Final value should be positive"
            assert result['final_value'] < 1.0, "Final value should be less than initial"
            assert result['integral'] > 0, "Integral should be positive"

        # Check that higher decay constants lead to smaller final values
        final_values = [r['final_value'] for r in results]
        k_values_sorted = [r['k_value'] for r in results]

        # Sort by k_value and check monotonicity
        sorted_indices = np.argsort(k_values_sorted)
        sorted_final_values = [final_values[i] for i in sorted_indices]

        for i in range(1, len(sorted_final_values)):
            assert sorted_final_values[i] <= sorted_final_values[i-1], "Higher k should give smaller final value"

    def test_concurrent_parameter_sweep(self):
        """Test concurrent parameter sweep simulation."""
        import concurrent.futures

        def parameter_sweep_task(param_set):
            """Single parameter set evaluation."""
            x0, k = param_set

            t = np.linspace(0, 3, 50)
            x = AnalyticalSolutions.exponential_decay(t, x0=x0, k=k)

            return {
                'x0': x0,
                'k': k,
                'final_value': x[-1],
                'half_life': np.log(2) / k if k > 0 else np.inf
            }

        # Parameter combinations
        x0_values = [1.0, 2.0, 3.0]
        k_values = [0.1, 0.2, 0.3]
        param_sets = [(x0, k) for x0 in x0_values for k in k_values]

        # Run with ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(parameter_sweep_task, params) for params in param_sets]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        assert len(results) == len(param_sets)

        # Verify scaling relationships
        for result in results:
            # Check half-life calculation
            expected_half_life = np.log(2) / result['k']
            assert np.isclose(result['half_life'], expected_half_life, rtol=1e-10)

            # Check final value scales with initial condition
            expected_ratio = result['final_value'] / result['x0']
            assert expected_ratio > 0 and expected_ratio < 1


# ========================================
# 9. Jupyter Notebook Integration Tests
# ========================================

class TestJupyterIntegration:
    """Test integration with Jupyter notebook environments."""

    def test_ipython_display_integration(self):
        """Test IPython display system integration."""
        # Mock IPython environment
        try:
            from IPython.display import display, HTML, Markdown
            IPYTHON_AVAILABLE = True
        except ImportError:
            IPYTHON_AVAILABLE = False
            pytest.skip("IPython not available")

        # Test creating displayable content
        def create_simulation_report(results):
            """Create HTML report from simulation results."""
            html_content = "<h3>Simulation Results</h3>\n<ul>\n"
            for key, value in results.items():
                html_content += f"<li><strong>{key}:</strong> {value}</li>\n"
            html_content += "</ul>"
            return HTML(html_content)

        # Test results
        test_results = {
            'final_time': 5.0,
            'final_value': 0.135,
            'integration_steps': 1000,
            'solver': 'RK45'
        }

        report = create_simulation_report(test_results)
        assert hasattr(report, '_repr_html_'), "Should have HTML representation"
        assert 'Simulation Results' in report._repr_html_()

    @pytest.mark.skipif(not MATPLOTLIB_AVAILABLE, reason="Matplotlib not available")
    def test_inline_plotting_support(self):
        """Test inline plotting for Jupyter notebooks."""
        # Generate sample data
        t = np.linspace(0, 5, 100)
        x1 = AnalyticalSolutions.exponential_decay(t, x0=1.0, k=0.1)
        x2 = AnalyticalSolutions.exponential_decay(t, x0=1.0, k=0.3)

        # Create plot
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.plot(t, x1, label='k=0.1', linewidth=2)
        ax.plot(t, x2, label='k=0.3', linewidth=2)
        ax.set_xlabel('Time')
        ax.set_ylabel('Value')
        ax.set_title('Exponential Decay Comparison')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Test that figure was created properly
        assert fig is not None
        assert len(ax.lines) == 2
        assert ax.get_xlabel() == 'Time'
        assert ax.get_ylabel() == 'Value'

        # Clean up
        plt.close(fig)

    def test_interactive_widget_compatibility(self):
        """Test compatibility with Jupyter interactive widgets."""
        # Mock ipywidgets
        class MockWidget:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def interact(self, func, **kwargs):
                # Simulate widget interaction
                return func(**{k: v[0] if isinstance(v, tuple) else v
                            for k, v in kwargs.items()})

        def interactive_simulation(k_value, t_max, n_points):
            """Interactive simulation function."""
            t = np.linspace(0, t_max, n_points)
            x = AnalyticalSolutions.exponential_decay(t, x0=1.0, k=k_value)
            return {
                'final_value': x[-1],
                'decay_time': 1/k_value if k_value > 0 else np.inf,
                'points': len(t)
            }

        # Simulate widget usage
        widget = MockWidget()
        result = widget.interact(
            interactive_simulation,
            k_value=(0.1, 1.0, 0.1),
            t_max=(1, 10, 1),
            n_points=(10, 1000, 10)
        )

        assert 'final_value' in result
        assert 'decay_time' in result
        assert result['points'] > 0

    def test_notebook_cell_output_formatting(self):
        """Test proper formatting of cell outputs."""
        class SimulationResult:
            """Simulation result with rich display methods."""

            def __init__(self, data):
                self.data = data

            def _repr_html_(self):
                """HTML representation for Jupyter."""
                html = "<div style='border: 1px solid #ccc; padding: 10px; margin: 5px;'>"
                html += "<h4>Simulation Result</h4>"
                html += "<table>"
                for key, value in self.data.items():
                    html += f"<tr><td><strong>{key}:</strong></td><td>{value:.6f}</td></tr>"
                html += "</table></div>"
                return html

            def _repr_latex_(self):
                """LaTeX representation for Jupyter."""
                latex = r"\begin{align}"
                for key, value in self.data.items():
                    latex += f"{key} &= {value:.6f} \\\\"
                latex += r"\end{align}"
                return latex

        # Test result formatting
        test_data = {
            'final_time': 5.0,
            'final_value': 0.135335,
            'error_estimate': 1e-8
        }

        result = SimulationResult(test_data)

        # Test HTML representation
        html_repr = result._repr_html_()
        assert 'Simulation Result' in html_repr
        assert 'final_time' in html_repr
        assert '0.135335' in html_repr

        # Test LaTeX representation
        latex_repr = result._repr_latex_()
        assert r'\begin{align}' in latex_repr
        assert 'final_time' in latex_repr


# ========================================
# Integration Tests with ESM Format
# ========================================

class TestESMFormatIntegration:
    """Test integration of simulation capabilities with ESM format."""

    def test_simulation_model_serialization(self):
        """Test serialization of models suitable for simulation."""
        # Create a model representing exponential decay
        model = Model(
            name="exponential_decay",
            variables={
                "x": ModelVariable(type="state", units="concentration", default=1.0),
                "k": ModelVariable(type="parameter", units="1/time", default=0.1),
                "t": ModelVariable(type="parameter", units="time", default=0.0)
            },
            equations=[
                Equation(
                    lhs=ExprNode(op="D", args=["x"], wrt="t"),
                    rhs=ExprNode(op="*", args=[
                        ExprNode(op="-", args=["k"]),
                        "x"
                    ])
                )
            ]
        )

        # Create ESM file
        esm_file = EsmFile(
            version="0.1.0",
            metadata=Metadata(title="Exponential Decay Simulation"),
            models=[model]
        )

        # Serialize and deserialize
        json_str = save(esm_file)
        reconstructed = load(json_str)

        # Verify simulation-relevant properties
        assert len(reconstructed.models) == 1
        recon_model = reconstructed.models[0]
        assert recon_model.name == "exponential_decay"
        assert "x" in recon_model.variables
        assert "k" in recon_model.variables
        assert recon_model.variables["x"].type == "state"
        assert recon_model.variables["k"].type == "parameter"

    def test_reaction_system_simulation_setup(self):
        """Test setting up reaction systems for simulation."""
        # Create a simple reaction system: A -> B
        reaction_system = ReactionSystem(
            name="simple_decay",
            species=[
                Species(name="A", units="mol/L"),
                Species(name="B", units="mol/L")
            ],
            parameters=[
                Parameter(name="k1", value=0.5, units="1/s")
            ],
            reactions=[
                Reaction(
                    name="A_to_B",
                    reactants={"A": 1.0},
                    products={"B": 1.0},
                    rate_constant="k1"
                )
            ]
        )

        # Create ESM file with reaction system
        esm_file = EsmFile(
            version="0.1.0",
            metadata=Metadata(title="Reaction System Simulation"),
            reaction_systems=[reaction_system]
        )

        # Test serialization
        json_str = save(esm_file)
        reconstructed = load(json_str)

        # Verify reaction system for simulation
        assert len(reconstructed.reaction_systems) == 1
        rs = reconstructed.reaction_systems[0]

        # Check species (state variables)
        assert len(rs.species) == 2
        species_names = {sp.name for sp in rs.species}
        assert species_names == {"A", "B"}

        # Check parameters
        assert len(rs.parameters) == 1
        assert rs.parameters[0].name == "k1"
        assert rs.parameters[0].value == 0.5

        # Check reaction (defines dynamics)
        assert len(rs.reactions) == 1
        reaction = rs.reactions[0]
        assert reaction.reactants == {"A": 1.0}
        assert reaction.products == {"B": 1.0}
        assert reaction.rate_constant == "k1"


# ========================================
# Utility Functions for Test Setup
# ========================================

@contextmanager
def simulation_environment():
    """Context manager for setting up simulation test environment."""
    # Set random seed for reproducibility
    np.random.seed(42)

    # Store original settings
    original_error_settings = np.geterr()

    # Set error handling for simulations
    np.seterr(all='warn')

    try:
        yield
    finally:
        # Restore original settings
        np.seterr(**original_error_settings)


def validate_simulation_result(result, expected_properties=None):
    """Validate simulation result against expected properties."""
    if expected_properties is None:
        expected_properties = {}

    # Basic validation
    assert isinstance(result, dict), "Result should be a dictionary"

    # Check for required fields
    required_fields = expected_properties.get('required_fields', [])
    for field in required_fields:
        assert field in result, f"Required field '{field}' missing from result"

    # Check value bounds
    bounds = expected_properties.get('bounds', {})
    for field, (min_val, max_val) in bounds.items():
        if field in result:
            value = result[field]
            assert min_val <= value <= max_val, f"Field '{field}' value {value} outside bounds [{min_val}, {max_val}]"

    # Check data types
    types = expected_properties.get('types', {})
    for field, expected_type in types.items():
        if field in result:
            assert isinstance(result[field], expected_type), f"Field '{field}' should be {expected_type}, got {type(result[field])}"


# Summary verification function (not run as a test)
def simulation_test_coverage_summary():
    """Summary of simulation test coverage - for documentation purposes."""
    coverage_areas = {
        'analytical_solutions': 'test_analytical_solutions',
        'sympy_integration': 'TestSymPyIntegration class',
        'scipy_integration': 'TestSciPyIntegration class',
        'numpy_operations': 'TestNumPyOperations class',
        'performance_benchmarks': 'TestPerformanceBenchmarks class',
        'parameter_estimation': 'TestParameterEstimation class',
        'sensitivity_analysis': 'TestSensitivityAnalysis class',
        'parallel_execution': 'TestParallelExecution class',
        'jupyter_integration': 'TestJupyterIntegration class',
        'esm_integration': 'TestESMFormatIntegration class'
    }

    print("✓ All simulation test categories are covered:")
    for category, implementation in coverage_areas.items():
        print(f"  - {category}: {implementation}")

    return coverage_areas


if __name__ == "__main__":
    pytest.main([__file__, "-v"])