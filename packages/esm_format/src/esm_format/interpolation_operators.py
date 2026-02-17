"""
Interpolation operator implementations for ESM Format.

This module provides implementations for various interpolation methods including:
- Linear interpolation
- Cubic spline interpolation
- Custom spline interpolation with configurable order
- Grid remapping and coordinate transformations

These operators are essential for data fusion, regridding, and coupling between
models with different spatial and temporal resolutions.
"""

import warnings
import numpy as np
from typing import Any, Union, List, Dict, Optional, Tuple
from dataclasses import dataclass
from scipy.interpolate import interp1d, CubicSpline, BSpline, splrep, splev
from scipy.spatial import cKDTree
import scipy.ndimage as ndimage

from .esm_types import Operator, OperatorType


@dataclass
class InterpolationConfig:
    """Configuration for interpolation operators."""
    method: str = "linear"  # "linear", "cubic", "spline", "nearest", "quadratic"
    order: int = 3  # spline order (1=linear, 2=quadratic, 3=cubic, etc.)
    extrapolate: str = "constant"  # "constant", "linear", "extrapolate", "raise"
    bounds_error: bool = False  # whether to raise error for out-of-bounds values
    fill_value: Union[float, str] = np.nan  # value for out-of-bounds points
    axis: int = -1  # axis along which to interpolate
    assume_sorted: bool = False  # whether x values are assumed to be sorted
    smoothing: float = 0.0  # smoothing factor for splines (0 = no smoothing)


class BaseInterpolationOperator:
    """
    Base class for interpolation operators.

    Provides common functionality for input validation, coordinate handling,
    and result formatting.
    """

    def __init__(self, config: Operator):
        """
        Initialize the interpolation operator.

        Args:
            config: Operator configuration
        """
        self.config = config
        self.name = config.name
        self.parameters = config.parameters
        self.input_variables = config.input_variables
        self.output_variables = config.output_variables

        # Parse interpolation-specific configuration
        self.interp_config = InterpolationConfig()
        if "method" in self.parameters:
            self.interp_config.method = self.parameters["method"]
        if "order" in self.parameters:
            self.interp_config.order = int(self.parameters["order"])
        if "extrapolate" in self.parameters:
            self.interp_config.extrapolate = self.parameters["extrapolate"]
        if "bounds_error" in self.parameters:
            self.interp_config.bounds_error = bool(self.parameters["bounds_error"])
        if "fill_value" in self.parameters:
            self.interp_config.fill_value = self.parameters["fill_value"]
        if "axis" in self.parameters:
            self.interp_config.axis = int(self.parameters["axis"])
        if "assume_sorted" in self.parameters:
            self.interp_config.assume_sorted = bool(self.parameters["assume_sorted"])
        if "smoothing" in self.parameters:
            self.interp_config.smoothing = float(self.parameters["smoothing"])

    def _validate_inputs(self, x: Any, y: Any, x_new: Any) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Validate and prepare interpolation inputs.

        Args:
            x: Known x coordinates
            y: Known y values
            x_new: New x coordinates to interpolate at

        Returns:
            Tuple of validated (x, y, x_new) arrays

        Raises:
            ValueError: If inputs are invalid
        """
        try:
            x_arr = np.asarray(x)
            y_arr = np.asarray(y)
            x_new_arr = np.asarray(x_new)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Cannot convert inputs to arrays: {e}")

        if x_arr.size == 0 or y_arr.size == 0:
            raise ValueError("Input arrays cannot be empty")

        if x_arr.ndim != 1:
            raise ValueError(f"x coordinates must be 1D, got shape {x_arr.shape}")

        if x_arr.size != y_arr.shape[self.interp_config.axis]:
            raise ValueError(
                f"Size mismatch: x has {x_arr.size} points, but y has "
                f"{y_arr.shape[self.interp_config.axis]} points along axis {self.interp_config.axis}"
            )

        if x_new_arr.size == 0:
            raise ValueError("New x coordinates cannot be empty")

        # Check for duplicate x values (causes issues with most interpolation methods)
        if len(np.unique(x_arr)) != len(x_arr):
            warnings.warn("Duplicate x values detected, may cause interpolation issues", RuntimeWarning)

        # Sort if not assumed sorted
        if not self.interp_config.assume_sorted:
            sort_idx = np.argsort(x_arr)
            x_arr = x_arr[sort_idx]
            if y_arr.ndim == 1:
                y_arr = y_arr[sort_idx]
            else:
                y_arr = np.take(y_arr, sort_idx, axis=self.interp_config.axis)

        return x_arr, y_arr, x_new_arr

    def _handle_extrapolation(self, result: np.ndarray, x: np.ndarray, x_new: np.ndarray) -> np.ndarray:
        """
        Handle extrapolation based on configuration.

        Args:
            result: Interpolated result
            x: Original x coordinates
            x_new: New x coordinates

        Returns:
            Result with extrapolation handling applied
        """
        if self.interp_config.extrapolate == "raise":
            x_min, x_max = x.min(), x.max()
            out_of_bounds = (x_new < x_min) | (x_new > x_max)
            if np.any(out_of_bounds):
                raise ValueError(f"Extrapolation not allowed, x_new values outside [{x_min}, {x_max}]")

        elif self.interp_config.extrapolate == "constant":
            x_min, x_max = x.min(), x.max()
            below_mask = x_new < x_min
            above_mask = x_new > x_max

            if isinstance(self.interp_config.fill_value, str):
                if self.interp_config.fill_value == "extrapolate":
                    pass  # Keep original result
                else:
                    fill_val = np.nan
            else:
                fill_val = float(self.interp_config.fill_value)

            if not isinstance(self.interp_config.fill_value, str) or self.interp_config.fill_value != "extrapolate":
                result[below_mask] = fill_val
                result[above_mask] = fill_val

        return result

    def interpolate(self, x: Any, y: Any, x_new: Any) -> np.ndarray:
        """
        Perform interpolation.

        This method should be implemented by subclasses.

        Args:
            x: Known x coordinates
            y: Known y values
            x_new: New x coordinates to interpolate at

        Returns:
            Interpolated values at x_new
        """
        raise NotImplementedError("Subclasses must implement interpolate method")


class LinearInterpolationOperator(BaseInterpolationOperator):
    """Linear interpolation operator using scipy.interpolate.interp1d."""

    def interpolate(self, x: Any, y: Any, x_new: Any) -> np.ndarray:
        """
        Perform linear interpolation.

        Args:
            x: Known x coordinates
            y: Known y values
            x_new: New x coordinates to interpolate at

        Returns:
            Linearly interpolated values at x_new
        """
        x_arr, y_arr, x_new_arr = self._validate_inputs(x, y, x_new)

        try:
            # Configure scipy interp1d
            bounds_error = self.interp_config.bounds_error
            fill_value = self.interp_config.fill_value

            if self.interp_config.extrapolate == "extrapolate":
                bounds_error = False
                fill_value = "extrapolate"
            elif not bounds_error and isinstance(fill_value, str) and fill_value != "extrapolate":
                fill_value = np.nan

            # Create interpolation function
            f = interp1d(
                x_arr, y_arr,
                kind='linear',
                axis=self.interp_config.axis,
                bounds_error=bounds_error,
                fill_value=fill_value,
                assume_sorted=self.interp_config.assume_sorted
            )

            # Perform interpolation
            result = f(x_new_arr)

            # Handle extrapolation if needed
            if not bounds_error and self.interp_config.extrapolate != "extrapolate":
                result = self._handle_extrapolation(result, x_arr, x_new_arr)

            return result

        except Exception as e:
            raise ValueError(f"Linear interpolation failed: {e}")

    def __str__(self):
        return f"LinearInterpolation(extrapolate={self.interp_config.extrapolate})"


class CubicInterpolationOperator(BaseInterpolationOperator):
    """Cubic spline interpolation operator using scipy.interpolate.CubicSpline."""

    def interpolate(self, x: Any, y: Any, x_new: Any) -> np.ndarray:
        """
        Perform cubic spline interpolation.

        Args:
            x: Known x coordinates
            y: Known y values
            x_new: New x coordinates to interpolate at

        Returns:
            Cubic spline interpolated values at x_new
        """
        x_arr, y_arr, x_new_arr = self._validate_inputs(x, y, x_new)

        if len(x_arr) < 2:
            raise ValueError("Cubic interpolation requires at least 2 points")

        try:
            # Configure boundary conditions based on extrapolation setting
            if self.interp_config.extrapolate == "extrapolate":
                extrapolate = True
            else:
                extrapolate = False

            # Create cubic spline
            cs = CubicSpline(
                x_arr, y_arr,
                axis=self.interp_config.axis,
                extrapolate=extrapolate
            )

            # Perform interpolation
            result = cs(x_new_arr)

            # Handle extrapolation if needed
            if not extrapolate:
                result = self._handle_extrapolation(result, x_arr, x_new_arr)

            return result

        except Exception as e:
            raise ValueError(f"Cubic interpolation failed: {e}")

    def __str__(self):
        return f"CubicInterpolation(extrapolate={self.interp_config.extrapolate})"


class SplineInterpolationOperator(BaseInterpolationOperator):
    """General spline interpolation operator with configurable order."""

    def interpolate(self, x: Any, y: Any, x_new: Any) -> np.ndarray:
        """
        Perform spline interpolation with configurable order.

        Args:
            x: Known x coordinates
            y: Known y values
            x_new: New x coordinates to interpolate at

        Returns:
            Spline interpolated values at x_new
        """
        x_arr, y_arr, x_new_arr = self._validate_inputs(x, y, x_new)

        order = self.interp_config.order
        if len(x_arr) <= order:
            raise ValueError(f"Spline of order {order} requires at least {order + 1} points, got {len(x_arr)}")

        try:
            # Handle different interpolation approaches based on order
            if order == 1:
                # Use linear interpolation for order 1
                return LinearInterpolationOperator(self.config).interpolate(x, y, x_new)
            elif order == 3 and self.interp_config.smoothing == 0.0:
                # Use CubicSpline for order 3 without smoothing
                return CubicInterpolationOperator(self.config).interpolate(x, y, x_new)
            else:
                # Use scipy's splrep/splev for general case
                bounds_error = self.interp_config.bounds_error

                # Create spline representation
                if y_arr.ndim == 1:
                    # 1D case
                    tck = splrep(
                        x_arr, y_arr,
                        k=min(order, len(x_arr) - 1),
                        s=self.interp_config.smoothing
                    )
                    result = splev(x_new_arr, tck, ext=0 if bounds_error else 1)

                else:
                    # Multi-dimensional case - interpolate along specified axis
                    if self.interp_config.axis != -1 and self.interp_config.axis != y_arr.ndim - 1:
                        # Move interpolation axis to last position
                        y_arr = np.moveaxis(y_arr, self.interp_config.axis, -1)

                    # Reshape for processing
                    original_shape = y_arr.shape
                    y_reshaped = y_arr.reshape(-1, original_shape[-1])

                    # Interpolate each row
                    result_list = []
                    for i in range(y_reshaped.shape[0]):
                        tck = splrep(
                            x_arr, y_reshaped[i],
                            k=min(order, len(x_arr) - 1),
                            s=self.interp_config.smoothing
                        )
                        row_result = splev(x_new_arr, tck, ext=0 if bounds_error else 1)
                        result_list.append(row_result)

                    # Reshape back
                    result = np.array(result_list).reshape(original_shape[:-1] + (len(x_new_arr),))

                    # Move axis back if needed
                    if self.interp_config.axis != -1 and self.interp_config.axis != y_arr.ndim - 1:
                        result = np.moveaxis(result, -1, self.interp_config.axis)

                # Handle extrapolation
                if not bounds_error:
                    result = self._handle_extrapolation(result, x_arr, x_new_arr)

                return result

        except Exception as e:
            raise ValueError(f"Spline interpolation (order {order}) failed: {e}")

    def __str__(self):
        return f"SplineInterpolation(order={self.interp_config.order}, smoothing={self.interp_config.smoothing})"


class GridInterpolationOperator(BaseInterpolationOperator):
    """
    Grid-based interpolation operator for multi-dimensional data.

    Supports nearest-neighbor, linear, and cubic interpolation on regular grids.
    Useful for regridding and coordinate transformations.
    """

    def interpolate_grid(self, coords: List[np.ndarray], values: np.ndarray,
                        new_coords: List[np.ndarray]) -> np.ndarray:
        """
        Perform grid-based interpolation.

        Args:
            coords: List of coordinate arrays for each dimension
            values: Values on the grid
            new_coords: New coordinate arrays to interpolate to

        Returns:
            Interpolated values at new coordinates
        """
        if len(coords) != values.ndim:
            raise ValueError(f"Number of coordinate arrays ({len(coords)}) must match data dimensions ({values.ndim})")

        if len(new_coords) != len(coords):
            raise ValueError(f"Number of new coordinate arrays ({len(new_coords)}) must match original ({len(coords)})")

        try:
            # Validate all coordinates are sorted
            for i, coord in enumerate(coords):
                if not self.interp_config.assume_sorted and not np.all(coord[1:] >= coord[:-1]):
                    raise ValueError(f"Coordinate array {i} must be sorted")

            # Map interpolation methods
            method_map = {
                "linear": 1,
                "nearest": 0,
                "cubic": 3
            }

            order = method_map.get(self.interp_config.method, 1)

            # Create coordinate transformation
            new_indices = []
            for i, (old_coord, new_coord) in enumerate(zip(coords, new_coords)):
                # Map new coordinates to indices in old grid
                indices = np.interp(new_coord, old_coord, np.arange(len(old_coord)))
                new_indices.append(indices)

            # Create meshgrid of new indices
            new_index_grids = np.meshgrid(*new_indices, indexing='ij')

            # Perform interpolation using scipy.ndimage
            result = ndimage.map_coordinates(
                values,
                new_index_grids,
                order=order,
                mode='constant' if self.interp_config.extrapolate == "constant" else 'nearest',
                cval=self.interp_config.fill_value if isinstance(self.interp_config.fill_value, (int, float)) else np.nan,
                prefilter=True
            )

            return result

        except Exception as e:
            raise ValueError(f"Grid interpolation failed: {e}")

    def interpolate(self, x: Any, y: Any, x_new: Any) -> np.ndarray:
        """
        Wrapper for 1D interpolation to maintain interface compatibility.

        For true grid interpolation, use interpolate_grid method directly.
        """
        return super().interpolate(x, y, x_new)

    def __str__(self):
        return f"GridInterpolation(method={self.interp_config.method})"


# Factory function for creating interpolation operators
def create_interpolation_operator(method: str, config: Operator) -> BaseInterpolationOperator:
    """
    Factory function to create interpolation operators.

    Args:
        method: Interpolation method ('linear', 'cubic', 'spline', 'grid')
        config: Operator configuration

    Returns:
        Appropriate interpolation operator instance

    Raises:
        ValueError: If method is not supported
    """
    method_map = {
        'linear': LinearInterpolationOperator,
        'cubic': CubicInterpolationOperator,
        'spline': SplineInterpolationOperator,
        'grid': GridInterpolationOperator
    }

    if method not in method_map:
        available = ', '.join(method_map.keys())
        raise ValueError(f"Unsupported interpolation method '{method}'. Available methods: {available}")

    return method_map[method](config)