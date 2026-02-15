#!/usr/bin/env python3
"""
Example script demonstrating HDF5 data loader functionality for ESM Format.

This example shows how to:
1. Create sample HDF5 files with hierarchical data
2. Load HDF5 data using both h5py and pytables backends
3. Navigate hierarchical data structures
4. Extract metadata and dataset information
5. Work with compressed and chunked datasets
"""

import numpy as np
import tempfile
from pathlib import Path
import h5py
from esm_format.types import DataLoader, DataLoaderType
from esm_format.data_loaders import HDF5Loader
from esm_format.data_loader_registry import create_data_loader


def create_sample_hdf5_file(filepath: str) -> None:
    """
    Create a comprehensive sample HDF5 file with hierarchical structure.

    Args:
        filepath: Path where the HDF5 file will be created
    """
    print(f"Creating sample HDF5 file: {filepath}")

    with h5py.File(filepath, 'w') as f:
        # Global attributes
        f.attrs['title'] = 'Sample Atmospheric Chemistry Data'
        f.attrs['institution'] = 'ESM Format Demo'
        f.attrs['conventions'] = 'CF-1.8'
        f.attrs['history'] = 'Created for HDF5 loader demonstration'

        # Create coordinate variables
        print("Creating coordinate variables...")
        time = np.arange(48, dtype=np.float64)  # 48 hours
        lat = np.linspace(-90, 90, 19, dtype=np.float32)  # 19 latitudes
        lon = np.linspace(-180, 180, 37, dtype=np.float32)  # 37 longitudes
        height = np.array([0, 10, 50, 100, 500, 1000], dtype=np.float32)  # 6 levels in meters

        # Time coordinate
        time_ds = f.create_dataset('time', data=time, compression='gzip')
        time_ds.attrs['units'] = 'hours since 2020-01-01 00:00:00'
        time_ds.attrs['long_name'] = 'Time'
        time_ds.attrs['standard_name'] = 'time'

        # Spatial coordinates
        lat_ds = f.create_dataset('lat', data=lat)
        lat_ds.attrs['units'] = 'degrees_north'
        lat_ds.attrs['long_name'] = 'Latitude'
        lat_ds.attrs['standard_name'] = 'latitude'

        lon_ds = f.create_dataset('lon', data=lon)
        lon_ds.attrs['units'] = 'degrees_east'
        lon_ds.attrs['long_name'] = 'Longitude'
        lon_ds.attrs['standard_name'] = 'longitude'

        height_ds = f.create_dataset('height', data=height)
        height_ds.attrs['units'] = 'm'
        height_ds.attrs['long_name'] = 'Height above surface'
        height_ds.attrs['standard_name'] = 'height'
        height_ds.attrs['positive'] = 'up'

        # Create meteorological data
        print("Creating meteorological variables...")

        # Temperature (4D: time, height, lat, lon)
        temp_data = (15 + 8 * np.random.randn(48, 6, 19, 37) -
                    height.reshape(1, -1, 1, 1) * 0.006).astype(np.float32)  # Lapse rate
        temp_ds = f.create_dataset('temperature', data=temp_data,
                                 chunks=(1, 6, 19, 37), compression='gzip', compression_opts=6)
        temp_ds.attrs['units'] = 'degC'
        temp_ds.attrs['long_name'] = 'Air Temperature'
        temp_ds.attrs['standard_name'] = 'air_temperature'
        temp_ds.attrs['valid_range'] = np.array([-50.0, 50.0])
        temp_ds.attrs['_FillValue'] = -999.0

        # Wind components (4D)
        u_wind = 10 * np.random.randn(48, 6, 19, 37).astype(np.float32)
        v_wind = 10 * np.random.randn(48, 6, 19, 37).astype(np.float32)

        u_ds = f.create_dataset('u_wind', data=u_wind,
                               chunks=(1, 6, 19, 37), compression='lzf')
        u_ds.attrs['units'] = 'm/s'
        u_ds.attrs['long_name'] = 'Eastward Wind Component'
        u_ds.attrs['standard_name'] = 'eastward_wind'

        v_ds = f.create_dataset('v_wind', data=v_wind,
                               chunks=(1, 6, 19, 37), compression='lzf')
        v_ds.attrs['units'] = 'm/s'
        v_ds.attrs['long_name'] = 'Northward Wind Component'
        v_ds.attrs['standard_name'] = 'northward_wind'

        # Surface pressure (3D: time, lat, lon)
        psurf_data = (101325 + 2000 * np.random.randn(48, 19, 37)).astype(np.float32)
        psurf_ds = f.create_dataset('surface_pressure', data=psurf_data,
                                   chunks=(1, 19, 37), compression='gzip')
        psurf_ds.attrs['units'] = 'Pa'
        psurf_ds.attrs['long_name'] = 'Surface Air Pressure'
        psurf_ds.attrs['standard_name'] = 'surface_air_pressure'

        # Create hierarchical chemistry data
        print("Creating chemistry group structure...")
        chem_group = f.create_group('chemistry')
        chem_group.attrs['description'] = 'Atmospheric chemistry data'
        chem_group.attrs['model'] = 'GEOS-Chem'

        # Species concentrations
        species_group = chem_group.create_group('species')
        species_group.attrs['units_note'] = 'All concentrations in ppbv unless noted'

        # Create species data
        species_list = ['O3', 'NO2', 'CO', 'SO2', 'NH3']
        concentrations = {}

        for species in species_list:
            # Different concentration levels for different species
            if species == 'O3':
                base_conc = 30 + 20 * np.random.rand(48, 6, 19, 37)
            elif species == 'NO2':
                base_conc = 10 + 15 * np.random.rand(48, 6, 19, 37)
            elif species == 'CO':
                base_conc = 100 + 200 * np.random.rand(48, 6, 19, 37)
            elif species == 'SO2':
                base_conc = 1 + 5 * np.random.rand(48, 6, 19, 37)
            else:  # NH3
                base_conc = 0.5 + 2 * np.random.rand(48, 6, 19, 37)

            conc_data = base_conc.astype(np.float32)

            ds = species_group.create_dataset(species, data=conc_data,
                                            chunks=(1, 6, 19, 37),
                                            compression='gzip', compression_opts=4,
                                            shuffle=True, fletcher32=True)
            ds.attrs['units'] = 'ppbv'
            ds.attrs['long_name'] = f'{species} Concentration'
            ds.attrs['molecular_weight'] = {'O3': 48.0, 'NO2': 46.0, 'CO': 28.0,
                                          'SO2': 64.1, 'NH3': 17.0}[species]
            ds.attrs['_FillValue'] = -999.0
            concentrations[species] = conc_data

        # Reaction rates
        reactions_group = chem_group.create_group('reactions')
        reactions_group.attrs['description'] = 'Key photochemical reaction rates'
        reactions_group.attrs['units'] = 's-1'

        reaction_names = ['J_O3_O1D', 'J_NO2', 'k_HO2_NO']
        for rxn in reaction_names:
            if rxn.startswith('J_'):  # Photolysis rates
                rate_data = (1e-5 * np.random.rand(48, 6, 19, 37)).astype(np.float32)
            else:  # Thermal reaction rates
                rate_data = (1e-12 * np.random.rand(48, 6, 19, 37)).astype(np.float32)

            ds = reactions_group.create_dataset(rxn, data=rate_data,
                                              chunks=(1, 6, 19, 37), compression='gzip')
            ds.attrs['units'] = 's-1' if rxn.startswith('J_') else 'cm3/molecule/s'
            ds.attrs['long_name'] = f'Rate constant for {rxn}'

        # Analysis data
        analysis_group = f.create_group('analysis')
        analysis_group.attrs['description'] = 'Derived analysis products'

        # Calculate some derived quantities
        print("Creating analysis products...")

        # Temperature statistics
        temp_stats = np.array([
            np.mean(temp_data),
            np.std(temp_data),
            np.min(temp_data),
            np.max(temp_data),
            np.percentile(temp_data, 25),
            np.percentile(temp_data, 75)
        ])

        stats_ds = analysis_group.create_dataset('temperature_statistics', data=temp_stats)
        stats_ds.attrs['description'] = 'Temperature statistics: mean, std, min, max, Q1, Q3'
        stats_ds.attrs['units'] = 'degC'
        stats_ds.attrs['statistics'] = ['mean', 'standard_deviation', 'minimum', 'maximum',
                                       'first_quartile', 'third_quartile']

        # Wind speed and direction
        wind_speed = np.sqrt(u_wind**2 + v_wind**2)
        wind_dir = np.arctan2(v_wind, u_wind) * 180 / np.pi
        wind_dir[wind_dir < 0] += 360  # Convert to 0-360 degrees

        wspd_ds = analysis_group.create_dataset('wind_speed', data=wind_speed,
                                               chunks=(1, 6, 19, 37), compression='gzip')
        wspd_ds.attrs['units'] = 'm/s'
        wspd_ds.attrs['long_name'] = 'Wind Speed'
        wspd_ds.attrs['standard_name'] = 'wind_speed'

        wdir_ds = analysis_group.create_dataset('wind_direction', data=wind_dir,
                                               chunks=(1, 6, 19, 37), compression='gzip')
        wdir_ds.attrs['units'] = 'degrees'
        wdir_ds.attrs['long_name'] = 'Wind Direction'
        wdir_ds.attrs['standard_name'] = 'wind_from_direction'
        wdir_ds.attrs['valid_range'] = np.array([0.0, 360.0])

        # Station data (1D arrays)
        station_group = f.create_group('stations')
        station_group.attrs['description'] = 'Ground-based monitoring stations'

        n_stations = 25
        station_names = np.array([f'STATION_{i+1:03d}'.encode('ascii') for i in range(n_stations)])
        station_lats = -90 + 180 * np.random.rand(n_stations).astype(np.float32)
        station_lons = -180 + 360 * np.random.rand(n_stations).astype(np.float32)
        station_elevs = 1000 * np.random.rand(n_stations).astype(np.float32)

        # String dataset
        names_ds = station_group.create_dataset('names', data=station_names)
        names_ds.attrs['description'] = 'Station identification codes'

        # Station coordinates
        slat_ds = station_group.create_dataset('latitude', data=station_lats)
        slat_ds.attrs['units'] = 'degrees_north'
        slat_ds.attrs['long_name'] = 'Station Latitude'

        slon_ds = station_group.create_dataset('longitude', data=station_lons)
        slon_ds.attrs['units'] = 'degrees_east'
        slon_ds.attrs['long_name'] = 'Station Longitude'

        selev_ds = station_group.create_dataset('elevation', data=station_elevs)
        selev_ds.attrs['units'] = 'm'
        selev_ds.attrs['long_name'] = 'Station Elevation'

        # Station time series data
        station_o3 = 20 + 30 * np.random.rand(48, n_stations).astype(np.float32)
        so3_ds = station_group.create_dataset('ozone_timeseries', data=station_o3,
                                             chunks=(48, 5), compression='gzip')
        so3_ds.attrs['units'] = 'ppbv'
        so3_ds.attrs['long_name'] = 'Surface Ozone Concentration'
        so3_ds.attrs['coordinates'] = 'time stations/latitude stations/longitude'

    print(f"Sample HDF5 file created successfully: {filepath}")


def demonstrate_hdf5_loading():
    """Demonstrate various HDF5 loading capabilities."""

    # Create temporary file
    with tempfile.NamedTemporaryFile(suffix='.h5', delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        # Create sample file
        create_sample_hdf5_file(tmp_path)

        print("\n" + "="*60)
        print("HDF5 LOADER DEMONSTRATION")
        print("="*60)

        # Example 1: Basic loading with h5py backend
        print("\n1. BASIC LOADING WITH H5PY BACKEND")
        print("-" * 40)

        config = DataLoader(
            name="atmospheric_data",
            type=DataLoaderType.HDF5,
            source=tmp_path,
            format_options={"backend": "h5py", "mode": "r"}
        )

        loader = HDF5Loader(config)
        data = loader.load()

        print(f"Loaded {len(data)} datasets and attributes")
        print("Top-level datasets:")
        for key in sorted(data.keys()):
            if not key.endswith('_attrs'):
                if hasattr(data[key], 'shape'):
                    print(f"  {key}: shape {data[key].shape}, dtype {data[key].dtype}")
                else:
                    print(f"  {key}: {type(data[key])}")

        # Example 2: Variable filtering
        print("\n2. VARIABLE FILTERING")
        print("-" * 30)

        filtered_config = DataLoader(
            name="temperature_only",
            type=DataLoaderType.HDF5,
            source=tmp_path,
            variables=["temperature", "time", "lat", "lon", "height"]
        )

        filtered_loader = HDF5Loader(filtered_config)
        filtered_data = filtered_loader.load()

        print("Filtered data includes:")
        for key in sorted(filtered_data.keys()):
            if not key.endswith('_attrs'):
                print(f"  {key}: shape {filtered_data[key].shape}")

        # Check that attributes are included
        if 'temperature_attrs' in filtered_data:
            attrs = filtered_data['temperature_attrs']
            print(f"Temperature attributes: {list(attrs.keys())}")

        # Example 3: Hierarchical data access
        print("\n3. HIERARCHICAL DATA ACCESS")
        print("-" * 35)

        hierarchical_config = DataLoader(
            name="chemistry_data",
            type=DataLoaderType.HDF5,
            source=tmp_path,
            variables=["chemistry/species/O3", "chemistry/species/NO2",
                      "analysis/temperature_statistics"]
        )

        hier_loader = HDF5Loader(hierarchical_config)
        hier_data = hier_loader.load()

        print("Hierarchical data loaded:")
        for key in hier_data.keys():
            if not key.endswith('_attrs'):
                if hasattr(hier_data[key], 'shape'):
                    print(f"  {key}: shape {hier_data[key].shape}")
                else:
                    print(f"  {key}: {hier_data[key]}")

        # Example 4: File structure exploration
        print("\n4. FILE STRUCTURE EXPLORATION")
        print("-" * 38)

        structure = loader.get_file_structure()

        def print_structure(struct, indent=0):
            """Recursively print structure."""
            prefix = "  " * indent
            for name, info in struct.items():
                if info['type'] == 'group':
                    print(f"{prefix}{name}/ (group)")
                    if 'attrs' in info and info['attrs']:
                        print(f"{prefix}  attrs: {list(info['attrs'].keys())}")
                    if 'children' in info:
                        print_structure(info['children'], indent + 1)
                else:  # dataset
                    shape_str = f"shape {info['shape']}" if 'shape' in info else ""
                    dtype_str = f"dtype {info['dtype']}" if 'dtype' in info else ""
                    compression_str = f"compression: {info['compression']}" if info.get('compression') else ""
                    print(f"{prefix}{name} ({shape_str}, {dtype_str})")
                    if compression_str:
                        print(f"{prefix}  {compression_str}")

        print("File structure:")
        print_structure(structure)

        # Example 5: Dataset information
        print("\n5. DATASET INFORMATION")
        print("-" * 28)

        # Get info for all datasets
        dataset_info = loader.get_dataset_info()

        print("Dataset compression and storage info:")
        for name, info in list(dataset_info.items())[:5]:  # Show first 5
            if 'compression' in info and info['compression']:
                size_mb = info['size_bytes'] / (1024 * 1024)
                print(f"  {name}:")
                print(f"    Size: {size_mb:.2f} MB")
                print(f"    Compression: {info['compression']}")
                if 'chunks' in info and info['chunks']:
                    print(f"    Chunks: {info['chunks']}")

        # Example 6: Specific dataset reading with slicing
        print("\n6. DATASET SLICING")
        print("-" * 20)

        # Read first 12 hours of temperature data at surface level
        temp_slice = loader.read_dataset("temperature", (slice(0, 12), slice(0, 1), slice(None), slice(None)))
        print(f"Temperature slice shape: {temp_slice.shape}")
        print(f"Temperature range: {temp_slice.min():.2f} to {temp_slice.max():.2f} °C")

        # Example 7: Group and dataset listing
        print("\n7. GROUP AND DATASET LISTING")
        print("-" * 35)

        root_groups = loader.list_groups()
        print(f"Root groups: {root_groups}")

        root_datasets = loader.list_datasets()
        print(f"Root datasets (first 5): {root_datasets[:5]}")

        # List chemistry species
        chem_species = loader.list_datasets("/chemistry/species")
        print(f"Chemistry species: {chem_species}")

        # Example 8: Factory method usage
        print("\n8. FACTORY METHOD USAGE")
        print("-" * 30)

        # Using the registry factory
        factory_config = DataLoader(
            name="factory_test",
            type=DataLoaderType.HDF5,
            source=tmp_path,
            variables=["surface_pressure"]
        )

        factory_loader = create_data_loader(factory_config)
        factory_data = factory_loader.load()

        psurf = factory_data["surface_pressure"]
        print(f"Surface pressure loaded via factory:")
        print(f"  Shape: {psurf.shape}")
        print(f"  Range: {psurf.min():.1f} to {psurf.max():.1f} Pa")

        # Cleanup loaders
        loader.close()
        filtered_loader.close()
        hier_loader.close()
        factory_loader.close()

        print("\n" + "="*60)
        print("HDF5 LOADER DEMONSTRATION COMPLETE")
        print("="*60)

    finally:
        # Cleanup
        Path(tmp_path).unlink(missing_ok=True)
        print(f"\nTemporary file {tmp_path} deleted")


def demonstrate_error_handling():
    """Demonstrate error handling capabilities."""

    print("\n" + "="*50)
    print("ERROR HANDLING DEMONSTRATION")
    print("="*50)

    # Test 1: Non-existent file
    print("\n1. Non-existent file handling:")
    try:
        config = DataLoader(
            name="missing_file",
            type=DataLoaderType.HDF5,
            source="/nonexistent/path/file.h5"
        )
        loader = HDF5Loader(config)
        loader.load()
    except FileNotFoundError as e:
        print(f"   ✓ Correctly caught: {e}")

    # Test 2: Missing variables
    print("\n2. Missing variables handling:")
    with tempfile.NamedTemporaryFile(suffix='.h5', delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        # Create simple file
        with h5py.File(tmp_path, 'w') as f:
            f.create_dataset('temperature', data=np.random.randn(10, 5))

        config = DataLoader(
            name="missing_vars",
            type=DataLoaderType.HDF5,
            source=tmp_path,
            variables=["temperature", "nonexistent_variable"]
        )

        try:
            loader = HDF5Loader(config)
            loader.load()
        except ValueError as e:
            print(f"   ✓ Correctly caught: {e}")

    finally:
        Path(tmp_path).unlink(missing_ok=True)

    # Test 3: Wrong data loader type
    print("\n3. Wrong data loader type:")
    try:
        config = DataLoader(
            name="wrong_type",
            type=DataLoaderType.NETCDF,  # Wrong type
            source="test.h5"
        )
        HDF5Loader(config)
    except ValueError as e:
        print(f"   ✓ Correctly caught: {e}")

    print("\nError handling tests completed successfully!")


if __name__ == "__main__":
    print("ESM Format HDF5 Loader Example")
    print("=" * 35)

    # Check if required libraries are available
    try:
        import h5py
        print("✓ h5py available")
    except ImportError:
        print("✗ h5py not available - please install: pip install h5py")
        exit(1)

    try:
        import tables
        print("✓ pytables available")
    except ImportError:
        print("⚠ pytables not available - only h5py backend will be used")

    # Run demonstrations
    demonstrate_hdf5_loading()
    demonstrate_error_handling()

    print("\n" + "="*60)
    print("All demonstrations completed successfully!")
    print("For more information, see the HDF5Loader class documentation.")
    print("="*60)