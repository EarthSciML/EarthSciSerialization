"""Tests for data transformation pipeline."""

import pytest
import numpy as np
from esm_format.data_transformation import (
    TransformationType, TransformationConfig, DataDescriptor, TransformationResult,
    UnitConversionTransformation, GridInterpolationTransformation, CoordinateTransformation,
    VariableTransformation, DataTransformationPipeline, create_transformation_from_config,
    build_coupling_transformation_pipeline, PINT_AVAILABLE, SCIPY_AVAILABLE
)


class TestTransformationConfig:
    """Tests for TransformationConfig dataclass."""

    def test_transformation_config_creation(self):
        """Test creating a TransformationConfig."""
        config = TransformationConfig(
            type=TransformationType.UNIT_CONVERSION,
            parameters={'source_units': 'meter', 'target_units': 'kilometer'},
            metadata={'description': 'Distance conversion'}
        )

        assert config.type == TransformationType.UNIT_CONVERSION
        assert config.parameters['source_units'] == 'meter'
        assert config.metadata['description'] == 'Distance conversion'


class TestDataDescriptor:
    """Tests for DataDescriptor dataclass."""

    def test_data_descriptor_creation(self):
        """Test creating a DataDescriptor."""
        descriptor = DataDescriptor(
            shape=(100, 200),
            units='pascal',
            coordinate_system='WGS84',
            grid_type='regular',
            spatial_dimensions=['x', 'y'],
            dtype='float64'
        )

        assert descriptor.shape == (100, 200)
        assert descriptor.units == 'pascal'
        assert descriptor.coordinate_system == 'WGS84'
        assert descriptor.grid_type == 'regular'
        assert descriptor.spatial_dimensions == ['x', 'y']
        assert descriptor.dtype == 'float64'


@pytest.mark.skipif(not PINT_AVAILABLE, reason="Pint library not available")
class TestUnitConversionTransformation:
    """Tests for unit conversion transformation."""

    def test_unit_conversion_validation_success(self):
        """Test successful unit conversion validation."""
        config = TransformationConfig(type=TransformationType.UNIT_CONVERSION)
        transformer = UnitConversionTransformation(config)

        input_desc = DataDescriptor(units='meter')
        output_desc = DataDescriptor(units='kilometer')

        is_valid, errors, warnings = transformer.validate(input_desc, output_desc)

        assert is_valid
        assert len(errors) == 0

    def test_unit_conversion_validation_incompatible(self):
        """Test unit conversion validation with incompatible units."""
        config = TransformationConfig(type=TransformationType.UNIT_CONVERSION)
        transformer = UnitConversionTransformation(config)

        input_desc = DataDescriptor(units='meter')
        output_desc = DataDescriptor(units='second')

        is_valid, errors, warnings = transformer.validate(input_desc, output_desc)

        assert not is_valid
        assert len(errors) > 0
        assert 'dimensionality mismatch' in errors[0].lower()

    def test_unit_conversion_transform_success(self):
        """Test successful unit conversion transformation."""
        config = TransformationConfig(type=TransformationType.UNIT_CONVERSION)
        transformer = UnitConversionTransformation(config)

        input_data = np.array([1000.0, 2000.0, 3000.0])  # meters
        input_desc = DataDescriptor(units='meter', shape=input_data.shape)
        target_desc = DataDescriptor(units='kilometer')

        result = transformer.transform(input_data, input_desc, target_desc)

        assert result.success
        assert np.allclose(result.transformed_data, [1.0, 2.0, 3.0])  # kilometers
        assert result.output_descriptor.units == 'kilometer'

    def test_unit_conversion_cost_estimation(self):
        """Test unit conversion cost estimation."""
        config = TransformationConfig(type=TransformationType.UNIT_CONVERSION)
        transformer = UnitConversionTransformation(config)

        input_desc = DataDescriptor(shape=(1000,))
        output_desc = DataDescriptor()

        cost = transformer.estimate_cost(input_desc, output_desc)

        assert 'memory_ratio' in cost
        assert 'time_complexity' in cost
        assert 'accuracy' in cost
        assert cost['accuracy'] == 1.0  # Exact conversion


@pytest.mark.skipif(not SCIPY_AVAILABLE, reason="SciPy library not available")
class TestGridInterpolationTransformation:
    """Tests for grid interpolation transformation."""

    def test_grid_interpolation_1d(self):
        """Test 1D grid interpolation."""
        config = TransformationConfig(
            type=TransformationType.GRID_INTERPOLATION,
            parameters={
                'method': 'linear',
                'source_coordinates': [np.array([0, 1, 2, 3, 4])],
                'target_coordinates': [np.array([0.5, 1.5, 2.5, 3.5])]
            }
        )
        transformer = GridInterpolationTransformation(config)

        # Linear function: y = 2x
        input_data = np.array([0, 2, 4, 6, 8])
        input_desc = DataDescriptor(shape=input_data.shape, spatial_dimensions=['x'])
        target_desc = DataDescriptor(spatial_dimensions=['x'])

        result = transformer.transform(input_data, input_desc, target_desc)

        assert result.success
        expected = np.array([1, 3, 5, 7])  # Interpolated values
        assert np.allclose(result.transformed_data, expected)

    def test_grid_interpolation_2d(self):
        """Test 2D grid interpolation."""
        # Create a simple 2D function: z = x + y
        x_coords = np.array([0, 1, 2])
        y_coords = np.array([0, 1, 2])
        X, Y = np.meshgrid(x_coords, y_coords, indexing='ij')
        input_data = X + Y

        config = TransformationConfig(
            type=TransformationType.GRID_INTERPOLATION,
            parameters={
                'method': 'linear',
                'source_coordinates': [x_coords, y_coords],
                'target_coordinates': [np.array([0.5, 1.5]), np.array([0.5, 1.5])]
            }
        )
        transformer = GridInterpolationTransformation(config)

        input_desc = DataDescriptor(shape=input_data.shape, spatial_dimensions=['x', 'y'])
        target_desc = DataDescriptor(spatial_dimensions=['x', 'y'])

        result = transformer.transform(input_data, input_desc, target_desc)

        assert result.success
        # At (0.5, 0.5): expected = 0.5 + 0.5 = 1.0
        # At (0.5, 1.5): expected = 0.5 + 1.5 = 2.0
        # At (1.5, 0.5): expected = 1.5 + 0.5 = 2.0
        # At (1.5, 1.5): expected = 1.5 + 1.5 = 3.0
        expected = np.array([[1.0, 2.0], [2.0, 3.0]])
        assert np.allclose(result.transformed_data, expected)

    def test_grid_interpolation_validation_missing_coords(self):
        """Test grid interpolation validation with missing coordinates."""
        config = TransformationConfig(type=TransformationType.GRID_INTERPOLATION)
        transformer = GridInterpolationTransformation(config)

        input_desc = DataDescriptor(spatial_dimensions=['x', 'y'])
        output_desc = DataDescriptor(spatial_dimensions=['x', 'y'])

        is_valid, errors, warnings = transformer.validate(input_desc, output_desc)

        assert not is_valid
        assert any('source coordinates not specified' in error.lower() for error in errors)


class TestCoordinateTransformation:
    """Tests for coordinate transformation."""

    def test_lonlat_to_meters_transform(self):
        """Test lon/lat to meters transformation."""
        config = TransformationConfig(
            type=TransformationType.COORDINATE_TRANSFORM,
            parameters={'transform_type': 'lonlat_to_meters'}
        )
        transformer = CoordinateTransformation(config)

        # Test data: [longitude, latitude] pairs in degrees
        input_data = np.array([[0.0, 0.0], [1.0, 1.0]])  # [lon, lat]
        input_desc = DataDescriptor(
            shape=input_data.shape,
            coordinate_system='WGS84_lonlat',
            units='degrees'
        )
        target_desc = DataDescriptor(coordinate_system='WGS84_meters', units='meters')

        result = transformer.transform(input_data, input_desc, target_desc)

        assert result.success
        # Should convert to x, y coordinates in meters
        assert result.transformed_data.shape == input_data.shape
        assert result.output_descriptor.units == 'meters'
        assert result.output_descriptor.coordinate_system == 'WGS84_meters'

    def test_meters_to_lonlat_transform(self):
        """Test meters to lon/lat transformation."""
        config = TransformationConfig(
            type=TransformationType.COORDINATE_TRANSFORM,
            parameters={'transform_type': 'meters_to_lonlat'}
        )
        transformer = CoordinateTransformation(config)

        # Test data: [x, y] pairs in meters
        R_EARTH = 6371000.0
        input_data = np.array([[0.0, 0.0], [R_EARTH, R_EARTH]])  # [x, y]
        input_desc = DataDescriptor(
            shape=input_data.shape,
            coordinate_system='WGS84_meters',
            units='meters'
        )
        target_desc = DataDescriptor(coordinate_system='WGS84_lonlat', units='degrees')

        result = transformer.transform(input_data, input_desc, target_desc)

        assert result.success
        # Should convert to lon, lat coordinates in degrees
        assert result.transformed_data.shape == input_data.shape
        assert result.output_descriptor.units == 'degrees'


class TestVariableTransformation:
    """Tests for variable transformation."""

    def test_identity_transformation(self):
        """Test identity transformation."""
        config = TransformationConfig(type=TransformationType.IDENTITY)
        transformer = VariableTransformation(config)

        input_data = np.array([1, 2, 3, 4, 5])
        input_desc = DataDescriptor(units='pascal')
        target_desc = DataDescriptor(units='pascal')

        result = transformer.transform(input_data, input_desc, target_desc)

        assert result.success
        assert np.array_equal(result.transformed_data, input_data)

    def test_conversion_factor_transformation(self):
        """Test conversion factor transformation."""
        config = TransformationConfig(
            type=TransformationType.CONVERSION_FACTOR,
            parameters={'factor': 2.5}
        )
        transformer = VariableTransformation(config)

        input_data = np.array([2, 4, 6])
        input_desc = DataDescriptor(units='meter')
        target_desc = DataDescriptor(units='meter')

        result = transformer.transform(input_data, input_desc, target_desc)

        assert result.success
        expected = np.array([5, 10, 15])  # 2.5 * input
        assert np.array_equal(result.transformed_data, expected)

    def test_additive_transformation(self):
        """Test additive transformation."""
        config = TransformationConfig(
            type=TransformationType.ADDITIVE,
            parameters={'existing_value': 10.0}
        )
        transformer = VariableTransformation(config)

        input_data = np.array([1, 2, 3])
        input_desc = DataDescriptor(units='pascal')
        target_desc = DataDescriptor(units='pascal')

        result = transformer.transform(input_data, input_desc, target_desc)

        assert result.success
        expected = np.array([11, 12, 13])  # 10 + input
        assert np.array_equal(result.transformed_data, expected)

    def test_multiplicative_transformation(self):
        """Test multiplicative transformation."""
        config = TransformationConfig(
            type=TransformationType.MULTIPLICATIVE,
            parameters={'existing_value': 3.0}
        )
        transformer = VariableTransformation(config)

        input_data = np.array([2, 4, 6])
        input_desc = DataDescriptor()
        target_desc = DataDescriptor()

        result = transformer.transform(input_data, input_desc, target_desc)

        assert result.success
        expected = np.array([6, 12, 18])  # 3 * input
        assert np.array_equal(result.transformed_data, expected)

    def test_conversion_factor_validation_missing_factor(self):
        """Test validation failure when conversion factor is missing."""
        config = TransformationConfig(type=TransformationType.CONVERSION_FACTOR)
        transformer = VariableTransformation(config)

        input_desc = DataDescriptor()
        output_desc = DataDescriptor()

        is_valid, errors, warnings = transformer.validate(input_desc, output_desc)

        assert not is_valid
        assert any('conversion factor not specified' in error.lower() for error in errors)


class TestDataTransformationPipeline:
    """Tests for data transformation pipeline."""

    @pytest.mark.skipif(not PINT_AVAILABLE, reason="Pint library not available")
    def test_simple_pipeline_unit_conversion_and_scaling(self):
        """Test pipeline with unit conversion followed by scaling."""
        pipeline = DataTransformationPipeline()

        # Add unit conversion
        unit_config = TransformationConfig(type=TransformationType.UNIT_CONVERSION)
        pipeline.add_transformation(UnitConversionTransformation(unit_config))

        # Add scaling
        scale_config = TransformationConfig(
            type=TransformationType.CONVERSION_FACTOR,
            parameters={'factor': 2.0}
        )
        pipeline.add_transformation(VariableTransformation(scale_config))

        # Test data: 1000 meters -> 1 kilometer -> 2 kilometers (scaled)
        input_data = np.array([1000.0])
        input_desc = DataDescriptor(units='meter')
        target_desc = DataDescriptor(units='kilometer')

        result = pipeline.execute_pipeline(input_data, input_desc, target_desc)

        assert result.success
        # 1000 meters -> 1 kilometer -> 1 * 2.0 = 2.0 kilometers
        # But since the factor is applied after unit conversion, we get 2.0
        assert np.allclose(result.transformed_data, [2.0])  # 1 km * 2
        assert len(result.applied_transformations) == 2

    def test_empty_pipeline(self):
        """Test pipeline with no transformations."""
        pipeline = DataTransformationPipeline()

        input_data = np.array([1, 2, 3])
        input_desc = DataDescriptor()
        target_desc = DataDescriptor()

        result = pipeline.execute_pipeline(input_data, input_desc, target_desc)

        assert not result.success
        assert 'no transformations in pipeline' in result.errors[0].lower()

    def test_pipeline_validation(self):
        """Test pipeline validation."""
        pipeline = DataTransformationPipeline()

        # Add a valid transformation
        config = TransformationConfig(type=TransformationType.IDENTITY)
        pipeline.add_transformation(VariableTransformation(config))

        input_desc = DataDescriptor()
        output_desc = DataDescriptor()

        is_valid, errors, warnings = pipeline.validate_pipeline(input_desc, output_desc)

        assert is_valid
        assert len(errors) == 0

    def test_pipeline_cost_estimation(self):
        """Test pipeline cost estimation."""
        pipeline = DataTransformationPipeline()

        # Add transformations
        config1 = TransformationConfig(type=TransformationType.IDENTITY)
        config2 = TransformationConfig(
            type=TransformationType.CONVERSION_FACTOR,
            parameters={'factor': 1.5}
        )
        pipeline.add_transformation(VariableTransformation(config1))
        pipeline.add_transformation(VariableTransformation(config2))

        input_desc = DataDescriptor(shape=(1000,))
        output_desc = DataDescriptor()

        cost = pipeline.estimate_total_cost(input_desc, output_desc)

        assert 'memory_ratio' in cost
        assert 'time_complexity' in cost
        assert 'accuracy' in cost


class TestCreateTransformationFromConfig:
    """Tests for transformation factory function."""

    def test_create_unit_conversion_transformation(self):
        """Test creating unit conversion transformation."""
        config = TransformationConfig(type=TransformationType.UNIT_CONVERSION)
        transformation = create_transformation_from_config(config)

        assert isinstance(transformation, UnitConversionTransformation)

    def test_create_variable_transformation(self):
        """Test creating variable transformation."""
        config = TransformationConfig(type=TransformationType.ADDITIVE)
        transformation = create_transformation_from_config(config)

        assert isinstance(transformation, VariableTransformation)

    @pytest.mark.skipif(not SCIPY_AVAILABLE, reason="SciPy library not available")
    def test_create_grid_interpolation_transformation(self):
        """Test creating grid interpolation transformation."""
        config = TransformationConfig(type=TransformationType.GRID_INTERPOLATION)
        transformation = create_transformation_from_config(config)

        assert isinstance(transformation, GridInterpolationTransformation)

    def test_create_coordinate_transformation(self):
        """Test creating coordinate transformation."""
        config = TransformationConfig(type=TransformationType.COORDINATE_TRANSFORM)
        transformation = create_transformation_from_config(config)

        assert isinstance(transformation, CoordinateTransformation)

    def test_create_unsupported_transformation(self):
        """Test error when creating unsupported transformation."""
        # Create a fake transformation type by directly setting enum value
        config = TransformationConfig(type='unsupported_type')

        with pytest.raises(ValueError, match="Unsupported transformation type"):
            create_transformation_from_config(config)


class TestBuildCouplingTransformationPipeline:
    """Tests for building coupling transformation pipeline from ESM entries."""

    @pytest.mark.skipif(not PINT_AVAILABLE, reason="Pint library not available")
    def test_build_pipeline_with_unit_conversion(self):
        """Test building pipeline with unit conversion."""
        coupling_entry = {
            'type': 'variable_map',
            'transform': 'identity'
        }

        source_desc = DataDescriptor(units='meter')
        target_desc = DataDescriptor(units='kilometer')

        pipeline = build_coupling_transformation_pipeline(coupling_entry, source_desc, target_desc)

        # Should have unit conversion transformation
        assert len(pipeline.transformations) > 0
        assert isinstance(pipeline.transformations[0], UnitConversionTransformation)

    def test_build_pipeline_with_coordinate_transform(self):
        """Test building pipeline with coordinate transformation."""
        coupling_entry = {
            'type': 'variable_map',
            'transform': 'identity'
        }

        source_desc = DataDescriptor(coordinate_system='lonlat')
        target_desc = DataDescriptor(coordinate_system='meters')

        pipeline = build_coupling_transformation_pipeline(coupling_entry, source_desc, target_desc)

        # Should have coordinate transformation
        assert len(pipeline.transformations) > 0
        assert any(isinstance(t, CoordinateTransformation) for t in pipeline.transformations)

    def test_build_pipeline_with_variable_transform(self):
        """Test building pipeline with variable transformation."""
        coupling_entry = {
            'type': 'variable_map',
            'transform': 'conversion_factor',
            'transform_parameters': {'factor': 3.14}
        }

        source_desc = DataDescriptor(units='pascal')
        target_desc = DataDescriptor(units='pascal')

        pipeline = build_coupling_transformation_pipeline(coupling_entry, source_desc, target_desc)

        # Should have variable transformation
        assert len(pipeline.transformations) > 0
        var_transform = None
        for t in pipeline.transformations:
            if isinstance(t, VariableTransformation):
                var_transform = t
                break

        assert var_transform is not None
        assert var_transform.config.type == TransformationType.CONVERSION_FACTOR

    @pytest.mark.skipif(not SCIPY_AVAILABLE, reason="SciPy library not available")
    def test_build_pipeline_with_interpolation(self):
        """Test building pipeline with grid interpolation."""
        coupling_entry = {
            'type': 'interpolated',
            'transform': 'identity',
            'source_coordinates': [np.array([0, 1, 2])],
            'target_coordinates': [np.array([0.5, 1.5])],
            'interpolation_method': 'linear'
        }

        source_desc = DataDescriptor(grid_type='source_grid')
        target_desc = DataDescriptor(grid_type='target_grid')

        pipeline = build_coupling_transformation_pipeline(coupling_entry, source_desc, target_desc)

        # Should have grid interpolation transformation
        assert any(isinstance(t, GridInterpolationTransformation) for t in pipeline.transformations)


class TestIntegrationScenarios:
    """Integration tests for complete transformation scenarios."""

    @pytest.mark.skipif(not PINT_AVAILABLE, reason="Pint library not available")
    def test_atmospheric_pressure_coupling_scenario(self):
        """Test complete atmospheric pressure coupling scenario."""
        # Scenario: Couple surface pressure from weather model (hPa)
        # to atmospheric chemistry model (Pa)
        coupling_entry = {
            'type': 'variable_map',
            'from': 'WeatherModel.surface_pressure',
            'to': 'ChemistryModel.pressure',
            'transform': 'identity'
        }

        source_desc = DataDescriptor(
            shape=(100, 100),
            units='hectopascal',
            coordinate_system='WGS84',
            grid_type='regular'
        )

        target_desc = DataDescriptor(
            shape=(100, 100),
            units='pascal',
            coordinate_system='WGS84',
            grid_type='regular'
        )

        pipeline = build_coupling_transformation_pipeline(coupling_entry, source_desc, target_desc)

        # Test with realistic pressure data (1013.25 hPa = 101325 Pa)
        input_data = np.full((100, 100), 1013.25)

        result = pipeline.execute_pipeline(input_data, source_desc, target_desc)

        assert result.success
        assert np.allclose(result.transformed_data, 101325.0)  # Converted to pascals

    @pytest.mark.skipif(not SCIPY_AVAILABLE, reason="SciPy library not available")
    def test_ocean_wind_coupling_with_interpolation(self):
        """Test ocean-atmosphere wind coupling with grid interpolation."""
        # Scenario: Couple wind velocity from coarse atmospheric grid
        # to fine ocean surface grid
        source_coords_x = np.array([0, 10, 20])  # Coarse grid
        source_coords_y = np.array([0, 10, 20])
        target_coords_x = np.array([0, 5, 10, 15, 20])  # Fine grid
        target_coords_y = np.array([0, 5, 10, 15, 20])

        coupling_entry = {
            'type': 'interpolated',
            'transform': 'identity',
            'source_coordinates': [source_coords_x, source_coords_y],
            'target_coordinates': [target_coords_x, target_coords_y],
            'interpolation_method': 'linear'
        }

        source_desc = DataDescriptor(
            shape=(3, 3),
            units='meter/second',
            grid_type='coarse_atm_grid',
            spatial_dimensions=['x', 'y']
        )

        target_desc = DataDescriptor(
            shape=(5, 5),
            units='meter/second',
            grid_type='fine_ocean_grid',
            spatial_dimensions=['x', 'y']
        )

        pipeline = build_coupling_transformation_pipeline(coupling_entry, source_desc, target_desc)

        # Create test wind field: u = x/10, where x varies along first dimension
        # At coordinates [0,10,20] for x and [0,10,20] for y, we want u = x/10
        X, Y = np.meshgrid(source_coords_x, source_coords_y, indexing='ij')
        input_data = X / 10.0  # Simple linear wind field where u depends on x-coordinate

        result = pipeline.execute_pipeline(input_data, source_desc, target_desc)

        assert result.success
        assert result.transformed_data.shape == (5, 5)
        # Check interpolation result along x direction (row 0, which has y=0)
        # At y=0: x coordinates [0,5,10,15,20] should give u = [0,0.5,1.0,1.5,2.0]
        # But since we're interpolating in y as well, need to check the right slice
        # The result varies in the first dimension (x), so check along first dimension
        expected_x_values = np.array([0, 0.5, 1.0, 1.5, 2.0])  # target_coords_x / 10
        assert np.allclose(result.transformed_data[:, 0], expected_x_values)