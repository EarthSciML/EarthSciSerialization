"""Tests for enhanced hierarchical scope resolution algorithm."""

import pytest
from esm_format.hierarchical_scope_resolution import (
    HierarchicalScopeResolver, ScopeInfo, VariableResolution,
    create_enhanced_scoped_reference
)
from esm_format.types import (
    EsmFile, Model, ReactionSystem, DataLoader, Operator, Metadata,
    ModelVariable, Species, Parameter, Reaction, DataLoaderType, OperatorType
)


class TestHierarchicalScopeResolver:
    """Tests for HierarchicalScopeResolver class."""

    def _create_complex_esm_file(self):
        """Create a complex ESM file with variable shadowing and inheritance scenarios."""
        metadata = Metadata(title="ComplexESM")

        # Create a model with nested subsystems and variable shadowing
        atmosphere_model = {
            'name': 'AtmosphereModel',
            'variables': {
                'temperature': {'type': 'parameter', 'units': 'K', 'default': 298.15, 'description': 'Global temperature'},
                'pressure': {'type': 'parameter', 'units': 'Pa', 'default': 101325.0, 'description': 'Global pressure'},
                'global_flag': {'type': 'parameter', 'units': 'dimensionless', 'default': 1}
            },
            'subsystems': {
                'Chemistry': {
                    'variables': {
                        'temperature': {'type': 'state', 'units': 'K', 'default': 299.15, 'description': 'Chemistry temperature'},  # Shadows parent
                        'O3': {'type': 'state', 'units': 'mol/mol', 'default': 40e-9},
                        'NO': {'type': 'state', 'units': 'mol/mol', 'default': 0.1e-9},
                        'chemistry_flag': {'type': 'parameter', 'units': 'dimensionless', 'default': 2}
                        # pressure not defined here - should inherit from parent
                    },
                    'subsystems': {
                        'FastReactions': {
                            'variables': {
                                'temperature': {'type': 'parameter', 'units': 'K', 'default': 300.15, 'description': 'Fast reactions temperature'},  # Shadows both parent and grandparent
                                'k1': {'type': 'parameter', 'units': '1/s', 'default': 1e-5},
                                'k2': {'type': 'parameter', 'units': 'cm^3/molec/s', 'default': 1.8e-12}
                                # O3, NO, pressure, chemistry_flag, global_flag should all be inherited
                            }
                        },
                        'SlowReactions': {
                            'variables': {
                                'k_slow': {'type': 'parameter', 'units': '1/s', 'default': 1e-8}
                                # All variables should be inherited
                            }
                        }
                    }
                },
                'Transport': {
                    'variables': {
                        'wind_speed': {'type': 'parameter', 'units': 'm/s', 'default': 5.0},
                        'pressure': {'type': 'state', 'units': 'Pa', 'default': 100000.0, 'description': 'Transport pressure'}  # Shadows parent
                        # temperature, global_flag should be inherited
                    }
                }
            }
        }

        # Create ocean model with different hierarchy
        ocean_model = {
            'name': 'OceanModel',
            'variables': {
                'temperature': {'type': 'state', 'units': 'K', 'default': 288.15, 'description': 'Ocean temperature'},
                'salinity': {'type': 'state', 'units': 'psu', 'default': 35.0}
            },
            'subsystems': {
                'Biogeochemistry': {
                    'variables': {
                        'DIC': {'type': 'state', 'units': 'mol/m^3', 'default': 2100.0},
                        'alkalinity': {'type': 'state', 'units': 'mol/m^3', 'default': 2300.0}
                        # temperature, salinity should be inherited
                    }
                }
            }
        }

        esm_file = EsmFile(
            version="0.1.0",
            metadata=metadata,
            models={
                'AtmosphereModel': atmosphere_model,
                'OceanModel': ocean_model
            }
        )

        return esm_file

    def test_build_scope_tree(self):
        """Test building the complete scope tree."""
        esm_file = self._create_complex_esm_file()
        resolver = HierarchicalScopeResolver(esm_file)

        # Check that all expected scopes are created
        expected_scopes = [
            'AtmosphereModel',
            'AtmosphereModel.Chemistry',
            'AtmosphereModel.Chemistry.FastReactions',
            'AtmosphereModel.Chemistry.SlowReactions',
            'AtmosphereModel.Transport',
            'OceanModel',
            'OceanModel.Biogeochemistry'
        ]

        for scope in expected_scopes:
            assert scope in resolver.scope_tree, f"Expected scope '{scope}' not found"

        # Check parent-child relationships
        chem_scope = resolver.scope_tree['AtmosphereModel.Chemistry']
        assert chem_scope.parent is not None
        assert chem_scope.parent.name == 'AtmosphereModel'

        fast_reactions_scope = resolver.scope_tree['AtmosphereModel.Chemistry.FastReactions']
        assert fast_reactions_scope.parent.name == 'Chemistry'
        assert fast_reactions_scope.parent.parent.name == 'AtmosphereModel'

    def test_direct_variable_resolution(self):
        """Test resolving variables directly in their defined scope."""
        esm_file = self._create_complex_esm_file()
        resolver = HierarchicalScopeResolver(esm_file)

        # Resolve variable that exists directly in the target scope
        result = resolver.resolve_variable("AtmosphereModel.Chemistry.O3")

        assert result.variable_name == "O3"
        assert result.resolution_type == "direct"
        assert result.resolved_scope.name == "Chemistry"
        assert result.resolved_value['default'] == 40e-9
        assert len(result.shadow_chain) == 0

    def test_inherited_variable_resolution(self):
        """Test resolving variables through scope inheritance."""
        esm_file = self._create_complex_esm_file()
        resolver = HierarchicalScopeResolver(esm_file)

        # Resolve variable that doesn't exist in Chemistry but exists in AtmosphereModel
        result = resolver.resolve_variable("AtmosphereModel.Chemistry.global_flag")

        assert result.variable_name == "global_flag"
        assert result.resolution_type == "inherited"
        assert result.resolved_scope.name == "AtmosphereModel"
        assert result.resolved_value['default'] == 1

        # Deep inheritance - resolve global_flag from FastReactions
        result = resolver.resolve_variable("AtmosphereModel.Chemistry.FastReactions.global_flag")

        assert result.variable_name == "global_flag"
        assert result.resolution_type == "inherited"
        assert result.resolved_scope.name == "AtmosphereModel"
        assert len(result.available_scopes) == 3  # FastReactions, Chemistry, AtmosphereModel

    def test_variable_shadowing(self):
        """Test variable shadowing behavior."""
        esm_file = self._create_complex_esm_file()
        resolver = HierarchicalScopeResolver(esm_file)

        # Test temperature shadowing - FastReactions shadows both Chemistry and AtmosphereModel
        result = resolver.resolve_with_shadowing_info("AtmosphereModel.Chemistry.FastReactions.temperature")

        assert result.variable_name == "temperature"
        assert result.resolution_type == "direct"
        assert result.resolved_scope.name == "FastReactions"
        assert result.resolved_value['default'] == 300.15  # FastReactions value
        assert len(result.shadow_chain) == 2  # Shadows Chemistry and AtmosphereModel

        # Verify shadowed values
        shadows = resolver.find_variable_shadows("temperature", ["AtmosphereModel", "Chemistry", "FastReactions"])
        assert len(shadows) == 3
        assert shadows[0][1]['default'] == 300.15  # FastReactions
        assert shadows[1][1]['default'] == 299.15  # Chemistry
        assert shadows[2][1]['default'] == 298.15  # AtmosphereModel

    def test_pressure_inheritance_vs_shadowing(self):
        """Test complex scenario with both inheritance and shadowing."""
        esm_file = self._create_complex_esm_file()
        resolver = HierarchicalScopeResolver(esm_file)

        # Chemistry inherits pressure from AtmosphereModel
        result = resolver.resolve_variable("AtmosphereModel.Chemistry.pressure")
        assert result.resolution_type == "inherited"
        assert result.resolved_value['default'] == 101325.0  # AtmosphereModel value

        # Transport shadows pressure
        result = resolver.resolve_variable("AtmosphereModel.Transport.pressure")
        assert result.resolution_type == "direct"
        assert result.resolved_value['default'] == 100000.0  # Transport value

        # FastReactions inherits from Chemistry, which inherits from AtmosphereModel
        result = resolver.resolve_variable("AtmosphereModel.Chemistry.FastReactions.pressure")
        assert result.resolution_type == "inherited"
        assert result.resolved_scope.name == "AtmosphereModel"  # Skips Chemistry (no pressure there)
        assert result.resolved_value['default'] == 101325.0

    def test_cross_subsystem_isolation(self):
        """Test that subsystems don't access each other's variables."""
        esm_file = self._create_complex_esm_file()
        resolver = HierarchicalScopeResolver(esm_file)

        # Transport should not be able to access Chemistry's O3
        with pytest.raises(ValueError, match="Variable 'O3' not found"):
            resolver.resolve_variable("AtmosphereModel.Transport.O3")

        # FastReactions should not access SlowReactions' k_slow
        with pytest.raises(ValueError, match="Variable 'k_slow' not found"):
            resolver.resolve_variable("AtmosphereModel.Chemistry.FastReactions.k_slow")

    def test_variable_not_found_error(self):
        """Test proper error handling when variables are not found."""
        esm_file = self._create_complex_esm_file()
        resolver = HierarchicalScopeResolver(esm_file)

        with pytest.raises(ValueError, match="Variable 'nonexistent' not found"):
            resolver.resolve_variable("AtmosphereModel.Chemistry.nonexistent")

        # Error should include available variables
        try:
            resolver.resolve_variable("AtmosphereModel.Chemistry.nonexistent")
        except ValueError as e:
            error_msg = str(e)
            assert "Available variables:" in error_msg
            assert "O3" in error_msg
            assert "NO" in error_msg

    def test_invalid_scope_error(self):
        """Test error handling for invalid scopes."""
        esm_file = self._create_complex_esm_file()
        resolver = HierarchicalScopeResolver(esm_file)

        with pytest.raises(ValueError, match="Scope 'NonExistentModel.SubSystem' not found"):
            resolver.resolve_variable("NonExistentModel.SubSystem.variable")

    def test_invalid_reference_format_error(self):
        """Test error handling for invalid reference formats."""
        esm_file = self._create_complex_esm_file()
        resolver = HierarchicalScopeResolver(esm_file)

        with pytest.raises(ValueError, match="Invalid scoped reference 'single'"):
            resolver.resolve_variable("single")

    def test_multiple_model_isolation(self):
        """Test that models are properly isolated from each other."""
        esm_file = self._create_complex_esm_file()
        resolver = HierarchicalScopeResolver(esm_file)

        # AtmosphereModel should not access OceanModel variables
        with pytest.raises(ValueError, match="Variable 'salinity' not found"):
            resolver.resolve_variable("AtmosphereModel.Chemistry.salinity")

        # OceanModel should not access AtmosphereModel variables
        with pytest.raises(ValueError, match="Variable 'O3' not found"):
            resolver.resolve_variable("OceanModel.Biogeochemistry.O3")

    def test_validate_scope_hierarchy(self):
        """Test validation of the scope hierarchy."""
        esm_file = self._create_complex_esm_file()
        resolver = HierarchicalScopeResolver(esm_file)

        is_valid, errors = resolver.validate_scope_hierarchy()
        assert is_valid
        assert len(errors) == 0

    def test_get_scope_statistics(self):
        """Test getting statistics about the scope hierarchy."""
        esm_file = self._create_complex_esm_file()
        resolver = HierarchicalScopeResolver(esm_file)

        stats = resolver.get_scope_statistics()

        assert stats['total_scopes'] == 7  # 2 root + 5 subsystems
        assert stats['max_depth'] == 3  # AtmosphereModel.Chemistry.FastReactions
        assert stats['scopes_by_type']['model'] == 7  # All are model scopes
        assert stats['total_variables'] > 0

        # Check specific scope variable counts
        assert 'AtmosphereModel' in stats['variables_by_scope']
        assert stats['variables_by_scope']['AtmosphereModel'] == 3  # temperature, pressure, global_flag

    def test_create_enhanced_scoped_reference(self):
        """Test creating enhanced ScopedReference objects."""
        esm_file = self._create_complex_esm_file()
        resolver = HierarchicalScopeResolver(esm_file)

        scoped_ref = create_enhanced_scoped_reference(resolver, "AtmosphereModel.Chemistry.temperature")

        assert scoped_ref.original_reference == "AtmosphereModel.Chemistry.temperature"
        assert scoped_ref.path == ["AtmosphereModel", "Chemistry"]
        assert scoped_ref.target == "temperature"
        assert scoped_ref.resolved_variable['default'] == 299.15  # Chemistry's shadowed value
        assert scoped_ref.component_type == "model"


class TestComplexShadowingScenarios:
    """Tests for complex variable shadowing scenarios."""

    def _create_deep_hierarchy_esm(self):
        """Create ESM with very deep hierarchy for complex testing."""
        metadata = Metadata(title="DeepHierarchyESM")

        model = {
            'name': 'DeepModel',
            'variables': {
                'shared_var': {'type': 'parameter', 'value': 'level0', 'description': 'Root level'}
            },
            'subsystems': {
                'Level1': {
                    'variables': {
                        'shared_var': {'type': 'parameter', 'value': 'level1', 'description': 'Level 1 override'},
                        'level1_var': {'type': 'parameter', 'value': 'unique_l1'}
                    },
                    'subsystems': {
                        'Level2A': {
                            'variables': {
                                'level2a_var': {'type': 'parameter', 'value': 'unique_l2a'}
                                # Inherits shared_var from Level1, level1_var from Level1
                            },
                            'subsystems': {
                                'Level3': {
                                    'variables': {
                                        'shared_var': {'type': 'parameter', 'value': 'level3', 'description': 'Level 3 override'},
                                        'level3_var': {'type': 'parameter', 'value': 'unique_l3'}
                                        # Should inherit level1_var, level2a_var
                                    }
                                }
                            }
                        },
                        'Level2B': {
                            'variables': {
                                'level2b_var': {'type': 'parameter', 'value': 'unique_l2b'}
                                # Inherits shared_var from Level1, level1_var from Level1
                            }
                        }
                    }
                }
            }
        }

        return EsmFile(
            version="0.1.0",
            metadata=metadata,
            models={'DeepModel': model}
        )

    def test_deep_shadowing_chain(self):
        """Test shadowing across multiple levels."""
        esm_file = self._create_deep_hierarchy_esm()
        resolver = HierarchicalScopeResolver(esm_file)

        # Test Level3 accessing shared_var - should get Level3's version
        result = resolver.resolve_with_shadowing_info("DeepModel.Level1.Level2A.Level3.shared_var")

        assert result.resolution_type == "direct"
        assert result.resolved_value['value'] == 'level3'
        assert len(result.shadow_chain) == 2  # Shadows Level1 and DeepModel

        # Verify the shadow chain
        shadows = result.shadow_chain
        assert shadows[0].name == "Level1"  # First shadowed
        assert shadows[1].name == "DeepModel"  # Second shadowed

    def test_inheritance_across_missing_levels(self):
        """Test inheriting variables that skip intermediate levels."""
        esm_file = self._create_deep_hierarchy_esm()
        resolver = HierarchicalScopeResolver(esm_file)

        # Level2A should inherit shared_var from Level1 (skips its own level)
        result = resolver.resolve_variable("DeepModel.Level1.Level2A.shared_var")

        assert result.resolution_type == "inherited"
        assert result.resolved_scope.name == "Level1"
        assert result.resolved_value['value'] == 'level1'

        # Level3 should inherit level1_var from Level1 (skips Level2A)
        result = resolver.resolve_variable("DeepModel.Level1.Level2A.Level3.level1_var")

        assert result.resolution_type == "inherited"
        assert result.resolved_scope.name == "Level1"
        assert result.resolved_value['value'] == 'unique_l1'

        # Level3 should inherit level2a_var from Level2A
        result = resolver.resolve_variable("DeepModel.Level1.Level2A.Level3.level2a_var")

        assert result.resolution_type == "inherited"
        assert result.resolved_scope.name == "Level2A"
        assert result.resolved_value['value'] == 'unique_l2a'

    def test_sibling_isolation_deep_hierarchy(self):
        """Test that sibling subsystems cannot access each other's variables."""
        esm_file = self._create_deep_hierarchy_esm()
        resolver = HierarchicalScopeResolver(esm_file)

        # Level2B should not access Level2A's variables
        with pytest.raises(ValueError, match="Variable 'level2a_var' not found"):
            resolver.resolve_variable("DeepModel.Level1.Level2B.level2a_var")

        # Level2A should not access Level2B's variables
        with pytest.raises(ValueError, match="Variable 'level2b_var' not found"):
            resolver.resolve_variable("DeepModel.Level1.Level2A.level2b_var")

    def test_find_all_shadows(self):
        """Test finding all shadow instances of a variable."""
        esm_file = self._create_deep_hierarchy_esm()
        resolver = HierarchicalScopeResolver(esm_file)

        shadows = resolver.find_variable_shadows("shared_var", ["DeepModel", "Level1", "Level2A", "Level3"])

        assert len(shadows) == 3  # Level3, Level1, DeepModel
        assert shadows[0][0].name == "Level3"
        assert shadows[0][1]['value'] == 'level3'
        assert shadows[1][0].name == "Level1"
        assert shadows[1][1]['value'] == 'level1'
        assert shadows[2][0].name == "DeepModel"
        assert shadows[2][1]['value'] == 'level0'