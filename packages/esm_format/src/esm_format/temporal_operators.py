"""
Temporal operator implementations for ESM Format.

This module provides implementations for time-based mathematical operations
including derivatives, integrals, and temporal averaging for dynamic simulations.
Supports various time-stepping schemes and temporal discretization methods.
"""

import warnings
import numpy as np
from typing import Any, Union, List, Dict, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from .esm_types import Operator, OperatorType


class TemporalScheme(Enum):
    """Time-stepping and discretization schemes."""
    FORWARD_EULER = "forward_euler"
    BACKWARD_EULER = "backward_euler"
    CENTRAL_DIFFERENCE = "central_difference"
    RUNGE_KUTTA_4 = "runge_kutta_4"
    TRAPEZOIDAL = "trapezoidal"
    ADAMS_BASHFORTH = "adams_bashforth"
    ADAMS_MOULTON = "adams_moulton"


class IntegrationMethod(Enum):
    """Methods for temporal integration."""
    RECTANGULAR = "rectangular"  # Simple rectangular rule
    TRAPEZOIDAL = "trapezoidal"  # Trapezoidal rule
    SIMPSON = "simpson"         # Simpson's rule
    ADAPTIVE = "adaptive"       # Adaptive integration
    GAUSSIAN = "gaussian"       # Gaussian quadrature


@dataclass
class TemporalOperatorConfig:
    """Configuration for temporal operators."""
    dt: float = 1.0  # Time step size
    scheme: TemporalScheme = TemporalScheme.CENTRAL_DIFFERENCE
    integration_method: IntegrationMethod = IntegrationMethod.TRAPEZOIDAL
    order: int = 2  # Order of accuracy
    stencil_size: int = 3  # Number of points in finite difference stencil
    absolute_tolerance: float = 1e-8
    relative_tolerance: float = 1e-6
    boundary_treatment: str = "zero"  # "zero", "extrapolate", "periodic"


def _validate_temporal_data(data: Any, time_axis: int = -1) -> np.ndarray:
    """
    Validate and prepare temporal data for operations.

    Args:
        data: Input data (scalar, array, or time series)
        time_axis: Axis along which time varies

    Returns:
        Validated numpy array

    Raises:
        TypeError: If data cannot be converted to numerical array
        ValueError: If time axis is invalid
    """
    try:
        arr = np.asarray(data, dtype=float)
    except (ValueError, TypeError):
        raise TypeError(f"Cannot convert data to numeric array: {type(data)}")

    if arr.ndim == 0:
        # Scalar - convert to 1D array
        return arr.reshape(1)

    if time_axis < -arr.ndim or time_axis >= arr.ndim:
        raise ValueError(f"Invalid time axis {time_axis} for array with {arr.ndim} dimensions")

    return arr


def _apply_boundary_conditions(
    data: np.ndarray,
    boundary_treatment: str,
    time_axis: int = -1,
    n_points: int = 1
) -> np.ndarray:
    """
    Apply boundary conditions for temporal operators.

    Args:
        data: Input data array
        boundary_treatment: Method for handling boundaries
        time_axis: Time axis
        n_points: Number of boundary points to handle

    Returns:
        Data with appropriate boundary treatment
    """
    if boundary_treatment == "zero":
        # Pad with zeros
        pad_width = [(0, 0)] * data.ndim
        pad_width[time_axis] = (n_points, n_points)
        return np.pad(data, pad_width, mode='constant', constant_values=0)

    elif boundary_treatment == "extrapolate":
        # Linear extrapolation
        pad_width = [(0, 0)] * data.ndim
        pad_width[time_axis] = (n_points, n_points)
        return np.pad(data, pad_width, mode='edge')

    elif boundary_treatment == "periodic":
        # Periodic boundary conditions
        pad_width = [(0, 0)] * data.ndim
        pad_width[time_axis] = (n_points, n_points)
        return np.pad(data, pad_width, mode='wrap')

    else:
        raise ValueError(f"Unknown boundary treatment: {boundary_treatment}")


class BaseTemporalOperator:
    """
    Base class for temporal operators.

    Provides common functionality for time-based operations including
    finite difference schemes, integration methods, and boundary treatment.
    """

    def __init__(self, config: Operator):
        """
        Initialize the temporal operator.

        Args:
            config: Operator configuration
        """
        self.config = config
        self.name = config.name
        self.parameters = config.parameters
        self.input_variables = config.input_variables
        self.output_variables = config.output_variables

        # Parse temporal-specific configuration
        self.temporal_config = TemporalOperatorConfig()
        if "dt" in self.parameters:
            self.temporal_config.dt = float(self.parameters["dt"])
        if "scheme" in self.parameters:
            self.temporal_config.scheme = TemporalScheme(self.parameters["scheme"])
        if "integration_method" in self.parameters:
            self.temporal_config.integration_method = IntegrationMethod(self.parameters["integration_method"])
        if "order" in self.parameters:
            self.temporal_config.order = int(self.parameters["order"])
        if "stencil_size" in self.parameters:
            self.temporal_config.stencil_size = int(self.parameters["stencil_size"])
        if "absolute_tolerance" in self.parameters:
            self.temporal_config.absolute_tolerance = float(self.parameters["absolute_tolerance"])
        if "relative_tolerance" in self.parameters:
            self.temporal_config.relative_tolerance = float(self.parameters["relative_tolerance"])
        if "boundary_treatment" in self.parameters:
            self.temporal_config.boundary_treatment = self.parameters["boundary_treatment"]

    def _validate_inputs(self, data: Any, time_axis: int = -1) -> np.ndarray:
        """
        Validate input data for temporal operations.

        Args:
            data: Input data
            time_axis: Axis along which time varies

        Returns:
            Validated numpy array
        """
        try:
            return _validate_temporal_data(data, time_axis)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid input for {self.name}: {e}")

    def evaluate(self, *args, **kwargs) -> Any:
        """
        Evaluate the temporal operator.

        This method should be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement evaluate method")


class DerivativeOperator(BaseTemporalOperator):
    """
    Temporal derivative operator using finite difference schemes.

    Supports various finite difference schemes including forward, backward,
    and central differences with configurable order of accuracy.
    """

    def evaluate(self, data: Any, time_axis: int = -1) -> Any:
        """
        Compute temporal derivative using finite differences.

        Args:
            data: Input time series data
            time_axis: Axis along which to compute derivative (default: last axis)

        Returns:
            Temporal derivative of input data
        """
        validated_data = self._validate_inputs(data, time_axis)

        if validated_data.shape[time_axis] < 2:
            raise ValueError("Need at least 2 time points to compute derivative")

        dt = self.temporal_config.dt
        scheme = self.temporal_config.scheme
        boundary_treatment = self.temporal_config.boundary_treatment

        try:
            if scheme == TemporalScheme.FORWARD_EULER:
                # Forward difference: (f[i+1] - f[i]) / dt
                derivative = np.diff(validated_data, axis=time_axis) / dt

                # Handle boundary - add zero at the end
                if boundary_treatment == "zero":
                    pad_shape = list(validated_data.shape)
                    pad_shape[time_axis] = 1
                    zero_pad = np.zeros(pad_shape)
                    derivative = np.concatenate([derivative, zero_pad], axis=time_axis)
                elif boundary_treatment == "extrapolate":
                    # Repeat last difference
                    last_diff = np.take(derivative, [-1], axis=time_axis)
                    derivative = np.concatenate([derivative, last_diff], axis=time_axis)

            elif scheme == TemporalScheme.BACKWARD_EULER:
                # Backward difference: (f[i] - f[i-1]) / dt
                derivative = np.diff(validated_data, axis=time_axis) / dt

                # Handle boundary - add zero at the beginning
                if boundary_treatment == "zero":
                    pad_shape = list(validated_data.shape)
                    pad_shape[time_axis] = 1
                    zero_pad = np.zeros(pad_shape)
                    derivative = np.concatenate([zero_pad, derivative], axis=time_axis)
                elif boundary_treatment == "extrapolate":
                    # Repeat first difference
                    first_diff = np.take(derivative, [0], axis=time_axis)
                    derivative = np.concatenate([first_diff, derivative], axis=time_axis)

            elif scheme == TemporalScheme.CENTRAL_DIFFERENCE:
                # Central difference: (f[i+1] - f[i-1]) / (2*dt)
                if validated_data.shape[time_axis] < 3:
                    raise ValueError("Need at least 3 time points for central difference")

                # Apply boundary conditions to get padded data
                padded_data = _apply_boundary_conditions(
                    validated_data, boundary_treatment, time_axis, 1
                )

                # Compute central differences
                forward_slice = [slice(None)] * padded_data.ndim
                forward_slice[time_axis] = slice(2, None)

                backward_slice = [slice(None)] * padded_data.ndim
                backward_slice[time_axis] = slice(None, -2)

                derivative = (padded_data[tuple(forward_slice)] -
                            padded_data[tuple(backward_slice)]) / (2 * dt)

            else:
                raise NotImplementedError(f"Scheme {scheme} not yet implemented")

            # Check for numerical issues
            if np.any(np.isnan(derivative)):
                warnings.warn("NaN values in temporal derivative", RuntimeWarning)
            if np.any(np.isinf(derivative)):
                warnings.warn("Infinite values in temporal derivative", RuntimeWarning)

            return derivative

        except Exception as e:
            raise ValueError(f"Derivative computation failed: {e}")

    def __str__(self):
        return f"Derivative(dt={self.temporal_config.dt}, scheme={self.temporal_config.scheme.value})"


class IntegralOperator(BaseTemporalOperator):
    """
    Temporal integral operator using various numerical integration methods.

    Supports rectangular rule, trapezoidal rule, Simpson's rule, and adaptive
    integration schemes for computing definite integrals over time.
    """

    def evaluate(self, data: Any, time_axis: int = -1) -> Any:
        """
        Compute temporal integral using numerical integration.

        Args:
            data: Input time series data
            time_axis: Axis along which to integrate (default: last axis)

        Returns:
            Temporal integral of input data
        """
        validated_data = self._validate_inputs(data, time_axis)

        if validated_data.shape[time_axis] < 2:
            raise ValueError("Need at least 2 time points to compute integral")

        dt = self.temporal_config.dt
        method = self.temporal_config.integration_method

        try:
            if method == IntegrationMethod.RECTANGULAR:
                # Simple rectangular rule: sum(f[i] * dt)
                # Start with zero and then cumulative sum
                first_shape = list(validated_data.shape)
                first_shape[time_axis] = 1
                zeros = np.zeros(first_shape)

                # Handle different time axes
                if time_axis == -1 or time_axis == validated_data.ndim - 1:
                    # Simple case: time is last axis
                    increments = validated_data[..., :-1] * dt  # Use all but last point
                else:
                    # General case: create slice for any axis
                    increment_slice = [slice(None)] * validated_data.ndim
                    increment_slice[time_axis] = slice(None, -1)
                    increments = validated_data[tuple(increment_slice)] * dt

                cumulative = np.cumsum(increments, axis=time_axis)
                integral = np.concatenate([zeros, cumulative], axis=time_axis)

            elif method == IntegrationMethod.TRAPEZOIDAL:
                # Use the helper method
                integral = self._trapezoidal_integration(validated_data, dt, time_axis)

            elif method == IntegrationMethod.SIMPSON:
                # Simpson's 1/3 rule (requires odd number of intervals)
                n = validated_data.shape[time_axis]
                if n < 3:
                    raise ValueError("Simpson's rule requires at least 3 points")

                # Use trapezoidal for now if odd number of points, Simpson's for groups of 3
                if n % 2 == 1:
                    # Can use Simpson's rule directly
                    # For now, fall back to trapezoidal
                    warnings.warn("Simpson's rule implementation incomplete, using trapezoidal", RuntimeWarning)
                    return self._trapezoidal_integration(validated_data, dt, time_axis)
                else:
                    warnings.warn("Simpson's rule requires odd number of points, using trapezoidal", RuntimeWarning)
                    return self._trapezoidal_integration(validated_data, dt, time_axis)

            else:
                raise NotImplementedError(f"Integration method {method} not yet implemented")

            # Check for numerical issues
            if np.any(np.isnan(integral)):
                warnings.warn("NaN values in temporal integral", RuntimeWarning)
            if np.any(np.isinf(integral)):
                warnings.warn("Infinite values in temporal integral", RuntimeWarning)

            return integral

        except Exception as e:
            raise ValueError(f"Integration computation failed: {e}")

    def _trapezoidal_integration(self, data: np.ndarray, dt: float, time_axis: int) -> np.ndarray:
        """Helper method for trapezoidal integration."""
        first_shape = list(data.shape)
        first_shape[time_axis] = 1
        zeros = np.zeros(first_shape)

        # Handle the general case for any time axis
        if time_axis == -1 or time_axis == data.ndim - 1:
            # Simple case: time is last axis
            f_current = data[..., :-1]
            f_next = data[..., 1:]
        else:
            # General case: create slices for any axis
            f_current_slice = [slice(None)] * data.ndim
            f_current_slice[time_axis] = slice(None, -1)
            f_current = data[tuple(f_current_slice)]

            f_next_slice = [slice(None)] * data.ndim
            f_next_slice[time_axis] = slice(1, None)
            f_next = data[tuple(f_next_slice)]

        increments = (f_current + f_next) * dt / 2
        cumulative = np.cumsum(increments, axis=time_axis)
        return np.concatenate([zeros, cumulative], axis=time_axis)

    def __str__(self):
        return f"Integral(dt={self.temporal_config.dt}, method={self.temporal_config.integration_method.value})"


class TemporalAveragingOperator(BaseTemporalOperator):
    """
    Temporal averaging operator for computing time-averaged quantities.

    Supports moving averages, exponential smoothing, and other temporal
    filtering operations commonly used in atmospheric and climate modeling.
    """

    def evaluate(self, data: Any, window_size: int = None, time_axis: int = -1) -> Any:
        """
        Compute temporal average over specified window.

        Args:
            data: Input time series data
            window_size: Size of averaging window (default: use full time series)
            time_axis: Axis along which to average (default: last axis)

        Returns:
            Time-averaged data
        """
        validated_data = self._validate_inputs(data, time_axis)

        if window_size is None:
            window_size = validated_data.shape[time_axis]

        if window_size < 1:
            raise ValueError("Window size must be positive")

        if window_size > validated_data.shape[time_axis]:
            warnings.warn("Window size larger than data length, using full length", RuntimeWarning)
            window_size = validated_data.shape[time_axis]

        try:
            # Simple moving average using convolution
            if window_size == 1:
                return validated_data

            # Special case: if window size equals data length, return global mean
            if window_size >= validated_data.shape[time_axis]:
                mean_value = np.mean(validated_data, axis=time_axis, keepdims=True)
                # Broadcast to original shape
                result_shape = list(validated_data.shape)
                result = np.broadcast_to(mean_value, result_shape).copy()
                return result

            # Apply moving average
            result = self._moving_average_1d(validated_data, window_size, time_axis)

            return result

        except Exception as e:
            raise ValueError(f"Temporal averaging failed: {e}")

    def _moving_average_1d(self, data: np.ndarray, window_size: int, time_axis: int) -> np.ndarray:
        """Helper method for computing moving average along one axis."""
        # Move time axis to last position for easier processing
        data_moved = np.moveaxis(data, time_axis, -1)
        original_shape = data_moved.shape

        # Reshape to 2D for processing
        data_2d = data_moved.reshape(-1, original_shape[-1])

        # Apply moving average to each row
        n_time = original_shape[-1]
        result_2d = np.zeros_like(data_2d)

        for i in range(n_time):
            start_idx = max(0, i - window_size // 2)
            end_idx = min(n_time, i + window_size // 2 + 1)
            result_2d[:, i] = np.mean(data_2d[:, start_idx:end_idx], axis=1)

        # Reshape back and move axis back
        result = result_2d.reshape(original_shape)
        return np.moveaxis(result, -1, time_axis)

    def __str__(self):
        return f"TemporalAveraging(boundary_treatment={self.temporal_config.boundary_treatment})"


class TimeSteppingOperator(BaseTemporalOperator):
    """
    Time-stepping operator for advancing model states in time.

    Implements various time-stepping schemes like Runge-Kutta methods,
    Euler schemes, and predictor-corrector methods for temporal evolution.
    """

    def evaluate(self, state: Any, rhs_function: Callable, time_axis: int = -1) -> Any:
        """
        Advance state by one time step using specified scheme.

        Args:
            state: Current state variables
            rhs_function: Right-hand side function f(t, y) for dy/dt = f(t, y)
            time_axis: Time axis (not used for single step)

        Returns:
            Updated state after one time step
        """
        validated_state = self._validate_inputs(state)
        dt = self.temporal_config.dt
        scheme = self.temporal_config.scheme

        try:
            if scheme == TemporalScheme.FORWARD_EULER:
                # y_{n+1} = y_n + dt * f(t_n, y_n)
                dydt = rhs_function(0, validated_state)  # Assume t=0 for now
                new_state = validated_state + dt * dydt

            elif scheme == TemporalScheme.BACKWARD_EULER:
                # y_{n+1} = y_n + dt * f(t_{n+1}, y_{n+1})
                # This requires solving an implicit equation - use simple iteration for now
                warnings.warn("Backward Euler uses simple iteration approximation", RuntimeWarning)
                dydt = rhs_function(dt, validated_state)  # Approximation
                new_state = validated_state + dt * dydt

            elif scheme == TemporalScheme.RUNGE_KUTTA_4:
                # Fourth-order Runge-Kutta
                k1 = rhs_function(0, validated_state)
                k2 = rhs_function(dt/2, validated_state + dt/2 * k1)
                k3 = rhs_function(dt/2, validated_state + dt/2 * k2)
                k4 = rhs_function(dt, validated_state + dt * k3)

                new_state = validated_state + dt/6 * (k1 + 2*k2 + 2*k3 + k4)

            else:
                raise NotImplementedError(f"Time-stepping scheme {scheme} not yet implemented")

            return new_state

        except Exception as e:
            raise ValueError(f"Time stepping failed: {e}")

    def __str__(self):
        return f"TimeStepping(dt={self.temporal_config.dt}, scheme={self.temporal_config.scheme.value})"