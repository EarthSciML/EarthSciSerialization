"""
Tests for data loader registry and plugin system.
"""

import pytest
import tempfile
import json
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock

from esm_format.data_loader_registry import (
    DataLoaderRegistry,
    get_registry,
    register_loader,
    create_data_loader,
    create_auto_loader,
    detect_loader_type,
)
from esm_format.types import DataLoader, DataLoaderType
from esm_format.data_loaders import NetCDFLoader, JSONLoader


class MockLoader:
    """Mock loader for testing registry functionality."""

    def __init__(self, data_loader: DataLoader):
        if data_loader.type != DataLoaderType.CSV:
            raise ValueError(f"Expected DataLoaderType.CSV, got {data_loader.type}")
        self.config = data_loader

    def load(self):
        return {"mock": "data"}


class TestDataLoaderRegistry:
    """Tests for DataLoaderRegistry class."""

    def test_registry_initialization(self):
        """Test registry initialization with builtin loaders."""
        registry = DataLoaderRegistry()

        # Should have NetCDF and JSON loaders registered
        registered = registry.list_registered_loaders()
        assert DataLoaderType.NETCDF in registered
        assert DataLoaderType.JSON in registered

        # Check NetCDF loader details
        netcdf_info = registered[DataLoaderType.NETCDF]
        assert netcdf_info['class'] == NetCDFLoader
        assert '.nc' in netcdf_info['extensions']
        assert 'application/x-netcdf' in netcdf_info['mime_types']

        # Check JSON loader details
        json_info = registered[DataLoaderType.JSON]
        assert json_info['class'] == JSONLoader
        assert '.json' in json_info['extensions']
        assert 'application/json' in json_info['mime_types']

    def test_register_new_loader(self):
        """Test registering a new loader type."""
        registry = DataLoaderRegistry()

        registry.register_loader(
            DataLoaderType.CSV,
            MockLoader,
            extensions=['.csv', '.tsv'],
            mime_types=['text/csv']
        )

        # Check that loader is registered
        registered = registry.list_registered_loaders()
        assert DataLoaderType.CSV in registered

        csv_info = registered[DataLoaderType.CSV]
        assert csv_info['class'] == MockLoader
        assert '.csv' in csv_info['extensions']
        assert '.tsv' in csv_info['extensions']
        assert 'text/csv' in csv_info['mime_types']

    def test_register_duplicate_loader_error(self):
        """Test that registering the same type with different class raises error."""
        registry = DataLoaderRegistry()

        # Register CSV loader first time
        registry.register_loader(DataLoaderType.CSV, MockLoader)

        # Try to register same type with different class - should raise error
        with pytest.raises(ValueError, match="is already registered"):
            registry.register_loader(DataLoaderType.CSV, NetCDFLoader)

        # But registering same type with same class should work
        registry.register_loader(DataLoaderType.CSV, MockLoader)  # Should not raise

    def test_unregister_loader(self):
        """Test unregistering a loader."""
        registry = DataLoaderRegistry()

        # Register then unregister CSV loader
        registry.register_loader(
            DataLoaderType.CSV,
            MockLoader,
            extensions=['.csv'],
            mime_types=['text/csv']
        )

        registry.unregister_loader(DataLoaderType.CSV)

        # Check that loader is removed
        registered = registry.list_registered_loaders()
        assert DataLoaderType.CSV not in registered

        # Check that extension mapping is cleaned up
        assert registry.detect_loader_type('test.csv') is None

    def test_unregister_nonexistent_loader_error(self):
        """Test unregistering a non-existent loader raises error."""
        registry = DataLoaderRegistry()

        with pytest.raises(ValueError, match="is not registered"):
            registry.unregister_loader(DataLoaderType.CSV)

    def test_get_loader_class(self):
        """Test getting loader class by type."""
        registry = DataLoaderRegistry()

        # Test built-in loader
        netcdf_class = registry.get_loader_class(DataLoaderType.NETCDF)
        assert netcdf_class == NetCDFLoader

        # Test custom loader
        registry.register_loader(DataLoaderType.CSV, MockLoader)
        csv_class = registry.get_loader_class(DataLoaderType.CSV)
        assert csv_class == MockLoader

    def test_get_nonexistent_loader_class_error(self):
        """Test getting non-existent loader class raises error."""
        registry = DataLoaderRegistry()

        with pytest.raises(ValueError, match="is not registered"):
            registry.get_loader_class(DataLoaderType.CSV)

    def test_detect_loader_type_by_extension(self):
        """Test loader type detection by file extension."""
        registry = DataLoaderRegistry()

        # Test built-in extensions
        assert registry.detect_loader_type('test.nc') == DataLoaderType.NETCDF
        assert registry.detect_loader_type('test.json') == DataLoaderType.JSON
        assert registry.detect_loader_type('test.jsonl') == DataLoaderType.JSON

        # Test case insensitive
        assert registry.detect_loader_type('TEST.NC') == DataLoaderType.NETCDF

        # Test custom extension
        registry.register_loader(DataLoaderType.CSV, MockLoader, extensions=['.csv'])
        assert registry.detect_loader_type('data.csv') == DataLoaderType.CSV

        # Test unknown extension
        assert registry.detect_loader_type('unknown.xyz') is None

    @patch('mimetypes.guess_type')
    @patch('pathlib.Path.exists')
    def test_detect_loader_type_by_mime_type(self, mock_exists, mock_guess_type):
        """Test loader type detection by MIME type."""
        registry = DataLoaderRegistry()

        mock_exists.return_value = True
        mock_guess_type.return_value = ('application/json', None)

        # Should detect JSON by MIME type even without extension
        assert registry.detect_loader_type('data') == DataLoaderType.JSON

        # Test NetCDF MIME type
        mock_guess_type.return_value = ('application/x-netcdf', None)
        assert registry.detect_loader_type('data') == DataLoaderType.NETCDF

    def test_create_loader(self):
        """Test creating loader instances."""
        registry = DataLoaderRegistry()

        # Test creating NetCDF loader - should succeed with registry
        netcdf_config = DataLoader(
            name="test",
            type=DataLoaderType.NETCDF,
            source="test.nc"
        )

        # Should successfully create NetCDFLoader instance
        loader = registry.create_loader(netcdf_config)
        assert isinstance(loader, NetCDFLoader)

        # Test with unregistered loader type
        csv_config = DataLoader(
            name="test",
            type=DataLoaderType.CSV,
            source="test.csv"
        )

        with pytest.raises(ValueError, match="is not registered"):
            registry.create_loader(csv_config)

    def test_create_auto_loader(self):
        """Test automatic loader creation."""
        registry = DataLoaderRegistry()

        # Create a temporary JSON file for testing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump({"test": "data"}, tmp_file)
            tmp_file_path = tmp_file.name

        try:
            # Test auto-detection and creation
            loader = registry.create_auto_loader("test", tmp_file_path)
            assert isinstance(loader, JSONLoader)

            # Test with variables and format options
            loader = registry.create_auto_loader(
                "test",
                tmp_file_path,
                variables=["test"],
                format_options={"type_coercion": False}
            )
            assert isinstance(loader, JSONLoader)
            assert loader.config.variables == ["test"]
            assert loader.config.format_options["type_coercion"] is False

            # Test unknown file type
            with pytest.raises(ValueError, match="Cannot detect suitable loader"):
                registry.create_auto_loader("test", "unknown.xyz")

        finally:
            Path(tmp_file_path).unlink()

    def test_loader_chains(self):
        """Test loader chain registration and retrieval."""
        registry = DataLoaderRegistry()

        # Register a chain
        chain = [DataLoaderType.JSON, DataLoaderType.NETCDF]
        registry.register_loader_chain("json_to_netcdf", chain)

        # Retrieve the chain
        retrieved_chain = registry.get_loader_chain("json_to_netcdf")
        assert retrieved_chain == chain

        # Check that modifying the retrieved chain doesn't affect the stored one
        retrieved_chain.append(DataLoaderType.CSV)
        stored_chain = registry.get_loader_chain("json_to_netcdf")
        assert len(stored_chain) == 2

    def test_loader_chains_validation(self):
        """Test loader chain validation."""
        registry = DataLoaderRegistry()

        # Test with unregistered loader type
        with pytest.raises(ValueError, match="in chain is not registered"):
            registry.register_loader_chain("invalid", [DataLoaderType.CSV])

        # Test retrieving non-existent chain
        with pytest.raises(KeyError, match="is not registered"):
            registry.get_loader_chain("nonexistent")

    def test_discover_plugins(self):
        """Test plugin discovery functionality."""
        registry = DataLoaderRegistry()

        # Test with non-existent directory
        plugin_count = registry.discover_plugins("/nonexistent/path")
        assert plugin_count == 0

        # Test with empty directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            plugin_count = registry.discover_plugins(tmp_dir)
            assert plugin_count == 0

    @patch('esm_format.data_loader_registry.import_module')
    def test_discover_plugins_with_mock_plugin(self, mock_import):
        """Test plugin discovery with a mock plugin."""
        registry = DataLoaderRegistry()

        # Create temporary plugin directory with a mock plugin file
        with tempfile.TemporaryDirectory() as tmp_dir:
            plugin_file = Path(tmp_dir) / "test_plugin.py"
            plugin_file.write_text("# Mock plugin file")

            # Mock the imported module
            mock_module = MagicMock()
            mock_module.register_loader = MagicMock()
            mock_import.return_value = mock_module

            plugin_count = registry.discover_plugins(tmp_dir)
            assert plugin_count == 1
            mock_module.register_loader.assert_called_once_with(registry)


class TestGlobalRegistryFunctions:
    """Tests for global registry convenience functions."""

    def test_get_registry(self):
        """Test getting the global registry instance."""
        registry = get_registry()
        assert isinstance(registry, DataLoaderRegistry)

        # Should return the same instance
        registry2 = get_registry()
        assert registry is registry2

    def test_register_loader(self):
        """Test global register_loader function."""
        initial_count = len(get_registry().list_registered_loaders())

        register_loader(DataLoaderType.BINARY, MockLoader, extensions=['.bin'])

        # Check that loader was registered
        registry = get_registry()
        registered = registry.list_registered_loaders()
        assert DataLoaderType.BINARY in registered
        assert len(registered) == initial_count + 1

        # Clean up
        registry.unregister_loader(DataLoaderType.BINARY)

    def test_create_data_loader_global(self):
        """Test global create_data_loader function."""
        # Create a temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump({"test": "data"}, tmp_file)
            tmp_file_path = tmp_file.name

        try:
            config = DataLoader(
                name="test",
                type=DataLoaderType.JSON,
                source=tmp_file_path
            )

            loader = create_data_loader(config)
            assert isinstance(loader, JSONLoader)

        finally:
            Path(tmp_file_path).unlink()

    def test_create_auto_loader_global(self):
        """Test global create_auto_loader function."""
        # Create a temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump({"test": "data"}, tmp_file)
            tmp_file_path = tmp_file.name

        try:
            loader = create_auto_loader("test", tmp_file_path)
            assert isinstance(loader, JSONLoader)

        finally:
            Path(tmp_file_path).unlink()

    def test_detect_loader_type_global(self):
        """Test global detect_loader_type function."""
        assert detect_loader_type('test.json') == DataLoaderType.JSON
        assert detect_loader_type('test.nc') == DataLoaderType.NETCDF
        assert detect_loader_type('test.xyz') is None


class TestRegistryIntegration:
    """Integration tests for the registry system."""

    def test_backward_compatibility(self):
        """Test that the old create_data_loader function still works."""
        # Import the old function from data_loaders module
        from esm_format.data_loaders import create_data_loader as old_create_loader

        # Create a temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump({"test": "data"}, tmp_file)
            tmp_file_path = tmp_file.name

        try:
            config = DataLoader(
                name="test",
                type=DataLoaderType.JSON,
                source=tmp_file_path
            )

            # The old function should delegate to the registry
            loader = old_create_loader(config)
            assert isinstance(loader, JSONLoader)

        finally:
            Path(tmp_file_path).unlink()

    def test_registry_extension_override(self):
        """Test that custom extensions can override built-in ones."""
        registry = DataLoaderRegistry()

        # Register a custom loader for .json files
        class CustomJSONLoader:
            def __init__(self, data_loader):
                self.config = data_loader

        # This should override the built-in JSON loader for .json files
        registry.register_loader(
            DataLoaderType.BINARY,  # Use a different type
            CustomJSONLoader,
            extensions=['.json']  # Override .json
        )

        # The .json extension should now map to BINARY type
        detected_type = registry.detect_loader_type('test.json')
        assert detected_type == DataLoaderType.BINARY

        # Clean up
        registry.unregister_loader(DataLoaderType.BINARY)