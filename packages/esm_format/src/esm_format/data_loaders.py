"""
Data loading functionality for ESM Format.

This module provides implementations for loading data from various scientific
data formats, with support for CF conventions and proper metadata handling.
"""

from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import numpy as np

try:
    import xarray as xr
    XARRAY_AVAILABLE = True
except ImportError:
    XARRAY_AVAILABLE = False

from .types import DataLoader, DataLoaderType


class NetCDFLoader:
    """
    NetCDF data loader using xarray for multidimensional scientific data.

    Supports CF conventions, coordinate system validation, and proper metadata extraction.
    Essential for atmospheric and climate data ingestion.
    """

    def __init__(self, data_loader: DataLoader):
        """
        Initialize NetCDF loader with configuration.

        Args:
            data_loader: DataLoader configuration object

        Raises:
            ImportError: If xarray is not available
            ValueError: If data_loader type is not NETCDF
        """
        if not XARRAY_AVAILABLE:
            raise ImportError("xarray and netcdf4 are required for NetCDF loading. "
                            "Install with: pip install xarray netcdf4")

        if data_loader.type != DataLoaderType.NETCDF:
            raise ValueError(f"Expected DataLoaderType.NETCDF, got {data_loader.type}")

        self.config = data_loader
        self.dataset: Optional[xr.Dataset] = None

    def load(self) -> xr.Dataset:
        """
        Load the NetCDF dataset from the configured source.

        Returns:
            xarray Dataset containing the loaded data

        Raises:
            FileNotFoundError: If the source file doesn't exist
            OSError: If the file can't be opened (corrupt, wrong format, etc.)
        """
        source_path = Path(self.config.source)

        if not source_path.exists():
            raise FileNotFoundError(f"NetCDF file not found: {source_path}")

        try:
            # Load with xarray, applying any format options
            format_options = self.config.format_options or {}

            # Extract xarray-specific options
            chunks = format_options.get('chunks', None)
            decode_times = format_options.get('decode_times', True)
            decode_cf = format_options.get('decode_cf', True)
            mask_and_scale = format_options.get('mask_and_scale', True)

            self.dataset = xr.open_dataset(
                source_path,
                chunks=chunks,
                decode_times=decode_times,
                decode_cf=decode_cf,
                mask_and_scale=mask_and_scale
            )

            # Filter to requested variables if specified
            if self.config.variables:
                available_vars = set(self.dataset.data_vars.keys())
                requested_vars = set(self.config.variables)

                # Check for missing variables
                missing_vars = requested_vars - available_vars
                if missing_vars:
                    raise ValueError(f"Requested variables not found in dataset: {missing_vars}")

                # Select only requested variables, keep all coordinates
                self.dataset = self.dataset[list(requested_vars)]

            return self.dataset

        except ValueError:
            # Re-raise ValueError without wrapping
            raise
        except Exception as e:
            raise OSError(f"Failed to load NetCDF file {source_path}: {e}") from e

    def validate_cf_conventions(self) -> Dict[str, Any]:
        """
        Validate CF (Climate and Forecast) conventions compliance.

        Returns:
            Dictionary with validation results and metadata
        """
        if self.dataset is None:
            raise RuntimeError("Dataset must be loaded before validation")

        validation_result = {
            'cf_compliant': True,
            'warnings': [],
            'errors': [],
            'metadata': {}
        }

        # Check for CF convention version
        conventions = self.dataset.attrs.get('Conventions', '')
        validation_result['metadata']['conventions'] = conventions

        if 'CF-' not in conventions:
            validation_result['warnings'].append("No CF conventions declared in global attributes")

        # Validate coordinate variables
        for coord_name, coord in self.dataset.coords.items():
            # Check for required attributes
            if not coord.attrs.get('units'):
                validation_result['warnings'].append(f"Coordinate '{coord_name}' missing units attribute")

            # Check for standard_name or long_name
            if not coord.attrs.get('standard_name') and not coord.attrs.get('long_name'):
                validation_result['warnings'].append(f"Coordinate '{coord_name}' missing standard_name or long_name")

        # Validate data variables
        for var_name, var in self.dataset.data_vars.items():
            # Check for units
            if not var.attrs.get('units'):
                validation_result['warnings'].append(f"Variable '{var_name}' missing units attribute")

            # Check for fill value consistency
            fill_value = var.attrs.get('_FillValue')
            missing_value = var.attrs.get('missing_value')

            if fill_value is not None and missing_value is not None:
                if fill_value != missing_value:
                    validation_result['warnings'].append(
                        f"Variable '{var_name}' has inconsistent _FillValue and missing_value"
                    )

        # Set overall compliance based on errors
        validation_result['cf_compliant'] = len(validation_result['errors']) == 0

        return validation_result

    def get_variable_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Extract metadata for all variables in the dataset.

        Returns:
            Dictionary mapping variable names to their metadata
        """
        if self.dataset is None:
            raise RuntimeError("Dataset must be loaded before extracting variable info")

        variable_info = {}

        # Include both data variables and coordinates
        all_vars = {**self.dataset.data_vars, **self.dataset.coords}

        for var_name, var in all_vars.items():
            # Get attributes, handling potential empty attributes gracefully
            attrs = dict(var.attrs) if hasattr(var, 'attrs') else {}

            info = {
                'dimensions': list(var.dims),
                'shape': var.shape,
                'dtype': str(var.dtype),
                'attributes': attrs,
                'is_coordinate': var_name in self.dataset.coords
            }

            # Add coordinate information if it's a data variable
            if var_name in self.dataset.data_vars:
                coords = {}
                for dim in var.dims:
                    if dim in self.dataset.coords:
                        coord = self.dataset.coords[dim]
                        coord_attrs = dict(coord.attrs) if hasattr(coord, 'attrs') else {}
                        coords[dim] = {
                            'size': coord.size,
                            'units': coord_attrs.get('units', ''),
                            'long_name': coord_attrs.get('long_name', ''),
                            'standard_name': coord_attrs.get('standard_name', '')
                        }
                info['coordinates'] = coords

            variable_info[var_name] = info

        return variable_info

    def close(self):
        """Close the dataset and free resources."""
        if self.dataset is not None:
            self.dataset.close()
            self.dataset = None


def create_data_loader(data_loader: DataLoader) -> Union[NetCDFLoader]:
    """
    Factory function to create appropriate data loader based on type.

    Args:
        data_loader: DataLoader configuration object

    Returns:
        Appropriate data loader instance

    Raises:
        ValueError: If data loader type is not supported
    """
    if data_loader.type == DataLoaderType.NETCDF:
        return NetCDFLoader(data_loader)
    else:
        raise ValueError(f"Data loader type {data_loader.type} not yet implemented")