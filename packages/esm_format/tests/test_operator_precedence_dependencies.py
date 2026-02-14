"""
Test cases for operator precedence and dependency system.
"""

import pytest
from unittest.mock import MagicMock

from esm_format.types import Operator, OperatorType
from esm_format.operator_registry import (
    OperatorRegistry,
    Associativity,
    OperatorPrecedence,
    get_registry,
    set_operator_precedence,
    get_operator_precedence,
    compare_precedence,
    add_operator_dependency,
    remove_operator_dependency,
    get_operator_dependencies,
    get_operator_dependents,
    topological_sort_operators,
    get_execution_order,
    register_operator
)


class MockOperator:
    """Mock operator class for testing."""
    def __init__(self, config: Operator):
        self.config = config


class TestOperatorPrecedence:
    """Test cases for operator precedence system."""

    def test_default_precedence_initialization(self):
        """Test that default precedence rules are initialized correctly."""
        registry = OperatorRegistry()

        # Test function-like operators have highest precedence
        sin_prec = registry.get_operator_precedence("sin")
        assert sin_prec is not None
        assert sin_prec.level == 1

        # Test exponentiation has right associativity
        pow_prec = registry.get_operator_precedence("^")
        assert pow_prec is not None
        assert pow_prec.level == 2
        assert pow_prec.associativity == Associativity.RIGHT

        # Test unary minus is unary and prefix
        unary_minus_prec = registry.get_operator_precedence("unary_minus")
        assert unary_minus_prec is not None
        assert unary_minus_prec.is_unary is True
        assert unary_minus_prec.is_prefix is True

        # Test multiplication has higher precedence than addition
        mult_prec = registry.get_operator_precedence("multiply")
        add_prec = registry.get_operator_precedence("add")
        assert mult_prec is not None
        assert add_prec is not None
        assert mult_prec.level < add_prec.level

        # Test logical operators have lowest precedence
        or_prec = registry.get_operator_precedence("or")
        assert or_prec is not None
        assert or_prec.level == 8

    def test_set_and_get_precedence(self):
        """Test setting and getting operator precedence."""
        registry = OperatorRegistry()

        # Set custom precedence
        registry.set_operator_precedence(
            "custom_op",
            level=5,
            associativity=Associativity.RIGHT,
            is_unary=True,
            is_prefix=False
        )

        prec = registry.get_operator_precedence("custom_op")
        assert prec is not None
        assert prec.level == 5
        assert prec.associativity == Associativity.RIGHT
        assert prec.is_unary is True
        assert prec.is_prefix is False

    def test_compare_precedence(self):
        """Test precedence comparison."""
        registry = OperatorRegistry()

        # Test higher precedence (lower level number)
        assert registry.compare_precedence("*", "+") == -1  # multiplication has higher precedence
        assert registry.compare_precedence("+", "*") == 1   # addition has lower precedence
        assert registry.compare_precedence("+", "-") == 0   # same precedence level

        # Test unknown operators
        assert registry.compare_precedence("unknown", "+") == 1  # unknown has lowest precedence
        assert registry.compare_precedence("+", "unknown") == -1
        assert registry.compare_precedence("unknown1", "unknown2") == 0

    def test_precedence_in_operator_registration(self):
        """Test setting precedence during operator registration."""
        registry = OperatorRegistry()

        registry.register_operator(
            name="test_op",
            operator_type=OperatorType.ARITHMETIC,
            operator_class=MockOperator,
            precedence_level=3,
            associativity=Associativity.RIGHT,
            is_unary=True
        )

        prec = registry.get_operator_precedence("test_op")
        assert prec is not None
        assert prec.level == 3
        assert prec.associativity == Associativity.RIGHT
        assert prec.is_unary is True

        # Test operator info includes precedence
        info = registry.get_operator_info("test_op")
        assert info['precedence'] is not None
        assert info['precedence']['level'] == 3
        assert info['precedence']['associativity'] == 'right'
        assert info['precedence']['is_unary'] is True


class TestOperatorDependencies:
    """Test cases for operator dependency system."""

    def test_add_and_get_dependencies(self):
        """Test adding and getting operator dependencies."""
        registry = OperatorRegistry()

        # Register some test operators
        for name in ["op_a", "op_b", "op_c"]:
            registry.register_operator(name, OperatorType.ARITHMETIC, MockOperator)

        # Add dependencies: op_c depends on op_b, op_b depends on op_a
        registry.add_operator_dependency("op_c", "op_b")
        registry.add_operator_dependency("op_b", "op_a")

        # Test getting dependencies
        assert registry.get_operator_dependencies("op_c") == {"op_b"}
        assert registry.get_operator_dependencies("op_b") == {"op_a"}
        assert registry.get_operator_dependencies("op_a") == set()

        # Test getting dependents
        assert registry.get_operator_dependents("op_a") == {"op_b"}
        assert registry.get_operator_dependents("op_b") == {"op_c"}
        assert registry.get_operator_dependents("op_c") == set()

    def test_circular_dependency_detection(self):
        """Test that circular dependencies are detected and prevented."""
        registry = OperatorRegistry()

        # Register test operators
        for name in ["op_a", "op_b", "op_c"]:
            registry.register_operator(name, OperatorType.ARITHMETIC, MockOperator)

        # Create a dependency chain: op_a -> op_b -> op_c
        registry.add_operator_dependency("op_a", "op_b")
        registry.add_operator_dependency("op_b", "op_c")

        # Try to create circular dependency: op_c -> op_a
        with pytest.raises(ValueError, match="would create a circular dependency"):
            registry.add_operator_dependency("op_c", "op_a")

    def test_remove_dependencies(self):
        """Test removing operator dependencies."""
        registry = OperatorRegistry()

        # Register test operators
        for name in ["op_a", "op_b"]:
            registry.register_operator(name, OperatorType.ARITHMETIC, MockOperator)

        # Add dependency
        registry.add_operator_dependency("op_b", "op_a")
        assert registry.get_operator_dependencies("op_b") == {"op_a"}
        assert registry.get_operator_dependents("op_a") == {"op_b"}

        # Remove dependency
        registry.remove_operator_dependency("op_b", "op_a")
        assert registry.get_operator_dependencies("op_b") == set()
        assert registry.get_operator_dependents("op_a") == set()

    def test_topological_sort(self):
        """Test topological sorting of operators."""
        registry = OperatorRegistry()

        # Register test operators
        for name in ["op_a", "op_b", "op_c", "op_d"]:
            registry.register_operator(name, OperatorType.ARITHMETIC, MockOperator)

        # Create dependencies: op_d -> op_b, op_b -> op_a, op_c -> op_a
        registry.add_operator_dependency("op_d", "op_b")
        registry.add_operator_dependency("op_b", "op_a")
        registry.add_operator_dependency("op_c", "op_a")

        sorted_ops = registry.topological_sort_operators(["op_a", "op_b", "op_c", "op_d"])

        # op_a should come before op_b and op_c
        # op_b should come before op_d
        assert sorted_ops.index("op_a") < sorted_ops.index("op_b")
        assert sorted_ops.index("op_a") < sorted_ops.index("op_c")
        assert sorted_ops.index("op_b") < sorted_ops.index("op_d")

    def test_topological_sort_circular_dependency_error(self):
        """Test that circular dependencies cause topological sort to fail."""
        registry = OperatorRegistry()

        # Register test operators
        for name in ["op_a", "op_b"]:
            registry.register_operator(name, OperatorType.ARITHMETIC, MockOperator)

        # Manually create circular dependency (bypassing the check for testing)
        registry._dependencies["op_a"].add("op_b")
        registry._dependencies["op_b"].add("op_a")
        registry._dependents["op_a"].add("op_b")
        registry._dependents["op_b"].add("op_a")

        with pytest.raises(ValueError, match="Circular dependency detected"):
            registry.topological_sort_operators(["op_a", "op_b"])

    def test_execution_order(self):
        """Test getting execution order combining dependencies and precedence."""
        registry = OperatorRegistry()

        # Register operators with different precedence levels
        registry.register_operator("high_prec", OperatorType.ARITHMETIC, MockOperator, precedence_level=1)
        registry.register_operator("medium_prec", OperatorType.ARITHMETIC, MockOperator, precedence_level=5)
        registry.register_operator("low_prec", OperatorType.ARITHMETIC, MockOperator, precedence_level=10)
        registry.register_operator("depends_on_low", OperatorType.ARITHMETIC, MockOperator, precedence_level=1)

        # Create dependency: depends_on_low -> low_prec
        registry.add_operator_dependency("depends_on_low", "low_prec")

        operators = ["high_prec", "medium_prec", "low_prec", "depends_on_low"]
        execution_order = registry.get_execution_order(operators)

        # low_prec must come before depends_on_low (dependency)
        assert execution_order.index("low_prec") < execution_order.index("depends_on_low")

        # Among operators at same dependency level, higher precedence should come first
        # (but this is secondary to dependency constraints)


class TestGlobalRegistryPrecedenceFunctions:
    """Test cases for global precedence and dependency functions."""

    def test_global_precedence_functions(self):
        """Test global precedence management functions."""
        # Set custom precedence
        set_operator_precedence("global_test", 7, Associativity.RIGHT, is_unary=True)

        # Get precedence
        prec = get_operator_precedence("global_test")
        assert prec is not None
        assert prec.level == 7
        assert prec.associativity == Associativity.RIGHT
        assert prec.is_unary is True

        # Compare precedence
        assert compare_precedence("global_test", "+") == 1  # global_test has higher level (lower precedence)

    def test_global_dependency_functions(self):
        """Test global dependency management functions."""
        # Ensure operators are registered
        registry = get_registry()
        cleanup_needed = []

        if "dep_test_a" not in registry._operators:
            register_operator("dep_test_a", OperatorType.ARITHMETIC, MockOperator)
            cleanup_needed.append("dep_test_a")
        if "dep_test_b" not in registry._operators:
            register_operator("dep_test_b", OperatorType.ARITHMETIC, MockOperator)
            cleanup_needed.append("dep_test_b")

        try:
            # Add dependency
            add_operator_dependency("dep_test_b", "dep_test_a")

            # Get dependencies
            deps = get_operator_dependencies("dep_test_b")
            assert "dep_test_a" in deps

            # Get dependents
            dependents = get_operator_dependents("dep_test_a")
            assert "dep_test_b" in dependents

            # Test topological sort
            sorted_ops = topological_sort_operators(["dep_test_a", "dep_test_b"])
            assert sorted_ops.index("dep_test_a") < sorted_ops.index("dep_test_b")

            # Test execution order
            exec_order = get_execution_order(["dep_test_a", "dep_test_b"])
            assert exec_order.index("dep_test_a") < exec_order.index("dep_test_b")

            # Remove dependency
            remove_operator_dependency("dep_test_b", "dep_test_a")
            deps = get_operator_dependencies("dep_test_b")
            assert "dep_test_a" not in deps
        finally:
            # Clean up test operators
            for op_name in cleanup_needed:
                if op_name in registry._operators:
                    registry.unregister_operator(op_name)

    def test_unregister_cleans_up_precedence_and_dependencies(self):
        """Test that unregistering operators cleans up precedence and dependency information."""
        registry = OperatorRegistry()

        # Register operators
        registry.register_operator("cleanup_a", OperatorType.ARITHMETIC, MockOperator, precedence_level=5)
        registry.register_operator("cleanup_b", OperatorType.ARITHMETIC, MockOperator)

        # Set up precedence and dependencies
        registry.add_operator_dependency("cleanup_b", "cleanup_a")

        # Verify setup
        assert registry.get_operator_precedence("cleanup_a") is not None
        assert "cleanup_a" in registry.get_operator_dependencies("cleanup_b")
        assert "cleanup_b" in registry.get_operator_dependents("cleanup_a")

        # Unregister cleanup_a
        registry.unregister_operator("cleanup_a")

        # Verify cleanup
        assert registry.get_operator_precedence("cleanup_a") is None
        assert "cleanup_a" not in registry.get_operator_dependencies("cleanup_b")


class TestOperatorPrecedenceClass:
    """Test cases for OperatorPrecedence class."""

    def test_operator_precedence_creation(self):
        """Test creating OperatorPrecedence instances."""
        # Test defaults
        prec = OperatorPrecedence(5)
        assert prec.level == 5
        assert prec.associativity == Associativity.LEFT
        assert prec.is_unary is False
        assert prec.is_prefix is True

        # Test custom values
        prec = OperatorPrecedence(
            level=3,
            associativity=Associativity.RIGHT,
            is_unary=True,
            is_prefix=False
        )
        assert prec.level == 3
        assert prec.associativity == Associativity.RIGHT
        assert prec.is_unary is True
        assert prec.is_prefix is False


class TestAssociativityEnum:
    """Test cases for Associativity enum."""

    def test_associativity_values(self):
        """Test that Associativity enum has correct values."""
        assert Associativity.LEFT.value == "left"
        assert Associativity.RIGHT.value == "right"
        assert Associativity.NONE.value == "none"


class TestIntegrationScenarios:
    """Integration test scenarios combining precedence and dependencies."""

    def test_complex_expression_evaluation_order(self):
        """Test realistic scenario with complex mathematical expressions."""
        registry = OperatorRegistry()

        # Register operators for a complex expression: sin(x) * cos(y) + z^2
        operations = [
            ("sin", OperatorType.ARITHMETIC, 1),
            ("cos", OperatorType.ARITHMETIC, 1),
            ("*", OperatorType.ARITHMETIC, 4),
            ("+", OperatorType.ARITHMETIC, 5),
            ("^", OperatorType.ARITHMETIC, 2)
        ]

        for name, op_type, prec_level in operations:
            registry.register_operator(
                name=name,
                operator_type=op_type,
                operator_class=MockOperator,
                precedence_level=prec_level,
                associativity=Associativity.RIGHT if name == "^" else Associativity.LEFT
            )

        # Test precedence comparisons
        assert registry.compare_precedence("sin", "*") == -1  # sin has higher precedence
        assert registry.compare_precedence("*", "+") == -1    # * has higher precedence than +
        assert registry.compare_precedence("^", "*") == -1    # ^ has higher precedence than *

        # Test execution order
        operators = ["sin", "cos", "*", "^", "+"]
        execution_order = registry.get_execution_order(operators)

        # Functions (sin, cos) should have highest precedence
        sin_idx = execution_order.index("sin")
        cos_idx = execution_order.index("cos")
        mult_idx = execution_order.index("*")
        pow_idx = execution_order.index("^")
        add_idx = execution_order.index("+")

        # Higher precedence operators should appear first in execution order
        assert sin_idx < mult_idx < add_idx
        assert cos_idx < mult_idx < add_idx
        assert pow_idx < add_idx

    def test_chemical_equation_dependencies(self):
        """Test operator dependencies in chemical equations context."""
        registry = OperatorRegistry()

        # Register operators that might be used in chemical equations (use custom names to avoid conflicts)
        operators = [
            ("derivative_op", OperatorType.DIFFERENTIATION, 1),  # Derivative
            ("gradient_op", OperatorType.DIFFERENTIATION, 1),  # Gradient
            ("mult_op", OperatorType.ARITHMETIC, 4),  # Multiplication
            ("add_op", OperatorType.ARITHMETIC, 5),  # Addition
        ]

        for name, op_type, prec_level in operators:
            registry.register_operator(
                name=name,
                operator_type=op_type,
                operator_class=MockOperator,
                precedence_level=prec_level
            )

        # Add dependency: gradient calculation depends on derivative calculation
        registry.add_operator_dependency("gradient_op", "derivative_op")

        # Test that dependency is respected in execution order
        execution_order = registry.get_execution_order(["derivative_op", "gradient_op", "mult_op", "add_op"])
        assert execution_order.index("derivative_op") < execution_order.index("gradient_op")