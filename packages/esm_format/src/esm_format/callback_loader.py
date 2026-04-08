"""Callback data loader implementation for programmatic data sources."""

import inspect
from typing import Dict, Any, List, Optional, Union, Callable
import warnings

from .esm_types import DataLoader, DataLoaderType


class CallbackValidationError(Exception):
    """Raised when callback data validation fails."""
    pass


class CallbackLoader:
    """Callback data loader for programmatic data sources."""

    def __init__(self, data_loader: DataLoader):
        """Initialize callback loader with DataLoader configuration.

        Args:
            data_loader: DataLoader configuration object
        """
        if data_loader.type != DataLoaderType.CALLBACK:
            raise ValueError(f"Callback loader only supports CALLBACK type, got {data_loader.type}")

        self.config = data_loader
        self.source = data_loader.source
        self.format_options = data_loader.format_options or {}
        self.variables = data_loader.variables or []
        self.callback_function = None

    def load(self) -> Any:
        """Load data using callback function.

        Returns:
            Any: Data returned by the callback function

        Raises:
            CallbackValidationError: If validation fails
            ValueError: If callback configuration is invalid
        """
        try:
            # Resolve the callback function
            self._resolve_callback()

            # Validate callback function
            self._validate_callback()

            # Prepare callback arguments
            callback_args = self._prepare_callback_args()

            # Execute callback - try with kwargs first, then without
            try:
                result = self.callback_function(**callback_args)
            except TypeError as e:
                if "takes no keyword arguments" in str(e) or "unexpected keyword argument" in str(e):
                    # Try calling without kwargs if function doesn't accept them
                    try:
                        # Check if there are specific args to pass positionally
                        if 'callback_args' in self.format_options and isinstance(self.format_options['callback_args'], dict):
                            args_dict = self.format_options['callback_args']
                            if len(args_dict) == 1 and 'obj' in args_dict:
                                # Special case for functions like len() that take one positional argument
                                result = self.callback_function(args_dict['obj'])
                            else:
                                # Try calling with no arguments
                                result = self.callback_function()
                        else:
                            result = self.callback_function()
                    except TypeError:
                        # If all fails, raise the original error
                        raise e
                else:
                    raise e

            # Validate and process result
            processed_result = self._process_callback_result(result)

            return processed_result

        except Exception as e:
            if isinstance(e, (CallbackValidationError, ValueError)):
                raise
            raise CallbackValidationError(f"Callback data loading failed: {e}")

    def _resolve_callback(self) -> None:
        """Resolve the callback function from the source specification."""
        if callable(self.source):
            # Source is already a callable
            self.callback_function = self.source
        elif isinstance(self.source, str):
            # Source is a string, resolve it
            self.callback_function = self._resolve_callback_from_string(self.source)
        else:
            raise ValueError(f"Callback source must be callable or string, got {type(self.source)}")

    def _resolve_callback_from_string(self, callback_spec: str) -> Callable:
        """Resolve callback function from string specification.

        Supports formats like:
        - 'module.function'
        - 'package.module.ClassName.method'
        - 'function_name' (looks in globals)
        """
        if '.' in callback_spec:
            # Import from module
            parts = callback_spec.split('.')
            module_name = '.'.join(parts[:-1])
            function_name = parts[-1]

            try:
                module = __import__(module_name, fromlist=[function_name])
                callback = getattr(module, function_name)
                return callback
            except (ImportError, AttributeError) as e:
                raise ValueError(f"Cannot import callback '{callback_spec}': {e}")
        else:
            # Look for function in caller's globals or format_options
            if 'globals' in self.format_options:
                globals_dict = self.format_options['globals']
                if callback_spec in globals_dict:
                    return globals_dict[callback_spec]

            # Look in common namespaces
            import builtins
            if hasattr(builtins, callback_spec):
                return getattr(builtins, callback_spec)

            raise ValueError(f"Cannot resolve callback function: {callback_spec}")

    def _validate_callback(self) -> None:
        """Validate that the callback function is suitable."""
        if not callable(self.callback_function):
            raise CallbackValidationError("Callback source is not callable")

        # Check function signature if inspection is possible
        try:
            sig = inspect.signature(self.callback_function)

            # Warn about functions with required positional arguments
            required_args = [
                param for param in sig.parameters.values()
                if param.default == inspect.Parameter.empty and param.kind != inspect.Parameter.VAR_KEYWORD
            ]

            if required_args and 'callback_args' not in self.format_options:
                warnings.warn(
                    f"Callback function requires arguments {[arg.name for arg in required_args]} "
                    "but no 'callback_args' provided in format_options"
                )
        except (ValueError, TypeError):
            # Inspection failed, continue anyway
            pass

    def _prepare_callback_args(self) -> Dict[str, Any]:
        """Prepare arguments to pass to the callback function."""
        args = {}

        # Start with args from format_options
        if 'callback_args' in self.format_options:
            callback_args = self.format_options['callback_args']
            if isinstance(callback_args, dict):
                args.update(callback_args)
            else:
                warnings.warn("callback_args should be a dictionary")

        # Add standard arguments that callbacks might expect
        args.update({
            'variables': self.variables,
            'format_options': self.format_options,
            'config': self.config
        })

        return args

    def _process_callback_result(self, result: Any) -> Any:
        """Process and validate the callback result."""
        # Apply any post-processing specified in format_options
        if 'post_process' in self.format_options:
            post_process = self.format_options['post_process']
            if callable(post_process):
                result = post_process(result)
            elif isinstance(post_process, str):
                # Simple post-processing operations
                if post_process == 'to_dict' and hasattr(result, '__dict__'):
                    result = result.__dict__
                elif post_process == 'to_list' and hasattr(result, '__iter__'):
                    result = list(result)

        # Validate result contains expected variables if specified
        if self.variables and hasattr(result, 'keys'):
            missing_vars = [var for var in self.variables if var not in result]
            if missing_vars:
                warnings.warn(f"Callback result missing expected variables: {missing_vars}")

        return result


class CallbackDataSource:
    """Helper class for creating callback data sources with common patterns."""

    @staticmethod
    def create_constant_data(value: Any) -> Callable:
        """Create a callback that returns constant data."""
        def constant_callback(**kwargs):
            return value
        return constant_callback

    @staticmethod
    def create_random_data(shape: tuple, dtype: str = 'float64', **numpy_kwargs) -> Callable:
        """Create a callback that generates random data using numpy."""
        def random_callback(**kwargs):
            try:
                import numpy as np
                if dtype == 'float64':
                    return np.random.random(shape, **numpy_kwargs)
                elif dtype == 'int':
                    return np.random.randint(0, 100, shape, **numpy_kwargs)
                else:
                    return np.random.random(shape).astype(dtype)
            except ImportError:
                raise CallbackValidationError("Random data generation requires numpy")
        return random_callback

    @staticmethod
    def create_time_series_data(start_time: float, end_time: float, num_points: int) -> Callable:
        """Create a callback that generates time series data."""
        def timeseries_callback(variables=None, **kwargs):
            try:
                import numpy as np
                time = np.linspace(start_time, end_time, num_points)

                result = {'time': time}

                if variables:
                    for var in variables:
                        if var != 'time':
                            # Generate some sample data for each variable
                            result[var] = np.sin(2 * np.pi * time / (end_time - start_time)) + 0.1 * np.random.random(len(time))

                return result
            except ImportError:
                raise CallbackValidationError("Time series generation requires numpy")
        return timeseries_callback


def load_callback_data(data_loader: DataLoader) -> Any:
    """Convenience function to load callback data.

    Args:
        data_loader: DataLoader configuration

    Returns:
        Any: Data returned by the callback
    """
    loader = CallbackLoader(data_loader)
    return loader.load()