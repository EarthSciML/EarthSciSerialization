#!/usr/bin/env python3
"""
Demonstration of coupling data transformation pipeline.

This script showcases the comprehensive data transformation pipeline
for coupling heterogeneous Earth system model components, including:
- Unit conversion between different measurement systems
- Grid remapping and interpolation between different spatial grids
- Coordinate transformations between different coordinate systems
- Variable transformation semantics (additive, multiplicative, etc.)

The pipeline provides both validation and execution capabilities for transformations
specified in ESM coupling entries according to the ESM specification.
"""

import numpy as np
import matplotlib.pyplot as plt
from esm_format.data_transformation import (
    TransformationType, TransformationConfig, DataDescriptor,
    UnitConversionTransformation, GridInterpolationTransformation,
    CoordinateTransformation, VariableTransformation,
    DataTransformationPipeline, build_coupling_transformation_pipeline,
    PINT_AVAILABLE, SCIPY_AVAILABLE
)


def demo_unit_conversion():
    """Demonstrate unit conversion between different measurement systems."""
    print("=" * 60)
    print("UNIT CONVERSION DEMONSTRATION")
    print("=" * 60)
    print()

    if not PINT_AVAILABLE:
        print("⚠️  Pint library not available - skipping unit conversion demo")
        return

    # Create transformation config
    config = TransformationConfig(type=TransformationType.UNIT_CONVERSION)
    transformer = UnitConversionTransformation(config)

    # Test cases: atmospheric pressure conversions
    test_cases = [
        {
            'name': 'Surface Pressure: hPa → Pa',
            'data': np.array([1013.25, 1020.5, 995.8]),  # hectopascals
            'input_desc': DataDescriptor(units='hectopascal'),
            'target_desc': DataDescriptor(units='pascal'),
            'description': 'Convert weather model surface pressure to chemistry model units'
        },
        {
            'name': 'Temperature: Celsius → Kelvin',
            'data': np.array([15.0, 25.0, -5.0]),  # degrees Celsius
            'input_desc': DataDescriptor(units='celsius'),
            'target_desc': DataDescriptor(units='kelvin'),
            'description': 'Convert ocean temperature to atmospheric temperature units'
        },
        {
            'name': 'Wind Speed: m/s → km/h',
            'data': np.array([5.0, 10.0, 15.0]),  # meters per second
            'input_desc': DataDescriptor(units='meter/second'),
            'target_desc': DataDescriptor(units='kilometer/hour'),
            'description': 'Convert atmospheric wind speed to oceanographic units'
        }
    ]

    for case in test_cases:
        print(f"📊 {case['name']}")
        print(f"   {case['description']}")
        print(f"   Input data: {case['data']} [{case['input_desc'].units}]")

        result = transformer.transform(case['data'], case['input_desc'], case['target_desc'])

        if result.success:
            print(f"   ✅ Converted: {result.transformed_data} [{result.output_descriptor.units}]")
            if 'conversion_factor' in result.performance_info:
                print(f"   ⚙️  Conversion factor: {result.performance_info['conversion_factor']:.6f}")
        else:
            print(f"   ❌ Failed: {', '.join(result.errors)}")
        print()


def demo_grid_interpolation():
    """Demonstrate grid interpolation between different spatial resolutions."""
    print("=" * 60)
    print("GRID INTERPOLATION DEMONSTRATION")
    print("=" * 60)
    print()

    if not SCIPY_AVAILABLE:
        print("⚠️  SciPy library not available - skipping grid interpolation demo")
        return

    # Scenario: Ocean-Atmosphere coupling
    # Coarse atmospheric model (50 km resolution) → Fine ocean model (10 km resolution)

    print("🌊 Ocean-Atmosphere Coupling: Wind Stress Transfer")
    print("   Scenario: Transfer wind stress from atmospheric model (50km) to ocean model (10km)")
    print()

    # Define grids
    atm_x = np.array([0, 50, 100, 150, 200])  # km, coarse atmospheric grid
    atm_y = np.array([0, 50, 100, 150, 200])  # km

    ocean_x = np.array([0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100])  # km, fine ocean grid
    ocean_y = np.array([0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100])  # km

    # Create synthetic wind stress data (τ = f(x,y))
    # Simulate a wind pattern: τ = sin(x/100) * cos(y/100)
    X_atm, Y_atm = np.meshgrid(atm_x, atm_y, indexing='ij')
    wind_stress_atm = 0.1 * np.sin(X_atm / 100.0) * np.cos(Y_atm / 100.0)  # N/m²

    print(f"   📏 Atmospheric grid: {len(atm_x)}×{len(atm_y)} points (50 km resolution)")
    print(f"   📏 Ocean grid: {len(ocean_x)}×{len(ocean_y)} points (10 km resolution)")
    print(f"   🌪️  Wind stress range: {wind_stress_atm.min():.4f} to {wind_stress_atm.max():.4f} N/m²")
    print()

    # Configure interpolation
    config = TransformationConfig(
        type=TransformationType.GRID_INTERPOLATION,
        parameters={
            'method': 'linear',
            'source_coordinates': [atm_x, atm_y],
            'target_coordinates': [ocean_x, ocean_y]
        }
    )

    transformer = GridInterpolationTransformation(config)

    input_desc = DataDescriptor(
        shape=wind_stress_atm.shape,
        units='newton/meter**2',
        grid_type='atmospheric_grid',
        spatial_dimensions=['x', 'y']
    )

    target_desc = DataDescriptor(
        shape=(len(ocean_x), len(ocean_y)),
        units='newton/meter**2',
        grid_type='ocean_grid',
        spatial_dimensions=['x', 'y']
    )

    # Apply interpolation
    result = transformer.transform(wind_stress_atm, input_desc, target_desc)

    if result.success:
        print("   ✅ Interpolation successful!")
        print(f"   📏 Output grid: {result.transformed_data.shape}")
        print(f"   🌪️  Interpolated wind stress range: {result.transformed_data.min():.4f} to {result.transformed_data.max():.4f} N/m²")

        # Show interpolation quality
        error_estimate = abs(result.transformed_data.max() - wind_stress_atm.max()) / abs(wind_stress_atm.max())
        print(f"   📈 Maximum value preservation: {(1-error_estimate)*100:.1f}%")

        return result.transformed_data, ocean_x, ocean_y
    else:
        print(f"   ❌ Interpolation failed: {', '.join(result.errors)}")
        return None, None, None


def demo_coordinate_transformation():
    """Demonstrate coordinate system transformations."""
    print("=" * 60)
    print("COORDINATE TRANSFORMATION DEMONSTRATION")
    print("=" * 60)
    print()

    print("🗺️  Geographic Coordinate Transformations")
    print("   Scenario: Convert between longitude/latitude and metric coordinates")
    print()

    # Test data: Representative geographic points
    geographic_points = np.array([
        [-74.0060, 40.7128],  # New York City
        [-118.2437, 34.0522], # Los Angeles
        [2.3522, 48.8566],    # Paris
        [139.6917, 35.6895]   # Tokyo
    ])

    city_names = ['New York', 'Los Angeles', 'Paris', 'Tokyo']

    print("   📍 Test locations:")
    for i, (name, coords) in enumerate(zip(city_names, geographic_points)):
        print(f"      {name}: {coords[0]:.4f}°, {coords[1]:.4f}°")
    print()

    # Longitude/Latitude → Meters transformation
    config = TransformationConfig(
        type=TransformationType.COORDINATE_TRANSFORM,
        parameters={'transform_type': 'lonlat_to_meters'}
    )

    transformer = CoordinateTransformation(config)

    input_desc = DataDescriptor(
        shape=geographic_points.shape,
        coordinate_system='WGS84_lonlat',
        units='degrees'
    )

    target_desc = DataDescriptor(
        coordinate_system='WGS84_meters',
        units='meters'
    )

    result = transformer.transform(geographic_points, input_desc, target_desc)

    if result.success:
        print("   ✅ Coordinate transformation successful!")
        print("   📐 Converted to metric coordinates:")
        for i, (name, coords) in enumerate(zip(city_names, result.transformed_data)):
            print(f"      {name}: {coords[0]:.0f} m, {coords[1]:.0f} m")

        # Demonstrate inverse transformation
        print()
        print("   🔄 Testing inverse transformation (meters → degrees)")

        inverse_config = TransformationConfig(
            type=TransformationType.COORDINATE_TRANSFORM,
            parameters={'transform_type': 'meters_to_lonlat'}
        )

        inverse_transformer = CoordinateTransformation(inverse_config)

        inverse_result = inverse_transformer.transform(
            result.transformed_data,
            result.output_descriptor,
            input_desc
        )

        if inverse_result.success:
            print("   ✅ Inverse transformation successful!")
            max_error = np.max(np.abs(inverse_result.transformed_data - geographic_points))
            print(f"   📏 Round-trip error: {max_error:.6f} degrees")
        else:
            print(f"   ❌ Inverse transformation failed: {', '.join(inverse_result.errors)}")
    else:
        print(f"   ❌ Coordinate transformation failed: {', '.join(result.errors)}")


def demo_variable_transformations():
    """Demonstrate ESM variable transformation semantics."""
    print("=" * 60)
    print("VARIABLE TRANSFORMATION DEMONSTRATION")
    print("=" * 60)
    print()

    print("🔄 ESM Variable Transformation Semantics")
    print("   Testing different coupling transformation types from ESM specification")
    print()

    # Test data representing emission rates
    base_emissions = np.array([1.5, 2.3, 3.1, 1.8])  # kg/m²/s
    print(f"   📊 Base emission rates: {base_emissions} kg/m²/s")
    print()

    transformations = [
        {
            'name': 'Identity',
            'config': TransformationConfig(type=TransformationType.IDENTITY),
            'description': 'Direct pass-through (no transformation)'
        },
        {
            'name': 'Conversion Factor',
            'config': TransformationConfig(
                type=TransformationType.CONVERSION_FACTOR,
                parameters={'factor': 3600}  # Convert /s to /hour
            ),
            'description': 'Scale by factor (e.g., unit conversion /s → /hour)'
        },
        {
            'name': 'Additive',
            'config': TransformationConfig(
                type=TransformationType.ADDITIVE,
                parameters={'existing_value': 0.5}  # Background emission
            ),
            'description': 'Add to existing background value'
        },
        {
            'name': 'Multiplicative',
            'config': TransformationConfig(
                type=TransformationType.MULTIPLICATIVE,
                parameters={'existing_value': 2.0}  # Amplification factor
            ),
            'description': 'Multiply existing value by input'
        }
    ]

    for transform_info in transformations:
        print(f"   🔧 {transform_info['name']} Transformation")
        print(f"      {transform_info['description']}")

        transformer = VariableTransformation(transform_info['config'])

        input_desc = DataDescriptor(units='kg/m**2/second')
        target_desc = DataDescriptor(units='kg/m**2/second')

        result = transformer.transform(base_emissions, input_desc, target_desc)

        if result.success:
            print(f"      ✅ Result: {result.transformed_data}")

            # Calculate change
            if transform_info['name'] == 'Identity':
                change = "No change"
            else:
                percent_change = ((result.transformed_data - base_emissions) / base_emissions * 100)
                change = f"Average change: {np.mean(percent_change):+.1f}%"
            print(f"      📈 {change}")
        else:
            print(f"      ❌ Failed: {', '.join(result.errors)}")
        print()


def demo_complete_coupling_pipeline():
    """Demonstrate a complete coupling transformation pipeline."""
    print("=" * 60)
    print("COMPLETE COUPLING PIPELINE DEMONSTRATION")
    print("=" * 60)
    print()

    if not PINT_AVAILABLE or not SCIPY_AVAILABLE:
        print("⚠️  Required libraries not available - skipping complete pipeline demo")
        return

    print("🌍 Atmospheric Chemistry - Meteorology Coupling Example")
    print("   Scenario: Couple temperature from weather model to chemistry model")
    print("   Pipeline: Unit conversion + Grid interpolation + Variable scaling")
    print()

    # Define the coupling scenario
    coupling_entry = {
        'type': 'variable_map',
        'from': 'WeatherModel.surface_temperature',
        'to': 'ChemistryModel.temperature',
        'transform': 'conversion_factor',
        'transform_parameters': {'factor': 1.02},  # Slight adjustment for local effects
        'source_coordinates': [np.array([0, 25, 50]), np.array([0, 25, 50])],  # Coarse weather grid
        'target_coordinates': [np.array([0, 10, 20, 30, 40, 50]), np.array([0, 10, 20, 30, 40, 50])],  # Fine chemistry grid
        'interpolation_method': 'linear'
    }

    # Source: Weather model data
    source_desc = DataDescriptor(
        shape=(3, 3),
        units='celsius',
        coordinate_system='WGS84',
        grid_type='weather_grid',
        spatial_dimensions=['x', 'y']
    )

    # Target: Chemistry model requirements
    target_desc = DataDescriptor(
        shape=(6, 6),
        units='kelvin',
        coordinate_system='WGS84',
        grid_type='chemistry_grid',
        spatial_dimensions=['x', 'y']
    )

    # Create synthetic temperature field (15°C base + spatial variation)
    x_coords, y_coords = coupling_entry['source_coordinates']
    X, Y = np.meshgrid(x_coords, y_coords, indexing='ij')
    temperature_celsius = 15.0 + 5.0 * np.sin(X/50.0) * np.cos(Y/50.0)  # Realistic temperature pattern

    print(f"   🌡️  Source temperature (weather model): {temperature_celsius.min():.1f}°C to {temperature_celsius.max():.1f}°C")
    print(f"   📏 Source grid: {source_desc.shape} ({source_desc.grid_type})")
    print(f"   📏 Target grid: {target_desc.shape} ({target_desc.grid_type})")
    print()

    # Build and execute transformation pipeline
    pipeline = build_coupling_transformation_pipeline(coupling_entry, source_desc, target_desc)

    print(f"   🔧 Pipeline steps: {len(pipeline.transformations)}")
    for i, transform in enumerate(pipeline.transformations):
        print(f"      {i+1}. {transform.__class__.__name__}")
    print()

    # Execute the complete pipeline
    result = pipeline.execute_pipeline(temperature_celsius, source_desc, target_desc)

    if result.success:
        print("   ✅ Complete pipeline execution successful!")
        temp_kelvin = result.transformed_data
        print(f"   🌡️  Final temperature (chemistry model): {temp_kelvin.min():.1f}K to {temp_kelvin.max():.1f}K")
        print(f"   📏 Output grid shape: {temp_kelvin.shape}")
        print(f"   🔧 Transformations applied: {len(result.applied_transformations)}")

        # Verify the transformations
        expected_temp_k = (temperature_celsius + 273.15) * 1.02  # Manual calculation
        center_point_source = temperature_celsius[1, 1]  # Center point of source grid
        center_point_result = temp_kelvin[2, 2]  # Roughly corresponding point in target grid
        expected_center = (center_point_source + 273.15) * 1.02

        print(f"   🎯 Verification (center point):")
        print(f"      Source: {center_point_source:.2f}°C")
        print(f"      Result: {center_point_result:.2f}K")
        print(f"      Expected: {expected_center:.2f}K")
        print(f"      Error: {abs(center_point_result - expected_center):.4f}K")

        if result.warnings:
            print("   ⚠️  Warnings:")
            for warning in result.warnings:
                print(f"      {warning}")

        return result.transformed_data

    else:
        print("   ❌ Pipeline execution failed!")
        for error in result.errors:
            print(f"      ❌ {error}")
        return None


def demo_cost_estimation():
    """Demonstrate transformation cost estimation for performance planning."""
    print("=" * 60)
    print("TRANSFORMATION COST ESTIMATION")
    print("=" * 60)
    print()

    print("⚙️  Performance Planning for Large-Scale Coupling")
    print("   Estimating computational costs for different transformation scenarios")
    print()

    # Define different grid sizes for cost comparison
    grid_scenarios = [
        {'name': 'Regional (100×100)', 'shape': (100, 100)},
        {'name': 'Continental (500×500)', 'shape': (500, 500)},
        {'name': 'Global (1000×1000)', 'shape': (1000, 1000)},
        {'name': 'High-res Global (2000×2000)', 'shape': (2000, 2000)}
    ]

    # Different transformation types
    transformations = [
        {
            'name': 'Unit Conversion',
            'config': TransformationConfig(type=TransformationType.UNIT_CONVERSION)
        },
        {
            'name': 'Variable Scaling',
            'config': TransformationConfig(
                type=TransformationType.CONVERSION_FACTOR,
                parameters={'factor': 2.0}
            )
        }
    ]

    if SCIPY_AVAILABLE:
        transformations.append({
            'name': 'Grid Interpolation',
            'config': TransformationConfig(
                type=TransformationType.GRID_INTERPOLATION,
                parameters={'method': 'linear'}
            )
        })

    print("   📊 Cost Estimates by Grid Size:")
    print()

    for scenario in grid_scenarios:
        print(f"   📏 {scenario['name']} Grid:")

        input_desc = DataDescriptor(shape=scenario['shape'])
        output_desc = DataDescriptor(shape=scenario['shape'])

        for transform_info in transformations:
            if transform_info['name'] == 'Unit Conversion' and not PINT_AVAILABLE:
                continue
            if transform_info['name'] == 'Grid Interpolation' and not SCIPY_AVAILABLE:
                continue

            try:
                if transform_info['name'] == 'Unit Conversion':
                    transformer = UnitConversionTransformation(transform_info['config'])
                elif transform_info['name'] == 'Grid Interpolation':
                    transformer = GridInterpolationTransformation(transform_info['config'])
                else:
                    transformer = VariableTransformation(transform_info['config'])

                cost = transformer.estimate_cost(input_desc, output_desc)

                data_size = np.prod(scenario['shape']) if scenario['shape'] else 1
                memory_mb = (data_size * 8 * cost.get('memory_ratio', 1.0)) / (1024*1024)  # Assuming float64
                time_ms = cost.get('time_complexity', 0) * 1000
                accuracy = cost.get('accuracy', 1.0)

                print(f"      {transform_info['name']:.<20} Memory: {memory_mb:>8.1f} MB  Time: {time_ms:>8.2f} ms  Accuracy: {accuracy:>5.1%}")

            except Exception as e:
                print(f"      {transform_info['name']:.<20} Error: {str(e)}")

        print()


def main():
    """Run all demonstrations."""
    print("🌍 ESM FORMAT DATA TRANSFORMATION PIPELINE DEMONSTRATION")
    print()
    print("This demonstration showcases the comprehensive data transformation pipeline")
    print("for coupling heterogeneous Earth system model components according to")
    print("the ESM Format specification.")
    print()

    # Check library availability
    print("📋 Library Availability Check:")
    print(f"   {'✅' if PINT_AVAILABLE else '❌'} Pint (unit conversions): {'Available' if PINT_AVAILABLE else 'Not available'}")
    print(f"   {'✅' if SCIPY_AVAILABLE else '❌'} SciPy (grid interpolation): {'Available' if SCIPY_AVAILABLE else 'Not available'}")
    print()

    # Run demonstrations
    demo_unit_conversion()
    demo_grid_interpolation()
    demo_coordinate_transformation()
    demo_variable_transformations()
    demo_complete_coupling_pipeline()
    demo_cost_estimation()

    print("=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("=" * 60)
    print()
    print("🎉 The ESM Format coupling data transformation pipeline provides:")
    print("   • Comprehensive unit conversion using Pint")
    print("   • Flexible grid interpolation using SciPy")
    print("   • Coordinate system transformations")
    print("   • ESM variable transformation semantics")
    print("   • Performance cost estimation")
    print("   • Robust validation and error handling")
    print()
    print("🔗 This enables seamless coupling between heterogeneous Earth system")
    print("   model components with different units, grids, and coordinate systems.")


if __name__ == "__main__":
    main()