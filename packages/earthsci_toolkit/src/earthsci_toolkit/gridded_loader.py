"""Gridded data loader implementation for NetCDF and multidimensional datasets."""

import numpy as np
from typing import Dict, Any, List, Optional, Union, Tuple
from pathlib import Path
import warnings

from .esm_types import DataLoader, DataLoaderType


class GriddedValidationError(Exception):
    """Raised when gridded data validation fails."""
    pass


class GriddedDataLoader:
    """Gridded data loader for NetCDF files and multidimensional datasets."""

    def __init__(self, data_loader: DataLoader):
        """Initialize gridded data loader with DataLoader configuration.

        Args:
            data_loader: DataLoader configuration object
        """
        if data_loader.type != DataLoaderType.GRIDDED_DATA:
            raise ValueError(f"Gridded loader only supports GRIDDED_DATA type, got {data_loader.type}")

        self.config = data_loader
        self.source = data_loader.source
        self.format_options = data_loader.format_options or {}
        self.variables = data_loader.variables or []

    def load(self) -> Dict[str, Any]:
        """Load gridded data from NetCDF or similar format.

        Returns:
            Dict[str, Any]: Dictionary containing loaded variables and metadata

        Raises:
            GriddedValidationError: If validation fails
            FileNotFoundError: If data file doesn't exist
        """
        try:
            # Validate file exists
            file_path = Path(self.source)
            if not file_path.exists():
                raise FileNotFoundError(f"Gridded data file not found: {self.source}")

            # Determine file format and load accordingly
            if file_path.suffix.lower() in ['.nc', '.netcdf', '.nc4']:
                return self._load_netcdf()
            elif file_path.suffix.lower() in ['.h5', '.hdf5']:
                return self._load_hdf5()
            else:
                return self._load_generic()

        except Exception as e:
            if isinstance(e, (GriddedValidationError, FileNotFoundError)):
                raise
            raise GriddedValidationError(f"Gridded data loading failed: {e}")

    def _load_netcdf(self) -> Dict[str, Any]:
        """Load NetCDF files using xarray if available, fallback to netCDF4."""
        try:
            # Try xarray first (more convenient)
            import xarray as xr
            ds = xr.open_dataset(self.source)

            result = {
                'data': ds,
                'type': 'xarray_dataset',
                'dimensions': dict(ds.dims),
                'coordinates': {name: ds.coords[name].values for name in ds.coords},
                'metadata': dict(ds.attrs)
            }

            # Filter to requested variables if specified
            if self.variables:
                missing_vars = [var for var in self.variables if var not in ds.data_vars]
                if missing_vars:
                    warnings.warn(f"Requested variables not found: {missing_vars}")
                available_vars = [var for var in self.variables if var in ds.data_vars]
                if available_vars:
                    result['data'] = ds[available_vars]

            return result

        except ImportError:
            # Fallback to netCDF4
            try:
                import netCDF4 as nc
                dataset = nc.Dataset(self.source, 'r')

                result = {
                    'data': dataset,
                    'type': 'netcdf4_dataset',
                    'dimensions': {name: len(dataset.dimensions[name]) for name in dataset.dimensions},
                    'variables': {name: dataset.variables[name] for name in dataset.variables},
                    'metadata': dict(dataset.__dict__)
                }

                return result

            except ImportError:
                raise GriddedValidationError(
                    "NetCDF support requires either xarray or netCDF4 library. "
                    "Install with: pip install xarray netcdf4"
                )

    def _load_hdf5(self) -> Dict[str, Any]:
        """Load HDF5 files."""
        try:
            import h5py

            with h5py.File(self.source, 'r') as f:
                result = {
                    'data': {},
                    'type': 'hdf5_dict',
                    'metadata': dict(f.attrs)
                }

                # Load variables
                variables_to_load = self.variables if self.variables else list(f.keys())
                for var_name in variables_to_load:
                    if var_name in f:
                        result['data'][var_name] = f[var_name][:]
                        if hasattr(f[var_name], 'attrs'):
                            result['data'][f'{var_name}_attrs'] = dict(f[var_name].attrs)
                    else:
                        warnings.warn(f"Variable '{var_name}' not found in HDF5 file")

                return result

        except ImportError:
            raise GriddedValidationError(
                "HDF5 support requires h5py library. Install with: pip install h5py"
            )

    def _load_generic(self) -> Dict[str, Any]:
        """Load generic binary or text files based on format options."""
        format_type = self.format_options.get('format', 'binary')

        if format_type == 'binary':
            return self._load_binary()
        elif format_type == 'text':
            return self._load_text_grid()
        else:
            raise GriddedValidationError(f"Unsupported format type: {format_type}")

    def _load_binary(self) -> Dict[str, Any]:
        """Load binary grid data."""
        dtype = self.format_options.get('dtype', np.float64)
        shape = self.format_options.get('shape', None)

        if shape is None:
            raise GriddedValidationError("Binary format requires 'shape' in format_options")

        try:
            data = np.fromfile(self.source, dtype=dtype).reshape(shape)
            return {
                'data': data,
                'type': 'numpy_array',
                'shape': shape,
                'dtype': str(dtype),
                'metadata': self.format_options
            }
        except Exception as e:
            raise GriddedValidationError(f"Failed to load binary data: {e}")

    def _load_text_grid(self) -> Dict[str, Any]:
        """Load text-based grid data."""
        try:
            # Load as text and parse
            with open(self.source, 'r') as f:
                lines = f.readlines()

            # Skip header lines if specified
            skip_lines = self.format_options.get('skip_lines', 0)
            data_lines = lines[skip_lines:]

            # Parse numeric data
            data = []
            for line in data_lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    values = [float(x) for x in line.split()]
                    data.append(values)

            data_array = np.array(data)

            return {
                'data': data_array,
                'type': 'numpy_array',
                'shape': data_array.shape,
                'metadata': self.format_options
            }

        except Exception as e:
            raise GriddedValidationError(f"Failed to load text grid data: {e}")


def load_gridded_data(data_loader: DataLoader) -> Dict[str, Any]:
    """Convenience function to load gridded data.

    Args:
        data_loader: DataLoader configuration

    Returns:
        Dict[str, Any]: Loaded gridded data
    """
    loader = GriddedDataLoader(data_loader)
    return loader.load()