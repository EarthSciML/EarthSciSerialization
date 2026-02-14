"""
Operator registry and plugin system for ESM Format.

This module provides a registry system allowing runtime registration of new operators,
plugin discovery, operator selection based on name/type, and operator versioning.
"""

import warnings
from typing import Dict, List, Type, Optional, Callable, Any, Union
from importlib import import_module
from pathlib import Path

from .types import Operator, OperatorType


class OperatorRegistry:
    """
    Registry for operator implementations.

    Manages operator registration, discovery, and selection based on various criteria
    including operator name, type, and signature.
    """

    def __init__(self):
        """Initialize the registry with built-in operators."""
        self._operators: Dict[str, Type] = {}
        self._type_mapping: Dict[OperatorType, List[str]] = {
            op_type: [] for op_type in OperatorType
        }
        self._version_mapping: Dict[str, Dict[str, Type]] = {}

        # Register built-in operators (placeholder for future implementation)
        self._register_builtin_operators()

    def _register_builtin_operators(self):
        """Register the built-in operators."""
        # Placeholder for built-in operators
        # In the future, this would register standard operators like:
        # - LinearInterpolation
        # - SplineInterpolation
        # - RungeKuttaIntegrator
        # - ForwardDifference
        # etc.
        pass

    def register_operator(
        self,
        name: str,
        operator_type: OperatorType,
        operator_class: Type,
        version: str = "1.0"
    ) -> None:
        """
        Register an operator implementation.

        Args:
            name: Unique name for the operator
            operator_type: Type of the operator
            operator_class: Class implementing the operator
            version: Version string for the operator

        Raises:
            ValueError: If the same version is already registered with a different class
        """
        # Store version mapping first
        if name not in self._version_mapping:
            self._version_mapping[name] = {}

        # Check if this specific version is already registered with a different class
        if (version in self._version_mapping[name] and
            self._version_mapping[name][version] != operator_class):
            raise ValueError(f"Operator '{name}' version '{version}' is already registered with class {self._version_mapping[name][version]}")

        self._version_mapping[name][version] = operator_class

        # Set as default operator class if it's the first registration or if it's version 1.0
        if name not in self._operators or version == "1.0":
            self._operators[name] = operator_class

        # Add to type mapping
        if name not in self._type_mapping[operator_type]:
            self._type_mapping[operator_type].append(name)

    def unregister_operator(self, name: str) -> None:
        """
        Unregister an operator.

        Args:
            name: Name of operator to unregister

        Raises:
            ValueError: If operator name is not registered
        """
        if name not in self._operators:
            raise ValueError(f"Operator '{name}' is not registered")

        # Remove from main registry
        del self._operators[name]

        # Remove from type mappings
        for operator_type, names in self._type_mapping.items():
            if name in names:
                names.remove(name)

        # Remove from version mappings
        if name in self._version_mapping:
            del self._version_mapping[name]

    def get_operator_class(self, name: str, version: Optional[str] = None) -> Type:
        """
        Get the operator class for a given name and optional version.

        Args:
            name: Name of operator to get
            version: Optional version string. If None, uses the default version

        Returns:
            Operator class

        Raises:
            ValueError: If operator name is not registered or version not found
        """
        if name not in self._operators:
            raise ValueError(f"Operator '{name}' is not registered")

        if version is None:
            return self._operators[name]

        if name not in self._version_mapping or version not in self._version_mapping[name]:
            raise ValueError(f"Operator '{name}' version '{version}' is not registered")

        return self._version_mapping[name][version]

    def list_operators_by_type(self, operator_type: OperatorType) -> List[str]:
        """
        List all registered operators of a given type.

        Args:
            operator_type: Type of operators to list

        Returns:
            List of operator names
        """
        return self._type_mapping[operator_type].copy()

    def get_operator_info(self, name: str) -> Dict[str, Any]:
        """
        Get information about a registered operator.

        Args:
            name: Name of the operator

        Returns:
            Dictionary containing operator metadata

        Raises:
            ValueError: If operator name is not registered
        """
        if name not in self._operators:
            raise ValueError(f"Operator '{name}' is not registered")

        operator_class = self._operators[name]

        # Find which type this operator belongs to
        operator_type = None
        for op_type, names in self._type_mapping.items():
            if name in names:
                operator_type = op_type
                break

        # Get available versions
        versions = list(self._version_mapping.get(name, {}).keys())

        return {
            'name': name,
            'class': operator_class,
            'class_name': operator_class.__name__,
            'type': operator_type,
            'versions': versions,
            'default_version': versions[0] if versions else None
        }

    def create_operator(self, operator_config: Operator) -> Any:
        """
        Create an operator instance for the given Operator configuration.

        Args:
            operator_config: Operator configuration

        Returns:
            Operator instance

        Raises:
            ValueError: If the operator name is not registered
        """
        if operator_config.name not in self._operators:
            raise ValueError(f"Operator '{operator_config.name}' is not registered")

        operator_class = self._operators[operator_config.name]
        return operator_class(operator_config)

    def create_operator_by_name(
        self,
        name: str,
        operator_type: OperatorType,
        parameters: Optional[Dict[str, Any]] = None,
        input_variables: Optional[List[str]] = None,
        output_variables: Optional[List[str]] = None,
        version: Optional[str] = None
    ) -> Any:
        """
        Create an operator instance by name and configuration.

        Args:
            name: Name of the operator
            operator_type: Type of the operator
            parameters: Parameters for the operator
            input_variables: List of input variables
            output_variables: List of output variables
            version: Optional version string

        Returns:
            Operator instance

        Raises:
            ValueError: If operator name is not registered
        """
        operator_class = self.get_operator_class(name, version)

        operator_config = Operator(
            name=name,
            type=operator_type,
            parameters=parameters or {},
            input_variables=input_variables or [],
            output_variables=output_variables or []
        )

        return operator_class(operator_config)

    def has_operator(self, name: str, version: Optional[str] = None) -> bool:
        """
        Check if an operator is registered.

        Args:
            name: Name of the operator
            version: Optional version string

        Returns:
            True if operator is registered, False otherwise
        """
        if name not in self._operators:
            return False

        if version is None:
            return True

        return (name in self._version_mapping and
                version in self._version_mapping[name])

    def list_all_operators(self) -> Dict[str, Dict[str, Any]]:
        """
        List all registered operators with their metadata.

        Returns:
            Dictionary mapping operator names to their metadata
        """
        result = {}
        for name in self._operators:
            result[name] = self.get_operator_info(name)
        return result

    def resolve_conflicts(self, conflicts: List[str]) -> Optional[str]:
        """
        Resolve conflicts when multiple operators have the same signature.

        Args:
            conflicts: List of conflicting operator names

        Returns:
            Name of the operator to use, or None if no resolution possible

        Note:
            This is a simple conflict resolution mechanism. In the future,
            more sophisticated resolution strategies could be implemented.
        """
        if not conflicts:
            return None

        # Simple strategy: prefer the first registered operator
        # In the future, this could consider version numbers, priorities, etc.
        return conflicts[0]

    def discover_plugins(self, plugin_dir: Optional[Union[str, Path]] = None) -> int:
        """
        Discover and register operator plugins from a directory.

        Args:
            plugin_dir: Directory to search for plugins. If None, uses default locations.

        Returns:
            Number of plugins discovered and registered

        Note:
            This is a placeholder for future plugin discovery functionality.
            Plugins should define operators following the established pattern.
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

                    # Look for register_operator function in the plugin
                    if hasattr(module, 'register_operator'):
                        module.register_operator(self)
                        plugins_found += 1

                except Exception as e:
                    warnings.warn(f"Failed to load plugin {plugin_file.name}: {e}")

        return plugins_found


# Global registry instance
_global_registry = OperatorRegistry()


def get_registry() -> OperatorRegistry:
    """Get the global operator registry instance."""
    return _global_registry


def register_operator(
    name: str,
    operator_type: OperatorType,
    operator_class: Type,
    version: str = "1.0"
) -> None:
    """
    Register an operator with the global registry.

    Args:
        name: Unique name for the operator
        operator_type: Type of the operator
        operator_class: Class implementing the operator
        version: Version string for the operator
    """
    _global_registry.register_operator(name, operator_type, operator_class, version)


def create_operator(operator_config: Operator) -> Any:
    """
    Create an operator instance using the global registry.

    Args:
        operator_config: Operator configuration

    Returns:
        Operator instance
    """
    return _global_registry.create_operator(operator_config)


def create_operator_by_name(
    name: str,
    operator_type: OperatorType,
    parameters: Optional[Dict[str, Any]] = None,
    input_variables: Optional[List[str]] = None,
    output_variables: Optional[List[str]] = None,
    version: Optional[str] = None
) -> Any:
    """
    Create an operator instance by name using the global registry.

    Args:
        name: Name of the operator
        operator_type: Type of the operator
        parameters: Parameters for the operator
        input_variables: List of input variables
        output_variables: List of output variables
        version: Optional version string

    Returns:
        Operator instance
    """
    return _global_registry.create_operator_by_name(
        name, operator_type, parameters, input_variables, output_variables, version
    )


def list_operators_by_type(operator_type: OperatorType) -> List[str]:
    """
    List all registered operators of a given type using the global registry.

    Args:
        operator_type: Type of operators to list

    Returns:
        List of operator names
    """
    return _global_registry.list_operators_by_type(operator_type)


def has_operator(name: str, version: Optional[str] = None) -> bool:
    """
    Check if an operator is registered using the global registry.

    Args:
        name: Name of the operator
        version: Optional version string

    Returns:
        True if operator is registered, False otherwise
    """
    return _global_registry.has_operator(name, version)