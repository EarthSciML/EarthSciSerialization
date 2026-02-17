"""
Data loader registry and plugin system for ESM Format.

This module provides a registry system allowing runtime registration of new loaders,
plugin discovery, loader selection based on file extensions/mime types, and loader
chaining capabilities.
"""

import os
import mimetypes
from pathlib import Path
from typing import Dict, List, Type, Optional, Callable, Any, Union
from importlib import import_module
import warnings

from .types import DataLoader, DataLoaderType
from .data_loaders import NetCDFLoader, JSONLoader, BinaryLoader, DatabaseLoader, HDF5Loader, GRIBLoader, StreamingLoader, RemoteLoader


class DataLoaderRegistry:
    """
    Registry for data loader implementations.

    Manages loader registration, discovery, and selection based on various criteria
    including file extensions, MIME types, and explicit loader types.
    """

    def __init__(self):
        """Initialize the registry with built-in loaders."""
        self._loaders: Dict[DataLoaderType, Type] = {}
        self._extension_mapping: Dict[str, DataLoaderType] = {}
        self._mime_type_mapping: Dict[str, DataLoaderType] = {}
        self._loader_chains: Dict[str, List[DataLoaderType]] = {}

        # Register built-in loaders
        self._register_builtin_loaders()

    def _register_builtin_loaders(self):
        """Register the built-in data loaders."""
        # Register NetCDF loader
        self.register_loader(
            DataLoaderType.NETCDF,
            NetCDFLoader,
            extensions=['.nc', '.netcdf', '.nc4'],
            mime_types=['application/x-netcdf']
        )

        # Register JSON loader
        self.register_loader(
            DataLoaderType.JSON,
            JSONLoader,
            extensions=['.json', '.jsonl'],
            mime_types=['application/json', 'application/jsonl']
        )

        # Register Binary loader
        self.register_loader(
            DataLoaderType.BINARY,
            BinaryLoader,
            extensions=['.bin', '.dat', '.raw', '.data'],
            mime_types=['application/octet-stream']
        )

        # Register Database loader
        self.register_loader(
            DataLoaderType.DATABASE,
            DatabaseLoader,
            extensions=['.db', '.sqlite', '.sqlite3'],
            mime_types=['application/x-sqlite3']
        )

        # Register HDF5 loader
        self.register_loader(
            DataLoaderType.HDF5,
            HDF5Loader,
            extensions=['.h5', '.hdf5', '.hdf'],
            mime_types=['application/x-hdf', 'application/x-hdf5']
        )

        # Register GRIB loader
        self.register_loader(
            DataLoaderType.GRIB,
            GRIBLoader,
            extensions=['.grib', '.grib1', '.grib2', '.grb', '.grb2'],
            mime_types=['application/x-grib']
        )

        # Register Streaming loader
        self.register_loader(
            DataLoaderType.STREAMING,
            StreamingLoader,
            extensions=[],  # Streaming doesn't use file extensions
            mime_types=[]   # Streaming doesn't use MIME types
        )

        # Register Remote loader
        self.register_loader(
            DataLoaderType.REMOTE,
            RemoteLoader,
            extensions=[],  # Remote doesn't use file extensions (URLs)
            mime_types=[]   # Remote doesn't use MIME types (determined at runtime)
        )

    def register_loader(
        self,
        loader_type: DataLoaderType,
        loader_class: Type,
        extensions: Optional[List[str]] = None,
        mime_types: Optional[List[str]] = None
    ) -> None:
        """
        Register a data loader implementation.

        Args:
            loader_type: Type of the data loader
            loader_class: Class implementing the data loader
            extensions: List of file extensions this loader handles
            mime_types: List of MIME types this loader handles

        Raises:
            ValueError: If loader_type is already registered with a different class
        """
        # Check if loader is already registered with a different class
        if loader_type in self._loaders and self._loaders[loader_type] != loader_class:
            raise ValueError(f"Loader type {loader_type} is already registered with class {self._loaders[loader_type]}")

        self._loaders[loader_type] = loader_class

        # Register file extensions
        if extensions:
            for ext in extensions:
                if not ext.startswith('.'):
                    ext = '.' + ext
                self._extension_mapping[ext.lower()] = loader_type

        # Register MIME types
        if mime_types:
            for mime_type in mime_types:
                self._mime_type_mapping[mime_type.lower()] = loader_type

    def unregister_loader(self, loader_type: DataLoaderType) -> None:
        """
        Unregister a data loader.

        Args:
            loader_type: Type of loader to unregister

        Raises:
            ValueError: If loader_type is not registered
        """
        if loader_type not in self._loaders:
            raise ValueError(f"Loader type {loader_type} is not registered")

        # Remove from main registry
        del self._loaders[loader_type]

        # Remove from extension mappings
        extensions_to_remove = [ext for ext, ltype in self._extension_mapping.items() if ltype == loader_type]
        for ext in extensions_to_remove:
            del self._extension_mapping[ext]

        # Remove from MIME type mappings
        mime_types_to_remove = [mime for mime, ltype in self._mime_type_mapping.items() if ltype == loader_type]
        for mime_type in mime_types_to_remove:
            del self._mime_type_mapping[mime_type]

    def get_loader_class(self, loader_type: DataLoaderType) -> Type:
        """
        Get the loader class for a given loader type.

        Args:
            loader_type: Type of loader to get

        Returns:
            Loader class

        Raises:
            ValueError: If loader_type is not registered
        """
        if loader_type not in self._loaders:
            raise ValueError(f"Loader type {loader_type} is not registered")

        return self._loaders[loader_type]

    def detect_loader_type(self, source: Union[str, Path]) -> Optional[DataLoaderType]:
        """
        Detect the appropriate loader type based on file extension and/or MIME type.

        Args:
            source: File path or URL to analyze

        Returns:
            Detected loader type, or None if no suitable loader is found
        """
        source_str = str(source)

        # Check if it's a URL (remote source)
        from urllib.parse import urlparse
        parsed = urlparse(source_str)
        if parsed.scheme in ['http', 'https', 'ftp', 'sftp', 's3', 'gs', 'azure']:
            return DataLoaderType.REMOTE

        source_path = Path(source)

        # Try file extension first
        if source_path.suffix:
            extension = source_path.suffix.lower()
            if extension in self._extension_mapping:
                return self._extension_mapping[extension]

        # Try MIME type if file exists
        if source_path.exists():
            mime_type, _ = mimetypes.guess_type(str(source_path))
            if mime_type and mime_type.lower() in self._mime_type_mapping:
                return self._mime_type_mapping[mime_type.lower()]

        return None

    def create_loader(self, data_loader: DataLoader) -> Any:
        """
        Create a loader instance for the given DataLoader configuration.

        Args:
            data_loader: DataLoader configuration

        Returns:
            Loader instance

        Raises:
            ValueError: If the loader type is not supported
        """
        if data_loader.type not in self._loaders:
            raise ValueError(f"Loader type {data_loader.type} is not registered")

        loader_class = self._loaders[data_loader.type]
        return loader_class(data_loader)

    def create_auto_loader(
        self,
        name: str,
        source: Union[str, Path],
        variables: Optional[List[str]] = None,
        format_options: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Automatically create a loader based on file type detection.

        Args:
            name: Name for the loader
            source: File path or URL
            variables: List of variables to load (optional)
            format_options: Format-specific options (optional)

        Returns:
            Loader instance

        Raises:
            ValueError: If no suitable loader can be detected
        """
        loader_type = self.detect_loader_type(source)
        if loader_type is None:
            raise ValueError(f"Cannot detect suitable loader for source: {source}")

        data_loader = DataLoader(
            name=name,
            type=loader_type,
            source=str(source),
            variables=variables or [],
            format_options=format_options or {}
        )

        return self.create_loader(data_loader)

    def register_loader_chain(self, name: str, chain: List[DataLoaderType]) -> None:
        """
        Register a chain of loaders that can be applied sequentially.

        Args:
            name: Name for the loader chain
            chain: List of loader types to apply in order

        Raises:
            ValueError: If any loader type in the chain is not registered
        """
        for loader_type in chain:
            if loader_type not in self._loaders:
                raise ValueError(f"Loader type {loader_type} in chain is not registered")

        self._loader_chains[name] = chain.copy()

    def get_loader_chain(self, name: str) -> List[DataLoaderType]:
        """
        Get a registered loader chain.

        Args:
            name: Name of the loader chain

        Returns:
            List of loader types in the chain

        Raises:
            KeyError: If chain name is not registered
        """
        if name not in self._loader_chains:
            raise KeyError(f"Loader chain '{name}' is not registered")

        return self._loader_chains[name].copy()

    def list_registered_loaders(self) -> Dict[DataLoaderType, Dict[str, Any]]:
        """
        List all registered loaders with their metadata.

        Returns:
            Dictionary mapping loader types to their metadata
        """
        result = {}
        for loader_type, loader_class in self._loaders.items():
            # Get extensions for this loader
            extensions = [ext for ext, ltype in self._extension_mapping.items() if ltype == loader_type]

            # Get MIME types for this loader
            mime_types = [mime for mime, ltype in self._mime_type_mapping.items() if ltype == loader_type]

            result[loader_type] = {
                'class': loader_class,
                'class_name': loader_class.__name__,
                'extensions': extensions,
                'mime_types': mime_types
            }

        return result

    def discover_plugins(self, plugin_dir: Optional[Union[str, Path]] = None) -> int:
        """
        Discover and register data loader plugins from a directory.

        Args:
            plugin_dir: Directory to search for plugins. If None, uses default locations.

        Returns:
            Number of plugins discovered and registered

        Note:
            This is a placeholder for future plugin discovery functionality.
            Plugins should define loaders following the established pattern.
        """
        if plugin_dir is None:
            plugin_dir = Path(__file__).parent / "plugins"
        else:
            plugin_dir = Path(plugin_dir)

        plugins_found = 0

        if plugin_dir.exists() and plugin_dir.is_dir():
            for plugin_file in plugin_dir.glob("*.py"):
                if plugin_file.name.startswith("_"):
                    continue

                try:
                    # This is a simplified plugin discovery mechanism
                    # In a full implementation, plugins would have a standard interface
                    module_name = f"esm_format.plugins.{plugin_file.stem}"
                    module = import_module(module_name)

                    # Look for register_loader function in the plugin
                    if hasattr(module, 'register_loader'):
                        module.register_loader(self)
                        plugins_found += 1

                except Exception as e:
                    warnings.warn(f"Failed to load plugin {plugin_file.name}: {e}")

        return plugins_found


# Global registry instance
_global_registry = DataLoaderRegistry()


def get_registry() -> DataLoaderRegistry:
    """Get the global data loader registry instance."""
    return _global_registry


def register_loader(
    loader_type: DataLoaderType,
    loader_class: Type,
    extensions: Optional[List[str]] = None,
    mime_types: Optional[List[str]] = None
) -> None:
    """
    Register a loader with the global registry.

    Args:
        loader_type: Type of the data loader
        loader_class: Class implementing the data loader
        extensions: List of file extensions this loader handles
        mime_types: List of MIME types this loader handles
    """
    _global_registry.register_loader(loader_type, loader_class, extensions, mime_types)


def create_data_loader(data_loader: DataLoader) -> Any:
    """
    Create a loader instance using the global registry.

    Args:
        data_loader: DataLoader configuration

    Returns:
        Loader instance
    """
    return _global_registry.create_loader(data_loader)


def create_auto_loader(
    name: str,
    source: Union[str, Path],
    variables: Optional[List[str]] = None,
    format_options: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Automatically create a loader based on file type detection using the global registry.

    Args:
        name: Name for the loader
        source: File path or URL
        variables: List of variables to load (optional)
        format_options: Format-specific options (optional)

    Returns:
        Loader instance
    """
    return _global_registry.create_auto_loader(name, source, variables, format_options)


def detect_loader_type(source: Union[str, Path]) -> Optional[DataLoaderType]:
    """
    Detect the appropriate loader type using the global registry.

    Args:
        source: File path or URL to analyze

    Returns:
        Detected loader type, or None if no suitable loader is found
    """
    return _global_registry.detect_loader_type(source)