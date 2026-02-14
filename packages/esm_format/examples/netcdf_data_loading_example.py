#!/usr/bin/env python3
"""
NetCDF Data Loading Example

This example demonstrates how to use the ESM Format NetCDF data loader
to load and validate atmospheric/climate data from NetCDF files.
"""

import numpy as np
import tempfile
from pathlib import Path

# Import ESM Format components
from esm_format import DataLoader, DataLoaderType, NetCDFLoader, create_data_loader

# Try to import xarray for creating example data
try:
    import xarray as xr
    XARRAY_AVAILABLE = True
except ImportError:
    print("This example requires xarray. Install with: pip install xarray netcdf4")
    XARRAY_AVAILABLE = False

def create_sample_netcdf():
    """Create a sample NetCDF file with atmospheric data."""
    if not XARRAY_AVAILABLE:
        return None

    # Create sample coordinates
    time = np.arange(24)  # 24 hours
    lat = np.linspace(-90, 90, 19)  # 10-degree resolution
    lon = np.linspace(-180, 180, 37)  # 10-degree resolution

    # Create sample atmospheric variables
    np.random.seed(42)  # For reproducible results
    temperature = 15 + 8 * np.sin(lat[None, :, None] * np.pi/180) + 2 * np.random.randn(24, 19, 37)
    precipitation = 5 * np.random.exponential(1, (24, 19, 37))
    humidity = 50 + 30 * np.random.rand(24, 19, 37)

    # Create xarray dataset with CF-compliant metadata
    ds = xr.Dataset(
        {
            "temperature": (
                ["time", "lat", "lon"],
                temperature,
                {
                    "units": "degC",
                    "long_name": "Air Temperature at 2m",
                    "standard_name": "air_temperature",
                    "_FillValue": -999.0
                }
            ),
            "precipitation": (
                ["time", "lat", "lon"],
                precipitation,
                {
                    "units": "mm/h",
                    "long_name": "Hourly Precipitation Rate",
                    "standard_name": "precipitation_flux",
                    "_FillValue": -999.0
                }
            ),
            "humidity": (
                ["time", "lat", "lon"],
                humidity,
                {
                    "units": "percent",
                    "long_name": "Relative Humidity at 2m",
                    "standard_name": "relative_humidity",
                    "_FillValue": -999.0
                }
            ),
        },
        coords={
            "time": (
                "time",
                time,
                {
                    "units": "hours since 2020-01-01T00:00:00",
                    "long_name": "Time",
                    "standard_name": "time",
                    "axis": "T"
                }
            ),
            "lat": (
                "lat",
                lat,
                {
                    "units": "degrees_north",
                    "long_name": "Latitude",
                    "standard_name": "latitude",
                    "axis": "Y"
                }
            ),
            "lon": (
                "lon",
                lon,
                {
                    "units": "degrees_east",
                    "long_name": "Longitude",
                    "standard_name": "longitude",
                    "axis": "X"
                }
            ),
        },
        attrs={
            "Conventions": "CF-1.8",
            "title": "Sample Atmospheric Data for ESM Format Example",
            "institution": "ESM Format Example",
            "source": "Simulated atmospheric data for demonstration",
            "history": f"Created by netcdf_data_loading_example.py",
            "comment": "This is synthetic data for testing ESM Format NetCDF loading"
        }
    )

    # Write to temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.nc', delete=False)
    ds.to_netcdf(temp_file.name)
    temp_file.close()

    return temp_file.name


def demonstrate_netcdf_loading():
    """Demonstrate NetCDF data loading with ESM Format."""
    if not XARRAY_AVAILABLE:
        return

    print("🌍 ESM Format NetCDF Data Loading Example")
    print("=" * 50)

    # Create sample NetCDF file
    print("\n1. Creating sample NetCDF file...")
    netcdf_path = create_sample_netcdf()
    print(f"   Created: {netcdf_path}")

    try:
        # Configure data loader
        print("\n2. Configuring NetCDF data loader...")
        data_loader_config = DataLoader(
            name="atmospheric_data",
            type=DataLoaderType.NETCDF,
            source=netcdf_path,
            format_options={
                "decode_times": True,
                "decode_cf": True,
                "mask_and_scale": True
            },
            variables=["temperature", "precipitation"]  # Load only specific variables
        )

        # Create loader using factory function
        loader = create_data_loader(data_loader_config)
        print(f"   Created loader: {type(loader).__name__}")

        # Load the data
        print("\n3. Loading NetCDF data...")
        dataset = loader.load()
        print(f"   Dataset loaded successfully!")
        print(f"   Variables: {list(dataset.data_vars.keys())}")
        print(f"   Coordinates: {list(dataset.coords.keys())}")
        print(f"   Dimensions: {dict(dataset.dims)}")

        # Validate CF conventions
        print("\n4. Validating CF conventions...")
        validation_result = loader.validate_cf_conventions()
        print(f"   CF compliant: {validation_result['cf_compliant']}")
        print(f"   Conventions: {validation_result['metadata'].get('conventions', 'None declared')}")

        if validation_result['warnings']:
            print("   Warnings:")
            for warning in validation_result['warnings']:
                print(f"     - {warning}")

        # Extract variable information
        print("\n5. Extracting variable information...")
        var_info = loader.get_variable_info()

        for var_name, info in var_info.items():
            if var_name in dataset.data_vars:  # Focus on data variables
                print(f"\n   📊 {var_name}:")
                print(f"      Shape: {info['shape']}")
                print(f"      Dimensions: {info['dimensions']}")
                print(f"      Units: {info['attributes'].get('units', 'Not specified')}")
                print(f"      Long name: {info['attributes'].get('long_name', 'Not specified')}")

                # Show coordinate info
                if 'coordinates' in info:
                    print(f"      Coordinates:")
                    for coord_name, coord_info in info['coordinates'].items():
                        units = coord_info['units'] or 'N/A'
                        print(f"        {coord_name}: {coord_info['size']} points, units={units}")

        # Demonstrate data access
        print("\n6. Accessing data...")
        temp_data = dataset.temperature
        precip_data = dataset.precipitation

        print(f"   Temperature range: {float(temp_data.min()):.1f} to {float(temp_data.max()):.1f} °C")
        print(f"   Precipitation range: {float(precip_data.min()):.2f} to {float(precip_data.max()):.2f} mm/h")

        # Show global attributes
        print("\n7. Global attributes:")
        for attr, value in dataset.attrs.items():
            print(f"   {attr}: {value}")

        # Clean up
        loader.close()
        print("\n8. Dataset closed successfully ✓")

    finally:
        # Clean up temporary file
        Path(netcdf_path).unlink()
        print(f"   Cleaned up temporary file: {netcdf_path}")


def demonstrate_error_handling():
    """Demonstrate error handling in NetCDF loading."""
    if not XARRAY_AVAILABLE:
        return

    print("\n\n🚨 Error Handling Examples")
    print("=" * 30)

    # Test 1: Non-existent file
    print("\n1. Testing non-existent file...")
    try:
        config = DataLoader(
            name="missing_file",
            type=DataLoaderType.NETCDF,
            source="/nonexistent/path/data.nc"
        )
        loader = NetCDFLoader(config)
        loader.load()
    except FileNotFoundError as e:
        print(f"   ✓ Correctly caught FileNotFoundError: {e}")

    # Test 2: Missing variables
    print("\n2. Testing missing variables...")
    netcdf_path = create_sample_netcdf()
    try:
        config = DataLoader(
            name="missing_vars",
            type=DataLoaderType.NETCDF,
            source=netcdf_path,
            variables=["nonexistent_variable"]
        )
        loader = NetCDFLoader(config)
        loader.load()
    except ValueError as e:
        print(f"   ✓ Correctly caught ValueError: {e}")
    finally:
        Path(netcdf_path).unlink()

    # Test 3: Wrong data loader type
    print("\n3. Testing wrong data loader type...")
    try:
        config = DataLoader(
            name="wrong_type",
            type=DataLoaderType.CSV,  # Wrong type
            source="test.nc"
        )
        NetCDFLoader(config)
    except ValueError as e:
        print(f"   ✓ Correctly caught ValueError: {e}")


if __name__ == "__main__":
    if XARRAY_AVAILABLE:
        demonstrate_netcdf_loading()
        demonstrate_error_handling()
        print("\n🎉 NetCDF data loading example completed!")
    else:
        print("Please install xarray and netcdf4 to run this example:")
        print("pip install xarray netcdf4")