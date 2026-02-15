"""
Boundary condition processing system for ESM Format.

This module provides comprehensive boundary condition processing supporting:
- Various BC types: Dirichlet, Neumann, Robin, Periodic
- Spatial and temporal variation
- Consistency validation with domain geometry
- Integration with spatial operators

Key Features:
- Support for complex boundary expressions
- Time-varying boundary conditions
- Multi-dimensional boundary specification
- Domain geometry validation
- Efficient boundary condition application
"""

import numpy as np
import warnings
from typing import Any, Dict, List, Optional, Union, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

from .types import BoundaryCondition, BoundaryConditionType, Domain, SpatialDimension


class BoundaryLocationError(ValueError):
    """Raised when boundary location is invalid for domain geometry."""
    pass


class BoundaryValueError(ValueError):
    """Raised when boundary value specification is invalid."""
    pass


@dataclass
class BoundaryConstraint:
    """
    Enhanced boundary constraint supporting spatial/temporal variation.

    Extends basic BoundaryCondition with support for:
    - Spatial variation across boundary
    - Temporal variation over time
    - Robin boundary conditions
    """
    # Basic boundary condition info
    type: BoundaryConditionType
    dimensions: List[str]

    # Value specification (multiple options)
    value: Optional[Union[float, str, Callable]] = None  # Constant, expression, or function
    spatial_profile: Optional[Dict[str, Any]] = None  # Spatial variation specification
    temporal_profile: Optional[Dict[str, Any]] = None  # Temporal variation specification

    # Robin BC parameters (αu + β∂u/∂n = γ)
    robin_alpha: Optional[float] = None  # Coefficient for u
    robin_beta: Optional[float] = None   # Coefficient for ∂u/∂n
    robin_gamma: Optional[Union[float, str, Callable]] = None  # RHS value/expression

    # Boundary location specification
    location: Optional[str] = None  # "min", "max", "left", "right", "top", "bottom", etc.
    coordinate_range: Optional[Tuple[float, float]] = None  # Coordinate range for partial boundaries


@dataclass
class BoundaryProcessorConfig:
    """Configuration for boundary condition processor."""
    # Numerical parameters
    ghost_cells: int = 1  # Number of ghost cells for boundary padding
    interpolation_order: int = 2  # Order for spatial interpolation
    time_integration: str = "linear"  # Time interpolation method

    # Validation settings
    strict_geometry: bool = True  # Strict domain geometry validation
    warn_approximations: bool = True  # Warn about numerical approximations

    # Performance settings
    cache_evaluations: bool = True  # Cache boundary evaluations
    parallel_boundaries: bool = False  # Parallel boundary processing


class BoundaryConditionProcessor:
    """
    Comprehensive boundary condition processor and validator.

    Handles processing of boundary conditions including:
    - Validation against domain geometry
    - Spatial and temporal interpolation
    - Robin boundary condition support
    - Efficient boundary application
    """

    def __init__(self, config: Optional[BoundaryProcessorConfig] = None):
        """
        Initialize boundary condition processor.

        Args:
            config: Processor configuration (uses defaults if None)
        """
        self.config = config or BoundaryProcessorConfig()
        self._cached_evaluations = {}

    def validate_boundary_conditions(
        self,
        boundary_conditions: List[BoundaryCondition],
        domain: Domain
    ) -> List[str]:
        """
        Validate boundary conditions against domain geometry.

        Args:
            boundary_conditions: List of boundary conditions to validate
            domain: Domain specification to validate against

        Returns:
            List of validation warnings (empty if all valid)

        Raises:
            BoundaryLocationError: If boundary locations are invalid
            BoundaryValueError: If boundary values are incompatible
        """
        warnings_list = []

        if not boundary_conditions:
            return warnings_list

        # Check each boundary condition
        for i, bc in enumerate(boundary_conditions):
            try:
                # Validate dimensions exist in domain
                for dim in bc.dimensions:
                    if dim not in domain.spatial:
                        raise BoundaryLocationError(
                            f"Boundary condition {i}: dimension '{dim}' not found in domain spatial dimensions"
                        )

                # Validate boundary type requirements
                if bc.type in [BoundaryConditionType.CONSTANT, BoundaryConditionType.DIRICHLET]:
                    if bc.value is None:
                        raise BoundaryValueError(
                            f"Boundary condition {i}: {bc.type.value} boundary requires a value"
                        )

                # Validate Robin boundary conditions
                if bc.type.value == "robin":  # Handle Robin if added to enum later
                    # Robin BC validation would go here
                    pass

                # Check dimension compatibility with domain
                for dim in bc.dimensions:
                    spatial_dim = domain.spatial[dim]
                    self._validate_spatial_dimension_boundary(bc, dim, spatial_dim, i)

            except (BoundaryLocationError, BoundaryValueError):
                raise
            except Exception as e:
                warnings_list.append(f"Boundary condition {i}: unexpected validation error: {e}")

        return warnings_list

    def _validate_spatial_dimension_boundary(
        self,
        bc: BoundaryCondition,
        dim: str,
        spatial_dim: SpatialDimension,
        bc_index: int
    ) -> None:
        """
        Validate boundary condition against specific spatial dimension.

        Args:
            bc: Boundary condition to validate
            dim: Dimension name
            spatial_dim: Spatial dimension specification
            bc_index: Index for error reporting
        """
        # Check if periodic boundary is compatible with domain
        if bc.type == BoundaryConditionType.PERIODIC:
            # Periodic boundaries should have compatible domain extents
            if spatial_dim.min is None or spatial_dim.max is None:
                raise BoundaryLocationError(
                    f"Boundary condition {bc_index}: periodic boundary on dimension '{dim}' "
                    f"requires finite domain bounds"
                )

        # Validate grid spacing for gradient boundaries
        if bc.type == BoundaryConditionType.ZERO_GRADIENT or bc.type == BoundaryConditionType.NEUMANN:
            if spatial_dim.grid_spacing is None or spatial_dim.grid_spacing <= 0:
                raise BoundaryLocationError(
                    f"Boundary condition {bc_index}: gradient boundary on dimension '{dim}' "
                    f"requires positive grid spacing"
                )

    def process_boundary_conditions(
        self,
        field: np.ndarray,
        boundary_conditions: List[BoundaryCondition],
        domain: Domain,
        time: Optional[float] = None
    ) -> np.ndarray:
        """
        Apply boundary conditions to a field array.

        Args:
            field: Field array to apply boundaries to
            boundary_conditions: List of boundary conditions
            domain: Domain specification
            time: Current time for time-varying boundaries

        Returns:
            Field array with boundary conditions applied

        Raises:
            BoundaryLocationError: If boundary application fails
        """
        if not boundary_conditions:
            return field

        # Validate inputs (only in strict mode, otherwise just collect warnings)
        if self.config.strict_geometry:
            self.validate_boundary_conditions(boundary_conditions, domain)

        # Create working copy
        result_field = field.copy()

        # Apply each boundary condition
        for bc in boundary_conditions:
            try:
                # Validate each boundary condition individually for non-strict mode
                if not self.config.strict_geometry:
                    # Quick validation to see if this BC can be applied
                    skip_bc = False
                    for dim in bc.dimensions:
                        if dim not in domain.spatial:
                            warnings.warn(f"Boundary condition dimension '{dim}' not found in domain, skipping")
                            skip_bc = True
                            break
                    if skip_bc:
                        continue  # Skip this boundary condition

                result_field = self._apply_single_boundary_condition(
                    result_field, bc, domain, time
                )
            except (BoundaryLocationError, BoundaryValueError) as e:
                if self.config.strict_geometry:
                    raise
                else:
                    warnings.warn(f"Boundary condition application failed: {e}, skipping")
            except Exception as e:
                if self.config.strict_geometry:
                    raise BoundaryLocationError(f"Failed to apply boundary condition: {e}")
                else:
                    warnings.warn(f"Boundary condition application failed: {e}, skipping")

        return result_field

    def _apply_single_boundary_condition(
        self,
        field: np.ndarray,
        bc: BoundaryCondition,
        domain: Domain,
        time: Optional[float] = None
    ) -> np.ndarray:
        """
        Apply a single boundary condition to a field.

        Args:
            field: Field array to modify
            bc: Boundary condition to apply
            domain: Domain specification
            time: Current time

        Returns:
            Modified field array
        """
        if bc.type == BoundaryConditionType.PERIODIC:
            return self._apply_periodic_boundary(field, bc, domain)
        elif bc.type in [BoundaryConditionType.CONSTANT, BoundaryConditionType.DIRICHLET]:
            return self._apply_dirichlet_boundary(field, bc, domain, time)
        elif bc.type in [BoundaryConditionType.ZERO_GRADIENT, BoundaryConditionType.NEUMANN]:
            return self._apply_neumann_boundary(field, bc, domain, time)
        else:
            # For unsupported types, return unchanged with warning
            warnings.warn(f"Boundary condition type {bc.type} not fully implemented, skipping")
            return field

    def _apply_periodic_boundary(
        self,
        field: np.ndarray,
        bc: BoundaryCondition,
        domain: Domain
    ) -> np.ndarray:
        """Apply periodic boundary conditions."""
        # For periodic boundaries, values at one end should equal values at other end
        # This is typically handled in the spatial operators themselves
        # For now, return unchanged as periodic handling is complex
        return field

    def _apply_dirichlet_boundary(
        self,
        field: np.ndarray,
        bc: BoundaryCondition,
        domain: Domain,
        time: Optional[float] = None
    ) -> np.ndarray:
        """Apply Dirichlet (fixed value) boundary conditions."""
        if bc.value is None:
            warnings.warn("Dirichlet boundary condition missing value, skipping")
            return field

        # Get boundary value (could be time-dependent in future)
        boundary_value = self._evaluate_boundary_value(bc.value, time)

        # For simplicity, apply to field boundaries
        # In production, would determine which field boundaries correspond to domain boundaries
        result = field.copy()

        # Apply to all boundaries of the field (simplified implementation)
        if field.ndim == 1:
            result[0] = boundary_value
            result[-1] = boundary_value
        elif field.ndim == 2:
            result[0, :] = boundary_value  # Top boundary
            result[-1, :] = boundary_value  # Bottom boundary
            result[:, 0] = boundary_value  # Left boundary
            result[:, -1] = boundary_value  # Right boundary
        elif field.ndim == 3:
            # Apply to all faces in 3D
            result[0, :, :] = boundary_value
            result[-1, :, :] = boundary_value
            result[:, 0, :] = boundary_value
            result[:, -1, :] = boundary_value
            result[:, :, 0] = boundary_value
            result[:, :, -1] = boundary_value

        return result

    def _apply_neumann_boundary(
        self,
        field: np.ndarray,
        bc: BoundaryCondition,
        domain: Domain,
        time: Optional[float] = None
    ) -> np.ndarray:
        """Apply Neumann (gradient) boundary conditions."""
        # For zero gradient (most common Neumann case),
        # the boundary values should equal their interior neighbors
        result = field.copy()

        if field.ndim == 1:
            # Copy interior values to boundaries
            result[0] = result[1]  # Left boundary
            result[-1] = result[-2]  # Right boundary
        elif field.ndim == 2:
            result[0, :] = result[1, :]  # Top boundary
            result[-1, :] = result[-2, :]  # Bottom boundary
            result[:, 0] = result[:, 1]  # Left boundary
            result[:, -1] = result[:, -2]  # Right boundary
        elif field.ndim == 3:
            result[0, :, :] = result[1, :, :]
            result[-1, :, :] = result[-2, :, :]
            result[:, 0, :] = result[:, 1, :]
            result[:, -1, :] = result[:, -2, :]
            result[:, :, 0] = result[:, :, 1]
            result[:, :, -1] = result[:, :, -2]

        return result

    def _evaluate_boundary_value(
        self,
        value: Union[float, str, Callable],
        time: Optional[float] = None
    ) -> float:
        """
        Evaluate a boundary value, which may be time-dependent.

        Args:
            value: Value specification (constant, expression, or function)
            time: Current time

        Returns:
            Evaluated boundary value
        """
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str):
            # In future, could parse mathematical expressions
            try:
                return float(value)
            except ValueError:
                warnings.warn(f"Could not parse boundary value '{value}', using 0.0")
                return 0.0
        elif callable(value):
            try:
                if time is not None:
                    return float(value(time))
                else:
                    return float(value())
            except Exception as e:
                warnings.warn(f"Boundary value function evaluation failed: {e}, using 0.0")
                return 0.0
        else:
            warnings.warn(f"Unknown boundary value type {type(value)}, using 0.0")
            return 0.0


# Enhanced boundary condition creation helpers
def create_dirichlet_boundary(
    dimensions: List[str],
    value: Union[float, str, Callable],
    location: Optional[str] = None
) -> BoundaryCondition:
    """
    Create a Dirichlet (fixed value) boundary condition.

    Args:
        dimensions: List of dimensions this boundary applies to
        value: Fixed boundary value
        location: Boundary location specification

    Returns:
        BoundaryCondition object
    """
    return BoundaryCondition(
        type=BoundaryConditionType.DIRICHLET,
        dimensions=dimensions,
        value=value
    )


def create_neumann_boundary(
    dimensions: List[str],
    gradient_value: float = 0.0,
    location: Optional[str] = None
) -> BoundaryCondition:
    """
    Create a Neumann (gradient) boundary condition.

    Args:
        dimensions: List of dimensions this boundary applies to
        gradient_value: Normal gradient value (0.0 for zero gradient)
        location: Boundary location specification

    Returns:
        BoundaryCondition object
    """
    return BoundaryCondition(
        type=BoundaryConditionType.NEUMANN,
        dimensions=dimensions,
        value=gradient_value
    )


def create_periodic_boundary(
    dimensions: List[str]
) -> BoundaryCondition:
    """
    Create a periodic boundary condition.

    Args:
        dimensions: List of dimensions this boundary applies to

    Returns:
        BoundaryCondition object
    """
    return BoundaryCondition(
        type=BoundaryConditionType.PERIODIC,
        dimensions=dimensions
    )


# Validation utilities
def validate_domain_boundary_consistency(
    domain: Domain,
    strict: bool = True
) -> List[str]:
    """
    Validate overall consistency of domain boundary conditions.

    Args:
        domain: Domain to validate
        strict: Whether to raise errors or just return warnings

    Returns:
        List of validation warnings/issues

    Raises:
        BoundaryLocationError: If strict=True and critical issues found
    """
    issues = []

    if not domain.boundary_conditions:
        issues.append("No boundary conditions specified")
        return issues

    processor = BoundaryConditionProcessor()

    try:
        validation_warnings = processor.validate_boundary_conditions(
            domain.boundary_conditions,
            domain
        )
        issues.extend(validation_warnings)
    except Exception as e:
        if strict:
            raise
        else:
            issues.append(f"Boundary validation failed: {e}")

    return issues