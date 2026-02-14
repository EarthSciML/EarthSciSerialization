"""
Test cases for the operator registry and plugin system.
"""

import pytest
import tempfile
import warnings
from pathlib import Path
from unittest.mock import patch, MagicMock

from esm_format.types import Operator, OperatorType
from esm_format.operator_registry import (
    OperatorRegistry,
    get_registry,
    register_operator,
    create_operator,
    create_operator_by_name,
    list_operators_by_type,
    has_operator
)


class MockOperator:
    """Mock operator class for testing."""

    def __init__(self, config: Operator):
        self.config = config
        self.name = config.name
        self.type = config.type
        self.parameters = config.parameters
        self.input_variables = config.input_variables
        self.output_variables = config.output_variables


class AlternativeMockOperator:
    """Alternative mock operator class for testing conflicts."""

    def __init__(self, config: Operator):
        self.config = config


class TestOperatorRegistry:
    """Test cases for OperatorRegistry class."""

    def test_registry_initialization(self):
        """Test that registry initializes correctly."""
        registry = OperatorRegistry()

        # Check that all operator types are initialized
        for op_type in OperatorType:
            assert op_type in registry._type_mapping
            assert isinstance(registry._type_mapping[op_type], list)

    def test_register_new_operator(self):
        """Test registering a new operator."""
        registry = OperatorRegistry()

        registry.register_operator(
            name="test_interpolation",
            operator_type=OperatorType.INTERPOLATION,
            operator_class=MockOperator,
            version="1.0"
        )

        # Check operator is registered
        assert "test_interpolation" in registry._operators
        assert registry._operators["test_interpolation"] == MockOperator
        assert "test_interpolation" in registry._type_mapping[OperatorType.INTERPOLATION]
        assert "test_interpolation" in registry._version_mapping
        assert "1.0" in registry._version_mapping["test_interpolation"]

    def test_register_duplicate_operator_error(self):
        """Test that registering duplicate version with different class raises error."""
        registry = OperatorRegistry()

        # Register first operator
        registry.register_operator(
            name="duplicate_test",
            operator_type=OperatorType.INTERPOLATION,
            operator_class=MockOperator,
            version="1.0"
        )

        # Try to register same version with different class - should raise error
        with pytest.raises(ValueError, match="version '1.0' is already registered with class"):
            registry.register_operator(
                name="duplicate_test",
                operator_type=OperatorType.INTERPOLATION,
                operator_class=AlternativeMockOperator,
                version="1.0"
            )

    def test_register_same_operator_same_class(self):
        """Test that re-registering the same operator with same class is allowed."""
        registry = OperatorRegistry()

        # Register first time
        registry.register_operator(
            name="same_test",
            operator_type=OperatorType.INTERPOLATION,
            operator_class=MockOperator
        )

        # Re-register with same class - should not raise error
        registry.register_operator(
            name="same_test",
            operator_type=OperatorType.INTERPOLATION,
            operator_class=MockOperator
        )

        assert registry._operators["same_test"] == MockOperator

    def test_unregister_operator(self):
        """Test unregistering an operator."""
        registry = OperatorRegistry()

        # Register operator
        registry.register_operator(
            name="to_remove",
            operator_type=OperatorType.INTEGRATION,
            operator_class=MockOperator
        )

        # Verify it's registered
        assert "to_remove" in registry._operators
        assert "to_remove" in registry._type_mapping[OperatorType.INTEGRATION]

        # Unregister
        registry.unregister_operator("to_remove")

        # Verify it's removed
        assert "to_remove" not in registry._operators
        assert "to_remove" not in registry._type_mapping[OperatorType.INTEGRATION]
        assert "to_remove" not in registry._version_mapping

    def test_unregister_nonexistent_operator_error(self):
        """Test that unregistering nonexistent operator raises error."""
        registry = OperatorRegistry()

        with pytest.raises(ValueError, match="is not registered"):
            registry.unregister_operator("nonexistent")

    def test_get_operator_class(self):
        """Test getting operator class."""
        registry = OperatorRegistry()

        registry.register_operator(
            name="test_get",
            operator_type=OperatorType.FILTERING,
            operator_class=MockOperator,
            version="2.0"
        )

        # Test getting without version
        cls = registry.get_operator_class("test_get")
        assert cls == MockOperator

        # Test getting with version
        cls = registry.get_operator_class("test_get", "2.0")
        assert cls == MockOperator

    def test_get_nonexistent_operator_class_error(self):
        """Test that getting nonexistent operator class raises error."""
        registry = OperatorRegistry()

        with pytest.raises(ValueError, match="is not registered"):
            registry.get_operator_class("nonexistent")

    def test_get_nonexistent_version_error(self):
        """Test that getting nonexistent version raises error."""
        registry = OperatorRegistry()

        registry.register_operator(
            name="versioned",
            operator_type=OperatorType.TRANSFORMATION,
            operator_class=MockOperator,
            version="1.0"
        )

        with pytest.raises(ValueError, match="version '2.0' is not registered"):
            registry.get_operator_class("versioned", "2.0")

    def test_list_operators_by_type(self):
        """Test listing operators by type."""
        registry = OperatorRegistry()

        # Register operators of different types
        registry.register_operator(
            name="interp1",
            operator_type=OperatorType.INTERPOLATION,
            operator_class=MockOperator
        )
        registry.register_operator(
            name="interp2",
            operator_type=OperatorType.INTERPOLATION,
            operator_class=MockOperator
        )
        registry.register_operator(
            name="filter1",
            operator_type=OperatorType.FILTERING,
            operator_class=MockOperator
        )

        # Test listing
        interp_ops = registry.list_operators_by_type(OperatorType.INTERPOLATION)
        assert set(interp_ops) == {"interp1", "interp2"}

        filter_ops = registry.list_operators_by_type(OperatorType.FILTERING)
        assert filter_ops == ["filter1"]

        # Test empty type
        diff_ops = registry.list_operators_by_type(OperatorType.DIFFERENTIATION)
        assert diff_ops == []

    def test_get_operator_info(self):
        """Test getting operator information."""
        registry = OperatorRegistry()

        registry.register_operator(
            name="info_test",
            operator_type=OperatorType.INTEGRATION,
            operator_class=MockOperator,
            version="1.5"
        )

        info = registry.get_operator_info("info_test")

        assert info['name'] == "info_test"
        assert info['class'] == MockOperator
        assert info['class_name'] == "MockOperator"
        assert info['type'] == OperatorType.INTEGRATION
        assert "1.5" in info['versions']
        assert info['default_version'] == "1.5"

    def test_get_operator_info_nonexistent_error(self):
        """Test that getting info for nonexistent operator raises error."""
        registry = OperatorRegistry()

        with pytest.raises(ValueError, match="is not registered"):
            registry.get_operator_info("nonexistent")

    def test_create_operator(self):
        """Test creating operator from configuration."""
        registry = OperatorRegistry()

        registry.register_operator(
            name="create_test",
            operator_type=OperatorType.TRANSFORMATION,
            operator_class=MockOperator
        )

        config = Operator(
            name="create_test",
            type=OperatorType.TRANSFORMATION,
            parameters={"param1": "value1"},
            input_variables=["x", "y"],
            output_variables=["z"]
        )

        instance = registry.create_operator(config)

        assert isinstance(instance, MockOperator)
        assert instance.config == config
        assert instance.name == "create_test"
        assert instance.type == OperatorType.TRANSFORMATION
        assert instance.parameters == {"param1": "value1"}

    def test_create_operator_nonexistent_error(self):
        """Test that creating nonexistent operator raises error."""
        registry = OperatorRegistry()

        config = Operator(
            name="nonexistent",
            type=OperatorType.TRANSFORMATION,
            parameters={},
            input_variables=[],
            output_variables=[]
        )

        with pytest.raises(ValueError, match="is not registered"):
            registry.create_operator(config)

    def test_create_operator_by_name(self):
        """Test creating operator by name."""
        registry = OperatorRegistry()

        registry.register_operator(
            name="by_name_test",
            operator_type=OperatorType.DIFFERENTIATION,
            operator_class=MockOperator
        )

        instance = registry.create_operator_by_name(
            name="by_name_test",
            operator_type=OperatorType.DIFFERENTIATION,
            parameters={"order": 2},
            input_variables=["f"],
            output_variables=["df_dx"]
        )

        assert isinstance(instance, MockOperator)
        assert instance.name == "by_name_test"
        assert instance.type == OperatorType.DIFFERENTIATION
        assert instance.parameters == {"order": 2}
        assert instance.input_variables == ["f"]
        assert instance.output_variables == ["df_dx"]

    def test_has_operator(self):
        """Test checking if operator exists."""
        registry = OperatorRegistry()

        registry.register_operator(
            name="exists_test",
            operator_type=OperatorType.FILTERING,
            operator_class=MockOperator,
            version="1.0"
        )

        # Test existence
        assert registry.has_operator("exists_test")
        assert registry.has_operator("exists_test", "1.0")
        assert not registry.has_operator("exists_test", "2.0")
        assert not registry.has_operator("nonexistent")

    def test_list_all_operators(self):
        """Test listing all operators."""
        registry = OperatorRegistry()

        registry.register_operator(
            name="op1",
            operator_type=OperatorType.INTERPOLATION,
            operator_class=MockOperator
        )
        registry.register_operator(
            name="op2",
            operator_type=OperatorType.INTEGRATION,
            operator_class=MockOperator
        )

        all_ops = registry.list_all_operators()

        assert "op1" in all_ops
        assert "op2" in all_ops
        assert all_ops["op1"]["type"] == OperatorType.INTERPOLATION
        assert all_ops["op2"]["type"] == OperatorType.INTEGRATION

    def test_resolve_conflicts(self):
        """Test conflict resolution."""
        registry = OperatorRegistry()

        # Test empty conflicts
        assert registry.resolve_conflicts([]) is None

        # Test single conflict (no real conflict)
        assert registry.resolve_conflicts(["op1"]) == "op1"

        # Test multiple conflicts - should return first one
        assert registry.resolve_conflicts(["op1", "op2", "op3"]) == "op1"

    def test_discover_plugins_no_directory(self):
        """Test plugin discovery when directory doesn't exist."""
        registry = OperatorRegistry()

        # Test with nonexistent directory
        result = registry.discover_plugins(Path("/nonexistent/path"))
        assert result == 0

    def test_discover_plugins_empty_directory(self):
        """Test plugin discovery in empty directory."""
        registry = OperatorRegistry()

        with tempfile.TemporaryDirectory() as temp_dir:
            result = registry.discover_plugins(Path(temp_dir))
            assert result == 0

    def test_discover_plugins_with_mock_plugin(self):
        """Test plugin discovery with mock plugin."""
        registry = OperatorRegistry()

        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_path = Path(temp_dir) / "mock_plugin.py"
            plugin_path.write_text("""
def register_operator(registry):
    # Mock registration
    pass
""")

            # Mock the import_module function
            with patch('esm_format.operator_registry.import_module') as mock_import:
                mock_module = MagicMock()
                mock_module.register_operator = MagicMock()
                mock_import.return_value = mock_module

                result = registry.discover_plugins(Path(temp_dir))

                assert result == 1
                assert mock_module.register_operator.called

    def test_discover_plugins_with_failing_plugin(self):
        """Test plugin discovery handles failing plugins gracefully."""
        registry = OperatorRegistry()

        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_path = Path(temp_dir) / "failing_plugin.py"
            plugin_path.write_text("# This will fail to import properly")

            with patch('esm_format.operator_registry.import_module') as mock_import:
                mock_import.side_effect = ImportError("Mock import failure")

                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    result = registry.discover_plugins(Path(temp_dir))

                    assert result == 0
                    assert len(w) == 1
                    assert "Failed to load plugin" in str(w[0].message)


class TestGlobalRegistryFunctions:
    """Test cases for global registry functions."""

    def test_get_registry(self):
        """Test getting global registry."""
        registry = get_registry()
        assert isinstance(registry, OperatorRegistry)

        # Should return same instance
        assert get_registry() is registry

    def test_register_operator_global(self):
        """Test registering operator with global function."""
        # Clear any existing registration
        registry = get_registry()
        if "global_test" in registry._operators:
            registry.unregister_operator("global_test")

        register_operator(
            name="global_test",
            operator_type=OperatorType.INTERPOLATION,
            operator_class=MockOperator,
            version="1.0"
        )

        # Check it was registered
        registry = get_registry()
        assert "global_test" in registry._operators
        assert registry._operators["global_test"] == MockOperator

    def test_create_operator_global(self):
        """Test creating operator with global function."""
        # Ensure operator is registered
        registry = get_registry()
        if "global_create" not in registry._operators:
            register_operator(
                name="global_create",
                operator_type=OperatorType.TRANSFORMATION,
                operator_class=MockOperator
            )

        config = Operator(
            name="global_create",
            type=OperatorType.TRANSFORMATION,
            parameters={"test": "value"},
            input_variables=["a"],
            output_variables=["b"]
        )

        instance = create_operator(config)
        assert isinstance(instance, MockOperator)
        assert instance.config == config

    def test_create_operator_by_name_global(self):
        """Test creating operator by name with global function."""
        # Ensure operator is registered
        registry = get_registry()
        if "global_by_name" not in registry._operators:
            register_operator(
                name="global_by_name",
                operator_type=OperatorType.FILTERING,
                operator_class=MockOperator
            )

        instance = create_operator_by_name(
            name="global_by_name",
            operator_type=OperatorType.FILTERING,
            parameters={"cutoff": 0.5}
        )

        assert isinstance(instance, MockOperator)
        assert instance.name == "global_by_name"
        assert instance.parameters == {"cutoff": 0.5}

    def test_list_operators_by_type_global(self):
        """Test listing operators by type with global function."""
        # Ensure some operators are registered
        registry = get_registry()
        if "global_list_test" not in registry._operators:
            register_operator(
                name="global_list_test",
                operator_type=OperatorType.INTEGRATION,
                operator_class=MockOperator
            )

        operators = list_operators_by_type(OperatorType.INTEGRATION)
        assert "global_list_test" in operators

    def test_has_operator_global(self):
        """Test checking operator existence with global function."""
        # Ensure operator is registered
        registry = get_registry()
        if "global_exists" not in registry._operators:
            register_operator(
                name="global_exists",
                operator_type=OperatorType.DIFFERENTIATION,
                operator_class=MockOperator,
                version="1.0"
            )

        assert has_operator("global_exists")
        assert has_operator("global_exists", "1.0")
        assert not has_operator("global_exists", "2.0")
        assert not has_operator("nonexistent_global")


class TestRegistryIntegration:
    """Integration tests for operator registry."""

    def test_operator_versioning(self):
        """Test multiple versions of the same operator."""
        registry = OperatorRegistry()

        # Register v1.0
        registry.register_operator(
            name="versioned_op",
            operator_type=OperatorType.INTERPOLATION,
            operator_class=MockOperator,
            version="1.0"
        )

        # Register v2.0 with different class
        registry.register_operator(
            name="versioned_op",
            operator_type=OperatorType.INTERPOLATION,
            operator_class=AlternativeMockOperator,
            version="2.0"
        )

        # Test getting different versions
        v1_class = registry.get_operator_class("versioned_op", "1.0")
        v2_class = registry.get_operator_class("versioned_op", "2.0")
        default_class = registry.get_operator_class("versioned_op")

        assert v1_class == MockOperator
        assert v2_class == AlternativeMockOperator
        # Default should be the original registration
        assert default_class == MockOperator

    def test_workflow_integration(self):
        """Test complete workflow from registration to instantiation."""
        registry = OperatorRegistry()

        # Register operator
        registry.register_operator(
            name="workflow_test",
            operator_type=OperatorType.TRANSFORMATION,
            operator_class=MockOperator,
            version="1.0"
        )

        # Verify it's listed
        ops = registry.list_operators_by_type(OperatorType.TRANSFORMATION)
        assert "workflow_test" in ops

        # Get info
        info = registry.get_operator_info("workflow_test")
        assert info['name'] == "workflow_test"
        assert info['type'] == OperatorType.TRANSFORMATION

        # Create instance
        instance = registry.create_operator_by_name(
            name="workflow_test",
            operator_type=OperatorType.TRANSFORMATION,
            parameters={"workflow": True},
            input_variables=["in1", "in2"],
            output_variables=["out"]
        )

        assert isinstance(instance, MockOperator)
        assert instance.parameters == {"workflow": True}
        assert instance.input_variables == ["in1", "in2"]
        assert instance.output_variables == ["out"]