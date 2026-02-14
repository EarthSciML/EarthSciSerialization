"""
Tests for data loading functionality.
"""

import pytest
import tempfile
import numpy as np
from pathlib import Path

# Import the data loading functionality
from esm_format.data_loaders import NetCDFLoader, create_data_loader
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

        with pytest.raises(ValueError, match="not yet implemented"):
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