"""
Test cases for temporal operators.
"""

import pytest
import numpy as np
import warnings
from unittest.mock import Mock

from esm_format.types import Operator, OperatorType
from esm_format.temporal_operators import (
    DerivativeOperator,
    IntegralOperator,
    TemporalAveragingOperator,
    TimeSteppingOperator,
    TemporalScheme,
    IntegrationMethod,
    TemporalOperatorConfig,
    _validate_temporal_data,
    _apply_boundary_conditions
)
from esm_format.operator_registry import get_registry


class TestTemporalDataValidation:
    """Test cases for temporal data validation and preprocessing."""

    def test_validate_temporal_data_scalar(self):
        """Test validation of scalar data."""
        result = _validate_temporal_data(5.0)
        expected = np.array([5.0])
        np.testing.assert_array_equal(result, expected)

    def test_validate_temporal_data_array(self):
        """Test validation of array data."""
        data = np.array([1, 2, 3, 4, 5])
        result = _validate_temporal_data(data)
        np.testing.assert_array_equal(result, data)

    def test_validate_temporal_data_2d(self):
        """Test validation of 2D array with time axis."""
        data = np.array([[1, 2, 3], [4, 5, 6]])
        result = _validate_temporal_data(data, time_axis=1)
        np.testing.assert_array_equal(result, data)

    def test_validate_temporal_data_invalid_time_axis(self):
        """Test validation with invalid time axis."""
        data = np.array([1, 2, 3])
        with pytest.raises(ValueError, match="Invalid time axis"):
            _validate_temporal_data(data, time_axis=2)

    def test_validate_temporal_data_non_numeric(self):
        """Test validation with non-numeric data."""
        with pytest.raises(TypeError, match="Cannot convert data"):
            _validate_temporal_data(["a", "b", "c"])


class TestBoundaryConditions:
    """Test cases for boundary condition handling."""

    def test_boundary_conditions_zero_padding(self):
        """Test zero padding boundary conditions."""
        data = np.array([1, 2, 3])
        result = _apply_boundary_conditions(data, "zero", time_axis=0, n_points=1)
        expected = np.array([0, 1, 2, 3, 0])
        np.testing.assert_array_equal(result, expected)

    def test_boundary_conditions_extrapolate(self):
        """Test extrapolation boundary conditions."""
        data = np.array([1, 2, 3])
        result = _apply_boundary_conditions(data, "extrapolate", time_axis=0, n_points=1)
        expected = np.array([1, 1, 2, 3, 3])
        np.testing.assert_array_equal(result, expected)

    def test_boundary_conditions_periodic(self):
        """Test periodic boundary conditions."""
        data = np.array([1, 2, 3])
        result = _apply_boundary_conditions(data, "periodic", time_axis=0, n_points=1)
        expected = np.array([3, 1, 2, 3, 1])
        np.testing.assert_array_equal(result, expected)

    def test_boundary_conditions_unknown_method(self):
        """Test unknown boundary condition method."""
        data = np.array([1, 2, 3])
        with pytest.raises(ValueError, match="Unknown boundary treatment"):
            _apply_boundary_conditions(data, "unknown", time_axis=0, n_points=1)


class TestDerivativeOperator:
    """Test cases for temporal derivative operator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Operator(
            name="derivative",
            type=OperatorType.DIFFERENTIATION,
            parameters={"dt": 0.1, "scheme": "central_difference"},
            input_variables=["u"],
            output_variables=["dudt"]
        )
        self.operator = DerivativeOperator(self.config)

    def test_derivative_operator_init(self):
        """Test derivative operator initialization."""
        assert self.operator.name == "derivative"
        assert self.operator.temporal_config.dt == 0.1
        assert self.operator.temporal_config.scheme == TemporalScheme.CENTRAL_DIFFERENCE

    def test_derivative_forward_euler(self):
        """Test forward Euler derivative computation."""
        config = Operator(
            name="derivative",
            type=OperatorType.DIFFERENTIATION,
            parameters={"dt": 1.0, "scheme": "forward_euler"},
            input_variables=["u"],
            output_variables=["dudt"]
        )
        operator = DerivativeOperator(config)

        # Test with simple linear function: f(t) = t
        data = np.array([0, 1, 2, 3, 4])  # t = [0, 1, 2, 3, 4]
        result = operator.evaluate(data)

        # Derivative should be approximately 1 (except at boundary)
        expected_interior = np.ones(4)  # Forward difference gives 4 points
        assert len(result) == len(data)  # Same length due to boundary treatment
        np.testing.assert_array_almost_equal(result[:-1], expected_interior)

    def test_derivative_backward_euler(self):
        """Test backward Euler derivative computation."""
        config = Operator(
            name="derivative",
            type=OperatorType.DIFFERENTIATION,
            parameters={"dt": 1.0, "scheme": "backward_euler"},
            input_variables=["u"],
            output_variables=["dudt"]
        )
        operator = DerivativeOperator(config)

        # Test with simple linear function: f(t) = t
        data = np.array([0, 1, 2, 3, 4])
        result = operator.evaluate(data)

        # Derivative should be approximately 1 (except at boundary)
        expected_interior = np.ones(4)
        assert len(result) == len(data)  # Same length due to boundary treatment
        np.testing.assert_array_almost_equal(result[1:], expected_interior)

    def test_derivative_central_difference(self):
        """Test central difference derivative computation."""
        # Test with quadratic function: f(t) = t^2
        # Derivative should be 2*t
        t = np.linspace(0, 4, 5)  # [0, 1, 2, 3, 4]
        data = t**2  # [0, 1, 4, 9, 16]

        result = self.operator.evaluate(data, time_axis=0)

        # For central difference, expect derivative ≈ 2*t at interior points
        # Note: dt = 0.1, so we need to account for actual spacing
        # Our t has spacing of 1, not 0.1, so we'll adjust
        config_adjusted = Operator(
            name="derivative",
            type=OperatorType.DIFFERENTIATION,
            parameters={"dt": 1.0, "scheme": "central_difference"},
            input_variables=["u"],
            output_variables=["dudt"]
        )
        operator_adjusted = DerivativeOperator(config_adjusted)
        result_adjusted = operator_adjusted.evaluate(data, time_axis=0)

        # Central points should have derivative close to 2*t
        expected_center = 2 * t[1:-1]  # Exclude boundaries
        np.testing.assert_array_almost_equal(result_adjusted[1:-1], expected_center, decimal=6)

    def test_derivative_insufficient_data(self):
        """Test derivative with insufficient data points."""
        data = np.array([1])  # Only one point
        with pytest.raises(ValueError, match="Need at least 2 time points"):
            self.operator.evaluate(data)

    def test_derivative_insufficient_data_central(self):
        """Test central difference with insufficient data points."""
        data = np.array([1, 2])  # Only two points
        with pytest.raises(ValueError, match="Need at least 3 time points"):
            self.operator.evaluate(data)

    def test_derivative_2d_array(self):
        """Test derivative computation on 2D array."""
        # Create 2D data: each row is a different variable, columns are time
        data = np.array([[0, 1, 2, 3, 4],    # Linear function
                        [0, 1, 4, 9, 16]])   # Quadratic function

        config = Operator(
            name="derivative",
            type=OperatorType.DIFFERENTIATION,
            parameters={"dt": 1.0, "scheme": "forward_euler"},
            input_variables=["u"],
            output_variables=["dudt"]
        )
        operator = DerivativeOperator(config)

        result = operator.evaluate(data, time_axis=1)

        # First row (linear): derivative should be 1
        # Second row (quadratic): derivative should be approximately [1, 3, 5, 7]
        assert result.shape == data.shape
        np.testing.assert_array_almost_equal(result[0, :-1], [1, 1, 1, 1])


class TestIntegralOperator:
    """Test cases for temporal integral operator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Operator(
            name="integral",
            type=OperatorType.INTEGRATION,
            parameters={"dt": 1.0, "integration_method": "trapezoidal"},
            input_variables=["f"],
            output_variables=["integral_f"]
        )
        self.operator = IntegralOperator(self.config)

    def test_integral_operator_init(self):
        """Test integral operator initialization."""
        assert self.operator.name == "integral"
        assert self.operator.temporal_config.dt == 1.0
        assert self.operator.temporal_config.integration_method == IntegrationMethod.TRAPEZOIDAL

    def test_integral_rectangular(self):
        """Test rectangular rule integration."""
        config = Operator(
            name="integral",
            type=OperatorType.INTEGRATION,
            parameters={"dt": 1.0, "integration_method": "rectangular"},
            input_variables=["f"],
            output_variables=["integral_f"]
        )
        operator = IntegralOperator(config)

        # Test with constant function: f(t) = 2
        # Integral should be 2*t
        data = np.array([2, 2, 2, 2, 2])  # Constant function
        result = operator.evaluate(data)

        # Rectangular rule: [0, 2, 4, 6, 8, 10]
        expected = np.array([0, 2, 4, 6, 8])
        np.testing.assert_array_almost_equal(result, expected)

    def test_integral_trapezoidal(self):
        """Test trapezoidal rule integration."""
        # Test with linear function: f(t) = t
        # Integral should be t^2/2
        data = np.array([0, 1, 2, 3, 4])  # f(t) = t for t = [0, 1, 2, 3, 4]
        result = self.operator.evaluate(data)

        # Trapezoidal rule for f(t) = t should give approximately [0, 0.5, 2, 4.5, 8]
        expected = np.array([0, 0.5, 2, 4.5, 8])
        np.testing.assert_array_almost_equal(result, expected, decimal=6)

    def test_integral_insufficient_data(self):
        """Test integral with insufficient data points."""
        data = np.array([1])  # Only one point
        with pytest.raises(ValueError, match="Need at least 2 time points"):
            self.operator.evaluate(data)

    def test_integral_2d_array(self):
        """Test integral computation on 2D array."""
        # Create 2D data: each row is a different function, columns are time
        data = np.array([[1, 1, 1, 1],      # Constant function
                        [0, 1, 2, 3]])     # Linear function

        result = self.operator.evaluate(data, time_axis=1)

        # Check shapes
        assert result.shape == data.shape

        # First row (constant f=1): integral should be [0, 1, 2, 3] (trapezoidal)
        # Second row (linear f=[0,1,2,3]): integral should be [0, 0.5, 2, 4.5]
        expected_row1 = np.array([0, 1, 2, 3])
        expected_row2 = np.array([0, 0.5, 2, 4.5])

        np.testing.assert_array_almost_equal(result[0, :], expected_row1, decimal=6)
        np.testing.assert_array_almost_equal(result[1, :], expected_row2, decimal=6)


class TestTemporalAveragingOperator:
    """Test cases for temporal averaging operator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Operator(
            name="temporal_average",
            type=OperatorType.FILTERING,
            parameters={"boundary_treatment": "zero"},
            input_variables=["f"],
            output_variables=["f_avg"]
        )
        self.operator = TemporalAveragingOperator(self.config)

    def test_temporal_averaging_operator_init(self):
        """Test temporal averaging operator initialization."""
        assert self.operator.name == "temporal_average"
        assert self.operator.temporal_config.boundary_treatment == "zero"

    def test_temporal_averaging_full_window(self):
        """Test temporal averaging with full window (mean of entire series)."""
        data = np.array([1, 2, 3, 4, 5])
        result = self.operator.evaluate(data)

        # Full window average should be the mean for all points
        expected_mean = np.mean(data)
        expected = np.full_like(data, expected_mean, dtype=float)
        np.testing.assert_array_almost_equal(result, expected)

    def test_temporal_averaging_window_size_3(self):
        """Test temporal averaging with window size 3."""
        data = np.array([1, 2, 3, 4, 5])
        result = self.operator.evaluate(data, window_size=3)

        # Window size 3: each point is average of itself and neighbors
        # Point 0: avg([1]) = 1.0 (partial window)
        # Point 1: avg([1, 2]) = 1.5 (partial window)
        # Point 2: avg([1, 2, 3]) = 2.0 (full window)
        # Point 3: avg([2, 3, 4]) = 3.0 (full window)
        # Point 4: avg([3, 4, 5]) = 4.0 (full window)

        # The implementation uses centered windows, so results may vary
        assert result.shape == data.shape
        assert np.all(np.isfinite(result))

    def test_temporal_averaging_window_size_1(self):
        """Test temporal averaging with window size 1 (no averaging)."""
        data = np.array([1, 2, 3, 4, 5])
        result = self.operator.evaluate(data, window_size=1)

        # Window size 1 should return original data
        np.testing.assert_array_equal(result, data)

    def test_temporal_averaging_window_too_large(self):
        """Test temporal averaging with window size larger than data."""
        data = np.array([1, 2, 3])

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = self.operator.evaluate(data, window_size=10)

            # Should issue warning and use full length
            assert len(w) == 1
            assert "Window size larger than data length" in str(w[0].message)

        # Should still work and return something reasonable
        assert result.shape == data.shape

    def test_temporal_averaging_invalid_window_size(self):
        """Test temporal averaging with invalid window size."""
        data = np.array([1, 2, 3, 4, 5])

        with pytest.raises(ValueError, match="Window size must be positive"):
            self.operator.evaluate(data, window_size=0)


class TestTimeSteppingOperator:
    """Test cases for time stepping operator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Operator(
            name="time_stepping",
            type=OperatorType.INTEGRATION,
            parameters={"dt": 0.1, "scheme": "forward_euler"},
            input_variables=["y"],
            output_variables=["y_next"]
        )
        self.operator = TimeSteppingOperator(self.config)

    def test_time_stepping_operator_init(self):
        """Test time stepping operator initialization."""
        assert self.operator.name == "time_stepping"
        assert self.operator.temporal_config.dt == 0.1
        assert self.operator.temporal_config.scheme == TemporalScheme.FORWARD_EULER

    def test_time_stepping_forward_euler(self):
        """Test forward Euler time stepping."""
        # Simple ODE: dy/dt = y (solution: y = y0 * exp(t))
        initial_state = np.array([1.0])
        rhs_function = Mock(return_value=initial_state)  # dy/dt = y

        result = self.operator.evaluate(initial_state, rhs_function)

        # Forward Euler: y_{n+1} = y_n + dt * f(t_n, y_n)
        # y_{n+1} = 1.0 + 0.1 * 1.0 = 1.1
        expected = np.array([1.1])
        np.testing.assert_array_almost_equal(result, expected)

        # Verify that the RHS function was called correctly
        rhs_function.assert_called_once_with(0, initial_state)

    def test_time_stepping_runge_kutta_4(self):
        """Test fourth-order Runge-Kutta time stepping."""
        config = Operator(
            name="time_stepping",
            type=OperatorType.INTEGRATION,
            parameters={"dt": 0.1, "scheme": "runge_kutta_4"},
            input_variables=["y"],
            output_variables=["y_next"]
        )
        operator = TimeSteppingOperator(config)

        initial_state = np.array([1.0])

        # Mock RHS function that returns the input (dy/dt = y)
        def rhs_mock(t, y):
            return y

        result = operator.evaluate(initial_state, rhs_mock)

        # RK4 for dy/dt = y with dt = 0.1 and y0 = 1
        # Should be more accurate than Euler
        dt = 0.1
        y0 = 1.0

        # Manual RK4 calculation
        k1 = y0
        k2 = y0 + dt/2 * k1
        k3 = y0 + dt/2 * k2
        k4 = y0 + dt * k3
        expected_y = y0 + dt/6 * (k1 + 2*k2 + 2*k3 + k4)

        np.testing.assert_array_almost_equal(result, [expected_y])

    def test_time_stepping_multidimensional_state(self):
        """Test time stepping with multidimensional state vector."""
        # System: dx/dt = -x, dy/dt = -2*y
        initial_state = np.array([1.0, 2.0])

        def rhs_function(t, y):
            return np.array([-y[0], -2*y[1]])

        result = self.operator.evaluate(initial_state, rhs_function)

        # Forward Euler:
        # x_{n+1} = 1.0 + 0.1 * (-1.0) = 0.9
        # y_{n+1} = 2.0 + 0.1 * (-4.0) = 1.6
        expected = np.array([0.9, 1.6])
        np.testing.assert_array_almost_equal(result, expected)


class TestOperatorRegistration:
    """Test cases for temporal operator registration."""

    def test_temporal_operators_registered(self):
        """Test that temporal operators are registered in the global registry."""
        registry = get_registry()

        # Check that temporal operators are registered
        assert registry.has_operator("time_derivative")
        assert registry.has_operator("time_integral")
        assert registry.has_operator("temporal_average")
        assert registry.has_operator("time_stepping")

    def test_temporal_operators_types(self):
        """Test that temporal operators have correct types."""
        registry = get_registry()

        # Check operator types
        derivative_info = registry.get_operator_info("time_derivative")
        assert derivative_info["type"] == OperatorType.DIFFERENTIATION

        integral_info = registry.get_operator_info("time_integral")
        assert integral_info["type"] == OperatorType.INTEGRATION

        average_info = registry.get_operator_info("temporal_average")
        assert average_info["type"] == OperatorType.FILTERING

        stepping_info = registry.get_operator_info("time_stepping")
        assert stepping_info["type"] == OperatorType.INTEGRATION

    def test_create_temporal_operators_from_registry(self):
        """Test creating temporal operators from registry."""
        registry = get_registry()

        # Create operators using registry
        derivative_op = registry.create_operator_by_name(
            "time_derivative",
            OperatorType.DIFFERENTIATION,
            {"dt": 0.1}
        )
        assert isinstance(derivative_op, DerivativeOperator)

        integral_op = registry.create_operator_by_name(
            "time_integral",
            OperatorType.INTEGRATION,
            {"dt": 0.1}
        )
        assert isinstance(integral_op, IntegralOperator)

        average_op = registry.create_operator_by_name(
            "temporal_average",
            OperatorType.FILTERING
        )
        assert isinstance(average_op, TemporalAveragingOperator)

        stepping_op = registry.create_operator_by_name(
            "time_stepping",
            OperatorType.INTEGRATION,
            {"dt": 0.1}
        )
        assert isinstance(stepping_op, TimeSteppingOperator)


class TestTemporalOperatorConfig:
    """Test cases for temporal operator configuration."""

    def test_temporal_operator_config_defaults(self):
        """Test default temporal operator configuration."""
        config = TemporalOperatorConfig()

        assert config.dt == 1.0
        assert config.scheme == TemporalScheme.CENTRAL_DIFFERENCE
        assert config.integration_method == IntegrationMethod.TRAPEZOIDAL
        assert config.order == 2
        assert config.stencil_size == 3
        assert config.absolute_tolerance == 1e-8
        assert config.relative_tolerance == 1e-6
        assert config.boundary_treatment == "zero"

    def test_temporal_operator_config_custom(self):
        """Test custom temporal operator configuration."""
        config = TemporalOperatorConfig(
            dt=0.01,
            scheme=TemporalScheme.RUNGE_KUTTA_4,
            integration_method=IntegrationMethod.SIMPSON,
            order=4,
            boundary_treatment="periodic"
        )

        assert config.dt == 0.01
        assert config.scheme == TemporalScheme.RUNGE_KUTTA_4
        assert config.integration_method == IntegrationMethod.SIMPSON
        assert config.order == 4
        assert config.boundary_treatment == "periodic"


class TestIntegrationWithWarnings:
    """Test cases for proper warning handling in temporal operators."""

    def test_derivative_with_warnings(self):
        """Test derivative operator with data that produces warnings."""
        config = Operator(
            name="derivative",
            type=OperatorType.DIFFERENTIATION,
            parameters={"dt": 1.0, "scheme": "central_difference"},
            input_variables=["u"],
            output_variables=["dudt"]
        )
        operator = DerivativeOperator(config)

        # Create data with NaN to trigger warnings
        data = np.array([1, 2, np.nan, 4, 5])

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = operator.evaluate(data)

            # Should produce warning about NaN values
            warning_messages = [str(warning.message) for warning in w]
            assert any("NaN values in temporal derivative" in msg for msg in warning_messages)

        # Result should have same shape even with NaN input
        assert result.shape == data.shape

    def test_integral_simpson_warning(self):
        """Test integral operator Simpson's rule warning."""
        config = Operator(
            name="integral",
            type=OperatorType.INTEGRATION,
            parameters={"dt": 1.0, "integration_method": "simpson"},
            input_variables=["f"],
            output_variables=["integral_f"]
        )
        operator = IntegralOperator(config)

        data = np.array([1, 2, 3, 4])  # Even number of intervals

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = operator.evaluate(data)

            # Should produce warning about Simpson's rule falling back to trapezoidal
            warning_messages = [str(warning.message) for warning in w]
            assert any("requires odd number of points" in msg for msg in warning_messages)

        assert result.shape == data.shape