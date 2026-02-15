"""
Data loading functionality for ESM Format.

This module provides implementations for loading data from various scientific
data formats, with support for CF conventions and proper metadata handling.
"""

from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import json
import sqlite3
import numpy as np
import threading
from contextlib import contextmanager
from urllib.parse import urlparse

try:
    import xarray as xr
    XARRAY_AVAILABLE = True
except ImportError:
    XARRAY_AVAILABLE = False

try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

try:
    import psycopg2
    import psycopg2.pool
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False

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

try:
    import cfgrib
    import xarray as xr
    CFGRIB_AVAILABLE = True
except ImportError:
    CFGRIB_AVAILABLE = False

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


class JSONLoader:
    """
    JSON data loader with JSONSchema validation and type coercion.

    Supports nested object handling, schema validation, and type coercion capabilities.
    Essential for configuration files and structured metadata ingestion.
    """

    def __init__(self, data_loader: DataLoader):
        """
        Initialize JSON loader with configuration.

        Args:
            data_loader: DataLoader configuration object

        Raises:
            ValueError: If data_loader type is not JSON
        """
        if data_loader.type != DataLoaderType.JSON:
            raise ValueError(f"Expected DataLoaderType.JSON, got {data_loader.type}")

        self.config = data_loader
        self.data: Optional[Any] = None
        self._schema: Optional[Dict[str, Any]] = None

    def load(self) -> Dict[str, Any]:
        """
        Load JSON data from the configured source.

        Returns:
            Dictionary containing the loaded JSON data

        Raises:
            FileNotFoundError: If the source file doesn't exist
            JSONDecodeError: If the file contains invalid JSON
            OSError: If the file can't be read
        """
        source_path = Path(self.config.source)

        if not source_path.exists():
            raise FileNotFoundError(f"JSON file not found: {source_path}")

        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)

            # Apply type coercion if specified
            if self.config.format_options and self.config.format_options.get('type_coercion', True):
                self.data = self._apply_type_coercion(self.data)

            # Filter to requested variables if specified
            if self.config.variables and isinstance(self.data, dict):
                filtered_data = {}
                for var in self.config.variables:
                    if var in self.data:
                        filtered_data[var] = self.data[var]
                    else:
                        # Use dot notation for nested access
                        nested_value = self._get_nested_value(self.data, var)
                        if nested_value is not None:
                            filtered_data[var] = nested_value

                missing_vars = set(self.config.variables) - set(filtered_data.keys())
                if missing_vars:
                    raise ValueError(f"Requested variables not found in JSON: {missing_vars}")

                self.data = filtered_data

            return self.data

        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON in file {source_path}: {e.msg}", e.doc, e.pos) from e
        except ValueError:
            # Re-raise ValueError without wrapping (e.g., missing variables)
            raise
        except Exception as e:
            raise OSError(f"Failed to load JSON file {source_path}: {e}") from e

    def validate_schema(self, schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validate loaded JSON data against a JSONSchema.

        Args:
            schema: JSONSchema to validate against. If None, looks for schema in format_options

        Returns:
            Dictionary with validation results

        Raises:
            RuntimeError: If data must be loaded before validation
            ImportError: If jsonschema is not available
        """
        if self.data is None:
            raise RuntimeError("Data must be loaded before schema validation")

        if not JSONSCHEMA_AVAILABLE:
            raise ImportError("jsonschema library is required for schema validation. "
                            "Install with: pip install jsonschema")

        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        # Get schema from parameter or format_options
        if schema is None and self.config.format_options:
            schema = self.config.format_options.get('schema')

        if schema is None:
            validation_result['warnings'].append("No schema provided for validation")
            return validation_result

        try:
            # Validate the data against the schema
            jsonschema.validate(instance=self.data, schema=schema)
            validation_result['valid'] = True
        except jsonschema.ValidationError as e:
            validation_result['valid'] = False
            validation_result['errors'].append({
                'message': e.message,
                'path': list(e.path) if e.path else [],
                'schema_path': list(e.schema_path) if e.schema_path else []
            })
        except jsonschema.SchemaError as e:
            validation_result['valid'] = False
            validation_result['errors'].append({
                'message': f"Invalid schema: {e.message}",
                'path': [],
                'schema_path': list(e.schema_path) if e.schema_path else []
            })

        return validation_result

    def get_data_info(self) -> Dict[str, Any]:
        """
        Extract information about the loaded JSON data structure.

        Returns:
            Dictionary with data structure information

        Raises:
            RuntimeError: If data must be loaded before extracting info
        """
        if self.data is None:
            raise RuntimeError("Data must be loaded before extracting info")

        return {
            'type': type(self.data).__name__,
            'structure': self._analyze_structure(self.data),
            'size_info': self._get_size_info(self.data)
        }

    def _apply_type_coercion(self, data: Any, current_path: str = "") -> Any:
        """
        Apply type coercion to loaded data based on format options.

        Args:
            data: The loaded JSON data
            current_path: Current path in dot notation for nested coercion

        Returns:
            Data with type coercion applied
        """
        coercion_rules = self.config.format_options.get('coercion_rules', {})

        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                # Build current path
                new_path = f"{current_path}.{key}" if current_path else key

                # Apply specific coercion rules for this path
                if new_path in coercion_rules:
                    result[key] = self._coerce_value(value, coercion_rules[new_path])
                else:
                    # Recursively apply coercion
                    result[key] = self._apply_type_coercion(value, new_path)
            return result
        elif isinstance(data, list):
            return [self._apply_type_coercion(item, current_path) for item in data]
        else:
            return data

    def _coerce_value(self, value: Any, target_type: str) -> Any:
        """
        Coerce a value to the target type.

        Args:
            value: Value to coerce
            target_type: Target type name

        Returns:
            Coerced value
        """
        if target_type == 'float' and isinstance(value, (int, str)):
            try:
                return float(value)
            except (ValueError, TypeError):
                return value
        elif target_type == 'int' and isinstance(value, (float, str)):
            try:
                return int(value)
            except (ValueError, TypeError):
                return value
        elif target_type == 'str':
            return str(value)
        elif target_type == 'bool' and isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        elif target_type == 'numpy_array' and isinstance(value, list):
            try:
                return np.array(value)
            except Exception:
                return value

        return value

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """
        Get a nested value using dot notation.

        Args:
            data: Dictionary to search in
            path: Dot-separated path (e.g., 'metadata.title')

        Returns:
            The nested value or None if not found
        """
        keys = path.split('.')
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None

        return current

    def _analyze_structure(self, data: Any, max_depth: int = 3, current_depth: int = 0) -> Dict[str, Any]:
        """
        Analyze the structure of nested data.

        Args:
            data: Data to analyze
            max_depth: Maximum depth to analyze
            current_depth: Current recursion depth

        Returns:
            Dictionary describing the data structure
        """
        if current_depth >= max_depth:
            return {'type': type(data).__name__, 'truncated': True}

        if isinstance(data, dict):
            structure = {
                'type': 'dict',
                'keys': list(data.keys()),
                'length': len(data)
            }
            if current_depth < max_depth - 1:
                structure['children'] = {
                    key: self._analyze_structure(value, max_depth, current_depth + 1)
                    for key, value in list(data.items())[:10]  # Limit to first 10 items
                }
            return structure

        elif isinstance(data, list):
            structure = {
                'type': 'list',
                'length': len(data)
            }
            if data and current_depth < max_depth - 1:
                structure['element_type'] = self._analyze_structure(data[0], max_depth, current_depth + 1)
            return structure

        else:
            return {
                'type': type(data).__name__,
                'value': data if isinstance(data, (int, float, str, bool, type(None))) else str(data)[:100]
            }

    def _get_size_info(self, data: Any) -> Dict[str, Any]:
        """
        Get size information about the data.

        Args:
            data: Data to analyze

        Returns:
            Dictionary with size information
        """
        import sys

        size_info = {
            'memory_bytes': sys.getsizeof(data),
            'json_length': len(json.dumps(data)) if isinstance(data, (dict, list)) else 0
        }

        if isinstance(data, dict):
            size_info['num_keys'] = len(data)
        elif isinstance(data, list):
            size_info['num_items'] = len(data)

        return size_info


class DatabaseLoader:
    """
    Database data loader supporting SQLite and PostgreSQL.

    Provides connection pooling, query optimization, transaction handling,
    and support for both local SQLite databases and remote PostgreSQL instances.
    Essential for persistent data storage integration.
    """

    def __init__(self, data_loader: DataLoader):
        """
        Initialize database loader with configuration.

        Args:
            data_loader: DataLoader configuration object

        Raises:
            ValueError: If data_loader type is not DATABASE
            ImportError: If required database drivers are not available
        """
        if data_loader.type != DataLoaderType.DATABASE:
            raise ValueError(f"Expected DataLoaderType.DATABASE, got {data_loader.type}")

        self.config = data_loader
        self.connection_pool = None
        self.db_type = None
        self.data: Optional[List[Dict[str, Any]]] = None
        self._thread_local = threading.local()

        # Parse connection string to determine database type
        self._parse_connection_string()
        self._initialize_connection_pool()

    def _parse_connection_string(self):
        """Parse the connection string to determine database type and parameters."""
        source = self.config.source

        if source.startswith('sqlite://') or source.endswith('.db') or source.endswith('.sqlite'):
            self.db_type = 'sqlite'
            if source.startswith('sqlite://'):
                self.db_path = source.replace('sqlite://', '')
            else:
                self.db_path = source
        elif source.startswith('postgresql://') or source.startswith('postgres://'):
            self.db_type = 'postgresql'
            if not POSTGRESQL_AVAILABLE:
                raise ImportError(
                    "psycopg2 is required for PostgreSQL connections. "
                    "Install with: pip install psycopg2-binary"
                )
            self.connection_params = self._parse_postgres_url(source)
        else:
            # Try to detect by URL format
            try:
                parsed = urlparse(source)
                if parsed.scheme in ('postgresql', 'postgres'):
                    self.db_type = 'postgresql'
                    if not POSTGRESQL_AVAILABLE:
                        raise ImportError(
                            "psycopg2 is required for PostgreSQL connections. "
                            "Install with: pip install psycopg2-binary"
                        )
                    self.connection_params = self._parse_postgres_url(source)
                else:
                    # Default to SQLite
                    self.db_type = 'sqlite'
                    self.db_path = source
            except Exception:
                # If parsing fails, assume SQLite file path
                self.db_type = 'sqlite'
                self.db_path = source

    def _parse_postgres_url(self, url: str) -> Dict[str, Any]:
        """Parse PostgreSQL connection URL into parameters."""
        parsed = urlparse(url)
        return {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 5432,
            'database': parsed.path.lstrip('/') if parsed.path else 'postgres',
            'user': parsed.username,
            'password': parsed.password,
        }

    def _initialize_connection_pool(self):
        """Initialize connection pool based on database type."""
        format_options = self.config.format_options or {}

        if self.db_type == 'sqlite':
            # SQLite doesn't need a connection pool, but we simulate one for consistency
            self.pool_size = 1
            self.timeout = format_options.get('timeout', 30.0)

            # Test connection
            try:
                conn = sqlite3.connect(self.db_path, timeout=self.timeout)
                conn.close()
            except sqlite3.Error as e:
                raise OSError(f"Cannot connect to SQLite database {self.db_path}: {e}")

        elif self.db_type == 'postgresql':
            # Initialize PostgreSQL connection pool
            pool_size = format_options.get('pool_size', 5)
            max_connections = format_options.get('max_connections', 20)

            try:
                if POSTGRESQL_AVAILABLE:
                    self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                        pool_size, max_connections, **self.connection_params
                    )
                else:
                    raise OSError("PostgreSQL support not available")
            except Exception as e:
                if POSTGRESQL_AVAILABLE and hasattr(e, '__module__') and 'psycopg2' in str(e.__module__):
                    raise OSError(f"Cannot create PostgreSQL connection pool: {e}")
                else:
                    raise OSError(f"Cannot create PostgreSQL connection pool: {e}")

    @contextmanager
    def _get_connection(self):
        """Get a database connection from the pool."""
        if self.db_type == 'sqlite':
            conn = sqlite3.connect(self.db_path, timeout=self.timeout)
            try:
                conn.row_factory = sqlite3.Row  # Enable column name access
                yield conn
            finally:
                conn.close()

        elif self.db_type == 'postgresql' and POSTGRESQL_AVAILABLE:
            conn = self.connection_pool.getconn()
            try:
                yield conn
            finally:
                self.connection_pool.putconn(conn)

    def load(self) -> List[Dict[str, Any]]:
        """
        Load data from the database using the configured query.

        Returns:
            List of dictionaries containing the loaded data

        Raises:
            ValueError: If no query is specified or if variables are missing
            OSError: If database connection or query execution fails
        """
        format_options = self.config.format_options or {}
        query = format_options.get('query')
        table = format_options.get('table')

        if not query and not table:
            raise ValueError("Either 'query' or 'table' must be specified in format_options")

        # Build query from table name if not explicitly provided
        if not query:
            columns = "*"
            if self.config.variables:
                columns = ", ".join(self.config.variables)

            query = f"SELECT {columns} FROM {table}"

            # Add WHERE conditions if specified
            if format_options.get('where'):
                query += f" WHERE {format_options['where']}"

            # Add ORDER BY if specified
            if format_options.get('order_by'):
                query += f" ORDER BY {format_options['order_by']}"

            # Add LIMIT if specified
            if format_options.get('limit'):
                query += f" LIMIT {format_options['limit']}"

        try:
            with self._get_connection() as conn:
                if self.db_type == 'sqlite':
                    cursor = conn.cursor()
                    cursor.execute(query)

                    # Get column names
                    columns = [description[0] for description in cursor.description]

                    # Fetch all rows
                    rows = cursor.fetchall()

                    # Convert to list of dictionaries
                    self.data = [dict(zip(columns, row)) for row in rows]

                elif self.db_type == 'postgresql':
                    with conn.cursor() as cursor:
                        cursor.execute(query)

                        # Get column names
                        columns = [desc[0] for desc in cursor.description]

                        # Fetch all rows
                        rows = cursor.fetchall()

                        # Convert to list of dictionaries
                        self.data = [dict(zip(columns, row)) for row in rows]

        except sqlite3.OperationalError as e:
            if "no such column" in str(e):
                # Extract requested variables from error context
                if self.config.variables:
                    raise ValueError(f"Requested variables not found in table '{table}': {self.config.variables}")
                else:
                    raise ValueError(f"Database query failed: {e}")
            else:
                raise OSError(f"Failed to execute database query: {e}")
        except Exception as e:
            raise OSError(f"Failed to execute database query: {e}")

        # Filter variables if specified and not already handled in query
        if self.config.variables and not format_options.get('table'):
            # Variables were not used in query building, so filter results
            filtered_data = []
            for row in self.data:
                filtered_row = {var: row.get(var) for var in self.config.variables if var in row}
                missing_vars = set(self.config.variables) - set(filtered_row.keys())
                if missing_vars:
                    raise ValueError(f"Requested variables not found in query results: {missing_vars}")
                filtered_data.append(filtered_row)
            self.data = filtered_data

        return self.data

    def execute_query(self, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a custom SQL query with parameters.

        Args:
            query: SQL query to execute
            params: Query parameters for safe parameterized queries

        Returns:
            List of dictionaries containing the query results

        Raises:
            OSError: If query execution fails
        """
        try:
            with self._get_connection() as conn:
                if self.db_type == 'sqlite':
                    cursor = conn.cursor()
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)

                    columns = [description[0] for description in cursor.description]
                    rows = cursor.fetchall()
                    return [dict(zip(columns, row)) for row in rows]

                elif self.db_type == 'postgresql':
                    with conn.cursor() as cursor:
                        if params:
                            cursor.execute(query, params)
                        else:
                            cursor.execute(query)

                        if cursor.description:  # SELECT queries
                            columns = [desc[0] for desc in cursor.description]
                            rows = cursor.fetchall()
                            return [dict(zip(columns, row)) for row in rows]
                        else:  # INSERT/UPDATE/DELETE queries
                            return []

        except Exception as e:
            raise OSError(f"Failed to execute custom query: {e}")

    def get_table_info(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about database tables and their structure.

        Args:
            table_name: Specific table to inspect, or None for all tables

        Returns:
            Dictionary with table structure information

        Raises:
            RuntimeError: If no connection is established
        """
        table_info = {}

        try:
            with self._get_connection() as conn:
                if self.db_type == 'sqlite':
                    cursor = conn.cursor()

                    # Get table names
                    if table_name:
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                        tables = [row[0] for row in cursor.fetchall()]
                    else:
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                        tables = [row[0] for row in cursor.fetchall()]

                    # Get column information for each table
                    for table in tables:
                        cursor.execute(f"PRAGMA table_info({table})")
                        columns = cursor.fetchall()

                        table_info[table] = {
                            'columns': [
                                {
                                    'name': col[1],
                                    'type': col[2],
                                    'nullable': not col[3],
                                    'default': col[4],
                                    'primary_key': bool(col[5])
                                }
                                for col in columns
                            ]
                        }

                        # Get row count
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        table_info[table]['row_count'] = cursor.fetchone()[0]

                elif self.db_type == 'postgresql':
                    with conn.cursor() as cursor:
                        # Get table names
                        if table_name:
                            cursor.execute("""
                                SELECT table_name
                                FROM information_schema.tables
                                WHERE table_schema = 'public' AND table_name = %s
                            """, (table_name,))
                        else:
                            cursor.execute("""
                                SELECT table_name
                                FROM information_schema.tables
                                WHERE table_schema = 'public'
                            """)

                        tables = [row[0] for row in cursor.fetchall()]

                        # Get column information for each table
                        for table in tables:
                            cursor.execute("""
                                SELECT column_name, data_type, is_nullable, column_default
                                FROM information_schema.columns
                                WHERE table_schema = 'public' AND table_name = %s
                                ORDER BY ordinal_position
                            """, (table,))

                            columns = cursor.fetchall()

                            table_info[table] = {
                                'columns': [
                                    {
                                        'name': col[0],
                                        'type': col[1],
                                        'nullable': col[2] == 'YES',
                                        'default': col[3],
                                        'primary_key': False  # Would need additional query for PK info
                                    }
                                    for col in columns
                                ]
                            }

                            # Get row count
                            cursor.execute(f"SELECT COUNT(*) FROM {table}")
                            table_info[table]['row_count'] = cursor.fetchone()[0]

        except Exception as e:
            raise OSError(f"Failed to get table information: {e}")

        return table_info

    def begin_transaction(self):
        """
        Begin a database transaction.

        Note: This creates a connection that should be used with execute_transaction_query
        and closed with commit_transaction or rollback_transaction.
        """
        if not hasattr(self._thread_local, 'transaction_conn'):
            if self.db_type == 'sqlite':
                self._thread_local.transaction_conn = sqlite3.connect(self.db_path, timeout=self.timeout)
                self._thread_local.transaction_conn.row_factory = sqlite3.Row
                # SQLite doesn't have autocommit attribute - transactions are automatic
            elif self.db_type == 'postgresql' and POSTGRESQL_AVAILABLE:
                self._thread_local.transaction_conn = self.connection_pool.getconn()
                self._thread_local.transaction_conn.autocommit = False

    def commit_transaction(self):
        """Commit the current transaction and close the connection."""
        if hasattr(self._thread_local, 'transaction_conn'):
            try:
                self._thread_local.transaction_conn.commit()
            finally:
                if self.db_type == 'sqlite':
                    self._thread_local.transaction_conn.close()
                elif self.db_type == 'postgresql':
                    self.connection_pool.putconn(self._thread_local.transaction_conn)
                delattr(self._thread_local, 'transaction_conn')

    def rollback_transaction(self):
        """Rollback the current transaction and close the connection."""
        if hasattr(self._thread_local, 'transaction_conn'):
            try:
                self._thread_local.transaction_conn.rollback()
            finally:
                if self.db_type == 'sqlite':
                    self._thread_local.transaction_conn.close()
                elif self.db_type == 'postgresql':
                    self.connection_pool.putconn(self._thread_local.transaction_conn)
                delattr(self._thread_local, 'transaction_conn')

    def execute_transaction_query(self, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a query within the current transaction.

        Args:
            query: SQL query to execute
            params: Query parameters for safe parameterized queries

        Returns:
            List of dictionaries containing the query results
        """
        if not hasattr(self._thread_local, 'transaction_conn'):
            raise RuntimeError("No active transaction. Call begin_transaction() first.")

        conn = self._thread_local.transaction_conn

        try:
            if self.db_type == 'sqlite':
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                if cursor.description:  # SELECT queries
                    columns = [description[0] for description in cursor.description]
                    rows = cursor.fetchall()
                    return [dict(zip(columns, row)) for row in rows]
                else:  # INSERT/UPDATE/DELETE queries
                    return []

            elif self.db_type == 'postgresql':
                with conn.cursor() as cursor:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)

                    if cursor.description:  # SELECT queries
                        columns = [desc[0] for desc in cursor.description]
                        rows = cursor.fetchall()
                        return [dict(zip(columns, row)) for row in rows]
                    else:  # INSERT/UPDATE/DELETE queries
                        return []

        except Exception as e:
            raise OSError(f"Failed to execute transaction query: {e}")

    def close(self):
        """Close database connections and clean up resources."""
        if self.connection_pool and self.db_type == 'postgresql':
            self.connection_pool.closeall()
            self.connection_pool = None

        # Clean up any active transaction connections
        if hasattr(self._thread_local, 'transaction_conn'):
            if self.db_type == 'sqlite':
                self._thread_local.transaction_conn.close()
            elif self.db_type == 'postgresql':
                self.connection_pool.putconn(self._thread_local.transaction_conn)
            delattr(self._thread_local, 'transaction_conn')

        self.data = None


class HDF5Loader:
    """
    HDF5 data loader supporting hierarchical data structures with h5py/pytables integration.

    Provides comprehensive support for HDF5 files including group navigation, dataset chunking,
    compression handling, and metadata extraction. Essential for large-scale scientific
    dataset ingestion with hierarchical organization.
    """

    def __init__(self, data_loader: DataLoader):
        """
        Initialize HDF5 loader with configuration.

        Args:
            data_loader: DataLoader configuration object

        Raises:
            ImportError: If neither h5py nor pytables is available
            ValueError: If data_loader type is not HDF5
        """
        if data_loader.type != DataLoaderType.HDF5:
            raise ValueError(f"Expected DataLoaderType.HDF5, got {data_loader.type}")

        if not H5PY_AVAILABLE and not PYTABLES_AVAILABLE:
            raise ImportError("Either h5py or pytables is required for HDF5 loading. "
                            "Install with: pip install h5py or pip install tables")

        self.config = data_loader
        self.file_handle = None
        self.data: Optional[Dict[str, Any]] = None
        self.backend = 'h5py' if H5PY_AVAILABLE else 'pytables'

        # Prefer h5py if both are available, unless specified otherwise
        format_options = self.config.format_options or {}
        preferred_backend = format_options.get('backend', 'h5py')
        if preferred_backend == 'h5py' and H5PY_AVAILABLE:
            self.backend = 'h5py'
        elif preferred_backend == 'pytables' and PYTABLES_AVAILABLE:
            self.backend = 'pytables'
        elif preferred_backend == 'h5py' and not H5PY_AVAILABLE:
            if PYTABLES_AVAILABLE:
                self.backend = 'pytables'
            else:
                raise ImportError("h5py is not available. Install with: pip install h5py")
        elif preferred_backend == 'pytables' and not PYTABLES_AVAILABLE:
            if H5PY_AVAILABLE:
                self.backend = 'h5py'
            else:
                raise ImportError("pytables is not available. Install with: pip install tables")

    def load(self) -> Dict[str, Any]:
        """
        Load data from the HDF5 file.

        Returns:
            Dictionary containing the loaded data with group/dataset structure preserved

        Raises:
            FileNotFoundError: If the source file doesn't exist
            OSError: If the file can't be opened or read
            ValueError: If requested variables are not found
        """
        source_path = Path(self.config.source)

        if not source_path.exists():
            raise FileNotFoundError(f"HDF5 file not found: {source_path}")

        try:
            format_options = self.config.format_options or {}

            if self.backend == 'h5py':
                self.data = self._load_with_h5py(source_path, format_options)
            else:
                self.data = self._load_with_pytables(source_path, format_options)

            # Filter to requested variables if specified
            if self.config.variables:
                filtered_data = {}
                for var in self.config.variables:
                    if var in self.data:
                        filtered_data[var] = self.data[var]
                        # Also include attributes if they exist
                        attr_key = f"{var}_attrs"
                        if attr_key in self.data:
                            filtered_data[attr_key] = self.data[attr_key]
                    else:
                        # Try hierarchical access using '/' as separator
                        nested_value = self._get_nested_dataset(self.data, var)
                        if nested_value is not None:
                            filtered_data[var] = nested_value
                            # Also try to include attributes for nested datasets
                            attr_key = f"{var}_attrs"
                            if attr_key in self.data:
                                filtered_data[attr_key] = self.data[attr_key]

                missing_vars = set(self.config.variables) - set([k for k in filtered_data.keys() if not k.endswith('_attrs')])
                if missing_vars:
                    raise ValueError(f"Requested variables not found in HDF5 file: {missing_vars}")

                self.data = filtered_data

            return self.data

        except ValueError:
            # Re-raise ValueError without wrapping
            raise
        except Exception as e:
            raise OSError(f"Failed to load HDF5 file {source_path}: {e}") from e

    def _load_with_h5py(self, file_path: Path, format_options: Dict[str, Any]) -> Dict[str, Any]:
        """Load HDF5 data using h5py backend."""
        import h5py

        mode = format_options.get('mode', 'r')
        self.file_handle = h5py.File(file_path, mode)

        data = {}

        def visit_func(name, obj):
            if isinstance(obj, h5py.Dataset):
                # Load dataset data
                dataset_data = obj[...]

                # Convert to numpy array if needed
                if hasattr(dataset_data, 'shape'):
                    data[name] = np.array(dataset_data)
                else:
                    data[name] = dataset_data

                # Store metadata as attributes - use the dataset name without path
                if obj.attrs:
                    # For datasets at root level, use simple name
                    # For nested datasets, use full path
                    attr_key = f"{name}_attrs"
                    data[attr_key] = dict(obj.attrs)
            elif isinstance(obj, h5py.Group):
                # Store group metadata
                if obj.attrs:
                    data[f"{name}_attrs"] = dict(obj.attrs)

        self.file_handle.visititems(visit_func)
        return data

    def _load_with_pytables(self, file_path: Path, format_options: Dict[str, Any]) -> Dict[str, Any]:
        """Load HDF5 data using pytables backend."""
        import tables

        mode = format_options.get('mode', 'r')
        self.file_handle = tables.open_file(str(file_path), mode)

        data = {}

        def visit_nodes(node, path=""):
            for child in node:
                child_path = f"{path}/{child._v_name}" if path else child._v_name

                if isinstance(child, tables.Array):
                    # Load array data
                    data[child_path] = np.array(child.read())

                    # Store metadata
                    if child._v_attrs:
                        attrs = {}
                        for attr_name in child._v_attrs._f_list():
                            attrs[attr_name] = child._v_attrs[attr_name]
                        data[f"{child_path}_attrs"] = attrs

                elif isinstance(child, tables.Table):
                    # Load table data as structured array
                    data[child_path] = child.read()

                    # Store metadata
                    if child._v_attrs:
                        attrs = {}
                        for attr_name in child._v_attrs._f_list():
                            attrs[attr_name] = child._v_attrs[attr_name]
                        data[f"{child_path}_attrs"] = attrs

                elif isinstance(child, tables.Group):
                    # Recursively process groups
                    if child._v_attrs:
                        attrs = {}
                        for attr_name in child._v_attrs._f_list():
                            attrs[attr_name] = child._v_attrs[attr_name]
                        data[f"{child_path}_attrs"] = attrs

                    visit_nodes(child, child_path)

        visit_nodes(self.file_handle.root)
        return data

    def _get_nested_dataset(self, data: Dict[str, Any], path: str) -> Any:
        """
        Get a nested dataset using hierarchical path.

        Args:
            data: Dictionary to search in
            path: Hierarchical path (e.g., 'group1/dataset1' or 'group1.dataset1')

        Returns:
            The nested dataset or None if not found
        """
        # Try both '/' and '.' as separators
        for separator in ['/', '.']:
            if separator in path:
                keys = path.split(separator)
                current = data

                for key in keys:
                    if isinstance(current, dict) and key in current:
                        current = current[key]
                    else:
                        break
                else:
                    return current

        return None

    def get_file_structure(self) -> Dict[str, Any]:
        """
        Get the hierarchical structure of the HDF5 file.

        Returns:
            Dictionary describing the file structure with groups and datasets

        Raises:
            RuntimeError: If file must be loaded before extracting structure
        """
        if self.file_handle is None:
            raise RuntimeError("File must be loaded before extracting structure")

        structure = {}

        if self.backend == 'h5py':
            def build_structure(name, obj):
                parts = name.split('/')
                current = structure

                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {'type': 'group', 'children': {}}
                    current = current[part]['children']

                final_name = parts[-1]
                if hasattr(obj, 'shape'):  # Dataset
                    current[final_name] = {
                        'type': 'dataset',
                        'shape': obj.shape,
                        'dtype': str(obj.dtype),
                        'chunks': obj.chunks,
                        'compression': obj.compression,
                        'attrs': dict(obj.attrs) if obj.attrs else {}
                    }
                else:  # Group
                    if final_name not in current:
                        current[final_name] = {'type': 'group', 'children': {}}
                    current[final_name]['attrs'] = dict(obj.attrs) if obj.attrs else {}

            self.file_handle.visititems(build_structure)

        else:  # pytables
            def build_structure_pytables(node, current_dict, path=""):
                for child in node:
                    child_name = child._v_name

                    if isinstance(child, (tables.Array, tables.Table)):
                        current_dict[child_name] = {
                            'type': 'dataset',
                            'shape': child.shape,
                            'dtype': str(child.dtype),
                            'attrs': {attr: child._v_attrs[attr]
                                    for attr in child._v_attrs._f_list()} if child._v_attrs else {}
                        }

                        if isinstance(child, tables.Array) and hasattr(child, 'chunkshape'):
                            current_dict[child_name]['chunks'] = child.chunkshape

                    elif isinstance(child, tables.Group):
                        current_dict[child_name] = {
                            'type': 'group',
                            'children': {},
                            'attrs': {attr: child._v_attrs[attr]
                                    for attr in child._v_attrs._f_list()} if child._v_attrs else {}
                        }
                        build_structure_pytables(child, current_dict[child_name]['children'],
                                              f"{path}/{child_name}" if path else child_name)

            build_structure_pytables(self.file_handle.root, structure)

        return structure

    def get_dataset_info(self, dataset_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed information about datasets in the file.

        Args:
            dataset_path: Specific dataset path to inspect, or None for all datasets

        Returns:
            Dictionary with dataset information

        Raises:
            RuntimeError: If file must be loaded before extracting info
            ValueError: If specified dataset path is not found
        """
        if self.file_handle is None:
            raise RuntimeError("File must be loaded before extracting dataset info")

        info = {}

        if self.backend == 'h5py':
            def collect_dataset_info(name, obj):
                if hasattr(obj, 'shape'):  # It's a dataset
                    if dataset_path is None or name == dataset_path:
                        info[name] = {
                            'shape': obj.shape,
                            'dtype': str(obj.dtype),
                            'size_bytes': obj.size * obj.dtype.itemsize,
                            'chunks': obj.chunks,
                            'compression': obj.compression,
                            'compression_opts': obj.compression_opts,
                            'shuffle': obj.shuffle,
                            'fletcher32': obj.fletcher32,
                            'fillvalue': obj.fillvalue,
                            'attributes': dict(obj.attrs) if obj.attrs else {}
                        }

            self.file_handle.visititems(collect_dataset_info)

        else:  # pytables
            def collect_dataset_info_pytables(node, path=""):
                for child in node:
                    child_path = f"{path}/{child._v_name}" if path else child._v_name

                    if isinstance(child, (tables.Array, tables.Table)):
                        if dataset_path is None or child_path == dataset_path:
                            dataset_info = {
                                'shape': child.shape,
                                'dtype': str(child.dtype),
                                'size_bytes': child.size_in_memory,
                                'attributes': {attr: child._v_attrs[attr]
                                             for attr in child._v_attrs._f_list()} if child._v_attrs else {}
                            }

                            if hasattr(child, 'chunkshape'):
                                dataset_info['chunks'] = child.chunkshape
                            if hasattr(child, 'filters'):
                                dataset_info['compression'] = str(child.filters)

                            info[child_path] = dataset_info

                    elif isinstance(child, tables.Group):
                        collect_dataset_info_pytables(child, child_path)

            collect_dataset_info_pytables(self.file_handle.root)

        if dataset_path and dataset_path not in info:
            raise ValueError(f"Dataset path '{dataset_path}' not found in file")

        return info

    def read_dataset(self, dataset_path: str, slice_obj: Optional[tuple] = None) -> np.ndarray:
        """
        Read a specific dataset with optional slicing.

        Args:
            dataset_path: Path to the dataset
            slice_obj: Optional tuple defining slice (e.g., (slice(0, 10), slice(None)))

        Returns:
            NumPy array containing the dataset data

        Raises:
            RuntimeError: If file must be loaded before reading
            ValueError: If dataset path is not found
        """
        if self.file_handle is None:
            raise RuntimeError("File must be loaded before reading datasets")

        if self.backend == 'h5py':
            if dataset_path not in self.file_handle:
                raise ValueError(f"Dataset '{dataset_path}' not found in file")

            dataset = self.file_handle[dataset_path]
            if slice_obj:
                return np.array(dataset[slice_obj])
            else:
                return np.array(dataset[...])

        else:  # pytables
            try:
                node = self.file_handle.get_node(f"/{dataset_path}")
                if slice_obj:
                    return np.array(node[slice_obj])
                else:
                    return np.array(node.read())
            except tables.NoSuchNodeError:
                raise ValueError(f"Dataset '{dataset_path}' not found in file")

    def list_groups(self, group_path: str = "/") -> List[str]:
        """
        List all groups under the specified path.

        Args:
            group_path: Path to the group (default: root)

        Returns:
            List of group names

        Raises:
            RuntimeError: If file must be loaded before listing groups
        """
        if self.file_handle is None:
            raise RuntimeError("File must be loaded before listing groups")

        groups = []

        if self.backend == 'h5py':
            if group_path in self.file_handle:
                group = self.file_handle[group_path]
                for key in group.keys():
                    if isinstance(group[key], h5py.Group):
                        groups.append(key)

        else:  # pytables
            try:
                if group_path == "/":
                    group = self.file_handle.root
                else:
                    group = self.file_handle.get_node(group_path)

                for child in group:
                    if isinstance(child, tables.Group):
                        groups.append(child._v_name)
            except tables.NoSuchNodeError:
                pass

        return groups

    def list_datasets(self, group_path: str = "/") -> List[str]:
        """
        List all datasets under the specified path.

        Args:
            group_path: Path to the group (default: root)

        Returns:
            List of dataset names

        Raises:
            RuntimeError: If file must be loaded before listing datasets
        """
        if self.file_handle is None:
            raise RuntimeError("File must be loaded before listing datasets")

        datasets = []

        if self.backend == 'h5py':
            if group_path in self.file_handle:
                group = self.file_handle[group_path]
                for key in group.keys():
                    if isinstance(group[key], h5py.Dataset):
                        datasets.append(key)

        else:  # pytables
            try:
                if group_path == "/":
                    group = self.file_handle.root
                else:
                    group = self.file_handle.get_node(group_path)

                for child in group:
                    if isinstance(child, (tables.Array, tables.Table)):
                        datasets.append(child._v_name)
            except tables.NoSuchNodeError:
                pass

        return datasets

    def close(self):
        """Close the HDF5 file and free resources."""
        if self.file_handle is not None:
            self.file_handle.close()
            self.file_handle = None
        self.data = None


class GRIBLoader:
    """
    GRIB data loader supporting GRIB1 and GRIB2 meteorological data formats.

    Provides comprehensive support for GRIB files including parameter tables,
    grid definitions, ensemble data handling, and metadata extraction. Essential
    for weather and climate model data ingestion.
    """

    def __init__(self, data_loader: DataLoader):
        """
        Initialize GRIB loader with configuration.

        Args:
            data_loader: DataLoader configuration object

        Raises:
            ImportError: If cfgrib and xarray are not available
            ValueError: If data_loader type is not GRIB
        """
        if not CFGRIB_AVAILABLE:
            raise ImportError("cfgrib and xarray are required for GRIB loading. "
                            "Install with: pip install cfgrib xarray")

        if data_loader.type != DataLoaderType.GRIB:
            raise ValueError(f"Expected DataLoaderType.GRIB, got {data_loader.type}")

        self.config = data_loader
        self.dataset: Optional[xr.Dataset] = None

    def load(self) -> xr.Dataset:
        """
        Load the GRIB dataset from the configured source.

        Returns:
            xarray Dataset containing the loaded GRIB data

        Raises:
            FileNotFoundError: If the source file doesn't exist
            OSError: If the file can't be opened or read
            ValueError: If requested variables are not found
        """
        source_path = Path(self.config.source)

        if not source_path.exists():
            raise FileNotFoundError(f"GRIB file not found: {source_path}")

        try:
            # Load with cfgrib through xarray
            format_options = self.config.format_options or {}

            # Extract cfgrib-specific options
            backend_kwargs = format_options.get('backend_kwargs', {})
            filter_by_keys = format_options.get('filter_by_keys', {})
            chunks = format_options.get('chunks', None)

            # Set up backend kwargs for cfgrib
            if filter_by_keys:
                backend_kwargs['filter_by_keys'] = filter_by_keys

            # Load the dataset
            self.dataset = xr.open_dataset(
                source_path,
                engine='cfgrib',
                backend_kwargs=backend_kwargs,
                chunks=chunks
            )

            # Filter to requested variables if specified
            if self.config.variables:
                available_vars = set(self.dataset.data_vars.keys())
                requested_vars = set(self.config.variables)

                # Check for missing variables
                missing_vars = requested_vars - available_vars
                if missing_vars:
                    raise ValueError(f"Requested variables not found in GRIB dataset: {missing_vars}")

                # Select only requested variables, keep all coordinates
                self.dataset = self.dataset[list(requested_vars)]

            return self.dataset

        except ValueError:
            # Re-raise ValueError without wrapping
            raise
        except Exception as e:
            raise OSError(f"Failed to load GRIB file {source_path}: {e}") from e

    def get_parameter_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Extract GRIB parameter information for all variables.

        Returns:
            Dictionary mapping variable names to their GRIB parameter metadata

        Raises:
            RuntimeError: If dataset must be loaded before extracting parameter info
        """
        if self.dataset is None:
            raise RuntimeError("Dataset must be loaded before extracting parameter info")

        param_info = {}

        for var_name, var in self.dataset.data_vars.items():
            # Extract GRIB-specific attributes
            attrs = dict(var.attrs) if hasattr(var, 'attrs') else {}

            info = {
                'dimensions': list(var.dims),
                'shape': var.shape,
                'dtype': str(var.dtype),
                'long_name': attrs.get('long_name', ''),
                'units': attrs.get('units', ''),
                'standard_name': attrs.get('standard_name', ''),
                'GRIB_paramId': attrs.get('GRIB_paramId', ''),
                'GRIB_shortName': attrs.get('GRIB_shortName', ''),
                'GRIB_name': attrs.get('GRIB_name', ''),
                'GRIB_cfName': attrs.get('GRIB_cfName', ''),
                'GRIB_cfVarName': attrs.get('GRIB_cfVarName', ''),
                'GRIB_dataType': attrs.get('GRIB_dataType', ''),
                'GRIB_numberOfPoints': attrs.get('GRIB_numberOfPoints', ''),
                'GRIB_typeOfLevel': attrs.get('GRIB_typeOfLevel', ''),
                'GRIB_level': attrs.get('GRIB_level', '')
            }

            # Add coordinate information
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

            param_info[var_name] = info

        return param_info

    def get_grid_info(self) -> Dict[str, Any]:
        """
        Extract GRIB grid definition information.

        Returns:
            Dictionary containing grid information and metadata

        Raises:
            RuntimeError: If dataset must be loaded before extracting grid info
        """
        if self.dataset is None:
            raise RuntimeError("Dataset must be loaded before extracting grid info")

        grid_info = {
            'grid_type': 'unknown',
            'dimensions': {},
            'coordinate_info': {},
            'global_attributes': {}
        }

        # Extract global attributes
        if hasattr(self.dataset, 'attrs'):
            grid_info['global_attributes'] = dict(self.dataset.attrs)

        # Analyze coordinate dimensions
        for coord_name, coord in self.dataset.coords.items():
            coord_attrs = dict(coord.attrs) if hasattr(coord, 'attrs') else {}
            grid_info['dimensions'][coord_name] = coord.size
            grid_info['coordinate_info'][coord_name] = {
                'size': coord.size,
                'dtype': str(coord.dtype),
                'min_value': float(coord.min()) if coord.size > 0 else None,
                'max_value': float(coord.max()) if coord.size > 0 else None,
                'units': coord_attrs.get('units', ''),
                'long_name': coord_attrs.get('long_name', ''),
                'standard_name': coord_attrs.get('standard_name', ''),
            }

        # Determine grid type based on coordinates
        if 'latitude' in self.dataset.coords and 'longitude' in self.dataset.coords:
            grid_info['grid_type'] = 'regular_lat_lon'
        elif 'x' in self.dataset.coords and 'y' in self.dataset.coords:
            grid_info['grid_type'] = 'projected'

        return grid_info

    def get_time_info(self) -> Dict[str, Any]:
        """
        Extract temporal information from the GRIB dataset.

        Returns:
            Dictionary containing time dimension information

        Raises:
            RuntimeError: If dataset must be loaded before extracting time info
        """
        if self.dataset is None:
            raise RuntimeError("Dataset must be loaded before extracting time info")

        time_info = {}

        if 'time' in self.dataset.coords:
            time_coord = self.dataset.coords['time']
            time_attrs = dict(time_coord.attrs) if hasattr(time_coord, 'attrs') else {}

            time_info = {
                'num_times': time_coord.size,
                'start_time': str(time_coord.values[0]) if time_coord.size > 0 else None,
                'end_time': str(time_coord.values[-1]) if time_coord.size > 0 else None,
                'units': time_attrs.get('units', ''),
                'calendar': time_attrs.get('calendar', ''),
                'long_name': time_attrs.get('long_name', ''),
            }

            # Calculate time step if possible
            if time_coord.size > 1:
                time_diff = time_coord.values[1] - time_coord.values[0]
                time_info['time_step'] = str(time_diff)

        return time_info

    def list_available_parameters(self) -> List[Dict[str, str]]:
        """
        List all available parameters in the GRIB file.

        Returns:
            List of dictionaries containing parameter information

        Raises:
            RuntimeError: If dataset must be loaded before listing parameters
        """
        if self.dataset is None:
            raise RuntimeError("Dataset must be loaded before listing parameters")

        parameters = []

        for var_name, var in self.dataset.data_vars.items():
            attrs = dict(var.attrs) if hasattr(var, 'attrs') else {}

            param_info = {
                'variable_name': var_name,
                'long_name': attrs.get('long_name', ''),
                'units': attrs.get('units', ''),
                'GRIB_shortName': attrs.get('GRIB_shortName', ''),
                'GRIB_paramId': str(attrs.get('GRIB_paramId', '')),
                'GRIB_typeOfLevel': attrs.get('GRIB_typeOfLevel', ''),
                'dimensions': list(var.dims),
                'shape': var.shape
            }

            parameters.append(param_info)

        return parameters

    def extract_ensemble_info(self) -> Dict[str, Any]:
        """
        Extract ensemble information if available in the GRIB data.

        Returns:
            Dictionary containing ensemble metadata

        Raises:
            RuntimeError: If dataset must be loaded before extracting ensemble info
        """
        if self.dataset is None:
            raise RuntimeError("Dataset must be loaded before extracting ensemble info")

        ensemble_info = {
            'has_ensemble': False,
            'ensemble_dimension': None,
            'num_members': 0,
            'member_info': []
        }

        # Check for ensemble dimensions
        if 'number' in self.dataset.dims:
            ensemble_info['has_ensemble'] = True
            ensemble_info['ensemble_dimension'] = 'number'
            ensemble_info['num_members'] = self.dataset.dims['number']

            # Get ensemble member information
            if 'number' in self.dataset.coords:
                number_coord = self.dataset.coords['number']
                for i, member_num in enumerate(number_coord.values):
                    ensemble_info['member_info'].append({
                        'index': i,
                        'number': int(member_num)
                    })

        return ensemble_info

    def validate_grib_conventions(self) -> Dict[str, Any]:
        """
        Validate GRIB format conventions and metadata completeness.

        Returns:
            Dictionary with validation results and warnings
        """
        if self.dataset is None:
            raise RuntimeError("Dataset must be loaded before validation")

        validation_result = {
            'grib_compliant': True,
            'warnings': [],
            'errors': [],
            'metadata': {}
        }

        # Check for essential GRIB attributes in variables
        for var_name, var in self.dataset.data_vars.items():
            attrs = dict(var.attrs) if hasattr(var, 'attrs') else {}

            # Check for essential GRIB metadata
            if not attrs.get('GRIB_paramId'):
                validation_result['warnings'].append(f"Variable '{var_name}' missing GRIB_paramId")

            if not attrs.get('GRIB_shortName'):
                validation_result['warnings'].append(f"Variable '{var_name}' missing GRIB_shortName")

            if not attrs.get('units'):
                validation_result['warnings'].append(f"Variable '{var_name}' missing units")

            if not attrs.get('GRIB_typeOfLevel'):
                validation_result['warnings'].append(f"Variable '{var_name}' missing GRIB_typeOfLevel")

        # Check coordinate completeness
        required_coords = ['latitude', 'longitude']
        for coord in required_coords:
            if coord not in self.dataset.coords:
                validation_result['warnings'].append(f"Missing coordinate: {coord}")

        # Set overall compliance
        validation_result['grib_compliant'] = len(validation_result['errors']) == 0
        validation_result['metadata']['num_variables'] = len(self.dataset.data_vars)
        validation_result['metadata']['num_coordinates'] = len(self.dataset.coords)

        return validation_result

    def close(self):
        """Close the dataset and free resources."""
        if self.dataset is not None:
            self.dataset.close()
            self.dataset = None


def create_data_loader(data_loader: DataLoader) -> Union[NetCDFLoader, JSONLoader, DatabaseLoader, HDF5Loader, GRIBLoader]:
    """
    Factory function to create appropriate data loader based on type.

    This function is maintained for backward compatibility.
    For new code, prefer using the data_loader_registry module functions.

    Args:
        data_loader: DataLoader configuration object

    Returns:
        Appropriate data loader instance

    Raises:
        ValueError: If data loader type is not supported
    """
    # Import here to avoid circular imports
    from .data_loader_registry import create_data_loader as registry_create_loader

    return registry_create_loader(data_loader)