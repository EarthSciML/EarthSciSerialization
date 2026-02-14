"""Tests for scoped reference resolution algorithm."""

import pytest
from esm_format.coupling_graph import (
    ScopedReference, ScopedReferenceResolver, resolve_coupling_dependencies,
    build_execution_order_from_dependencies
)
from esm_format.types import (
    EsmFile, Model, ReactionSystem, DataLoader, Operator, Metadata,
    ModelVariable, Species, Parameter, Reaction, DataLoaderType, OperatorType
)


class TestScopedReferenceResolver:
    """Tests for ScopedReferenceResolver class."""

    def _create_test_esm_file(self):
        """Create a test ESM file with hierarchical components."""
        metadata = Metadata(title="TestESM")

        # Create a model with nested subsystems
        atmosphere_model = {
            'name': 'AtmosphereModel',
            'variables': {
                'pressure': {'type': 'parameter', 'units': 'Pa', 'default': 101325.0},
                'temperature': {'type': 'parameter', 'units': 'K', 'default': 298.15}
            },
            'subsystems': {
                'Chemistry': {
                    'variables': {
                        'O3': {'type': 'state', 'units': 'mol/mol', 'default': 40e-9},
                        'NO': {'type': 'state', 'units': 'mol/mol', 'default': 0.1e-9},
                        'temperature': {'type': 'parameter', 'units': 'K', 'default': 298.15}
                    },
                    'subsystems': {
                        'FastReactions': {
                            'variables': {
                                'k1': {'type': 'parameter', 'units': '1/s', 'default': 1e-5},
                                'k2': {'type': 'parameter', 'units': 'cm^3/molec/s', 'default': 1.8e-12}
                            }
                        }
                    }
                },
                'Transport': {
                    'variables': {
                        'wind_speed': {'type': 'parameter', 'units': 'm/s', 'default': 5.0}
                    }
                }
            }
        }

        # Create a data loader with subsystem
        met_data_loader = {
            'type': 'gridded_data',
            'loader_id': 'WRF',
            'provides': {
                'temperature': {'units': 'K'},
                'pressure': {'units': 'Pa'}
            },
            'subsystems': {
                'QualityControl': {
                    'variables': {
                        'data_quality_flag': {'type': 'parameter', 'units': 'dimensionless', 'default': 1.0}
                    }
                }
            }
        }

        # Create an operator with subsystem
        biogenic_operator = {
            'operator_id': 'MEGAN',
            'needed_vars': ['temperature'],
            'modifies': ['emission_rate_isoprene'],
            'subsystems': {
                'TemperatureDependence': {
                    'variables': {
                        'beta': {'type': 'parameter', 'units': '1/K', 'default': 0.09}
                    }
                }
            }
        }

        esm_file = EsmFile(
            version="0.1.0",
            metadata=metadata,
            models={'AtmosphereModel': atmosphere_model},
            data_loaders={'MeteorologicalData': met_data_loader},
            operators={'BiogenicEmissions': biogenic_operator}
        )

        return esm_file

    def test_resolve_two_level_model_reference(self):
        """Test resolving two-level model reference: AtmosphereModel.Chemistry"""
        esm_file = self._create_test_esm_file()
        resolver = ScopedReferenceResolver(esm_file)

        result = resolver.resolve_reference("AtmosphereModel.Chemistry")

        assert result.original_reference == "AtmosphereModel.Chemistry"
        assert result.path == ["AtmosphereModel", "Chemistry"]
        assert result.target == ""  # No specific variable targeted
        assert result.component_type == "model"
        assert result.resolved_variable is None

    def test_resolve_three_level_variable_reference(self):
        """Test resolving three-level variable reference: AtmosphereModel.Chemistry.temperature"""
        esm_file = self._create_test_esm_file()
        resolver = ScopedReferenceResolver(esm_file)

        result = resolver.resolve_reference("AtmosphereModel.Chemistry.temperature")

        assert result.original_reference == "AtmosphereModel.Chemistry.temperature"
        assert result.path == ["AtmosphereModel", "Chemistry"]
        assert result.target == "temperature"
        assert result.component_type == "model"
        assert result.resolved_variable is not None
        assert result.resolved_variable['type'] == 'parameter'
        assert result.resolved_variable['units'] == 'K'

    def test_resolve_four_level_deep_nesting(self):
        """Test resolving four-level deep nesting: AtmosphereModel.Chemistry.FastReactions.k1"""
        esm_file = self._create_test_esm_file()
        resolver = ScopedReferenceResolver(esm_file)

        result = resolver.resolve_reference("AtmosphereModel.Chemistry.FastReactions.k1")

        assert result.original_reference == "AtmosphereModel.Chemistry.FastReactions.k1"
        assert result.path == ["AtmosphereModel", "Chemistry", "FastReactions"]
        assert result.target == "k1"
        assert result.component_type == "model"
        assert result.resolved_variable is not None
        assert result.resolved_variable['type'] == 'parameter'
        assert result.resolved_variable['units'] == '1/s'

    def test_resolve_data_loader_reference(self):
        """Test resolving data loader reference: MeteorologicalData.QualityControl.data_quality_flag"""
        esm_file = self._create_test_esm_file()
        resolver = ScopedReferenceResolver(esm_file)

        result = resolver.resolve_reference("MeteorologicalData.QualityControl.data_quality_flag")

        assert result.original_reference == "MeteorologicalData.QualityControl.data_quality_flag"
        assert result.path == ["MeteorologicalData", "QualityControl"]
        assert result.target == "data_quality_flag"
        assert result.component_type == "data_loader"
        assert result.resolved_variable is not None
        assert result.resolved_variable['type'] == 'parameter'

    def test_resolve_operator_reference(self):
        """Test resolving operator reference: BiogenicEmissions.TemperatureDependence.beta"""
        esm_file = self._create_test_esm_file()
        resolver = ScopedReferenceResolver(esm_file)

        result = resolver.resolve_reference("BiogenicEmissions.TemperatureDependence.beta")

        assert result.original_reference == "BiogenicEmissions.TemperatureDependence.beta"
        assert result.path == ["BiogenicEmissions", "TemperatureDependence"]
        assert result.target == "beta"
        assert result.component_type == "operator"
        assert result.resolved_variable is not None
        assert result.resolved_variable['type'] == 'parameter'
        assert result.resolved_variable['units'] == '1/K'

    def test_resolve_invalid_top_level_component_error(self):
        """Test that invalid top-level component raises error."""
        esm_file = self._create_test_esm_file()
        resolver = ScopedReferenceResolver(esm_file)

        with pytest.raises(ValueError, match="Top-level component 'NonExistentModel' not found"):
            resolver.resolve_reference("NonExistentModel.Chemistry.O3")

    def test_resolve_invalid_subsystem_error(self):
        """Test that invalid subsystem raises error."""
        esm_file = self._create_test_esm_file()
        resolver = ScopedReferenceResolver(esm_file)

        with pytest.raises(ValueError, match="Subsystem 'NonExistentSub' not found"):
            resolver.resolve_reference("AtmosphereModel.NonExistentSub.O3")

    def test_resolve_invalid_variable_error(self):
        """Test that invalid variable raises error."""
        esm_file = self._create_test_esm_file()
        resolver = ScopedReferenceResolver(esm_file)

        with pytest.raises(ValueError, match="Target 'NonExistentVar' not found"):
            resolver.resolve_reference("AtmosphereModel.Chemistry.NonExistentVar")

    def test_resolve_invalid_reference_format_error(self):
        """Test that invalid reference format raises error."""
        esm_file = self._create_test_esm_file()
        resolver = ScopedReferenceResolver(esm_file)

        with pytest.raises(ValueError, match="Invalid scoped reference 'single': must contain at least one dot"):
            resolver.resolve_reference("single")

    def test_validate_reference_valid(self):
        """Test validating a valid reference."""
        esm_file = self._create_test_esm_file()
        resolver = ScopedReferenceResolver(esm_file)

        is_valid, errors = resolver.validate_reference("AtmosphereModel.Chemistry.temperature")

        assert is_valid
        assert len(errors) == 0

    def test_validate_reference_invalid(self):
        """Test validating an invalid reference."""
        esm_file = self._create_test_esm_file()
        resolver = ScopedReferenceResolver(esm_file)

        is_valid, errors = resolver.validate_reference("NonExistent.Component.var")

        assert not is_valid
        assert len(errors) == 1
        assert "Top-level component 'NonExistent' not found" in errors[0]


class TestDependencyResolution:
    """Tests for coupling dependency resolution functions."""

    def test_resolve_coupling_dependencies_empty(self):
        """Test resolving dependencies with no couplings."""
        metadata = Metadata(title="EmptyESM")
        esm_file = EsmFile(version="0.1.0", metadata=metadata)

        dependencies = resolve_coupling_dependencies(esm_file)

        assert len(dependencies) == 0

    def test_build_execution_order_simple(self):
        """Test building execution order from simple dependencies."""
        dependencies = {
            'component_b': ['component_a'],
            'component_c': ['component_b']
        }

        execution_order = build_execution_order_from_dependencies(dependencies)

        # Component A should be first, then B, then C
        assert execution_order.index('component_a') < execution_order.index('component_b')
        assert execution_order.index('component_b') < execution_order.index('component_c')

    def test_build_execution_order_with_cycle_error(self):
        """Test that circular dependencies raise error."""
        dependencies = {
            'component_a': ['component_b'],
            'component_b': ['component_a']
        }

        with pytest.raises(ValueError, match="Circular dependencies detected"):
            build_execution_order_from_dependencies(dependencies)

    def test_build_execution_order_complex(self):
        """Test building execution order from complex dependencies."""
        dependencies = {
            'component_d': ['component_b', 'component_c'],
            'component_b': ['component_a'],
            'component_c': ['component_a']
        }

        execution_order = build_execution_order_from_dependencies(dependencies)

        # A should be first
        assert execution_order[0] == 'component_a'
        # B and C should come after A but before D
        assert execution_order.index('component_b') > execution_order.index('component_a')
        assert execution_order.index('component_c') > execution_order.index('component_a')
        # D should be last
        assert execution_order[-1] == 'component_d'