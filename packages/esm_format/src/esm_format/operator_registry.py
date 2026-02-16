"""
Operator registry and plugin system for ESM Format.

This module provides a registry system allowing runtime registration of new operators,
plugin discovery, operator selection based on name/type, operator versioning,
precedence rules, dependency tracking, and execution ordering.
"""

import warnings
from typing import Dict, List, Type, Optional, Callable, Any, Union, Set, Tuple
from importlib import import_module
from pathlib import Path
from enum import Enum
from collections import defaultdict, deque

from .types import Operator, OperatorType


class Associativity(Enum):
    """Operator associativity rules."""
    LEFT = "left"
    RIGHT = "right"
    NONE = "none"  # For non-associative operators


class OperatorPrecedence:
    """Operator precedence and associativity information."""

    def __init__(
        self,
        level: int,
        associativity: Associativity = Associativity.LEFT,
        is_unary: bool = False,
        is_prefix: bool = True
    ):
        """
        Initialize operator precedence information.

        Args:
            level: Precedence level (lower numbers = higher precedence)
            associativity: How operator associates when used multiple times
            is_unary: Whether this is a unary operator
            is_prefix: Whether unary operator is prefix (True) or postfix (False)
        """
        self.level = level
        self.associativity = associativity
        self.is_unary = is_unary
        self.is_prefix = is_prefix


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

        # Precedence and dependency tracking
        self._precedence: Dict[str, OperatorPrecedence] = {}
        self._dependencies: Dict[str, Set[str]] = defaultdict(set)  # operator -> set of operators it depends on
        self._dependents: Dict[str, Set[str]] = defaultdict(set)    # operator -> set of operators that depend on it

        # Initialize precedence rules based on mathematical conventions
        self._initialize_default_precedence()

        # Register built-in operators (placeholder for future implementation)
        self._register_builtin_operators()

    def _initialize_default_precedence(self):
        """Initialize default operator precedence rules based on mathematical conventions."""
        # Based on precedence rules from the operator_precedence.json file
        precedence_rules = {
            # Level 1: Function application, derivatives, spatial operators (highest precedence)
            "sin": OperatorPrecedence(1),
            "cos": OperatorPrecedence(1),
            "exp": OperatorPrecedence(1),
            "log": OperatorPrecedence(1),
            "Pre": OperatorPrecedence(1),  # Event operator
            "D": OperatorPrecedence(1),    # Derivative operator
            "grad": OperatorPrecedence(1),
            "div": OperatorPrecedence(1),
            "laplacian": OperatorPrecedence(1),
            "time_derivative": OperatorPrecedence(1),
            "time_integral": OperatorPrecedence(1),
            "temporal_average": OperatorPrecedence(1),
            "time_stepping": OperatorPrecedence(1),

            # Statistical operators (same level as functions)
            "mean": OperatorPrecedence(1),
            "variance": OperatorPrecedence(1),
            "std": OperatorPrecedence(1),
            "percentile": OperatorPrecedence(1),
            "median": OperatorPrecedence(1),

            # Interpolation operators (same level as functions)
            "linear_interpolation": OperatorPrecedence(1),
            "cubic_interpolation": OperatorPrecedence(1),
            "spline_interpolation": OperatorPrecedence(1),
            "grid_interpolation": OperatorPrecedence(1),

            # Level 2: Exponentiation (right-associative)
            "^": OperatorPrecedence(2, Associativity.RIGHT),

            # Level 3: Unary minus (prefix unary operator)
            "unary_minus": OperatorPrecedence(3, Associativity.NONE, is_unary=True, is_prefix=True),

            # Level 4: Multiplication and division (left-associative)
            "*": OperatorPrecedence(4, Associativity.LEFT),
            "multiply": OperatorPrecedence(4, Associativity.LEFT),
            "/": OperatorPrecedence(4, Associativity.LEFT),
            "divide": OperatorPrecedence(4, Associativity.LEFT),

            # Level 5: Addition and subtraction (left-associative)
            "+": OperatorPrecedence(5, Associativity.LEFT),
            "add": OperatorPrecedence(5, Associativity.LEFT),
            "-": OperatorPrecedence(5, Associativity.LEFT),
            "subtract": OperatorPrecedence(5, Associativity.LEFT),

            # Level 6: Comparison operators
            ">": OperatorPrecedence(6),
            "<": OperatorPrecedence(6),
            ">=": OperatorPrecedence(6),
            "<=": OperatorPrecedence(6),
            "==": OperatorPrecedence(6),
            "!=": OperatorPrecedence(6),
            "gt": OperatorPrecedence(6),
            "lt": OperatorPrecedence(6),
            "ge": OperatorPrecedence(6),
            "le": OperatorPrecedence(6),
            "eq": OperatorPrecedence(6),
            "ne": OperatorPrecedence(6),

            # Level 7: Logical AND
            "and": OperatorPrecedence(7),

            # Level 8: Logical OR (lowest precedence)
            "or": OperatorPrecedence(8),

            # Logical NOT (unary, higher precedence than binary logical operators)
            "not": OperatorPrecedence(3, Associativity.NONE, is_unary=True, is_prefix=True),
        }

        self._precedence.update(precedence_rules)

    def _register_builtin_operators(self):
        """Register the built-in operators."""
        from .math_operators import AddOperator, SubtractOperator, MultiplyOperator, DivideOperator
        from .logical_operators import (
            AndOperator, OrOperator, NotOperator,
            EqualOperator, NotEqualOperator, LessThanOperator,
            LessThanOrEqualOperator, GreaterThanOperator, GreaterThanOrEqualOperator
        )
        from .spatial_operators import GradientOperator, DivergenceOperator, LaplacianOperator
        from .temporal_operators import (
            DerivativeOperator, IntegralOperator, TemporalAveragingOperator, TimeSteppingOperator
        )
        from .statistical_operators import (
            MeanOperator, VarianceOperator, PercentileOperator, StandardDeviationOperator, MedianOperator
        )
        from .interpolation_operators import (
            LinearInterpolationOperator, CubicInterpolationOperator, SplineInterpolationOperator, GridInterpolationOperator
        )

        # Register mathematical operators
        self.register_operator(
            name="add",
            operator_type=OperatorType.ARITHMETIC,
            operator_class=AddOperator,
            version="1.0"
        )

        self.register_operator(
            name="subtract",
            operator_type=OperatorType.ARITHMETIC,
            operator_class=SubtractOperator,
            version="1.0"
        )

        self.register_operator(
            name="multiply",
            operator_type=OperatorType.ARITHMETIC,
            operator_class=MultiplyOperator,
            version="1.0"
        )

        self.register_operator(
            name="divide",
            operator_type=OperatorType.ARITHMETIC,
            operator_class=DivideOperator,
            version="1.0"
        )

        # Register logical operators
        self.register_operator(
            name="and",
            operator_type=OperatorType.LOGICAL,
            operator_class=AndOperator,
            version="1.0"
        )

        self.register_operator(
            name="or",
            operator_type=OperatorType.LOGICAL,
            operator_class=OrOperator,
            version="1.0"
        )

        self.register_operator(
            name="not",
            operator_type=OperatorType.LOGICAL,
            operator_class=NotOperator,
            version="1.0"
        )

        # Register comparison operators
        self.register_operator(
            name="eq",
            operator_type=OperatorType.LOGICAL,
            operator_class=EqualOperator,
            version="1.0"
        )

        self.register_operator(
            name="ne",
            operator_type=OperatorType.LOGICAL,
            operator_class=NotEqualOperator,
            version="1.0"
        )

        self.register_operator(
            name="lt",
            operator_type=OperatorType.LOGICAL,
            operator_class=LessThanOperator,
            version="1.0"
        )

        self.register_operator(
            name="le",
            operator_type=OperatorType.LOGICAL,
            operator_class=LessThanOrEqualOperator,
            version="1.0"
        )

        self.register_operator(
            name="gt",
            operator_type=OperatorType.LOGICAL,
            operator_class=GreaterThanOperator,
            version="1.0"
        )

        self.register_operator(
            name="ge",
            operator_type=OperatorType.LOGICAL,
            operator_class=GreaterThanOrEqualOperator,
            version="1.0"
        )

        # Register spatial differential operators
        self.register_operator(
            name="grad",
            operator_type=OperatorType.DIFFERENTIATION,
            operator_class=GradientOperator,
            version="1.0"
        )

        self.register_operator(
            name="div",
            operator_type=OperatorType.DIFFERENTIATION,
            operator_class=DivergenceOperator,
            version="1.0"
        )

        self.register_operator(
            name="laplacian",
            operator_type=OperatorType.DIFFERENTIATION,
            operator_class=LaplacianOperator,
            version="1.0"
        )

        # Register temporal operators
        self.register_operator(
            name="time_derivative",
            operator_type=OperatorType.DIFFERENTIATION,
            operator_class=DerivativeOperator,
            version="1.0"
        )

        self.register_operator(
            name="time_integral",
            operator_type=OperatorType.INTEGRATION,
            operator_class=IntegralOperator,
            version="1.0"
        )

        self.register_operator(
            name="temporal_average",
            operator_type=OperatorType.FILTERING,
            operator_class=TemporalAveragingOperator,
            version="1.0"
        )

        self.register_operator(
            name="time_stepping",
            operator_type=OperatorType.INTEGRATION,
            operator_class=TimeSteppingOperator,
            version="1.0"
        )

        # Register statistical operators
        self.register_operator(
            name="mean",
            operator_type=OperatorType.STATISTICAL,
            operator_class=MeanOperator,
            version="1.0"
        )

        self.register_operator(
            name="variance",
            operator_type=OperatorType.STATISTICAL,
            operator_class=VarianceOperator,
            version="1.0"
        )

        self.register_operator(
            name="std",
            operator_type=OperatorType.STATISTICAL,
            operator_class=StandardDeviationOperator,
            version="1.0"
        )

        self.register_operator(
            name="percentile",
            operator_type=OperatorType.STATISTICAL,
            operator_class=PercentileOperator,
            version="1.0"
        )

        self.register_operator(
            name="median",
            operator_type=OperatorType.STATISTICAL,
            operator_class=MedianOperator,
            version="1.0"
        )

        # Register interpolation operators
        self.register_operator(
            name="linear_interpolation",
            operator_type=OperatorType.INTERPOLATION,
            operator_class=LinearInterpolationOperator,
            version="1.0"
        )

        self.register_operator(
            name="cubic_interpolation",
            operator_type=OperatorType.INTERPOLATION,
            operator_class=CubicInterpolationOperator,
            version="1.0"
        )

        self.register_operator(
            name="spline_interpolation",
            operator_type=OperatorType.INTERPOLATION,
            operator_class=SplineInterpolationOperator,
            version="1.0"
        )

        self.register_operator(
            name="grid_interpolation",
            operator_type=OperatorType.INTERPOLATION,
            operator_class=GridInterpolationOperator,
            version="1.0"
        )

    def set_operator_precedence(
        self,
        name: str,
        level: int,
        associativity: Associativity = Associativity.LEFT,
        is_unary: bool = False,
        is_prefix: bool = True
    ) -> None:
        """
        Set precedence information for an operator.

        Args:
            name: Name of the operator
            level: Precedence level (lower numbers = higher precedence)
            associativity: How operator associates when used multiple times
            is_unary: Whether this is a unary operator
            is_prefix: Whether unary operator is prefix (True) or postfix (False)
        """
        self._precedence[name] = OperatorPrecedence(level, associativity, is_unary, is_prefix)

    def get_operator_precedence(self, name: str) -> Optional[OperatorPrecedence]:
        """
        Get precedence information for an operator.

        Args:
            name: Name of the operator

        Returns:
            OperatorPrecedence instance, or None if not set
        """
        return self._precedence.get(name)

    def compare_precedence(self, op1: str, op2: str) -> int:
        """
        Compare precedence of two operators.

        Args:
            op1: First operator name
            op2: Second operator name

        Returns:
            -1 if op1 has higher precedence (lower level number)
             0 if same precedence
             1 if op2 has higher precedence
        """
        prec1 = self._precedence.get(op1)
        prec2 = self._precedence.get(op2)

        if prec1 is None and prec2 is None:
            return 0
        if prec1 is None:
            return 1  # Unknown operators have lowest precedence
        if prec2 is None:
            return -1

        if prec1.level < prec2.level:
            return -1
        elif prec1.level > prec2.level:
            return 1
        else:
            return 0

    def add_operator_dependency(self, operator: str, depends_on: str) -> None:
        """
        Add a dependency between operators.

        Args:
            operator: Name of operator that has dependency
            depends_on: Name of operator that is depended upon

        Raises:
            ValueError: If circular dependency would be created
        """
        # Check for circular dependency
        if self._would_create_circular_dependency(operator, depends_on):
            raise ValueError(f"Adding dependency {operator} -> {depends_on} would create a circular dependency")

        self._dependencies[operator].add(depends_on)
        self._dependents[depends_on].add(operator)

    def remove_operator_dependency(self, operator: str, depends_on: str) -> None:
        """
        Remove a dependency between operators.

        Args:
            operator: Name of operator that has dependency
            depends_on: Name of operator that is depended upon
        """
        self._dependencies[operator].discard(depends_on)
        self._dependents[depends_on].discard(operator)

    def get_operator_dependencies(self, operator: str) -> Set[str]:
        """
        Get all operators that this operator depends on.

        Args:
            operator: Name of the operator

        Returns:
            Set of operator names that this operator depends on
        """
        return self._dependencies[operator].copy()

    def get_operator_dependents(self, operator: str) -> Set[str]:
        """
        Get all operators that depend on this operator.

        Args:
            operator: Name of the operator

        Returns:
            Set of operator names that depend on this operator
        """
        return self._dependents[operator].copy()

    def _would_create_circular_dependency(self, operator: str, depends_on: str) -> bool:
        """
        Check if adding a dependency would create a circular dependency.

        Args:
            operator: Name of operator that would have dependency
            depends_on: Name of operator that would be depended upon

        Returns:
            True if circular dependency would be created, False otherwise
        """
        # Use DFS to check if depends_on already depends on operator (directly or indirectly)
        visited = set()
        stack = [depends_on]

        while stack:
            current = stack.pop()
            if current == operator:
                return True
            if current in visited:
                continue
            visited.add(current)
            stack.extend(self._dependencies[current])

        return False

    def topological_sort_operators(self, operators: List[str]) -> List[str]:
        """
        Sort operators topologically based on their dependencies.

        Args:
            operators: List of operator names to sort

        Returns:
            List of operator names in topological order (dependencies first)

        Raises:
            ValueError: If circular dependency exists among the given operators
        """
        # Create subgraph with only the given operators
        subgraph_deps = {}
        subgraph_indegree = {}

        for op in operators:
            subgraph_deps[op] = [dep for dep in self._dependencies[op] if dep in operators]
            subgraph_indegree[op] = len(subgraph_deps[op])

        # Kahn's algorithm for topological sorting
        result = []
        queue = deque([op for op in operators if subgraph_indegree[op] == 0])

        while queue:
            current = queue.popleft()
            result.append(current)

            # Update in-degrees of dependents
            for dependent in self._dependents[current]:
                if dependent in operators:
                    subgraph_indegree[dependent] -= 1
                    if subgraph_indegree[dependent] == 0:
                        queue.append(dependent)

        if len(result) != len(operators):
            # Circular dependency exists
            remaining = [op for op in operators if op not in result]
            raise ValueError(f"Circular dependency detected among operators: {remaining}")

        return result

    def get_execution_order(self, operators: List[str]) -> List[str]:
        """
        Get the execution order for a list of operators considering both dependencies and precedence.

        Args:
            operators: List of operator names

        Returns:
            List of operator names in execution order

        Raises:
            ValueError: If circular dependency exists
        """
        # First, sort by dependencies
        dependency_sorted = self.topological_sort_operators(operators)

        # Within operators of the same dependency level, sort by precedence
        # Group by dependency levels
        levels = {}
        for op in dependency_sorted:
            level = self._get_dependency_level(op, operators)
            if level not in levels:
                levels[level] = []
            levels[level].append(op)

        # Sort each level by precedence (higher precedence = lower precedence level number)
        result = []
        for level in sorted(levels.keys()):
            level_ops = levels[level]
            level_ops.sort(key=lambda op: self._precedence.get(op, OperatorPrecedence(999)).level)
            result.extend(level_ops)

        return result

    def _get_dependency_level(self, operator: str, all_operators: List[str]) -> int:
        """
        Get the dependency level of an operator (0 = no dependencies, 1 = depends on level 0, etc.)

        Args:
            operator: Name of the operator
            all_operators: List of all operators being considered

        Returns:
            Dependency level
        """
        visited = set()
        return self._calculate_dependency_level(operator, all_operators, visited)

    def _calculate_dependency_level(self, operator: str, all_operators: List[str], visited: Set[str]) -> int:
        """
        Recursively calculate dependency level.

        Args:
            operator: Name of the operator
            all_operators: List of all operators being considered
            visited: Set of already visited operators

        Returns:
            Dependency level
        """
        if operator in visited:
            return 0  # Avoid infinite recursion

        visited.add(operator)
        dependencies = [dep for dep in self._dependencies[operator] if dep in all_operators]

        if not dependencies:
            return 0

        max_level = 0
        for dep in dependencies:
            level = self._calculate_dependency_level(dep, all_operators, visited.copy())
            max_level = max(max_level, level + 1)

        return max_level

    def register_operator(
        self,
        name: str,
        operator_type: OperatorType,
        operator_class: Type,
        version: str = "1.0",
        precedence_level: Optional[int] = None,
        associativity: Associativity = Associativity.LEFT,
        is_unary: bool = False,
        is_prefix: bool = True
    ) -> None:
        """
        Register an operator implementation.

        Args:
            name: Unique name for the operator
            operator_type: Type of the operator
            operator_class: Class implementing the operator
            version: Version string for the operator
            precedence_level: Optional precedence level (lower = higher precedence)
            associativity: How the operator associates
            is_unary: Whether this is a unary operator
            is_prefix: Whether unary operator is prefix (True) or postfix (False)

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

        # Set precedence if provided (or use default if exists)
        if precedence_level is not None:
            self.set_operator_precedence(name, precedence_level, associativity, is_unary, is_prefix)
        elif name not in self._precedence:
            # Set a default precedence for unknown operators (lowest priority)
            self.set_operator_precedence(name, 999, associativity, is_unary, is_prefix)

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

        # Remove precedence information
        if name in self._precedence:
            del self._precedence[name]

        # Remove dependency information
        if name in self._dependencies:
            # Remove this operator's dependencies
            for depends_on in self._dependencies[name]:
                self._dependents[depends_on].discard(name)
            del self._dependencies[name]

        if name in self._dependents:
            # Remove dependencies on this operator
            for dependent in self._dependents[name]:
                self._dependencies[dependent].discard(name)
            del self._dependents[name]

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

        # Get precedence information
        precedence = self._precedence.get(name)
        precedence_info = None
        if precedence:
            precedence_info = {
                'level': precedence.level,
                'associativity': precedence.associativity.value,
                'is_unary': precedence.is_unary,
                'is_prefix': precedence.is_prefix
            }

        return {
            'name': name,
            'class': operator_class,
            'class_name': operator_class.__name__,
            'type': operator_type,
            'versions': versions,
            'default_version': versions[0] if versions else None,
            'precedence': precedence_info,
            'dependencies': list(self._dependencies[name]),
            'dependents': list(self._dependents[name])
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
    version: str = "1.0",
    precedence_level: Optional[int] = None,
    associativity: Associativity = Associativity.LEFT,
    is_unary: bool = False,
    is_prefix: bool = True
) -> None:
    """
    Register an operator with the global registry.

    Args:
        name: Unique name for the operator
        operator_type: Type of the operator
        operator_class: Class implementing the operator
        version: Version string for the operator
        precedence_level: Optional precedence level (lower = higher precedence)
        associativity: How the operator associates
        is_unary: Whether this is a unary operator
        is_prefix: Whether unary operator is prefix (True) or postfix (False)
    """
    _global_registry.register_operator(name, operator_type, operator_class, version,
                                       precedence_level, associativity, is_unary, is_prefix)


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


def set_operator_precedence(
    name: str,
    level: int,
    associativity: Associativity = Associativity.LEFT,
    is_unary: bool = False,
    is_prefix: bool = True
) -> None:
    """
    Set precedence information for an operator using the global registry.

    Args:
        name: Name of the operator
        level: Precedence level (lower numbers = higher precedence)
        associativity: How operator associates when used multiple times
        is_unary: Whether this is a unary operator
        is_prefix: Whether unary operator is prefix (True) or postfix (False)
    """
    _global_registry.set_operator_precedence(name, level, associativity, is_unary, is_prefix)


def get_operator_precedence(name: str) -> Optional[OperatorPrecedence]:
    """
    Get precedence information for an operator using the global registry.

    Args:
        name: Name of the operator

    Returns:
        OperatorPrecedence instance, or None if not set
    """
    return _global_registry.get_operator_precedence(name)


def compare_precedence(op1: str, op2: str) -> int:
    """
    Compare precedence of two operators using the global registry.

    Args:
        op1: First operator name
        op2: Second operator name

    Returns:
        -1 if op1 has higher precedence
         0 if same precedence
         1 if op2 has higher precedence
    """
    return _global_registry.compare_precedence(op1, op2)


def add_operator_dependency(operator: str, depends_on: str) -> None:
    """
    Add a dependency between operators using the global registry.

    Args:
        operator: Name of operator that has dependency
        depends_on: Name of operator that is depended upon

    Raises:
        ValueError: If circular dependency would be created
    """
    _global_registry.add_operator_dependency(operator, depends_on)


def remove_operator_dependency(operator: str, depends_on: str) -> None:
    """
    Remove a dependency between operators using the global registry.

    Args:
        operator: Name of operator that has dependency
        depends_on: Name of operator that is depended upon
    """
    _global_registry.remove_operator_dependency(operator, depends_on)


def get_operator_dependencies(operator: str) -> Set[str]:
    """
    Get all operators that this operator depends on using the global registry.

    Args:
        operator: Name of the operator

    Returns:
        Set of operator names that this operator depends on
    """
    return _global_registry.get_operator_dependencies(operator)


def get_operator_dependents(operator: str) -> Set[str]:
    """
    Get all operators that depend on this operator using the global registry.

    Args:
        operator: Name of the operator

    Returns:
        Set of operator names that depend on this operator
    """
    return _global_registry.get_operator_dependents(operator)


def topological_sort_operators(operators: List[str]) -> List[str]:
    """
    Sort operators topologically based on their dependencies using the global registry.

    Args:
        operators: List of operator names to sort

    Returns:
        List of operator names in topological order (dependencies first)

    Raises:
        ValueError: If circular dependency exists among the given operators
    """
    return _global_registry.topological_sort_operators(operators)


def get_execution_order(operators: List[str]) -> List[str]:
    """
    Get the execution order for a list of operators using the global registry.

    Args:
        operators: List of operator names

    Returns:
        List of operator names in execution order

    Raises:
        ValueError: If circular dependency exists
    """
    return _global_registry.get_execution_order(operators)