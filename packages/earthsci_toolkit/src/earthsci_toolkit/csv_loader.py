"""CSV data loader implementation with pandas integration."""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Union, Tuple
from pathlib import Path
import warnings

from .esm_types import DataLoader, DataLoaderType


class CSVValidationError(Exception):
    """Raised when CSV validation fails."""
    pass


class CSVLoader:
    """CSV data loader with pandas integration and validation."""

    def __init__(self, data_loader: DataLoader):
        """Initialize CSV loader with DataLoader configuration.

        Args:
            data_loader: DataLoader configuration object
        """
        # CSV loader can handle different types of data
        csv_compatible_types = {DataLoaderType.EMISSIONS, DataLoaderType.TIMESERIES, DataLoaderType.STATIC}
        if data_loader.type not in csv_compatible_types:
            raise ValueError(f"CSV loader supports {csv_compatible_types}, got {data_loader.type}")

        self.config = data_loader
        self.source = data_loader.source
        self.format_options = data_loader.format_options or {}
        self.variables = data_loader.variables or []

    def load(self) -> pd.DataFrame:
        """Load CSV data with validation.

        Returns:
            pandas.DataFrame: Loaded and validated data

        Raises:
            CSVValidationError: If validation fails
            FileNotFoundError: If CSV file doesn't exist
            pd.errors.ParserError: If CSV parsing fails
        """
        try:
            # Validate file exists
            file_path = Path(self.source)
            if not file_path.exists():
                raise FileNotFoundError(f"CSV file not found: {self.source}")

            # Prepare pandas read_csv options
            read_options = self._prepare_read_options()

            # Load CSV with pandas
            df = pd.read_csv(self.source, **read_options)

            # Validate the loaded data
            self._validate_dataframe(df)

            # Handle missing values
            df = self._handle_missing_values(df)

            # Filter to requested variables if specified
            if self.variables:
                df = self._filter_variables(df)

            return df

        except pd.errors.ParserError as e:
            raise CSVValidationError(f"CSV parsing failed: {e}")
        except Exception as e:
            if isinstance(e, (CSVValidationError, FileNotFoundError)):
                raise
            raise CSVValidationError(f"CSV loading failed: {e}")

    def _prepare_read_options(self) -> Dict[str, Any]:
        """Prepare options for pandas read_csv."""
        options = {}

        # Apply common options from format_options
        option_mapping = {
            'delimiter': 'sep',
            'sep': 'sep',
            'header': 'header',
            'skiprows': 'skiprows',
            'na_values': 'na_values',
            'encoding': 'encoding',
            'dtype': 'dtype',
        }

        for config_key, pandas_key in option_mapping.items():
            if config_key in self.format_options:
                options[pandas_key] = self.format_options[config_key]

        # Set reasonable defaults
        if 'sep' not in options:
            options['sep'] = ','
        if 'header' not in options:
            options['header'] = 0

        return options

    def _validate_dataframe(self, df: pd.DataFrame) -> None:
        """Validate the loaded DataFrame.

        Args:
            df: DataFrame to validate

        Raises:
            CSVValidationError: If validation fails
        """
        # Check if DataFrame is empty
        if df.empty:
            raise CSVValidationError("CSV file is empty or contains no valid data")

        # Validate column types if specified
        if 'column_types' in self.format_options:
            self._validate_column_types(df)

        # Check for all-null columns which might indicate parsing issues
        null_columns = df.columns[df.isnull().all()]
        if len(null_columns) > 0:
            warnings.warn(f"Found columns with all null values: {list(null_columns)}")

        # Check for duplicate column names
        if df.columns.duplicated().any():
            duplicate_cols = df.columns[df.columns.duplicated()].tolist()
            raise CSVValidationError(f"Duplicate column names found: {duplicate_cols}")

    def _validate_column_types(self, df: pd.DataFrame) -> None:
        """Validate column data types.

        Args:
            df: DataFrame to validate

        Raises:
            CSVValidationError: If type validation fails
        """
        expected_types = self.format_options['column_types']

        for column, expected_type in expected_types.items():
            if column not in df.columns:
                raise CSVValidationError(f"Expected column '{column}' not found in CSV")

            # Try to convert to expected type
            try:
                if expected_type in ['int', 'integer']:
                    pd.to_numeric(df[column], errors='coerce', downcast='integer')
                elif expected_type in ['float', 'number', 'numeric']:
                    pd.to_numeric(df[column], errors='coerce')
                elif expected_type in ['datetime', 'timestamp']:
                    pd.to_datetime(df[column], errors='coerce')
                elif expected_type == 'string':
                    # String is always valid
                    pass
                else:
                    warnings.warn(f"Unknown column type '{expected_type}' for column '{column}'")
            except Exception as e:
                raise CSVValidationError(f"Column '{column}' cannot be converted to {expected_type}: {e}")

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values based on configuration.

        Args:
            df: DataFrame to process

        Returns:
            DataFrame with missing values handled
        """
        if 'missing_value_strategy' not in self.format_options:
            return df

        strategy = self.format_options['missing_value_strategy']

        if strategy == 'drop_rows':
            df = df.dropna()
        elif strategy == 'drop_columns':
            df = df.dropna(axis=1)
        elif strategy == 'fill_forward':
            df = df.fillna(method='ffill')
        elif strategy == 'fill_backward':
            df = df.fillna(method='bfill')
        elif strategy == 'fill_zero':
            df = df.fillna(0)
        elif strategy == 'fill_mean':
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            df[numeric_columns] = df[numeric_columns].fillna(df[numeric_columns].mean())
        elif isinstance(strategy, dict):
            # Column-specific strategies
            for column, col_strategy in strategy.items():
                if column in df.columns:
                    if col_strategy == 'mean':
                        df[column] = df[column].fillna(df[column].mean())
                    elif col_strategy == 'median':
                        df[column] = df[column].fillna(df[column].median())
                    elif isinstance(col_strategy, (int, float, str)):
                        df[column] = df[column].fillna(col_strategy)

        return df

    def _filter_variables(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter DataFrame to requested variables.

        Args:
            df: DataFrame to filter

        Returns:
            Filtered DataFrame

        Raises:
            CSVValidationError: If requested variables not found
        """
        missing_variables = [var for var in self.variables if var not in df.columns]
        if missing_variables:
            raise CSVValidationError(f"Requested variables not found in CSV: {missing_variables}")

        return df[self.variables]


def load_csv_data(data_loader: DataLoader) -> pd.DataFrame:
    """Convenience function to load CSV data.

    Args:
        data_loader: DataLoader configuration

    Returns:
        pandas.DataFrame: Loaded CSV data
    """
    loader = CSVLoader(data_loader)
    return loader.load()