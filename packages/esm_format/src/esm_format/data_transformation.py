"""
Data transformation pipeline for ESM Format coupling interfaces.

This module implements the comprehensive data transformation pipeline for
coupling heterogeneous Earth system model components, including:
- Unit conversion
- Grid remapping and interpolation
- Coordinate transformations
- Data type conversions
- Variable transformation semantics (additive, multiplicative, etc.)

The pipeline provides both validation and execution capabilities for transformations
specified in ESM coupling entries.
"""

from typing import Dict, List, Set, Optional, Tuple, Union, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import numpy as np
from abc import ABC, abstractmethod

from .types import CouplingEntry, CouplingType

# Optional import for unit handling
try:
    from pint import UnitRegistry, DimensionalityError, Quantity, Unit
    PINT_AVAILABLE = True
    ureg = UnitRegistry()
except ImportError:
    PINT_AVAILABLE = False
    ureg = None
    logging.warning("Pint not available. Unit conversion features will be disabled.")

# Optional import for spatial interpolation
try:
    import scipy.spatial
    import scipy.interpolate
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logging.warning("SciPy not available. Grid interpolation features will be disabled.")


class TransformationType(Enum):
    """Types of data transformations supported in coupling pipeline."""
    # Variable mapping transforms (ESM Spec Section 10.4)
    PARAM_TO_VAR = "param_to_var"
    IDENTITY = "identity"
    ADDITIVE = "additive"
    MULTIPLICATIVE = "multiplicative"
    CONVERSION_FACTOR = "conversion_factor"
    REPLACEMENT = "replacement"

    # Spatial transformations
    GRID_INTERPOLATION = "grid_interpolation"
    COORDINATE_TRANSFORM = "coordinate_transform"
    SPATIAL_AGGREGATION = "spatial_aggregation"

    # Temporal transformations
    TEMPORAL_INTERPOLATION = "temporal_interpolation"
    TEMPORAL_AGGREGATION = "temporal_aggregation"

    # Data type conversions
    UNIT_CONVERSION = "unit_conversion"
    TYPE_CONVERSION = "type_conversion"


@dataclass
class TransformationConfig:
    """Configuration for a single transformation operation."""
    type: TransformationType
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataDescriptor:
    """Description of data characteristics for transformation validation."""
    shape: Optional[Tuple[int, ...]] = None
    units: Optional[str] = None
    coordinate_system: Optional[str] = None
    grid_type: Optional[str] = None
    temporal_info: Optional[Dict[str, Any]] = None
    dtype: Optional[str] = None
    spatial_dimensions: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransformationResult:
    """Result of a data transformation operation."""
    success: bool
    transformed_data: Optional[Any] = None
    output_descriptor: Optional[DataDescriptor] = None
    applied_transformations: List[TransformationConfig] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    performance_info: Dict[str, Any] = field(default_factory=dict)


class DataTransformation(ABC):
    """Abstract base class for data transformation operations."""

    def __init__(self, config: TransformationConfig):
        """Initialize transformation with configuration."""
        self.config = config
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    @abstractmethod
    def validate(self, input_descriptor: DataDescriptor,
                 output_descriptor: DataDescriptor) -> Tuple[bool, List[str], List[str]]:
        """
        Validate that this transformation can be applied.

        Args:
            input_descriptor: Description of input data characteristics
            output_descriptor: Description of expected output data characteristics

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        pass

    @abstractmethod
    def transform(self, data: Any, input_descriptor: DataDescriptor,
                  target_descriptor: DataDescriptor) -> TransformationResult:
        """
        Apply the transformation to input data.

        Args:
            data: Input data to transform
            input_descriptor: Description of input data
            target_descriptor: Description of target output format

        Returns:
            TransformationResult containing success status and output data
        """
        pass

    @abstractmethod
    def estimate_cost(self, input_descriptor: DataDescriptor,
                      output_descriptor: DataDescriptor) -> Dict[str, float]:
        """
        Estimate computational cost of applying this transformation.

        Returns:
            Dictionary containing cost estimates (memory, time, etc.)
        """
        pass


class UnitConversionTransformation(DataTransformation):
    """Unit conversion using Pint library."""

    def validate(self, input_descriptor: DataDescriptor,
                 output_descriptor: DataDescriptor) -> Tuple[bool, List[str], List[str]]:
        """Validate unit conversion compatibility."""
        errors = []
        warnings = []

        if not PINT_AVAILABLE:
            errors.append("Pint library not available for unit conversion")
            return False, errors, warnings

        input_units = input_descriptor.units
        output_units = output_descriptor.units

        if not input_units:
            errors.append("Input units not specified for unit conversion")

        if not output_units:
            errors.append("Output units not specified for unit conversion")

        if errors:
            return False, errors, warnings

        try:
            # Test conversion compatibility
            input_qty = ureg.Quantity(1.0, input_units)
            input_qty.to(output_units)

            # Check if conversion factor is reasonable
            conversion_factor = float(input_qty.to(output_units).magnitude)
            if abs(conversion_factor) < 1e-15 or abs(conversion_factor) > 1e15:
                warnings.append(f"Large unit conversion factor: {conversion_factor}")

        except DimensionalityError as e:
            errors.append(f"Unit dimensionality mismatch: {e}")
            return False, errors, warnings
        except Exception as e:
            errors.append(f"Unit conversion validation error: {e}")
            return False, errors, warnings

        return True, errors, warnings

    def transform(self, data: Any, input_descriptor: DataDescriptor,
                  target_descriptor: DataDescriptor) -> TransformationResult:
        """Apply unit conversion."""
        result = TransformationResult(success=False)

        if not PINT_AVAILABLE:
            result.errors.append("Pint library not available")
            return result

        try:
            input_units = input_descriptor.units
            output_units = target_descriptor.units

            # Create quantity and convert
            input_qty = ureg.Quantity(data, input_units)
            converted_qty = input_qty.to(output_units)

            # Extract converted data
            result.transformed_data = converted_qty.magnitude

            # Update output descriptor
            result.output_descriptor = DataDescriptor(
                shape=input_descriptor.shape,
                units=output_units,
                coordinate_system=input_descriptor.coordinate_system,
                grid_type=input_descriptor.grid_type,
                temporal_info=input_descriptor.temporal_info,
                dtype=input_descriptor.dtype,
                spatial_dimensions=input_descriptor.spatial_dimensions
            )

            result.applied_transformations.append(self.config)
            result.success = True

            # Add performance info
            result.performance_info['conversion_factor'] = float(converted_qty.magnitude / data) if np.any(data != 0) else 0.0

        except Exception as e:
            result.errors.append(f"Unit conversion failed: {e}")

        return result

    def estimate_cost(self, input_descriptor: DataDescriptor,
                      output_descriptor: DataDescriptor) -> Dict[str, float]:
        """Estimate cost of unit conversion (generally very low)."""
        data_size = 1.0
        if input_descriptor.shape:
            data_size = np.prod(input_descriptor.shape)

        return {
            'memory_ratio': 2.0,  # Need to hold input and output temporarily
            'time_complexity': data_size * 1e-8,  # Very fast operation
            'accuracy': 1.0  # Exact conversion
        }


class GridInterpolationTransformation(DataTransformation):
    """Grid interpolation and remapping using SciPy."""

    def validate(self, input_descriptor: DataDescriptor,
                 output_descriptor: DataDescriptor) -> Tuple[bool, List[str], List[str]]:
        """Validate grid interpolation requirements."""
        errors = []
        warnings = []

        if not SCIPY_AVAILABLE:
            errors.append("SciPy library not available for grid interpolation")
            return False, errors, warnings

        # Check that spatial information is available
        if not input_descriptor.spatial_dimensions:
            warnings.append("Input spatial dimensions not specified")

        if not output_descriptor.spatial_dimensions:
            warnings.append("Output spatial dimensions not specified")

        # Check interpolation method
        method = self.config.parameters.get('method', 'linear')
        valid_methods = ['linear', 'cubic', 'nearest', 'slinear', 'quadratic']
        if method not in valid_methods:
            errors.append(f"Invalid interpolation method '{method}'. Valid methods: {valid_methods}")

        # Check for coordinate information
        if not self.config.parameters.get('source_coordinates'):
            errors.append("Source coordinates not specified for interpolation")

        if not self.config.parameters.get('target_coordinates'):
            errors.append("Target coordinates not specified for interpolation")

        return len(errors) == 0, errors, warnings

    def transform(self, data: Any, input_descriptor: DataDescriptor,
                  target_descriptor: DataDescriptor) -> TransformationResult:
        """Apply grid interpolation."""
        result = TransformationResult(success=False)

        if not SCIPY_AVAILABLE:
            result.errors.append("SciPy library not available")
            return result

        try:
            source_coords = self.config.parameters['source_coordinates']
            target_coords = self.config.parameters['target_coordinates']
            method = self.config.parameters.get('method', 'linear')

            # Handle different dimensionalities
            if len(source_coords) == 1:
                # 1D interpolation
                interpolator = scipy.interpolate.interp1d(
                    source_coords[0], data, kind=method, bounds_error=False, fill_value='extrapolate'
                )
                result.transformed_data = interpolator(target_coords[0])

            elif len(source_coords) == 2:
                # 2D interpolation
                if method in ['linear', 'cubic']:
                    interpolator = scipy.interpolate.RegularGridInterpolator(
                        source_coords, data, method=method, bounds_error=False, fill_value=None
                    )
                    # Create target grid
                    target_grid = np.meshgrid(*target_coords, indexing='ij')
                    target_points = np.stack([g.ravel() for g in target_grid], axis=-1)
                    interpolated = interpolator(target_points)
                    result.transformed_data = interpolated.reshape([len(tc) for tc in target_coords])
                else:
                    # Use griddata for other methods
                    source_points = np.array(np.meshgrid(*source_coords, indexing='ij')).reshape(len(source_coords), -1).T
                    target_grid = np.meshgrid(*target_coords, indexing='ij')
                    target_points = np.stack([g.ravel() for g in target_grid], axis=-1)

                    interpolated = scipy.interpolate.griddata(
                        source_points, data.ravel(), target_points, method=method
                    )
                    result.transformed_data = interpolated.reshape([len(tc) for tc in target_coords])
            else:
                result.errors.append(f"Interpolation not implemented for {len(source_coords)}D data")
                return result

            # Update output descriptor
            result.output_descriptor = DataDescriptor(
                shape=result.transformed_data.shape,
                units=input_descriptor.units,  # Units preserved
                coordinate_system=target_descriptor.coordinate_system or input_descriptor.coordinate_system,
                grid_type=target_descriptor.grid_type or 'interpolated',
                temporal_info=input_descriptor.temporal_info,
                dtype=str(result.transformed_data.dtype),
                spatial_dimensions=target_descriptor.spatial_dimensions
            )

            result.applied_transformations.append(self.config)
            result.success = True

            # Add performance info
            result.performance_info['interpolation_method'] = method
            result.performance_info['input_size'] = data.size if hasattr(data, 'size') else len(data)
            result.performance_info['output_size'] = result.transformed_data.size

        except Exception as e:
            result.errors.append(f"Grid interpolation failed: {e}")

        return result

    def estimate_cost(self, input_descriptor: DataDescriptor,
                      output_descriptor: DataDescriptor) -> Dict[str, float]:
        """Estimate cost of grid interpolation."""
        input_size = 1.0
        output_size = 1.0

        if input_descriptor.shape:
            input_size = np.prod(input_descriptor.shape)
        if output_descriptor.shape:
            output_size = np.prod(output_descriptor.shape)

        method = self.config.parameters.get('method', 'linear')
        method_cost = {'linear': 1.0, 'cubic': 2.0, 'nearest': 0.5}.get(method, 1.0)

        return {
            'memory_ratio': 2.5,  # Input + output + interpolation structures
            'time_complexity': method_cost * (input_size + output_size) * 1e-6,
            'accuracy': {'linear': 0.9, 'cubic': 0.95, 'nearest': 0.7}.get(method, 0.8)
        }


class CoordinateTransformation(DataTransformation):
    """Coordinate system transformations."""

    def validate(self, input_descriptor: DataDescriptor,
                 output_descriptor: DataDescriptor) -> Tuple[bool, List[str], List[str]]:
        """Validate coordinate transformation."""
        errors = []
        warnings = []

        input_crs = input_descriptor.coordinate_system
        output_crs = output_descriptor.coordinate_system

        if not input_crs:
            errors.append("Input coordinate system not specified")
        if not output_crs:
            errors.append("Output coordinate system not specified")

        # Check transformation type
        transform_type = self.config.parameters.get('transform_type')
        if not transform_type:
            errors.append("Coordinate transformation type not specified")

        supported_transforms = ['lonlat_to_meters', 'meters_to_lonlat', 'projection']
        if transform_type not in supported_transforms:
            warnings.append(f"Coordinate transformation '{transform_type}' may not be fully supported")

        return len(errors) == 0, errors, warnings

    def transform(self, data: Any, input_descriptor: DataDescriptor,
                  target_descriptor: DataDescriptor) -> TransformationResult:
        """Apply coordinate transformation."""
        result = TransformationResult(success=False)

        try:
            transform_type = self.config.parameters['transform_type']

            if transform_type == 'lonlat_to_meters':
                # Simple spherical Earth approximation
                if len(data.shape) >= 2 and data.shape[-1] == 2:  # Assuming last dimension is [lon, lat]
                    R_EARTH = 6371000.0  # meters
                    lon_rad = np.radians(data[..., 0])
                    lat_rad = np.radians(data[..., 1])

                    # Convert to meters (simplified, assumes small areas)
                    x = R_EARTH * lon_rad * np.cos(np.mean(lat_rad))
                    y = R_EARTH * lat_rad

                    result.transformed_data = np.stack([x, y], axis=-1)
                else:
                    result.errors.append("Invalid data shape for lon/lat coordinates")
                    return result

            elif transform_type == 'meters_to_lonlat':
                # Inverse transformation
                if len(data.shape) >= 2 and data.shape[-1] == 2:  # Assuming last dimension is [x, y]
                    R_EARTH = 6371000.0  # meters
                    x = data[..., 0]
                    y = data[..., 1]

                    lat_rad = y / R_EARTH
                    lon_rad = x / (R_EARTH * np.cos(np.mean(lat_rad)))

                    lon = np.degrees(lon_rad)
                    lat = np.degrees(lat_rad)

                    result.transformed_data = np.stack([lon, lat], axis=-1)
                else:
                    result.errors.append("Invalid data shape for x/y coordinates")
                    return result
            else:
                result.errors.append(f"Coordinate transformation '{transform_type}' not implemented")
                return result

            # Update output descriptor
            result.output_descriptor = DataDescriptor(
                shape=result.transformed_data.shape,
                units=target_descriptor.units or ("meters" if "to_meters" in transform_type else "degrees"),
                coordinate_system=target_descriptor.coordinate_system,
                grid_type=input_descriptor.grid_type,
                temporal_info=input_descriptor.temporal_info,
                dtype=str(result.transformed_data.dtype),
                spatial_dimensions=target_descriptor.spatial_dimensions or input_descriptor.spatial_dimensions
            )

            result.applied_transformations.append(self.config)
            result.success = True

        except Exception as e:
            result.errors.append(f"Coordinate transformation failed: {e}")

        return result

    def estimate_cost(self, input_descriptor: DataDescriptor,
                      output_descriptor: DataDescriptor) -> Dict[str, float]:
        """Estimate cost of coordinate transformation."""
        data_size = 1.0
        if input_descriptor.shape:
            data_size = np.prod(input_descriptor.shape)

        return {
            'memory_ratio': 2.0,  # Input + output
            'time_complexity': data_size * 1e-7,  # Mathematical operations
            'accuracy': 0.95  # Depends on transformation complexity
        }


class VariableTransformation(DataTransformation):
    """ESM variable transformations (additive, multiplicative, etc.)."""

    def validate(self, input_descriptor: DataDescriptor,
                 output_descriptor: DataDescriptor) -> Tuple[bool, List[str], List[str]]:
        """Validate variable transformation."""
        errors = []
        warnings = []

        transform_type = self.config.type

        if transform_type == TransformationType.CONVERSION_FACTOR:
            factor = self.config.parameters.get('factor')
            if factor is None:
                errors.append("Conversion factor not specified")
            elif not isinstance(factor, (int, float)):
                errors.append("Conversion factor must be numeric")

        elif transform_type == TransformationType.ADDITIVE:
            # Check unit compatibility for addition
            if input_descriptor.units != output_descriptor.units:
                warnings.append("Unit mismatch in additive transformation may require prior conversion")

        elif transform_type == TransformationType.MULTIPLICATIVE:
            # Multiplicative transformations can change units
            pass

        return len(errors) == 0, errors, warnings

    def transform(self, data: Any, input_descriptor: DataDescriptor,
                  target_descriptor: DataDescriptor) -> TransformationResult:
        """Apply variable transformation."""
        result = TransformationResult(success=False)

        try:
            transform_type = self.config.type

            if transform_type == TransformationType.IDENTITY:
                result.transformed_data = data

            elif transform_type == TransformationType.CONVERSION_FACTOR:
                factor = self.config.parameters['factor']
                result.transformed_data = data * factor

            elif transform_type == TransformationType.ADDITIVE:
                # For additive, we need the existing value to add to
                existing_value = self.config.parameters.get('existing_value', 0.0)
                result.transformed_data = existing_value + data

            elif transform_type == TransformationType.MULTIPLICATIVE:
                # For multiplicative, we need the existing value to multiply
                existing_value = self.config.parameters.get('existing_value', 1.0)
                result.transformed_data = existing_value * data

            elif transform_type == TransformationType.REPLACEMENT:
                # Replacement is just identity (replace existing with new)
                result.transformed_data = data

            else:
                result.errors.append(f"Variable transformation type '{transform_type}' not implemented")
                return result

            # Update output descriptor
            result.output_descriptor = DataDescriptor(
                shape=getattr(result.transformed_data, 'shape', input_descriptor.shape),
                units=target_descriptor.units or input_descriptor.units,
                coordinate_system=input_descriptor.coordinate_system,
                grid_type=input_descriptor.grid_type,
                temporal_info=input_descriptor.temporal_info,
                dtype=str(getattr(result.transformed_data, 'dtype', type(result.transformed_data).__name__)),
                spatial_dimensions=input_descriptor.spatial_dimensions
            )

            result.applied_transformations.append(self.config)
            result.success = True

        except Exception as e:
            result.errors.append(f"Variable transformation failed: {e}")

        return result

    def estimate_cost(self, input_descriptor: DataDescriptor,
                      output_descriptor: DataDescriptor) -> Dict[str, float]:
        """Estimate cost of variable transformation."""
        data_size = 1.0
        if input_descriptor.shape:
            data_size = np.prod(input_descriptor.shape)

        return {
            'memory_ratio': 1.5,  # Minimal extra memory
            'time_complexity': data_size * 1e-9,  # Very fast arithmetic operations
            'accuracy': 1.0  # Exact arithmetic
        }


class DataTransformationPipeline:
    """Pipeline for chaining multiple data transformations."""

    def __init__(self):
        """Initialize empty transformation pipeline."""
        self.transformations: List[DataTransformation] = []
        self.logger = logging.getLogger("DataTransformationPipeline")

    def add_transformation(self, transformation: DataTransformation) -> None:
        """Add a transformation to the pipeline."""
        self.transformations.append(transformation)

    def clear(self) -> None:
        """Clear all transformations from the pipeline."""
        self.transformations.clear()

    def validate_pipeline(self, input_descriptor: DataDescriptor,
                          output_descriptor: DataDescriptor) -> Tuple[bool, List[str], List[str]]:
        """Validate the entire transformation pipeline."""
        all_errors = []
        all_warnings = []

        current_descriptor = input_descriptor

        for i, transformation in enumerate(self.transformations):
            # For intermediate steps, use a generic descriptor
            if i == len(self.transformations) - 1:
                target_descriptor = output_descriptor
            else:
                # Use current descriptor as intermediate target
                target_descriptor = current_descriptor

            is_valid, errors, warnings = transformation.validate(current_descriptor, target_descriptor)

            if not is_valid:
                all_errors.extend([f"Step {i+1}: {error}" for error in errors])

            all_warnings.extend([f"Step {i+1}: {warning}" for warning in warnings])

            # Update descriptor for next step (simplified)
            # In practice, would need to properly propagate descriptor changes
            # current_descriptor = update_descriptor_after_transformation(current_descriptor, transformation)

        return len(all_errors) == 0, all_errors, all_warnings

    def execute_pipeline(self, data: Any, input_descriptor: DataDescriptor,
                         target_descriptor: DataDescriptor) -> TransformationResult:
        """Execute the complete transformation pipeline."""
        overall_result = TransformationResult(success=False)
        overall_result.applied_transformations = []

        if not self.transformations:
            overall_result.errors.append("No transformations in pipeline")
            return overall_result

        current_data = data
        current_descriptor = input_descriptor

        for i, transformation in enumerate(self.transformations):
            # Determine target descriptor for this step
            if i == len(self.transformations) - 1:
                step_target_descriptor = target_descriptor
            else:
                # For intermediate steps, we need to determine appropriate intermediate targets
                # For now, let the transformation determine what it should produce
                # This is a simplified approach - in practice might need more sophisticated logic
                if isinstance(transformation, UnitConversionTransformation):
                    # For unit conversion, use final target units
                    step_target_descriptor = target_descriptor
                else:
                    # For other transformations, use current descriptor
                    step_target_descriptor = current_descriptor

            # Apply transformation
            step_result = transformation.transform(current_data, current_descriptor, step_target_descriptor)

            if not step_result.success:
                overall_result.errors.extend([f"Step {i+1}: {error}" for error in step_result.errors])
                overall_result.warnings.extend([f"Step {i+1}: {warning}" for warning in step_result.warnings])
                return overall_result

            # Update for next iteration
            current_data = step_result.transformed_data
            current_descriptor = step_result.output_descriptor or current_descriptor

            # Accumulate transformation info
            overall_result.applied_transformations.extend(step_result.applied_transformations)
            overall_result.warnings.extend(step_result.warnings)

        # Set final results
        overall_result.success = True
        overall_result.transformed_data = current_data
        overall_result.output_descriptor = current_descriptor

        return overall_result

    def estimate_total_cost(self, input_descriptor: DataDescriptor,
                            output_descriptor: DataDescriptor) -> Dict[str, float]:
        """Estimate total cost of pipeline execution."""
        total_cost = {
            'memory_ratio': 1.0,
            'time_complexity': 0.0,
            'accuracy': 1.0
        }

        current_descriptor = input_descriptor

        for transformation in self.transformations:
            step_cost = transformation.estimate_cost(current_descriptor, output_descriptor)

            # Accumulate costs (simplified model)
            total_cost['memory_ratio'] = max(total_cost['memory_ratio'], step_cost.get('memory_ratio', 1.0))
            total_cost['time_complexity'] += step_cost.get('time_complexity', 0.0)
            total_cost['accuracy'] *= step_cost.get('accuracy', 1.0)

        return total_cost


def create_transformation_from_config(config: TransformationConfig) -> DataTransformation:
    """Factory function to create transformation instances from configuration."""
    transform_type = config.type

    if transform_type == TransformationType.UNIT_CONVERSION:
        return UnitConversionTransformation(config)
    elif transform_type == TransformationType.GRID_INTERPOLATION:
        return GridInterpolationTransformation(config)
    elif transform_type == TransformationType.COORDINATE_TRANSFORM:
        return CoordinateTransformation(config)
    elif transform_type in [TransformationType.IDENTITY, TransformationType.ADDITIVE,
                           TransformationType.MULTIPLICATIVE, TransformationType.CONVERSION_FACTOR,
                           TransformationType.REPLACEMENT]:
        return VariableTransformation(config)
    else:
        raise ValueError(f"Unsupported transformation type: {transform_type}")


def build_coupling_transformation_pipeline(coupling_entry: Dict[str, Any],
                                          source_descriptor: DataDescriptor,
                                          target_descriptor: DataDescriptor) -> DataTransformationPipeline:
    """
    Build a transformation pipeline from an ESM coupling entry.

    Args:
        coupling_entry: ESM coupling specification
        source_descriptor: Description of source data
        target_descriptor: Description of target data

    Returns:
        Configured DataTransformationPipeline
    """
    pipeline = DataTransformationPipeline()

    # Handle different coupling types
    coupling_type = coupling_entry.get('type', 'direct')
    transform = coupling_entry.get('transform', 'identity')

    # 1. Unit conversion (if needed)
    if source_descriptor.units and target_descriptor.units and source_descriptor.units != target_descriptor.units:
        unit_config = TransformationConfig(
            type=TransformationType.UNIT_CONVERSION,
            parameters={'source_units': source_descriptor.units, 'target_units': target_descriptor.units}
        )
        pipeline.add_transformation(UnitConversionTransformation(unit_config))

    # 2. Coordinate transformation (if needed)
    if (source_descriptor.coordinate_system and target_descriptor.coordinate_system and
        source_descriptor.coordinate_system != target_descriptor.coordinate_system):
        coord_config = TransformationConfig(
            type=TransformationType.COORDINATE_TRANSFORM,
            parameters={
                'transform_type': _infer_coordinate_transform_type(
                    source_descriptor.coordinate_system,
                    target_descriptor.coordinate_system
                )
            }
        )
        pipeline.add_transformation(CoordinateTransformation(coord_config))

    # 3. Grid interpolation (if needed for different grids)
    if coupling_type == 'interpolated' or _requires_grid_interpolation(source_descriptor, target_descriptor):
        if 'source_coordinates' in coupling_entry and 'target_coordinates' in coupling_entry:
            interp_config = TransformationConfig(
                type=TransformationType.GRID_INTERPOLATION,
                parameters={
                    'method': coupling_entry.get('interpolation_method', 'linear'),
                    'source_coordinates': coupling_entry['source_coordinates'],
                    'target_coordinates': coupling_entry['target_coordinates']
                }
            )
            pipeline.add_transformation(GridInterpolationTransformation(interp_config))

    # 4. Variable transformation semantics
    if transform != 'identity':
        var_transform_type = _map_transform_to_type(transform)
        var_config = TransformationConfig(
            type=var_transform_type,
            parameters=coupling_entry.get('transform_parameters', {})
        )
        pipeline.add_transformation(VariableTransformation(var_config))

    return pipeline


def _infer_coordinate_transform_type(source_crs: str, target_crs: str) -> str:
    """Infer coordinate transformation type from source and target CRS."""
    if 'lonlat' in source_crs.lower() and 'meter' in target_crs.lower():
        return 'lonlat_to_meters'
    elif 'meter' in source_crs.lower() and 'lonlat' in target_crs.lower():
        return 'meters_to_lonlat'
    else:
        return 'projection'


def _requires_grid_interpolation(source_desc: DataDescriptor, target_desc: DataDescriptor) -> bool:
    """Determine if grid interpolation is required based on data descriptors."""
    # Simple heuristic: different grid types or spatial dimensions suggest interpolation needed
    if source_desc.grid_type != target_desc.grid_type:
        return True
    if source_desc.spatial_dimensions != target_desc.spatial_dimensions:
        return True
    if source_desc.shape != target_desc.shape:
        return True
    return False


def _map_transform_to_type(transform_name: str) -> TransformationType:
    """Map ESM transform names to transformation types."""
    mapping = {
        'param_to_var': TransformationType.PARAM_TO_VAR,
        'identity': TransformationType.IDENTITY,
        'additive': TransformationType.ADDITIVE,
        'multiplicative': TransformationType.MULTIPLICATIVE,
        'conversion_factor': TransformationType.CONVERSION_FACTOR,
        'replacement': TransformationType.REPLACEMENT
    }

    return mapping.get(transform_name, TransformationType.IDENTITY)