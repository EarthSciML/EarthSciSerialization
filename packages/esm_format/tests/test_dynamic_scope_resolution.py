"""Tests for dynamic scope resolution with runtime contexts."""

import pytest
import uuid
from datetime import datetime
from contextlib import contextmanager

# Import the modules (adjust path as needed)
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from esm_format.dynamic_scope_resolution import (
    DynamicScopeResolver, RuntimeVariable, RuntimeContext, ContextSwitchResult
)
from esm_format.hierarchical_scope_resolution import ScopeInfo, VariableResolution
from esm_format.types import (
    EsmFile, Model, ReactionSystem, DataLoader, Operator, Metadata,
    ModelVariable, Species, Parameter, Reaction, DataLoaderType, OperatorType
)


class TestDynamicScopeResolver:
    """Tests for DynamicScopeResolver class."""

    def _create_test_esm_file(self):
        """Create a test ESM file for dynamic scope resolution testing."""
        metadata = Metadata(title="DynamicTestESM")

        # Create a simple model for testing
        atmosphere_model = {
            'name': 'AtmosphereModel',
            'variables': {
                'temperature': {'type': 'parameter', 'units': 'K', 'default': 298.15},
                'pressure': {'type': 'parameter', 'units': 'Pa', 'default': 101325.0},
                'humidity': {'type': 'state', 'units': 'percent', 'default': 50.0}
            },
            'subsystems': {
                'Chemistry': {
                    'variables': {
                        'O3': {'type': 'state', 'units': 'mol/mol', 'default': 40e-9},
                        'NO': {'type': 'state', 'units': 'mol/mol', 'default': 0.1e-9}
                    }
                }
            }
        }

        esm_file = EsmFile(
            version="0.1.0",
            metadata=metadata,
            models={'AtmosphereModel': atmosphere_model}
        )

        return esm_file

    def test_initialization(self):
        """Test DynamicScopeResolver initialization."""
        esm_file = self._create_test_esm_file()
        resolver = DynamicScopeResolver(esm_file)

        # Should have a default context
        assert resolver.current_context_id == "default"
        assert "default" in resolver.contexts
        assert len(resolver.contexts) == 1

        # Base resolver should be initialized
        assert resolver.base_resolver is not None
        assert len(resolver.base_resolver.scope_tree) > 0

    def test_create_runtime_context(self):
        """Test creating new runtime contexts."""
        esm_file = self._create_test_esm_file()
        resolver = DynamicScopeResolver(esm_file)

        # Create a new context
        context_id = resolver.create_runtime_context(
            name="Test Context",
            description="A test runtime context",
            metadata={"test": True}
        )

        assert context_id is not None
        assert context_id in resolver.contexts
        assert resolver.contexts[context_id].name == "Test Context"
        assert resolver.contexts[context_id].description == "A test runtime context"
        assert resolver.contexts[context_id].metadata["test"] is True

        # Context should start empty
        context = resolver.contexts[context_id]
        assert len(context.injected_variables) == 0
        assert len(context.variable_overrides) == 0
        assert len(context.dynamic_scopes) == 0

    def test_create_context_with_parent(self):
        """Test creating contexts with parent inheritance."""
        esm_file = self._create_test_esm_file()
        resolver = DynamicScopeResolver(esm_file)

        # Inject something into default context
        resolver.inject_parameter("AtmosphereModel", "injected_var", 42.0)

        # Create child context
        child_id = resolver.create_runtime_context(
            name="Child Context",
            parent_context_id="default"
        )

        # Child should inherit injections
        child_context = resolver.contexts[child_id]
        assert "AtmosphereModel" in child_context.injected_variables
        assert "injected_var" in child_context.injected_variables["AtmosphereModel"]
        assert child_context.injected_variables["AtmosphereModel"]["injected_var"].value == 42.0

    def test_context_switching(self):
        """Test switching between runtime contexts."""
        esm_file = self._create_test_esm_file()
        resolver = DynamicScopeResolver(esm_file)

        # Create two contexts
        ctx1_id = resolver.create_runtime_context("Context 1")
        ctx2_id = resolver.create_runtime_context("Context 2")

        # Should start in default
        assert resolver.current_context_id == "default"

        # Switch to context 1
        result = resolver.switch_context(ctx1_id)
        assert result.switch_successful is True
        assert result.to_context_id == ctx1_id
        assert resolver.current_context_id == ctx1_id

        # Switch to context 2
        result = resolver.switch_context(ctx2_id)
        assert result.switch_successful is True
        assert result.from_context_id == ctx1_id
        assert result.to_context_id == ctx2_id
        assert resolver.current_context_id == ctx2_id

    def test_context_switching_invalid(self):
        """Test error handling for invalid context switches."""
        esm_file = self._create_test_esm_file()
        resolver = DynamicScopeResolver(esm_file)

        # Try to switch to non-existent context
        result = resolver.switch_context("nonexistent")
        assert result.switch_successful is False
        assert "does not exist" in result.error_message

    def test_temporary_context(self):
        """Test temporary context manager."""
        esm_file = self._create_test_esm_file()
        resolver = DynamicScopeResolver(esm_file)

        # Create a test context
        temp_id = resolver.create_runtime_context("Temporary")
        resolver.inject_parameter("AtmosphereModel", "temp_var", "temp_value", context_id=temp_id)

        original_context = resolver.current_context_id

        with resolver.temporary_context(temp_id) as temp_context:
            # Should be in temporary context
            assert resolver.current_context_id == temp_id
            assert temp_context.name == "Temporary"

            # Should be able to resolve injected variable
            result = resolver.resolve_variable_dynamic("AtmosphereModel.temp_var")
            assert result.resolved_value == "temp_value"

        # Should be back to original context
        assert resolver.current_context_id == original_context

    def test_parameter_injection(self):
        """Test injecting parameters into scopes."""
        esm_file = self._create_test_esm_file()
        resolver = DynamicScopeResolver(esm_file)

        # Inject a parameter
        success = resolver.inject_parameter(
            "AtmosphereModel",
            "new_parameter",
            123.45,
            units="m/s",
            description="An injected parameter",
            injector_id="test_suite"
        )

        assert success is True

        # Should be able to resolve the injected parameter
        result = resolver.resolve_variable_dynamic("AtmosphereModel.new_parameter")
        assert result.resolution_type == "injected"
        assert result.resolved_value == 123.45
        assert result.variable_name == "new_parameter"

        # Check the runtime variable details
        context = resolver.contexts[resolver.current_context_id]
        runtime_var = context.injected_variables["AtmosphereModel"]["new_parameter"]
        assert runtime_var.units == "m/s"
        assert runtime_var.description == "An injected parameter"
        assert runtime_var.injector_id == "test_suite"

    def test_parameter_injection_nested_scope(self):
        """Test injecting parameters into nested scopes."""
        esm_file = self._create_test_esm_file()
        resolver = DynamicScopeResolver(esm_file)

        # Inject into nested scope
        success = resolver.inject_parameter(
            "AtmosphereModel.Chemistry",
            "reaction_rate",
            1.5e-12,
            units="cm^3/molec/s"
        )

        assert success is True

        # Should be able to resolve from nested scope
        result = resolver.resolve_variable_dynamic("AtmosphereModel.Chemistry.reaction_rate")
        assert result.resolution_type == "injected"
        assert result.resolved_value == 1.5e-12

    def test_variable_override(self):
        """Test overriding existing variables."""
        esm_file = self._create_test_esm_file()
        resolver = DynamicScopeResolver(esm_file)

        # Override existing temperature variable
        success = resolver.override_variable(
            "AtmosphereModel",
            "temperature",
            310.15  # New temperature
        )

        assert success is True

        # Should resolve to override value
        result = resolver.resolve_variable_dynamic("AtmosphereModel.temperature")
        assert result.resolution_type == "overridden"
        assert result.resolved_value == 310.15

    def test_variable_override_nonexistent(self):
        """Test error handling when overriding non-existent variables."""
        esm_file = self._create_test_esm_file()
        resolver = DynamicScopeResolver(esm_file)

        # Try to override non-existent variable
        success = resolver.override_variable(
            "AtmosphereModel",
            "nonexistent_var",
            42.0
        )

        assert success is False

    def test_dynamic_scope_creation(self):
        """Test creating dynamic scopes at runtime."""
        esm_file = self._create_test_esm_file()
        resolver = DynamicScopeResolver(esm_file)

        # Create dynamic scope
        success = resolver.create_dynamic_scope(
            "AtmosphereModel",
            "DynamicSubsystem",
            variables={
                "dynamic_var1": {"type": "parameter", "value": 1.0},
                "dynamic_var2": {"type": "state", "value": 2.0}
            },
            component_type="dynamic"
        )

        assert success is True

        # Should be able to resolve variables from dynamic scope
        result = resolver.resolve_variable_dynamic("AtmosphereModel.DynamicSubsystem.dynamic_var1")
        assert result.resolution_type == "dynamic"
        assert result.resolved_value["value"] == 1.0

    def test_dynamic_scope_creation_invalid_parent(self):
        """Test error handling for dynamic scopes with invalid parents."""
        esm_file = self._create_test_esm_file()
        resolver = DynamicScopeResolver(esm_file)

        # Try to create dynamic scope with non-existent parent
        success = resolver.create_dynamic_scope(
            "NonExistentModel",
            "DynamicScope",
            variables={"var": 1.0}
        )

        assert success is False

    def test_resolution_priority_order(self):
        """Test that resolution follows correct priority order: override > inject > dynamic > base."""
        esm_file = self._create_test_esm_file()
        resolver = DynamicScopeResolver(esm_file)

        # Base variable exists (temperature = 298.15)
        base_result = resolver.resolve_variable_dynamic("AtmosphereModel.temperature")
        assert base_result.resolved_value == {'type': 'parameter', 'units': 'K', 'default': 298.15}

        # Inject a variable with same name
        resolver.inject_parameter("AtmosphereModel", "temperature", 300.0)
        injected_result = resolver.resolve_variable_dynamic("AtmosphereModel.temperature")
        # Should still resolve to base since it exists there

        # Override the variable
        resolver.override_variable("AtmosphereModel", "temperature", 305.0)
        override_result = resolver.resolve_variable_dynamic("AtmosphereModel.temperature")
        assert override_result.resolution_type == "overridden"
        assert override_result.resolved_value == 305.0

    def test_context_isolation(self):
        """Test that contexts are properly isolated."""
        esm_file = self._create_test_esm_file()
        resolver = DynamicScopeResolver(esm_file)

        # Create two contexts
        ctx1_id = resolver.create_runtime_context("Context 1")
        ctx2_id = resolver.create_runtime_context("Context 2")

        # Inject different values in each context
        resolver.inject_parameter("AtmosphereModel", "test_var", "value1", context_id=ctx1_id)
        resolver.inject_parameter("AtmosphereModel", "test_var", "value2", context_id=ctx2_id)

        # Switch to context 1 and verify
        resolver.switch_context(ctx1_id)
        result = resolver.resolve_variable_dynamic("AtmosphereModel.test_var")
        assert result.resolved_value == "value1"

        # Switch to context 2 and verify
        resolver.switch_context(ctx2_id)
        result = resolver.resolve_variable_dynamic("AtmosphereModel.test_var")
        assert result.resolved_value == "value2"

    def test_clear_context_injections(self):
        """Test clearing injected parameters from contexts."""
        esm_file = self._create_test_esm_file()
        resolver = DynamicScopeResolver(esm_file)

        # Inject multiple parameters
        resolver.inject_parameter("AtmosphereModel", "var1", 1.0)
        resolver.inject_parameter("AtmosphereModel", "var2", 2.0)
        resolver.inject_parameter("AtmosphereModel.Chemistry", "var3", 3.0)

        # Should be able to resolve all
        assert resolver.resolve_variable_dynamic("AtmosphereModel.var1").resolved_value == 1.0
        assert resolver.resolve_variable_dynamic("AtmosphereModel.var2").resolved_value == 2.0
        assert resolver.resolve_variable_dynamic("AtmosphereModel.Chemistry.var3").resolved_value == 3.0

        # Clear specific scope
        cleared = resolver.clear_context_injections("AtmosphereModel")
        assert cleared == 2

        # Should no longer be able to resolve cleared variables
        with pytest.raises(ValueError):
            resolver.resolve_variable_dynamic("AtmosphereModel.var1")

        # But other scope should still work
        assert resolver.resolve_variable_dynamic("AtmosphereModel.Chemistry.var3").resolved_value == 3.0

        # Clear all
        cleared = resolver.clear_context_injections()
        assert cleared == 1

    def test_list_contexts(self):
        """Test listing available contexts."""
        esm_file = self._create_test_esm_file()
        resolver = DynamicScopeResolver(esm_file)

        # Should have default context
        contexts = resolver.list_contexts()
        assert len(contexts) == 1
        assert contexts[0][0] == "default"
        assert contexts[0][1] == "Default Context"
        assert contexts[0][2] is True  # is_current

        # Create additional contexts
        ctx1_id = resolver.create_runtime_context("Context 1")
        ctx2_id = resolver.create_runtime_context("Context 2")

        contexts = resolver.list_contexts()
        assert len(contexts) == 3

        # Switch context and check current status
        resolver.switch_context(ctx1_id)
        contexts = resolver.list_contexts()
        for ctx_id, name, is_current in contexts:
            if ctx_id == ctx1_id:
                assert is_current is True
            else:
                assert is_current is False

    def test_get_context_info(self):
        """Test getting context information."""
        esm_file = self._create_test_esm_file()
        resolver = DynamicScopeResolver(esm_file)

        # Get default context info
        context_info = resolver.get_context_info()
        assert context_info.context_id == "default"
        assert context_info.name == "Default Context"

        # Create context with metadata
        ctx_id = resolver.create_runtime_context(
            "Test Context",
            description="Test description",
            metadata={"key": "value"}
        )

        context_info = resolver.get_context_info(ctx_id)
        assert context_info.name == "Test Context"
        assert context_info.description == "Test description"
        assert context_info.metadata["key"] == "value"

    def test_runtime_statistics(self):
        """Test getting runtime statistics."""
        esm_file = self._create_test_esm_file()
        resolver = DynamicScopeResolver(esm_file)

        # Initial statistics
        stats = resolver.get_runtime_statistics()
        assert stats['total_contexts'] == 1
        assert stats['current_context_id'] == "default"
        assert stats['total_injections'] == 0
        assert stats['total_overrides'] == 0
        assert stats['total_dynamic_scopes'] == 0

        # Add some data and check statistics
        ctx_id = resolver.create_runtime_context("Test Context")
        resolver.inject_parameter("AtmosphereModel", "var1", 1.0)
        resolver.inject_parameter("AtmosphereModel", "var2", 2.0)
        resolver.override_variable("AtmosphereModel", "temperature", 310.0)
        resolver.create_dynamic_scope("AtmosphereModel", "DynamicScope")

        stats = resolver.get_runtime_statistics()
        assert stats['total_contexts'] == 2
        assert stats['total_injections'] == 2
        assert stats['total_overrides'] == 1
        assert stats['total_dynamic_scopes'] == 1

    def test_fallback_to_base_resolution(self):
        """Test that dynamic resolver falls back to base resolution for regular variables."""
        esm_file = self._create_test_esm_file()
        resolver = DynamicScopeResolver(esm_file)

        # Should be able to resolve base variables normally
        result = resolver.resolve_variable_dynamic("AtmosphereModel.humidity")
        assert result.resolution_type in ["direct", "inherited"]
        assert result.resolved_value == {'type': 'state', 'units': 'percent', 'default': 50.0}

        # Should be able to resolve inherited variables
        result = resolver.resolve_variable_dynamic("AtmosphereModel.Chemistry.O3")
        assert result.resolved_value == {'type': 'state', 'units': 'mol/mol', 'default': 40e-9}

    def test_enhanced_error_messages(self):
        """Test that error messages include context information."""
        esm_file = self._create_test_esm_file()
        resolver = DynamicScopeResolver(esm_file)

        ctx_id = resolver.create_runtime_context("Error Test Context")
        resolver.switch_context(ctx_id)

        # Inject some variables for context
        resolver.inject_parameter("AtmosphereModel", "injected_var", 1.0)

        try:
            resolver.resolve_variable_dynamic("AtmosphereModel.nonexistent_var")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            error_msg = str(e)
            assert "context:" in error_msg
            assert ctx_id in error_msg
            assert "Injected variables:" in error_msg
            assert "injected_var" in error_msg

    def test_variable_change_listeners(self):
        """Test variable change listener functionality."""
        esm_file = self._create_test_esm_file()
        resolver = DynamicScopeResolver(esm_file)

        # Track changes
        changes = []

        def change_listener(change_type, scope_path, variable_name, new_value, context_id):
            changes.append((change_type, scope_path, variable_name, new_value, context_id))

        # Add listener
        resolver.add_variable_change_listener(change_listener)

        # Make changes
        resolver.inject_parameter("AtmosphereModel", "test_var", 42.0)
        resolver.override_variable("AtmosphereModel", "temperature", 310.0)

        # Check that changes were recorded
        assert len(changes) == 2
        assert changes[0][0] == "parameter_injected"
        assert changes[0][1] == "AtmosphereModel"
        assert changes[0][2] == "test_var"
        assert changes[0][3] == 42.0

        assert changes[1][0] == "variable_overridden"
        assert changes[1][1] == "AtmosphereModel"
        assert changes[1][2] == "temperature"
        assert changes[1][3] == 310.0

        # Remove listener
        resolver.remove_variable_change_listener(change_listener)

        # Make another change - should not be recorded
        resolver.inject_parameter("AtmosphereModel", "test_var2", 24.0)
        assert len(changes) == 2


class TestComplexDynamicScenarios:
    """Tests for complex dynamic scope scenarios."""

    def _create_complex_esm_file(self):
        """Create a more complex ESM file for advanced testing."""
        metadata = Metadata(title="ComplexDynamicESM")

        atmosphere_model = {
            'name': 'AtmosphereModel',
            'variables': {
                'temperature': {'type': 'parameter', 'units': 'K', 'default': 298.15},
                'pressure': {'type': 'parameter', 'units': 'Pa', 'default': 101325.0}
            },
            'subsystems': {
                'Chemistry': {
                    'variables': {
                        'temperature': {'type': 'state', 'units': 'K', 'default': 299.15},  # Shadows parent
                        'O3': {'type': 'state', 'units': 'mol/mol', 'default': 40e-9}
                    },
                    'subsystems': {
                        'FastReactions': {
                            'variables': {
                                'k1': {'type': 'parameter', 'units': '1/s', 'default': 1e-5}
                            }
                        }
                    }
                }
            }
        }

        esm_file = EsmFile(
            version="0.1.0",
            metadata=metadata,
            models={'AtmosphereModel': atmosphere_model}
        )

        return esm_file

    def test_dynamic_with_shadowing(self):
        """Test dynamic resolution with variable shadowing."""
        esm_file = self._create_complex_esm_file()
        resolver = DynamicScopeResolver(esm_file)

        # Base temperature in Chemistry should shadow AtmosphereModel
        result = resolver.resolve_variable_dynamic("AtmosphereModel.Chemistry.temperature")
        assert result.resolved_value == {'type': 'state', 'units': 'K', 'default': 299.15}

        # Override the shadowed variable
        resolver.override_variable("AtmosphereModel.Chemistry", "temperature", 305.0)
        result = resolver.resolve_variable_dynamic("AtmosphereModel.Chemistry.temperature")
        assert result.resolution_type == "overridden"
        assert result.resolved_value == 305.0

        # Injecting at parent level shouldn't affect shadowed resolution
        resolver.inject_parameter("AtmosphereModel", "temperature", 320.0)
        result = resolver.resolve_variable_dynamic("AtmosphereModel.Chemistry.temperature")
        assert result.resolution_type == "overridden"  # Still overridden, not injected
        assert result.resolved_value == 305.0

    def test_deep_dynamic_scopes(self):
        """Test creating dynamic scopes at deep nesting levels."""
        esm_file = self._create_complex_esm_file()
        resolver = DynamicScopeResolver(esm_file)

        # Create dynamic scope nested deeply
        success = resolver.create_dynamic_scope(
            "AtmosphereModel.Chemistry.FastReactions",
            "DynamicLevel",
            variables={"deep_var": {"type": "parameter", "value": "deep_value"}}
        )

        assert success is True

        # Should be able to resolve from deep dynamic scope
        result = resolver.resolve_variable_dynamic("AtmosphereModel.Chemistry.FastReactions.DynamicLevel.deep_var")
        assert result.resolution_type == "dynamic"
        assert result.resolved_value["value"] == "deep_value"

        # Deep scope should inherit from parent scopes
        # (This tests that the parent linkage is correct)
        context = resolver.contexts[resolver.current_context_id]
        deep_scope = context.dynamic_scopes["AtmosphereModel.Chemistry.FastReactions.DynamicLevel"]
        assert deep_scope.parent is not None
        assert deep_scope.parent.name == "FastReactions"

    def test_context_inheritance_with_overrides(self):
        """Test that child contexts properly inherit and can override parent context state."""
        esm_file = self._create_complex_esm_file()
        resolver = DynamicScopeResolver(esm_file)

        # Set up parent context
        parent_id = resolver.create_runtime_context("Parent Context")
        resolver.switch_context(parent_id)
        resolver.inject_parameter("AtmosphereModel", "parent_var", "parent_value")
        resolver.override_variable("AtmosphereModel", "temperature", 300.0)

        # Create child context
        child_id = resolver.create_runtime_context("Child Context", parent_context_id=parent_id)
        resolver.switch_context(child_id)

        # Should inherit parent injections and overrides
        result = resolver.resolve_variable_dynamic("AtmosphereModel.parent_var")
        assert result.resolved_value == "parent_value"

        result = resolver.resolve_variable_dynamic("AtmosphereModel.temperature")
        assert result.resolved_value == 300.0

        # Child can override parent state
        resolver.override_variable("AtmosphereModel", "temperature", 305.0)
        result = resolver.resolve_variable_dynamic("AtmosphereModel.temperature")
        assert result.resolved_value == 305.0

        # Parent context should be unaffected
        resolver.switch_context(parent_id)
        result = resolver.resolve_variable_dynamic("AtmosphereModel.temperature")
        assert result.resolved_value == 300.0  # Parent value unchanged

    def test_multiple_dynamic_scopes_same_level(self):
        """Test creating multiple dynamic scopes at the same nesting level."""
        esm_file = self._create_complex_esm_file()
        resolver = DynamicScopeResolver(esm_file)

        # Create multiple sibling dynamic scopes
        success1 = resolver.create_dynamic_scope(
            "AtmosphereModel.Chemistry",
            "DynamicA",
            variables={"varA": {"value": "A"}}
        )
        success2 = resolver.create_dynamic_scope(
            "AtmosphereModel.Chemistry",
            "DynamicB",
            variables={"varB": {"value": "B"}}
        )

        assert success1 is True
        assert success2 is True

        # Should be able to resolve from both
        resultA = resolver.resolve_variable_dynamic("AtmosphereModel.Chemistry.DynamicA.varA")
        assert resultA.resolved_value["value"] == "A"

        resultB = resolver.resolve_variable_dynamic("AtmosphereModel.Chemistry.DynamicB.varB")
        assert resultB.resolved_value["value"] == "B"

        # Dynamic scopes should be isolated from each other
        with pytest.raises(ValueError):
            resolver.resolve_variable_dynamic("AtmosphereModel.Chemistry.DynamicA.varB")

        with pytest.raises(ValueError):
            resolver.resolve_variable_dynamic("AtmosphereModel.Chemistry.DynamicB.varA")