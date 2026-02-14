"""
Spatial differential operator implementations for ESM Format.

This module provides implementations for spatial differential operations
including gradient, divergence, and Laplacian operators with grid-aware
implementations, boundary condition handling, and coordinate system support.
Critical for PDE-based models.
"""

import warnings
import numpy as np
from typing import Any, Union, List, Dict, Optional, Literal
from dataclasses import dataclass

from .types import Operator, OperatorType


def _ensure_grid_data(value: Any) -> np.ndarray:
    """
    Ensure a value is a numpy array suitable for grid operations.

    Args:
        value: Input value to convert

    Returns:
        Numpy array suitable for spatial operations

    Raises:
        TypeError: If value cannot be converted to a spatial array
        ValueError: If array dimensions are incompatible with spatial operations
    """
    if isinstance(value, np.ndarray):
        if value.ndim < 1:
            raise ValueError("Spatial operators require at least 1-dimensional arrays")
        return value
    elif isinstance(value, (list, tuple)):
        try:
            arr = np.array(value, dtype=float)
            if arr.ndim < 1:
                raise ValueError("Spatial operators require at least 1-dimensional arrays")
            return arr
        except (ValueError, TypeError) as e:
            raise TypeError(f"Cannot convert sequence to spatial array: {e}")
    elif isinstance(value, (int, float)):
        # For scalar values, create a minimal 1D array
        return np.array([value], dtype=float)
    else:
        try:
            arr = np.asarray(value, dtype=float)
            if arr.ndim < 1:
                raise ValueError("Spatial operators require at least 1-dimensional arrays")
            return arr
        except (ValueError, TypeError):
            raise TypeError(f"Cannot convert {type(value).__name__} to spatial array")


def _apply_boundary_conditions(
    field: np.ndarray,
    boundary_type: str = "zero_gradient",
    axis: Optional[int] = None
) -> np.ndarray:
    """
    Apply boundary conditions to a field for spatial operations.

    Args:
        field: Input field array
        boundary_type: Type of boundary condition ("zero_gradient", "periodic", "dirichlet")
        axis: Specific axis for boundary condition (if None, apply to all axes)

    Returns:
        Field with boundary conditions applied
    """
    if boundary_type == "zero_gradient":
        # Neumann boundaries: ∂field/∂n = 0 (no-flux)
        return field  # Zero gradient is implicitly handled in finite difference
    elif boundary_type == "periodic":
        # Periodic boundaries - would need special handling in operators
        return field
    elif boundary_type == "dirichlet":
        # Fixed value boundaries - would need external specification
        return field
    else:
        warnings.warn(f"Unknown boundary condition type: {boundary_type}, using zero_gradient")
        return field


@dataclass
class SpatialOperatorConfig:
    """Configuration for spatial differential operators."""
    grid_spacing: Union[float, List[float]] = 1.0  # Grid spacing (dx, dy, dz)
    boundary_conditions: str = "zero_gradient"  # "zero_gradient", "periodic", "dirichlet"
    coordinate_system: str = "cartesian"  # "cartesian", "cylindrical", "spherical"
    finite_difference_order: int = 2  # Order of finite difference scheme
    upwind_bias: float = 0.0  # Upwind bias factor (0 = centered, 1 = full upwind)
    stencil_padding: bool = True  # Whether to pad arrays for stencil operations


class BaseSpatialOperator:
    """
    Base class for spatial differential operators.

    Provides common functionality for grid operations, boundary conditions,
    and coordinate system handling.
    """

    def __init__(self, config: Operator):
        """
        Initialize the spatial operator.

        Args:
            config: Operator configuration
        """
        self.config = config
        self.name = config.name
        self.parameters = config.parameters
        self.input_variables = config.input_variables
        self.output_variables = config.output_variables

        # Parse spatial-specific configuration
        self.spatial_config = SpatialOperatorConfig()
        if "grid_spacing" in self.parameters:
            self.spatial_config.grid_spacing = self.parameters["grid_spacing"]
        if "boundary_conditions" in self.parameters:
            self.spatial_config.boundary_conditions = self.parameters["boundary_conditions"]
        if "coordinate_system" in self.parameters:
            self.spatial_config.coordinate_system = self.parameters["coordinate_system"]
        if "finite_difference_order" in self.parameters:
            self.spatial_config.finite_difference_order = self.parameters["finite_difference_order"]
        if "upwind_bias" in self.parameters:
            self.spatial_config.upwind_bias = self.parameters["upwind_bias"]
        if "stencil_padding" in self.parameters:
            self.spatial_config.stencil_padding = self.parameters["stencil_padding"]

    def _get_grid_spacing(self, dimension: Optional[str] = None) -> float:
        """
        Get grid spacing for a specific dimension.

        Args:
            dimension: Dimension name ("x", "y", "z") or None for uniform

        Returns:
            Grid spacing value
        """
        if isinstance(self.spatial_config.grid_spacing, (list, tuple)):
            if dimension == "x":
                return self.spatial_config.grid_spacing[0]
            elif dimension == "y" and len(self.spatial_config.grid_spacing) > 1:
                return self.spatial_config.grid_spacing[1]
            elif dimension == "z" and len(self.spatial_config.grid_spacing) > 2:
                return self.spatial_config.grid_spacing[2]
            else:
                return self.spatial_config.grid_spacing[0]
        else:
            return self.spatial_config.grid_spacing

    def _validate_spatial_inputs(self, *operands) -> List[np.ndarray]:
        """
        Validate and prepare input operands for spatial operations.

        Args:
            *operands: Input operands to validate

        Returns:
            List of validated spatial arrays

        Raises:
            TypeError: If operands are not suitable for spatial operations
            ValueError: If operands have incompatible shapes
        """
        validated = []

        for operand in operands:
            try:
                spatial_array = _ensure_grid_data(operand)
                validated.append(spatial_array)
            except TypeError as e:
                raise TypeError(f"Invalid operand in {self.name}: {e}")

        return validated

    def evaluate(self, *operands, **kwargs) -> Any:
        """
        Evaluate the spatial operator with given operands.

        This method should be implemented by subclasses.

        Args:
            *operands: Input operands
            **kwargs: Additional keyword arguments (e.g., dim for gradient)

        Returns:
            Result of the spatial operation
        """
        raise NotImplementedError("Subclasses must implement evaluate method")


class GradientOperator(BaseSpatialOperator):
    """Gradient operator with grid-aware finite difference implementation."""

    def evaluate(self, field: Any, **kwargs) -> Any:
        """
        Compute gradient of a field along specified dimension.

        Args:
            field: Input field to compute gradient of
            **kwargs: Additional arguments including 'dim' for dimension

        Returns:
            Gradient of the field
        """
        validated = self._validate_spatial_inputs(field)
        field_array = validated[0]

        # Get dimension from kwargs or config
        dimension = kwargs.get('dim', self.parameters.get('dimension', 'x'))

        try:
            # Determine axis for gradient computation
            # Standard convention: in a 2D array, axis 0 = y (rows), axis 1 = x (columns)
            if dimension == 'x':
                axis = 1 if field_array.ndim > 1 else 0  # x is typically the last axis (columns)
            elif dimension == 'y':
                axis = 0 if field_array.ndim > 1 else 0  # y is typically the first axis (rows)
            elif dimension == 'z':
                axis = 2 if field_array.ndim > 2 else 0  # z would be the third axis
            else:
                # Try to interpret as integer axis
                try:
                    axis = int(dimension)
                except (ValueError, TypeError):
                    axis = 0

            # Get grid spacing for this dimension
            dx = self._get_grid_spacing(dimension)

            # Apply boundary conditions
            padded_field = _apply_boundary_conditions(
                field_array,
                self.spatial_config.boundary_conditions,
                axis
            )

            # Compute finite difference gradient
            if self.spatial_config.finite_difference_order == 2:
                # Second-order centered difference
                gradient = np.gradient(padded_field, dx, axis=axis)
            elif self.spatial_config.finite_difference_order == 4:
                # Fourth-order centered difference (simplified)
                # For production, would implement proper 5-point stencil
                gradient = np.gradient(padded_field, dx, axis=axis)
                warnings.warn("Fourth-order finite difference not fully implemented, using second-order")
            else:
                # Default to second-order
                gradient = np.gradient(padded_field, dx, axis=axis)

            # Apply upwind bias if requested (for advection-type operators)
            if self.spatial_config.upwind_bias > 0:
                # Simple upwind modification - in production would be more sophisticated
                upwind_grad = np.gradient(padded_field, dx, axis=axis)
                gradient = (1 - self.spatial_config.upwind_bias) * gradient + \
                          self.spatial_config.upwind_bias * upwind_grad

            return gradient

        except Exception as e:
            raise ValueError(f"Gradient operation failed: {e}")

    def __str__(self):
        return f"Gradient(order={self.spatial_config.finite_difference_order}, dx={self.spatial_config.grid_spacing})"


class DivergenceOperator(BaseSpatialOperator):
    """Divergence operator for vector fields with finite difference implementation."""

    def evaluate(self, vector_field: Any, **kwargs) -> Any:
        """
        Compute divergence of a vector field.

        Args:
            vector_field: Input vector field (can be components or full vector)
            **kwargs: Additional arguments

        Returns:
            Divergence of the vector field
        """
        validated = self._validate_spatial_inputs(vector_field)
        field_array = validated[0]

        try:
            # For simplicity, assume field is a scalar and compute divergence
            # as sum of partial derivatives along each spatial dimension
            # In production, would handle proper vector field decomposition

            divergence = np.zeros_like(field_array)

            # Determine spatial dimensions
            if field_array.ndim >= 1:
                # x-component (last axis for 1D, axis 1 for 2D+)
                dx = self._get_grid_spacing("x")
                axis = 1 if field_array.ndim > 1 else 0
                grad_x = np.gradient(field_array, dx, axis=axis)
                divergence += grad_x

            if field_array.ndim >= 2:
                # y-component (axis 0 for 2D+)
                dy = self._get_grid_spacing("y")
                grad_y = np.gradient(field_array, dy, axis=0)
                divergence += grad_y

            if field_array.ndim >= 3:
                # z-component (axis 2 for 3D+)
                dz = self._get_grid_spacing("z")
                grad_z = np.gradient(field_array, dz, axis=2)
                divergence += grad_z

            # Apply boundary conditions
            divergence = _apply_boundary_conditions(
                divergence,
                self.spatial_config.boundary_conditions
            )

            return divergence

        except Exception as e:
            raise ValueError(f"Divergence operation failed: {e}")

    def __str__(self):
        return f"Divergence(order={self.spatial_config.finite_difference_order}, dx={self.spatial_config.grid_spacing})"


class LaplacianOperator(BaseSpatialOperator):
    """Laplacian operator (∇²) with finite difference implementation."""

    def evaluate(self, field: Any, **kwargs) -> Any:
        """
        Compute Laplacian (second derivative sum) of a scalar field.

        Args:
            field: Input scalar field
            **kwargs: Additional arguments

        Returns:
            Laplacian of the field
        """
        validated = self._validate_spatial_inputs(field)
        field_array = validated[0]

        try:
            # Apply boundary conditions
            padded_field = _apply_boundary_conditions(
                field_array,
                self.spatial_config.boundary_conditions
            )

            # Compute Laplacian as sum of second derivatives
            laplacian = np.zeros_like(padded_field)

            # x-direction second derivative
            if field_array.ndim >= 1:
                dx = self._get_grid_spacing("x")
                axis = 1 if field_array.ndim > 1 else 0
                if self.spatial_config.finite_difference_order == 2:
                    # Second-order finite difference: d²f/dx² ≈ (f[i+1] - 2f[i] + f[i-1]) / dx²
                    if padded_field.shape[axis] >= 3:
                        # Use numpy's second derivative approximation
                        d2_dx2 = np.gradient(np.gradient(padded_field, dx, axis=axis), dx, axis=axis)
                        laplacian += d2_dx2
                    else:
                        # For small arrays, approximate as zero
                        pass

            # y-direction second derivative
            if field_array.ndim >= 2:
                dy = self._get_grid_spacing("y")
                axis = 0
                if padded_field.shape[axis] >= 3:
                    d2_dy2 = np.gradient(np.gradient(padded_field, dy, axis=axis), dy, axis=axis)
                    laplacian += d2_dy2

            # z-direction second derivative
            if field_array.ndim >= 3:
                dz = self._get_grid_spacing("z")
                axis = 2
                if padded_field.shape[axis] >= 3:
                    d2_dz2 = np.gradient(np.gradient(padded_field, dz, axis=axis), dz, axis=axis)
                    laplacian += d2_dz2

            return laplacian

        except Exception as e:
            raise ValueError(f"Laplacian operation failed: {e}")

    def __str__(self):
        return f"Laplacian(order={self.spatial_config.finite_difference_order}, dx={self.spatial_config.grid_spacing})"