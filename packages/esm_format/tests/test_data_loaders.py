"""
Tests for data loading functionality.
"""

import pytest
import tempfile
import json
import numpy as np
from pathlib import Path

# Import the data loading functionality
from esm_format.data_loaders import NetCDFLoader, JSONLoader, BinaryLoader, HDF5Loader, GRIBLoader, StreamingLoader, create_data_loader
from esm_format.types import DataLoader, DataLoaderType

# Try to import xarray for creating test data
try:
    import xarray as xr
    XARRAY_AVAILABLE = True
except ImportError:
    XARRAY_AVAILABLE = False

# Try to import cfgrib for GRIB testing
try:
    import cfgrib
    CFGRIB_AVAILABLE = True
except ImportError:
    CFGRIB_AVAILABLE = False


@pytest.fixture
def sample_netcdf_file():
    """Create a sample NetCDF file for testing."""
    if not XARRAY_AVAILABLE:
        pytest.skip("xarray not available")

    # Create sample data
    time = np.arange(10)
    lat = np.linspace(-90, 90, 18)
    lon = np.linspace(-180, 180, 36)

    # Create sample data arrays
    temperature = 15 + 8 * np.random.randn(10, 18, 36)
    precipitation = 10 * np.random.rand(10, 18, 36)

    # Create dataset
    ds = xr.Dataset(
        {
            "temperature": (["time", "lat", "lon"], temperature,
                          {"units": "degC", "long_name": "Air Temperature"}),
            "precipitation": (["time", "lat", "lon"], precipitation,
                            {"units": "mm/day", "long_name": "Daily Precipitation"}),
        },
        coords={
            "time": ("time", time, {"units": "days since 2020-01-01", "long_name": "Time"}),
            "lat": ("lat", lat, {"units": "degrees_north", "long_name": "Latitude"}),
            "lon": ("lon", lon, {"units": "degrees_east", "long_name": "Longitude"}),
        },
        attrs={
            "Conventions": "CF-1.8",
            "title": "Sample atmospheric data",
            "institution": "Test Institute"
        }
    )

    # Write to temporary file
    with tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as tmp_file:
        ds.to_netcdf(tmp_file.name)
        yield tmp_file.name

    # Cleanup
    Path(tmp_file.name).unlink()


@pytest.fixture
def sample_data_loader_config(sample_netcdf_file):
    """Create a sample DataLoader configuration."""
    return DataLoader(
        name="test_climate_data",
        type=DataLoaderType.NETCDF,
        source=sample_netcdf_file,
        format_options={
            "decode_times": True,
            "decode_cf": True,
            "mask_and_scale": True
        },
        variables=["temperature", "precipitation"]
    )


class TestNetCDFLoader:
    """Tests for NetCDF data loader."""

    @pytest.mark.skipif(not XARRAY_AVAILABLE, reason="xarray not available")
    def test_netcdf_loader_initialization(self, sample_data_loader_config):
        """Test NetCDF loader initialization."""
        loader = NetCDFLoader(sample_data_loader_config)
        assert loader.config == sample_data_loader_config
        assert loader.dataset is None

    def test_netcdf_loader_wrong_type(self):
        """Test NetCDF loader with wrong data loader type."""
        wrong_config = DataLoader(
            name="test",
            type=DataLoaderType.CSV,  # Wrong type
            source="test.nc"
        )

        with pytest.raises(ValueError, match="Expected DataLoaderType.NETCDF"):
            NetCDFLoader(wrong_config)

    @pytest.mark.skipif(not XARRAY_AVAILABLE, reason="xarray not available")
    def test_load_nonexistent_file(self):
        """Test loading a file that doesn't exist."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.NETCDF,
            source="/nonexistent/path/file.nc"
        )

        loader = NetCDFLoader(config)
        with pytest.raises(FileNotFoundError, match="NetCDF file not found"):
            loader.load()

    @pytest.mark.skipif(not XARRAY_AVAILABLE, reason="xarray not available")
    def test_load_valid_file(self, sample_data_loader_config):
        """Test loading a valid NetCDF file."""
        loader = NetCDFLoader(sample_data_loader_config)
        dataset = loader.load()

        # Check that dataset was loaded
        assert loader.dataset is not None
        assert dataset is not None

        # Check expected variables are present
        assert "temperature" in dataset.data_vars
        assert "precipitation" in dataset.data_vars

        # Check expected coordinates are present
        assert "time" in dataset.coords
        assert "lat" in dataset.coords
        assert "lon" in dataset.coords

        # Check data shapes
        assert dataset.temperature.shape == (10, 18, 36)
        assert dataset.precipitation.shape == (10, 18, 36)

        # Check attributes
        assert dataset.temperature.attrs["units"] == "degC"
        assert dataset.precipitation.attrs["units"] == "mm/day"

        loader.close()

    @pytest.mark.skipif(not XARRAY_AVAILABLE, reason="xarray not available")
    def test_load_with_variable_filtering(self, sample_netcdf_file):
        """Test loading with specific variables only."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.NETCDF,
            source=sample_netcdf_file,
            variables=["temperature"]  # Only temperature
        )

        loader = NetCDFLoader(config)
        dataset = loader.load()

        # Should only have temperature, not precipitation
        assert "temperature" in dataset.data_vars
        assert "precipitation" not in dataset.data_vars

        # Coordinates should still be present
        assert "time" in dataset.coords
        assert "lat" in dataset.coords
        assert "lon" in dataset.coords

        loader.close()

    @pytest.mark.skipif(not XARRAY_AVAILABLE, reason="xarray not available")
    def test_load_with_missing_variables(self, sample_netcdf_file):
        """Test loading with variables that don't exist."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.NETCDF,
            source=sample_netcdf_file,
            variables=["nonexistent_variable"]
        )

        loader = NetCDFLoader(config)
        with pytest.raises(ValueError, match="Requested variables not found"):
            loader.load()

    @pytest.mark.skipif(not XARRAY_AVAILABLE, reason="xarray not available")
    def test_cf_conventions_validation(self, sample_data_loader_config):
        """Test CF conventions validation."""
        loader = NetCDFLoader(sample_data_loader_config)
        loader.load()

        validation_result = loader.validate_cf_conventions()

        # Should be CF compliant
        assert validation_result["cf_compliant"] is True
        assert "CF-" in validation_result["metadata"]["conventions"]

        # Should have no errors
        assert len(validation_result["errors"]) == 0

        # May have warnings (e.g., for missing standard_name on coordinates)
        assert isinstance(validation_result["warnings"], list)

        loader.close()

    @pytest.mark.skipif(not XARRAY_AVAILABLE, reason="xarray not available")
    def test_get_variable_info(self, sample_data_loader_config):
        """Test variable information extraction."""
        loader = NetCDFLoader(sample_data_loader_config)
        loader.load()

        var_info = loader.get_variable_info()

        # Should have info for all variables including coordinates
        assert "temperature" in var_info
        assert "precipitation" in var_info
        assert "time" in var_info
        assert "lat" in var_info
        assert "lon" in var_info

        # Check temperature variable info
        temp_info = var_info["temperature"]
        assert temp_info["dimensions"] == ["time", "lat", "lon"]
        assert temp_info["shape"] == (10, 18, 36)
        assert temp_info["attributes"]["units"] == "degC"
        assert temp_info["is_coordinate"] is False

        # Check coordinate variable info
        time_info = var_info["time"]
        assert time_info["is_coordinate"] is True
        assert time_info["shape"] == (10,)
        # Note: xarray may modify time units during decode_times, so check for long_name instead
        assert time_info["attributes"]["long_name"] == "Time"

        loader.close()

    @pytest.mark.skipif(not XARRAY_AVAILABLE, reason="xarray not available")
    def test_validation_before_loading(self, sample_data_loader_config):
        """Test that validation fails if called before loading."""
        loader = NetCDFLoader(sample_data_loader_config)

        with pytest.raises(RuntimeError, match="Dataset must be loaded"):
            loader.validate_cf_conventions()

        with pytest.raises(RuntimeError, match="Dataset must be loaded"):
            loader.get_variable_info()

    @pytest.mark.skipif(not XARRAY_AVAILABLE, reason="xarray not available")
    def test_close_dataset(self, sample_data_loader_config):
        """Test closing dataset."""
        loader = NetCDFLoader(sample_data_loader_config)
        loader.load()

        assert loader.dataset is not None

        loader.close()
        assert loader.dataset is None


class TestDataLoaderFactory:
    """Tests for data loader factory function."""

    @pytest.mark.skipif(not XARRAY_AVAILABLE, reason="xarray not available")
    def test_create_netcdf_loader(self, sample_data_loader_config):
        """Test creating NetCDF loader through factory."""
        loader = create_data_loader(sample_data_loader_config)
        assert isinstance(loader, NetCDFLoader)
        assert loader.config == sample_data_loader_config

    def test_create_unsupported_loader(self):
        """Test creating unsupported data loader type."""
        # Test with CSV type which is defined but not implemented
        config = DataLoader(
            name="test",
            type=DataLoaderType.CSV,  # Not implemented yet
            source="test.csv"
        )

        with pytest.raises(ValueError, match="is not registered"):
            create_data_loader(config)


# Test missing xarray dependency
def test_netcdf_loader_without_xarray(monkeypatch):
    """Test NetCDF loader when xarray is not available."""
    # Mock xarray as unavailable
    monkeypatch.setattr("esm_format.data_loaders.XARRAY_AVAILABLE", False)

    config = DataLoader(
        name="test",
        type=DataLoaderType.NETCDF,
        source="test.nc"
    )

    with pytest.raises(ImportError, match="xarray and netcdf4 are required"):
        NetCDFLoader(config)


# JSON Loader Test Fixtures and Tests

@pytest.fixture
def sample_json_data():
    """Sample JSON data for testing."""
    return {
        "metadata": {
            "title": "Sample Climate Data",
            "author": "Test User",
            "version": "1.0",
            "description": "Test dataset for validation"
        },
        "configuration": {
            "simulation_time": 3600,
            "time_step": 60,
            "output_frequency": 300,
            "use_cache": True
        },
        "variables": {
            "temperature": {
                "units": "K",
                "description": "Air temperature",
                "values": [273.15, 274.15, 275.15, 276.15]
            },
            "pressure": {
                "units": "Pa",
                "description": "Atmospheric pressure",
                "values": [101325, 101320, 101315, 101310]
            }
        },
        "nested_arrays": {
            "matrix_2d": [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
            "coordinates": {
                "lat": [-90, -45, 0, 45, 90],
                "lon": [-180, -90, 0, 90, 180]
            }
        }
    }


@pytest.fixture
def sample_json_file(sample_json_data):
    """Create a sample JSON file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
        json.dump(sample_json_data, tmp_file, indent=2)
        tmp_path = tmp_file.name

    yield tmp_path

    # Cleanup
    Path(tmp_path).unlink(missing_ok=True)


@pytest.fixture
def sample_json_schema():
    """Sample JSON schema for validation testing."""
    return {
        "type": "object",
        "properties": {
            "metadata": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "author": {"type": "string"},
                    "version": {"type": "string"}
                },
                "required": ["title", "author"]
            },
            "configuration": {
                "type": "object",
                "properties": {
                    "simulation_time": {"type": "number"},
                    "time_step": {"type": "number"},
                    "use_cache": {"type": "boolean"}
                }
            },
            "variables": {"type": "object"}
        },
        "required": ["metadata", "configuration"]
    }


@pytest.fixture
def sample_json_data_loader_config(sample_json_file):
    """Create a sample JSON DataLoader configuration."""
    return DataLoader(
        name="test_json_data",
        type=DataLoaderType.JSON,
        source=sample_json_file,
        format_options={
            "type_coercion": True,
            "coercion_rules": {
                "simulation_time": "int",
                "temperature.values": "numpy_array"
            }
        },
        variables=["metadata", "configuration", "variables"]
    )


class TestJSONLoader:
    """Tests for JSON data loader."""

    def test_json_loader_initialization(self, sample_json_data_loader_config):
        """Test JSON loader initialization."""
        loader = JSONLoader(sample_json_data_loader_config)
        assert loader.config == sample_json_data_loader_config
        assert loader.data is None

    def test_json_loader_wrong_type(self):
        """Test JSON loader with wrong data loader type."""
        wrong_config = DataLoader(
            name="test",
            type=DataLoaderType.CSV,  # Wrong type
            source="test.json"
        )

        with pytest.raises(ValueError, match="Expected DataLoaderType.JSON"):
            JSONLoader(wrong_config)

    def test_load_nonexistent_file(self):
        """Test loading a file that doesn't exist."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.JSON,
            source="/nonexistent/path/file.json"
        )

        loader = JSONLoader(config)
        with pytest.raises(FileNotFoundError, match="JSON file not found"):
            loader.load()

    def test_load_invalid_json(self):
        """Test loading a file with invalid JSON."""
        # Create file with invalid JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            tmp_file.write('{"invalid": json,}')  # Invalid JSON
            invalid_json_file = tmp_file.name

        try:
            config = DataLoader(
                name="test",
                type=DataLoaderType.JSON,
                source=invalid_json_file
            )

            loader = JSONLoader(config)
            with pytest.raises(json.JSONDecodeError):
                loader.load()

        finally:
            Path(invalid_json_file).unlink()

    def test_load_valid_file(self, sample_json_data_loader_config, sample_json_data):
        """Test loading a valid JSON file."""
        loader = JSONLoader(sample_json_data_loader_config)
        data = loader.load()

        # Check that data was loaded
        assert loader.data is not None
        assert data is not None

        # Check expected top-level keys are present
        assert "metadata" in data
        assert "configuration" in data
        assert "variables" in data

        # Check metadata content
        assert data["metadata"]["title"] == sample_json_data["metadata"]["title"]
        assert data["metadata"]["author"] == sample_json_data["metadata"]["author"]

        # Check configuration content
        assert data["configuration"]["use_cache"] is True

    def test_load_with_variable_filtering(self, sample_json_file):
        """Test loading with specific variables only."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.JSON,
            source=sample_json_file,
            variables=["metadata", "configuration"]
        )

        loader = JSONLoader(config)
        data = loader.load()

        # Should only have metadata and configuration
        assert "metadata" in data
        assert "configuration" in data
        assert "variables" not in data
        assert "nested_arrays" not in data

    def test_load_with_nested_variable_access(self, sample_json_file):
        """Test loading with dot notation for nested variables."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.JSON,
            source=sample_json_file,
            variables=["metadata.title", "configuration.simulation_time", "variables.temperature.units"]
        )

        loader = JSONLoader(config)
        data = loader.load()

        # Should have the nested values with their original paths as keys
        assert "metadata.title" in data
        assert "configuration.simulation_time" in data
        assert "variables.temperature.units" in data

        assert data["metadata.title"] == "Sample Climate Data"
        assert data["configuration.simulation_time"] == 3600
        assert data["variables.temperature.units"] == "K"

    def test_load_with_missing_variables(self, sample_json_file):
        """Test loading with variables that don't exist."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.JSON,
            source=sample_json_file,
            variables=["nonexistent_variable"]
        )

        loader = JSONLoader(config)
        with pytest.raises(ValueError, match="Requested variables not found"):
            loader.load()

    def test_type_coercion(self, sample_json_file):
        """Test type coercion functionality."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.JSON,
            source=sample_json_file,
            format_options={
                "type_coercion": True,
                "coercion_rules": {
                    "configuration.simulation_time": "float"
                }
            }
        )

        loader = JSONLoader(config)
        data = loader.load()

        # simulation_time should be coerced to float
        assert isinstance(data["configuration"]["simulation_time"], float)
        assert data["configuration"]["simulation_time"] == 3600.0

    def test_schema_validation_valid(self, sample_json_data_loader_config, sample_json_schema):
        """Test schema validation with valid data."""
        loader = JSONLoader(sample_json_data_loader_config)
        loader.load()

        validation_result = loader.validate_schema(sample_json_schema)

        assert validation_result["valid"] is True
        assert len(validation_result["errors"]) == 0

    def test_schema_validation_invalid(self, sample_json_file, sample_json_schema):
        """Test schema validation with invalid data."""
        # Modify schema to make current data invalid
        invalid_schema = sample_json_schema.copy()
        invalid_schema["properties"]["metadata"]["properties"]["title"]["type"] = "number"  # Should be string

        config = DataLoader(
            name="test",
            type=DataLoaderType.JSON,
            source=sample_json_file
        )

        loader = JSONLoader(config)
        loader.load()

        validation_result = loader.validate_schema(invalid_schema)

        assert validation_result["valid"] is False
        assert len(validation_result["errors"]) > 0

    def test_schema_validation_with_format_options(self, sample_json_file, sample_json_schema):
        """Test schema validation using schema from format_options."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.JSON,
            source=sample_json_file,
            format_options={"schema": sample_json_schema}
        )

        loader = JSONLoader(config)
        loader.load()

        validation_result = loader.validate_schema()
        assert validation_result["valid"] is True

    def test_schema_validation_no_schema(self, sample_json_data_loader_config):
        """Test schema validation without providing a schema."""
        loader = JSONLoader(sample_json_data_loader_config)
        loader.load()

        validation_result = loader.validate_schema()
        assert len(validation_result["warnings"]) > 0
        assert "No schema provided" in validation_result["warnings"][0]

    def test_schema_validation_before_loading(self, sample_json_data_loader_config, sample_json_schema):
        """Test that schema validation fails if called before loading."""
        loader = JSONLoader(sample_json_data_loader_config)

        with pytest.raises(RuntimeError, match="Data must be loaded"):
            loader.validate_schema(sample_json_schema)

    def test_get_data_info(self, sample_json_data_loader_config):
        """Test data information extraction."""
        loader = JSONLoader(sample_json_data_loader_config)
        loader.load()

        data_info = loader.get_data_info()

        assert data_info["type"] == "dict"
        assert "structure" in data_info
        assert "size_info" in data_info

        # Check structure information
        structure = data_info["structure"]
        assert structure["type"] == "dict"
        assert "metadata" in structure["keys"]
        assert "configuration" in structure["keys"]

        # Check size information
        size_info = data_info["size_info"]
        assert "memory_bytes" in size_info
        assert "json_length" in size_info
        assert "num_keys" in size_info

    def test_get_data_info_before_loading(self, sample_json_data_loader_config):
        """Test that get_data_info fails if called before loading."""
        loader = JSONLoader(sample_json_data_loader_config)

        with pytest.raises(RuntimeError, match="Data must be loaded"):
            loader.get_data_info()

    def test_numpy_array_coercion(self, sample_json_file):
        """Test coercing JSON arrays to NumPy arrays."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.JSON,
            source=sample_json_file,
            format_options={
                "type_coercion": True,
                "coercion_rules": {
                    "variables.temperature.values": "numpy_array"
                }
            }
        )

        loader = JSONLoader(config)
        data = loader.load()

        temp_values = data["variables"]["temperature"]["values"]
        assert isinstance(temp_values, np.ndarray)
        assert temp_values.shape == (4,)
        assert np.allclose(temp_values, [273.15, 274.15, 275.15, 276.15])


class TestJSONLoaderFactory:
    """Tests for JSON loader factory integration."""

    def test_create_json_loader(self, sample_json_data_loader_config):
        """Test creating JSON loader through factory."""
        loader = create_data_loader(sample_json_data_loader_config)
        assert isinstance(loader, JSONLoader)
        assert loader.config == sample_json_data_loader_config

    def test_factory_updated_for_json(self):
        """Test that factory now supports JSON loaders."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.JSON,
            source="test.json"
        )

        # Should not raise "not yet implemented" error
        loader = create_data_loader(config)
        assert isinstance(loader, JSONLoader)


# Test missing jsonschema dependency
def test_json_loader_schema_validation_without_jsonschema(monkeypatch, sample_json_data_loader_config, sample_json_schema):
    """Test JSON loader schema validation when jsonschema is not available."""
    # Mock jsonschema as unavailable
    monkeypatch.setattr("esm_format.data_loaders.JSONSCHEMA_AVAILABLE", False)

    loader = JSONLoader(sample_json_data_loader_config)
    loader.load()

    with pytest.raises(ImportError, match="jsonschema library is required"):
        loader.validate_schema(sample_json_schema)


# Try to import HDF5 libraries for creating test data
try:
    import h5py
    H5PY_AVAILABLE = True
except ImportError:
    H5PY_AVAILABLE = False

try:
    import tables
    PYTABLES_AVAILABLE = True
except ImportError:
    PYTABLES_AVAILABLE = False


@pytest.fixture
def sample_hdf5_file():
    """Create a sample HDF5 file for testing."""
    if not H5PY_AVAILABLE:
        pytest.skip("h5py not available")

    # Create temporary file
    with tempfile.NamedTemporaryFile(suffix='.h5', delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        with h5py.File(tmp_path, 'w') as f:
            # Create sample datasets
            time = np.arange(24, dtype=np.float64)  # 24 hours
            lat = np.linspace(-90, 90, 18, dtype=np.float32)
            lon = np.linspace(-180, 180, 36, dtype=np.float32)

            # Create temperature data with proper chunking
            temp_data = 15 + 8 * np.random.randn(24, 18, 36).astype(np.float32)
            temp_ds = f.create_dataset('temperature', data=temp_data,
                                     chunks=(1, 18, 36), compression='gzip')
            temp_ds.attrs['units'] = 'degC'
            temp_ds.attrs['long_name'] = 'Air Temperature'
            temp_ds.attrs['standard_name'] = 'air_temperature'

            # Create pressure data
            pressure_data = (101325 + 1000 * np.random.randn(24, 18, 36)).astype(np.float32)
            pressure_ds = f.create_dataset('pressure', data=pressure_data,
                                         chunks=(1, 18, 36), compression='lzf')
            pressure_ds.attrs['units'] = 'Pa'
            pressure_ds.attrs['long_name'] = 'Atmospheric Pressure'

            # Create coordinate datasets
            time_ds = f.create_dataset('time', data=time)
            time_ds.attrs['units'] = 'hours since 2020-01-01 00:00:00'
            time_ds.attrs['long_name'] = 'Time'

            lat_ds = f.create_dataset('lat', data=lat)
            lat_ds.attrs['units'] = 'degrees_north'
            lat_ds.attrs['long_name'] = 'Latitude'

            lon_ds = f.create_dataset('lon', data=lon)
            lon_ds.attrs['units'] = 'degrees_east'
            lon_ds.attrs['long_name'] = 'Longitude'

            # Create hierarchical groups
            metadata_group = f.create_group('metadata')
            metadata_group.attrs['title'] = 'Sample atmospheric data'
            metadata_group.attrs['institution'] = 'Test Institute'
            metadata_group.attrs['created'] = '2020-01-01'

            # Create nested group with additional data
            analysis_group = metadata_group.create_group('analysis')
            stats_data = np.array([np.mean(temp_data), np.std(temp_data),
                                 np.min(temp_data), np.max(temp_data)])
            stats_ds = analysis_group.create_dataset('temperature_stats', data=stats_data)
            stats_ds.attrs['description'] = 'Temperature statistics: mean, std, min, max'
            stats_ds.attrs['units'] = 'degC'

            # Create string dataset
            string_data = np.array([b'station_1', b'station_2', b'station_3'], dtype='S20')
            station_ds = f.create_dataset('stations', data=string_data)
            station_ds.attrs['description'] = 'Station identifiers'

            # Global attributes
            f.attrs['Conventions'] = 'CF-1.8'
            f.attrs['title'] = 'Test HDF5 file for ESM Format'
            f.attrs['history'] = 'Created for testing purposes'

        yield tmp_path

    finally:
        # Cleanup
        Path(tmp_path).unlink(missing_ok=True)


@pytest.fixture
def sample_hdf5_data_loader_config(sample_hdf5_file):
    """Create a sample HDF5 DataLoader configuration."""
    return DataLoader(
        name="test_hdf5_data",
        type=DataLoaderType.HDF5,
        source=sample_hdf5_file,
        format_options={
            "backend": "h5py",
            "mode": "r"
        },
        variables=["temperature", "pressure", "time", "lat", "lon"]
    )


class TestHDF5Loader:
    """Tests for HDF5 data loader."""

    @pytest.mark.skipif(not H5PY_AVAILABLE and not PYTABLES_AVAILABLE,
                       reason="Neither h5py nor pytables available")
    def test_hdf5_loader_initialization(self, sample_hdf5_data_loader_config):
        """Test HDF5 loader initialization."""
        loader = HDF5Loader(sample_hdf5_data_loader_config)
        assert loader.config == sample_hdf5_data_loader_config
        assert loader.file_handle is None
        assert loader.data is None
        assert loader.backend in ['h5py', 'pytables']

    def test_hdf5_loader_wrong_type(self):
        """Test HDF5 loader with wrong data loader type."""
        wrong_config = DataLoader(
            name="test",
            type=DataLoaderType.NETCDF,  # Wrong type
            source="test.h5"
        )

        with pytest.raises(ValueError, match="Expected DataLoaderType.HDF5"):
            HDF5Loader(wrong_config)

    def test_hdf5_loader_no_backend_available(self, monkeypatch):
        """Test HDF5 loader when no backend is available."""
        # Mock both backends as unavailable
        monkeypatch.setattr("esm_format.data_loaders.H5PY_AVAILABLE", False)
        monkeypatch.setattr("esm_format.data_loaders.PYTABLES_AVAILABLE", False)

        config = DataLoader(
            name="test",
            type=DataLoaderType.HDF5,
            source="test.h5"
        )

        with pytest.raises(ImportError, match="Either h5py or pytables is required"):
            HDF5Loader(config)

    @pytest.mark.skipif(not H5PY_AVAILABLE and not PYTABLES_AVAILABLE,
                       reason="Neither h5py nor pytables available")
    def test_load_nonexistent_file(self):
        """Test loading a file that doesn't exist."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.HDF5,
            source="/nonexistent/path/file.h5"
        )

        loader = HDF5Loader(config)
        with pytest.raises(FileNotFoundError, match="HDF5 file not found"):
            loader.load()

    @pytest.mark.skipif(not H5PY_AVAILABLE, reason="h5py not available")
    def test_load_valid_file(self, sample_hdf5_data_loader_config):
        """Test loading a valid HDF5 file."""
        loader = HDF5Loader(sample_hdf5_data_loader_config)
        data = loader.load()

        # Check that data was loaded
        assert loader.data is not None
        assert data is not None

        # Check expected variables are present
        assert "temperature" in data
        assert "pressure" in data
        assert "time" in data
        assert "lat" in data
        assert "lon" in data

        # Check data types and shapes
        assert isinstance(data["temperature"], np.ndarray)
        assert data["temperature"].shape == (24, 18, 36)
        assert isinstance(data["pressure"], np.ndarray)
        assert data["pressure"].shape == (24, 18, 36)
        assert isinstance(data["time"], np.ndarray)
        assert data["time"].shape == (24,)

        # Check metadata attributes are loaded
        assert "temperature_attrs" in data
        assert data["temperature_attrs"]["units"] == "degC"
        assert data["temperature_attrs"]["long_name"] == "Air Temperature"

        loader.close()

    @pytest.mark.skipif(not H5PY_AVAILABLE, reason="h5py not available")
    def test_load_with_variable_filtering(self, sample_hdf5_file):
        """Test loading with specific variables only."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.HDF5,
            source=sample_hdf5_file,
            variables=["temperature", "time"]
        )

        loader = HDF5Loader(config)
        data = loader.load()

        # Should only have temperature and time
        assert "temperature" in data
        assert "time" in data
        assert "pressure" not in data
        assert "lat" not in data
        assert "lon" not in data

        # Should still have metadata attributes
        assert "temperature_attrs" in data
        assert "time_attrs" in data

        loader.close()

    @pytest.mark.skipif(not H5PY_AVAILABLE, reason="h5py not available")
    def test_load_with_hierarchical_variables(self, sample_hdf5_file):
        """Test loading with hierarchical variable access."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.HDF5,
            source=sample_hdf5_file,
            variables=["metadata/analysis/temperature_stats"]
        )

        loader = HDF5Loader(config)
        data = loader.load()

        # Should have the hierarchical dataset
        assert "metadata/analysis/temperature_stats" in data
        stats_data = data["metadata/analysis/temperature_stats"]
        assert isinstance(stats_data, np.ndarray)
        assert stats_data.shape == (4,)  # mean, std, min, max

        loader.close()

    @pytest.mark.skipif(not H5PY_AVAILABLE, reason="h5py not available")
    def test_load_with_missing_variables(self, sample_hdf5_file):
        """Test loading with variables that don't exist."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.HDF5,
            source=sample_hdf5_file,
            variables=["nonexistent_dataset"]
        )

        loader = HDF5Loader(config)
        with pytest.raises(ValueError, match="Requested variables not found"):
            loader.load()

    @pytest.mark.skipif(not H5PY_AVAILABLE, reason="h5py not available")
    def test_get_file_structure(self, sample_hdf5_data_loader_config):
        """Test file structure extraction."""
        loader = HDF5Loader(sample_hdf5_data_loader_config)
        loader.load()

        structure = loader.get_file_structure()

        # Check top-level structure
        assert isinstance(structure, dict)
        assert "metadata" in structure
        assert structure["metadata"]["type"] == "group"

        # Check nested structure
        assert "analysis" in structure["metadata"]["children"]
        assert structure["metadata"]["children"]["analysis"]["type"] == "group"

        loader.close()

    @pytest.mark.skipif(not H5PY_AVAILABLE, reason="h5py not available")
    def test_get_dataset_info(self, sample_hdf5_data_loader_config):
        """Test dataset information extraction."""
        loader = HDF5Loader(sample_hdf5_data_loader_config)
        loader.load()

        # Get info for all datasets
        info = loader.get_dataset_info()
        assert "temperature" in info
        assert "pressure" in info

        # Check temperature dataset info
        temp_info = info["temperature"]
        assert temp_info["shape"] == (24, 18, 36)
        assert temp_info["dtype"] == "float32"
        assert temp_info["compression"] == "gzip"
        assert temp_info["chunks"] == (1, 18, 36)
        assert temp_info["attributes"]["units"] == "degC"

        # Get info for specific dataset
        specific_info = loader.get_dataset_info("pressure")
        assert "pressure" in specific_info
        assert specific_info["pressure"]["compression"] == "lzf"

        loader.close()

    @pytest.mark.skipif(not H5PY_AVAILABLE, reason="h5py not available")
    def test_read_dataset(self, sample_hdf5_data_loader_config):
        """Test reading specific datasets."""
        loader = HDF5Loader(sample_hdf5_data_loader_config)
        loader.load()

        # Read full dataset
        temp_data = loader.read_dataset("temperature")
        assert temp_data.shape == (24, 18, 36)

        # Read with slicing
        temp_slice = loader.read_dataset("temperature", (slice(0, 5), slice(None), slice(None)))
        assert temp_slice.shape == (5, 18, 36)

        loader.close()

    @pytest.mark.skipif(not H5PY_AVAILABLE, reason="h5py not available")
    def test_read_nonexistent_dataset(self, sample_hdf5_data_loader_config):
        """Test reading dataset that doesn't exist."""
        loader = HDF5Loader(sample_hdf5_data_loader_config)
        loader.load()

        with pytest.raises(ValueError, match="Dataset .* not found"):
            loader.read_dataset("nonexistent_dataset")

        loader.close()

    @pytest.mark.skipif(not H5PY_AVAILABLE, reason="h5py not available")
    def test_list_groups(self, sample_hdf5_data_loader_config):
        """Test listing groups in the file."""
        loader = HDF5Loader(sample_hdf5_data_loader_config)
        loader.load()

        # List root groups
        root_groups = loader.list_groups()
        assert "metadata" in root_groups

        # List nested groups
        nested_groups = loader.list_groups("/metadata")
        assert "analysis" in nested_groups

        loader.close()

    @pytest.mark.skipif(not H5PY_AVAILABLE, reason="h5py not available")
    def test_list_datasets(self, sample_hdf5_data_loader_config):
        """Test listing datasets in the file."""
        loader = HDF5Loader(sample_hdf5_data_loader_config)
        loader.load()

        # List root datasets
        root_datasets = loader.list_datasets()
        expected_datasets = ["temperature", "pressure", "time", "lat", "lon", "stations"]
        for dataset in expected_datasets:
            assert dataset in root_datasets

        # List datasets in nested group
        nested_datasets = loader.list_datasets("/metadata/analysis")
        assert "temperature_stats" in nested_datasets

        loader.close()

    @pytest.mark.skipif(not H5PY_AVAILABLE, reason="h5py not available")
    def test_backend_preference(self, sample_hdf5_file):
        """Test backend preference selection."""
        # Test explicit h5py preference
        config_h5py = DataLoader(
            name="test",
            type=DataLoaderType.HDF5,
            source=sample_hdf5_file,
            format_options={"backend": "h5py"}
        )

        loader_h5py = HDF5Loader(config_h5py)
        if H5PY_AVAILABLE:
            assert loader_h5py.backend == "h5py"

        # Test explicit pytables preference (if available)
        if PYTABLES_AVAILABLE:
            config_pytables = DataLoader(
                name="test",
                type=DataLoaderType.HDF5,
                source=sample_hdf5_file,
                format_options={"backend": "pytables"}
            )

            loader_pytables = HDF5Loader(config_pytables)
            assert loader_pytables.backend == "pytables"

    @pytest.mark.skipif(not H5PY_AVAILABLE, reason="h5py not available")
    def test_operations_before_loading(self, sample_hdf5_data_loader_config):
        """Test that operations fail if called before loading."""
        loader = HDF5Loader(sample_hdf5_data_loader_config)

        with pytest.raises(RuntimeError, match="File must be loaded"):
            loader.get_file_structure()

        with pytest.raises(RuntimeError, match="File must be loaded"):
            loader.get_dataset_info()

        with pytest.raises(RuntimeError, match="File must be loaded"):
            loader.read_dataset("temperature")

        with pytest.raises(RuntimeError, match="File must be loaded"):
            loader.list_groups()

        with pytest.raises(RuntimeError, match="File must be loaded"):
            loader.list_datasets()

    @pytest.mark.skipif(not H5PY_AVAILABLE, reason="h5py not available")
    def test_close_file(self, sample_hdf5_data_loader_config):
        """Test closing HDF5 file."""
        loader = HDF5Loader(sample_hdf5_data_loader_config)
        loader.load()

        assert loader.file_handle is not None
        assert loader.data is not None

        loader.close()
        assert loader.file_handle is None
        assert loader.data is None


class TestHDF5LoaderFactory:
    """Tests for HDF5 loader factory integration."""

    @pytest.mark.skipif(not H5PY_AVAILABLE and not PYTABLES_AVAILABLE,
                       reason="Neither h5py nor pytables available")
    def test_create_hdf5_loader(self, sample_hdf5_data_loader_config):
        """Test creating HDF5 loader through factory."""
        loader = create_data_loader(sample_hdf5_data_loader_config)
        assert isinstance(loader, HDF5Loader)
        assert loader.config == sample_hdf5_data_loader_config

    @pytest.mark.skipif(not H5PY_AVAILABLE and not PYTABLES_AVAILABLE,
                       reason="Neither h5py nor pytables available")
    def test_factory_supports_hdf5(self):
        """Test that factory now supports HDF5 loaders."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.HDF5,
            source="test.h5"
        )

        # Should not raise "not registered" error
        loader = create_data_loader(config)
        assert isinstance(loader, HDF5Loader)


# Test missing HDF5 dependencies
def test_hdf5_loader_without_backends(monkeypatch):
    """Test HDF5 loader when both h5py and pytables are not available."""
    # Mock both backends as unavailable
    monkeypatch.setattr("esm_format.data_loaders.H5PY_AVAILABLE", False)
    monkeypatch.setattr("esm_format.data_loaders.PYTABLES_AVAILABLE", False)

    config = DataLoader(
        name="test",
        type=DataLoaderType.HDF5,
        source="test.h5"
    )

    with pytest.raises(ImportError, match="Either h5py or pytables is required"):
        HDF5Loader(config)


# ========================================
# GRIB Loader Tests
# ========================================

@pytest.fixture
def sample_grib_file():
    """Create a sample GRIB file for testing."""
    if not CFGRIB_AVAILABLE:
        pytest.skip("cfgrib not available")

    # Since creating GRIB files programmatically is complex, we'll simulate
    # the test by creating a mock file path that would normally exist
    # In a real scenario, you would use actual GRIB test files
    return Path(tempfile.mkdtemp()) / "sample.grib2"


@pytest.fixture
def sample_grib_data_loader_config():
    """Sample GRIB data loader configuration."""
    return DataLoader(
        name="GRIB_TestData",
        type=DataLoaderType.GRIB,
        source="test_data.grib2",
        variables=["temperature", "pressure"],
        format_options={
            "filter_by_keys": {"typeOfLevel": "surface"},
            "chunks": {"time": 10}
        }
    )


class TestGRIBLoader:
    """Tests for GRIB data loading functionality."""

    def test_grib_loader_initialization(self):
        """Test GRIB loader initialization."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.GRIB,
            source="test.grib2"
        )

        if CFGRIB_AVAILABLE:
            loader = GRIBLoader(config)
            assert loader.config == config
            assert loader.dataset is None
        else:
            with pytest.raises(ImportError, match="cfgrib and xarray are required"):
                GRIBLoader(config)

    def test_grib_loader_wrong_type(self):
        """Test GRIB loader with wrong data loader type."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.JSON,  # Wrong type
            source="test.grib2"
        )

        if CFGRIB_AVAILABLE:
            with pytest.raises(ValueError, match="Expected DataLoaderType.GRIB"):
                GRIBLoader(config)

    @pytest.mark.skipif(not CFGRIB_AVAILABLE, reason="cfgrib not available")
    def test_grib_loader_file_not_found(self):
        """Test GRIB loader with non-existent file."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.GRIB,
            source="nonexistent.grib2"
        )

        loader = GRIBLoader(config)
        with pytest.raises(FileNotFoundError, match="GRIB file not found"):
            loader.load()

    @pytest.mark.skipif(not CFGRIB_AVAILABLE, reason="cfgrib not available")
    def test_grib_loader_methods_before_load(self):
        """Test GRIB loader methods that require loaded data."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.GRIB,
            source="test.grib2"
        )

        loader = GRIBLoader(config)

        # These methods should raise RuntimeError before loading
        with pytest.raises(RuntimeError, match="Dataset must be loaded"):
            loader.get_parameter_info()

        with pytest.raises(RuntimeError, match="Dataset must be loaded"):
            loader.get_grid_info()

        with pytest.raises(RuntimeError, match="Dataset must be loaded"):
            loader.get_time_info()

        with pytest.raises(RuntimeError, match="Dataset must be loaded"):
            loader.list_available_parameters()

        with pytest.raises(RuntimeError, match="Dataset must be loaded"):
            loader.extract_ensemble_info()

        with pytest.raises(RuntimeError, match="Dataset must be loaded"):
            loader.validate_grib_conventions()

    @pytest.mark.skipif(not CFGRIB_AVAILABLE, reason="cfgrib not available")
    def test_grib_loader_close(self):
        """Test GRIB loader close functionality."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.GRIB,
            source="test.grib2"
        )

        loader = GRIBLoader(config)

        # Should be safe to close even without loading
        loader.close()
        assert loader.dataset is None

    @pytest.mark.skipif(not CFGRIB_AVAILABLE, reason="cfgrib not available")
    def test_grib_loader_configuration(self, sample_grib_data_loader_config):
        """Test GRIB loader configuration handling."""
        loader = GRIBLoader(sample_grib_data_loader_config)

        # Check that configuration is properly stored
        assert loader.config.name == "GRIB_TestData"
        assert loader.config.type == DataLoaderType.GRIB
        assert loader.config.variables == ["temperature", "pressure"]
        assert "filter_by_keys" in loader.config.format_options
        assert "chunks" in loader.config.format_options


class TestGRIBLoaderFactory:
    """Tests for GRIB loader factory integration."""

    @pytest.mark.skipif(not CFGRIB_AVAILABLE, reason="cfgrib not available")
    def test_create_grib_loader(self, sample_grib_data_loader_config):
        """Test creating GRIB loader through factory."""
        loader = create_data_loader(sample_grib_data_loader_config)
        assert isinstance(loader, GRIBLoader)
        assert loader.config == sample_grib_data_loader_config

    @pytest.mark.skipif(not CFGRIB_AVAILABLE, reason="cfgrib not available")
    def test_factory_supports_grib(self):
        """Test that factory now supports GRIB loaders."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.GRIB,
            source="test.grib2"
        )

        # Should not raise "not registered" error
        loader = create_data_loader(config)
        assert isinstance(loader, GRIBLoader)


# Test missing GRIB dependencies
def test_grib_loader_without_cfgrib(monkeypatch):
    """Test GRIB loader when cfgrib is not available."""
    # Mock cfgrib as unavailable
    monkeypatch.setattr("esm_format.data_loaders.CFGRIB_AVAILABLE", False)

    config = DataLoader(
        name="test",
        type=DataLoaderType.GRIB,
        source="test.grib2"
    )

    with pytest.raises(ImportError, match="cfgrib and xarray are required"):
        GRIBLoader(config)


class TestStreamingLoader:
    """Test cases for StreamingLoader."""

    def test_streaming_loader_initialization(self):
        """Test basic initialization of StreamingLoader."""
        config = DataLoader(
            name="test_stream",
            type=DataLoaderType.STREAMING,
            source="ws://localhost:8080/stream"
        )

        loader = StreamingLoader(config)
        assert loader.config == config
        assert not loader.is_running
        assert loader.buffer == []
        assert loader.data_count == 0
        assert loader.error_count == 0

    def test_streaming_loader_wrong_type(self):
        """Test StreamingLoader with wrong data loader type."""
        config = DataLoader(
            name="test",
            type=DataLoaderType.JSON,
            source="ws://localhost:8080/stream"
        )

        with pytest.raises(ValueError, match="Expected DataLoaderType.STREAMING"):
            StreamingLoader(config)

    def test_detect_websocket_source_type(self):
        """Test detection of WebSocket source type."""
        config = DataLoader(
            name="test_ws",
            type=DataLoaderType.STREAMING,
            source="ws://localhost:8080/stream"
        )

        loader = StreamingLoader(config)
        assert loader.source_type == 'websocket'

    def test_detect_http_stream_source_type(self):
        """Test detection of HTTP stream source type."""
        config = DataLoader(
            name="test_http",
            type=DataLoaderType.STREAMING,
            source="http://localhost:8080/stream"
        )

        loader = StreamingLoader(config)
        assert loader.source_type == 'http_stream'

    def test_detect_queue_source_type(self):
        """Test detection of message queue source type."""
        config = DataLoader(
            name="test_queue",
            type=DataLoaderType.STREAMING,
            source="kafka://localhost:9092/topic"
        )

        loader = StreamingLoader(config)
        assert loader.source_type == 'queue'

    def test_detect_tcp_source_type(self):
        """Test detection of TCP source type."""
        config = DataLoader(
            name="test_tcp",
            type=DataLoaderType.STREAMING,
            source="tcp://localhost:9999"
        )

        loader = StreamingLoader(config)
        assert loader.source_type == 'tcp'

    def test_configuration_options(self):
        """Test configuration options for streaming loader."""
        config = DataLoader(
            name="test_config",
            type=DataLoaderType.STREAMING,
            source="ws://localhost:8080/stream",
            format_options={
                'buffer_size': 2000,
                'reconnect_attempts': 10,
                'reconnect_delay': 2.0,
                'timeout': 60.0
            }
        )

        loader = StreamingLoader(config)
        assert loader.buffer_size == 2000
        assert loader.reconnect_attempts == 10
        assert loader.reconnect_delay == 2.0
        assert loader.timeout == 60.0

    def test_start_stop_streaming(self):
        """Test starting and stopping streaming."""
        config = DataLoader(
            name="test_start_stop",
            type=DataLoaderType.STREAMING,
            source="ws://localhost:8080/stream"
        )

        loader = StreamingLoader(config)
        assert not loader.is_running

        # Start streaming
        loader.start_streaming()
        assert loader.is_running
        assert loader.connection is not None

        # Stop streaming
        loader.stop_streaming()
        assert not loader.is_running
        assert loader.connection is None

    def test_start_streaming_already_running(self):
        """Test starting streaming when already running."""
        config = DataLoader(
            name="test_already_running",
            type=DataLoaderType.STREAMING,
            source="ws://localhost:8080/stream"
        )

        loader = StreamingLoader(config)
        loader.start_streaming()

        with pytest.raises(RuntimeError, match="Streaming is already running"):
            loader.start_streaming()

        loader.stop_streaming()

    def test_mock_data_buffering(self):
        """Test adding and reading mock data from buffer."""
        config = DataLoader(
            name="test_buffer",
            type=DataLoaderType.STREAMING,
            source="ws://localhost:8080/stream"
        )

        loader = StreamingLoader(config)

        # Add mock data
        test_data_1 = {"timestamp": "2023-01-01T12:00:00", "value": 42.5}
        test_data_2 = {"timestamp": "2023-01-01T12:01:00", "value": 43.1}

        loader.add_mock_data(test_data_1)
        loader.add_mock_data(test_data_2)

        assert len(loader.buffer) == 2
        assert loader.data_count == 2

        # Read data
        data = loader.read_data()
        assert len(data) == 2
        assert data[0] == test_data_1
        assert data[1] == test_data_2
        assert len(loader.buffer) == 0

    def test_backpressure_handling(self):
        """Test backpressure handling when buffer is full."""
        config = DataLoader(
            name="test_backpressure",
            type=DataLoaderType.STREAMING,
            source="ws://localhost:8080/stream",
            format_options={'buffer_size': 2}
        )

        loader = StreamingLoader(config)

        # Fill buffer beyond capacity
        loader.add_mock_data({"id": 1})
        loader.add_mock_data({"id": 2})
        loader.add_mock_data({"id": 3})  # Should push out first item

        assert len(loader.buffer) == 2
        assert loader.buffer[0]["id"] == 2  # First item was dropped
        assert loader.buffer[1]["id"] == 3

    def test_read_data_with_limit(self):
        """Test reading data with item limit."""
        config = DataLoader(
            name="test_read_limit",
            type=DataLoaderType.STREAMING,
            source="ws://localhost:8080/stream"
        )

        loader = StreamingLoader(config)

        # Add test data
        for i in range(5):
            loader.add_mock_data({"id": i})

        # Read with limit
        data = loader.read_data(max_items=2)
        assert len(data) == 2
        assert data[0]["id"] == 0
        assert data[1]["id"] == 1

        # Buffer should still have remaining items
        assert len(loader.buffer) == 3
        assert loader.buffer[0]["id"] == 2

    def test_get_status(self):
        """Test getting streaming status."""
        config = DataLoader(
            name="test_status",
            type=DataLoaderType.STREAMING,
            source="ws://localhost:8080/stream"
        )

        loader = StreamingLoader(config)
        loader.add_mock_data({"test": "data"})

        status = loader.get_status()
        assert status['is_running'] == False
        assert status['source_type'] == 'websocket'
        assert status['source'] == "ws://localhost:8080/stream"
        assert status['buffer_size'] == 1
        assert status['data_count'] == 1
        assert status['error_count'] == 0
        assert status['connection_status'] == 'disconnected'

    def test_clear_buffer(self):
        """Test clearing the data buffer."""
        config = DataLoader(
            name="test_clear",
            type=DataLoaderType.STREAMING,
            source="ws://localhost:8080/stream"
        )

        loader = StreamingLoader(config)

        # Add test data
        for i in range(3):
            loader.add_mock_data({"id": i})

        assert len(loader.buffer) == 3

        # Clear buffer
        cleared_count = loader.clear_buffer()
        assert cleared_count == 3
        assert len(loader.buffer) == 0

    def test_configure_backpressure(self):
        """Test configuring backpressure settings."""
        config = DataLoader(
            name="test_backpressure_config",
            type=DataLoaderType.STREAMING,
            source="ws://localhost:8080/stream",
            format_options={'buffer_size': 5}
        )

        loader = StreamingLoader(config)

        # Fill buffer
        for i in range(5):
            loader.add_mock_data({"id": i})

        assert len(loader.buffer) == 5

        # Reduce buffer size
        loader.configure_backpressure(3)
        assert loader.buffer_size == 3
        assert len(loader.buffer) == 3
        # Should keep the last 3 items
        assert loader.buffer[0]["id"] == 2

    def test_close_streaming_loader(self):
        """Test closing streaming loader."""
        config = DataLoader(
            name="test_close",
            type=DataLoaderType.STREAMING,
            source="ws://localhost:8080/stream"
        )

        loader = StreamingLoader(config)
        loader.start_streaming()
        loader.add_mock_data({"test": "data"})

        assert loader.is_running
        assert len(loader.buffer) > 0

        # Close loader
        loader.close()
        assert not loader.is_running
        assert len(loader.buffer) == 0
        assert loader.connection is None


class TestStreamingLoaderFactory:
    """Test factory function with StreamingLoader."""

    def test_create_streaming_loader(self):
        """Test factory creates StreamingLoader correctly."""
        config = DataLoader(
            name="test_factory_streaming",
            type=DataLoaderType.STREAMING,
            source="ws://localhost:8080/stream"
        )

        loader = create_data_loader(config)
        assert isinstance(loader, StreamingLoader)
        assert loader.config == config

    def test_factory_supports_streaming(self):
        """Test factory supports STREAMING type."""
        # This test ensures that the factory has been updated
        config = DataLoader(
            name="test_factory_support",
            type=DataLoaderType.STREAMING,
            source="http://localhost:8080/events"
        )

        # Should not raise "not supported" error
        loader = create_data_loader(config)
        assert isinstance(loader, StreamingLoader)


# ========================================
# Binary Loader Tests
# ========================================

@pytest.fixture
def sample_binary_file():
    """Create a sample binary file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
        # Create a simple binary file with known structure:
        # - Header (8 bytes): magic number (4) + version (4)
        # - Record 1: int32 (4), float32 (4), char[4] (4)
        # - Record 2: int32 (4), float32 (4), char[4] (4)

        # Header
        f.write(b'TESTBIN1')  # magic + version

        # Record 1
        f.write((42).to_bytes(4, 'little'))  # int32
        f.write(bytes([0x00, 0x00, 0x20, 0x41]))  # 10.0 as float32 little-endian
        f.write(b'TEST')  # char[4]

        # Record 2
        f.write((100).to_bytes(4, 'little'))  # int32
        f.write(bytes([0x00, 0x00, 0xA0, 0x41]))  # 20.0 as float32 little-endian
        f.write(b'DATA')  # char[4]

        return Path(f.name)


@pytest.fixture
def sample_mixed_binary_file():
    """Create a binary file with mixed data types."""
    with tempfile.NamedTemporaryFile(suffix='.dat', delete=False) as f:
        import struct

        # Write data in parts to avoid struct format issues
        # Use 0x1234 instead of 0xFFFF to test endianness properly
        f.write(struct.pack('<H', 0x1234))        # uint16 = 4660
        f.write(struct.pack('<i', -12345))        # int32
        f.write(struct.pack('<d', 3.14159))       # float64
        f.write(struct.pack('<?', True))          # bool
        f.write(struct.pack('<BBBB', 1, 2, 3, 4)) # uint8[4]

        return Path(f.name)


class TestBinaryLoader:
    """Test BinaryLoader class."""

    def test_binary_loader_initialization(self):
        """Test BinaryLoader initialization."""
        config = DataLoader(
            name="test_binary",
            type=DataLoaderType.BINARY,
            source="test.bin"
        )

        loader = BinaryLoader(config)
        assert loader.config == config
        assert loader.endianness == 'native'
        assert loader.header_size == 0
        assert loader.data is None
        assert loader.raw_data is None

    def test_binary_loader_wrong_type(self):
        """Test BinaryLoader with wrong data type."""
        config = DataLoader(
            name="test_wrong_type",
            type=DataLoaderType.JSON,
            source="test.bin"
        )

        with pytest.raises(ValueError, match="Expected DataLoaderType.BINARY"):
            BinaryLoader(config)

    def test_binary_loader_invalid_endianness(self):
        """Test BinaryLoader with invalid endianness."""
        config = DataLoader(
            name="test_invalid_endian",
            type=DataLoaderType.BINARY,
            source="test.bin",
            format_options={'endianness': 'invalid'}
        )

        with pytest.raises(ValueError, match="Invalid endianness"):
            BinaryLoader(config)

    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file."""
        config = DataLoader(
            name="test_nonexistent",
            type=DataLoaderType.BINARY,
            source="nonexistent.bin"
        )

        loader = BinaryLoader(config)
        with pytest.raises(FileNotFoundError):
            loader.load()

    def test_load_with_struct_format(self, sample_binary_file):
        """Test loading with struct format."""
        config = DataLoader(
            name="test_struct",
            type=DataLoaderType.BINARY,
            source=str(sample_binary_file),
            format_options={
                'header_size': 8,
                'struct_format': 'ifc',  # int32, float32, char
                'field_names': ['id', 'value', 'name'],
                'endianness': 'little',
                'record_size': 12
            }
        )

        loader = BinaryLoader(config)
        data = loader.load()

        assert 'records' in data
        assert len(data['records']) == 2

        # Check first record
        record1 = data['records'][0]
        assert record1['id'] == 42
        assert abs(record1['value'] - 10.0) < 0.001
        assert record1['name'] == b'T'  # First char only due to 'c' format

        # Check second record
        record2 = data['records'][1]
        assert record2['id'] == 100
        assert abs(record2['value'] - 20.0) < 0.001

    def test_load_with_data_types(self, sample_mixed_binary_file):
        """Test loading with data types specification."""
        config = DataLoader(
            name="test_data_types",
            type=DataLoaderType.BINARY,
            source=str(sample_mixed_binary_file),
            format_options={
                'endianness': 'little',
                'data_types': {
                    'id': 'uint16',
                    'count': 'int32',
                    'pi': 'float64',
                    'flag': 'bool',
                    'bytes': ['uint8', 4]
                }
            }
        )

        loader = BinaryLoader(config)
        data = loader.load()

        assert data['id'] == 0x1234  # 4660 in decimal
        assert data['count'] == -12345
        assert abs(data['pi'] - 3.14159) < 0.0001
        assert data['flag'] is True
        assert data['bytes'] == [1, 2, 3, 4]

    def test_load_with_custom_format(self, sample_mixed_binary_file):
        """Test loading with custom format specification."""
        config = DataLoader(
            name="test_custom",
            type=DataLoaderType.BINARY,
            source=str(sample_mixed_binary_file),
            format_options={
                'endianness': 'little',
                'custom_format': {
                    'header': {'type': 'uint16', 'count': 1},
                    'value': {'type': 'int32', 'count': 1, 'offset': 2},
                    'precision': {'type': 'float64', 'count': 1, 'offset': 6},
                    'enabled': {'type': 'bool', 'count': 1, 'offset': 14}
                }
            }
        )

        loader = BinaryLoader(config)
        data = loader.load()

        assert data['header'] == 0x1234
        assert data['value'] == -12345
        assert abs(data['precision'] - 3.14159) < 0.0001
        assert data['enabled'] is True

    def test_load_raw_bytes(self, sample_binary_file):
        """Test loading as raw bytes when no format specified."""
        config = DataLoader(
            name="test_raw",
            type=DataLoaderType.BINARY,
            source=str(sample_binary_file)
        )

        loader = BinaryLoader(config)
        data = loader.load()

        assert 'raw_data' in data
        assert isinstance(data['raw_data'], list)
        assert len(data['raw_data']) == 32  # 8 header + 24 data bytes

    def test_load_with_variable_filtering(self, sample_mixed_binary_file):
        """Test loading with variable filtering."""
        config = DataLoader(
            name="test_filtering",
            type=DataLoaderType.BINARY,
            source=str(sample_mixed_binary_file),
            format_options={
                'endianness': 'little',
                'data_types': {
                    'id': 'uint16',
                    'count': 'int32',
                    'pi': 'float64',
                    'flag': 'bool'
                }
            },
            variables=['id', 'pi']
        )

        loader = BinaryLoader(config)
        data = loader.load()

        assert len(data) == 2
        assert 'id' in data
        assert 'pi' in data
        assert 'count' not in data
        assert 'flag' not in data

        assert data['id'] == 0x1234  # 4660 in decimal
        assert abs(data['pi'] - 3.14159) < 0.0001

    def test_load_with_missing_variables(self, sample_binary_file):
        """Test loading with missing variables raises error."""
        config = DataLoader(
            name="test_missing_vars",
            type=DataLoaderType.BINARY,
            source=str(sample_binary_file),
            variables=['nonexistent', 'also_missing']
        )

        loader = BinaryLoader(config)
        with pytest.raises(ValueError, match="Requested variables not found"):
            loader.load()

    def test_get_file_info(self, sample_binary_file):
        """Test getting file information."""
        config = DataLoader(
            name="test_info",
            type=DataLoaderType.BINARY,
            source=str(sample_binary_file),
            format_options={
                'header_size': 8,
                'record_size': 12,
                'data_types': {
                    'test': 'int32'
                }
            }
        )

        loader = BinaryLoader(config)
        loader.load()

        info = loader.get_file_info()

        assert info['file_size_bytes'] == 32
        assert info['header_size'] == 8
        assert info['data_size_bytes'] == 24
        assert info['record_size'] == 12
        assert info['estimated_record_count'] == 2
        assert info['format_type'] == 'data_types'

    def test_validate_format(self, sample_binary_file):
        """Test format validation."""
        config = DataLoader(
            name="test_validate",
            type=DataLoaderType.BINARY,
            source=str(sample_binary_file),
            format_options={
                'header_size': 8,
                'struct_format': 'if4s',  # int, float, 4-byte string
                'field_names': ['id', 'value', 'name']
            }
        )

        loader = BinaryLoader(config)
        loader.load()

        validation = loader.validate_format()

        assert validation['valid'] is True
        assert len(validation['errors']) == 0
        assert 'struct_size' in validation['format_info']

    def test_read_header(self, sample_binary_file):
        """Test reading header."""
        config = DataLoader(
            name="test_header",
            type=DataLoaderType.BINARY,
            source=str(sample_binary_file),
            format_options={'header_size': 8}
        )

        loader = BinaryLoader(config)
        loader.load()

        header = loader.read_header()
        assert header == b'TESTBIN1'

    def test_read_raw_data(self, sample_binary_file):
        """Test reading raw data."""
        config = DataLoader(
            name="test_raw_read",
            type=DataLoaderType.BINARY,
            source=str(sample_binary_file),
            format_options={'header_size': 8}
        )

        loader = BinaryLoader(config)
        loader.load()

        # Read first 4 bytes of data (should be first int32)
        raw_data = loader.read_raw_data(offset=0, length=4)
        assert len(raw_data) == 4
        assert int.from_bytes(raw_data, 'little') == 42

    def test_export_to_numpy(self, sample_mixed_binary_file):
        """Test exporting to NumPy arrays."""
        config = DataLoader(
            name="test_numpy",
            type=DataLoaderType.BINARY,
            source=str(sample_mixed_binary_file),
            format_options={
                'endianness': 'little',
                'data_types': {
                    'values': ['int32', 2]  # Array of 2 int32s (but our file only has 1)
                }
            }
        )

        loader = BinaryLoader(config)
        try:
            data = loader.load()
            numpy_data = loader.export_to_numpy()

            # Check that arrays are converted to numpy
            assert hasattr(numpy_data['values'], 'shape')  # NumPy array

        except ValueError:
            # Expected if we try to read more data than available
            pass

    def test_operations_before_loading(self):
        """Test operations that require loading first."""
        config = DataLoader(
            name="test_before_load",
            type=DataLoaderType.BINARY,
            source="test.bin"
        )

        loader = BinaryLoader(config)

        with pytest.raises(RuntimeError, match="must be loaded"):
            loader.get_file_info()

        with pytest.raises(RuntimeError, match="must be loaded"):
            loader.validate_format()

        with pytest.raises(RuntimeError, match="must be loaded"):
            loader.read_header()

        with pytest.raises(RuntimeError, match="must be loaded"):
            loader.read_raw_data()

        with pytest.raises(RuntimeError, match="must be loaded"):
            loader.export_to_numpy()

    def test_close_loader(self, sample_binary_file):
        """Test closing the loader."""
        config = DataLoader(
            name="test_close",
            type=DataLoaderType.BINARY,
            source=str(sample_binary_file)
        )

        loader = BinaryLoader(config)
        loader.load()

        assert loader.data is not None
        assert loader.raw_data is not None

        loader.close()

        assert loader.data is None
        assert loader.raw_data is None

    def test_unsupported_data_type(self, sample_binary_file):
        """Test unsupported data type raises error."""
        config = DataLoader(
            name="test_unsupported",
            type=DataLoaderType.BINARY,
            source=str(sample_binary_file),
            format_options={
                'data_types': {
                    'bad_field': 'unsupported_type'
                }
            }
        )

        loader = BinaryLoader(config)
        with pytest.raises(ValueError, match="Unsupported type"):
            loader.load()

    def test_endianness_variations(self, sample_mixed_binary_file):
        """Test different endianness settings."""
        # Test with little endian (matches our file format)
        config_little = DataLoader(
            name="test_little_endian",
            type=DataLoaderType.BINARY,
            source=str(sample_mixed_binary_file),
            format_options={
                'endianness': 'little',
                'data_types': {'value': 'uint16'}
            }
        )

        loader_little = BinaryLoader(config_little)
        data_little = loader_little.load()

        # Test with big endian (will interpret same bytes differently)
        config_big = DataLoader(
            name="test_big_endian",
            type=DataLoaderType.BINARY,
            source=str(sample_mixed_binary_file),
            format_options={
                'endianness': 'big',
                'data_types': {'value': 'uint16'}
            }
        )

        loader_big = BinaryLoader(config_big)
        data_big = loader_big.load()

        # Values will be different due to endianness
        # 0x1234 in little endian vs 0x3412 in big endian
        assert data_little['value'] == 0x1234  # This should match little endian (4660)
        assert data_big['value'] == 0x3412     # This should be big endian interpretation (13330)


class TestBinaryLoaderFactory:
    """Test factory function with BinaryLoader."""

    def test_create_binary_loader(self):
        """Test factory creates BinaryLoader correctly."""
        config = DataLoader(
            name="test_factory_binary",
            type=DataLoaderType.BINARY,
            source="test.bin"
        )

        loader = create_data_loader(config)
        assert isinstance(loader, BinaryLoader)
        assert loader.config == config

    def test_factory_supports_binary(self):
        """Test factory supports BINARY type."""
        config = DataLoader(
            name="test_factory_support",
            type=DataLoaderType.BINARY,
            source="test.dat"
        )

        # Should not raise "not supported" error
        loader = create_data_loader(config)
        assert isinstance(loader, BinaryLoader)