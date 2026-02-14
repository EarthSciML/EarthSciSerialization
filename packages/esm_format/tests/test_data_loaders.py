"""
Tests for data loading functionality.
"""

import pytest
import tempfile
import json
import numpy as np
from pathlib import Path

# Import the data loading functionality
from esm_format.data_loaders import NetCDFLoader, JSONLoader, create_data_loader
from esm_format.types import DataLoader, DataLoaderType

# Try to import xarray for creating test data
try:
    import xarray as xr
    XARRAY_AVAILABLE = True
except ImportError:
    XARRAY_AVAILABLE = False


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
        config = DataLoader(
            name="test",
            type=DataLoaderType.HDF5,  # Not implemented yet
            source="test.h5"
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