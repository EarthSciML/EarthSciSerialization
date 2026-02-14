"""Integration tests for coupling resolution algorithm using test case data."""

import pytest
from esm_format.coupling_graph import ScopedReferenceResolver
from esm_format.types import EsmFile, Metadata


class TestCouplingResolutionIntegration:
    """Integration tests for the complete coupling resolution algorithm."""

    def _create_coupling_resolution_test_data(self):
        """
        Create test data mirroring the coupling_resolution_algorithm.esm test case.

        This creates a simplified version of the hierarchical test case to verify
        the scoped reference resolution algorithm works on realistic data.
        """
        metadata = Metadata(title="CouplingResolutionAlgorithmTests")

        # Create the hierarchical model structure from the test case
        atmosphere_model = {
            'coupletype': 'AtmosphereCoupler',
            'variables': {
                'pressure': {'type': 'parameter', 'units': 'Pa', 'default': 101325.0},
                'temperature': {'type': 'parameter', 'units': 'K', 'default': 298.15}
            },
            'subsystems': {
                'Chemistry': {
                    'coupletype': 'ChemistryCoupler',
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
                        },
                        'SlowReactions': {
                            'variables': {
                                'k_slow': {'type': 'parameter', 'units': '1/s', 'default': 1e-7}
                            }
                        }
                    }
                },
                'Transport': {
                    'variables': {
                        'wind_speed': {'type': 'parameter', 'units': 'm/s', 'default': 5.0},
                        'diffusivity': {'type': 'parameter', 'units': 'm^2/s', 'default': 10.0}
                    },
                    'subsystems': {
                        'Advection': {
                            'variables': {
                                'u_wind': {'type': 'parameter', 'units': 'm/s', 'default': 3.0},
                                'v_wind': {'type': 'parameter', 'units': 'm/s', 'default': 4.0}
                            }
                        }
                    }
                }
            }
        }

        surface_model = {
            'coupletype': 'SurfaceCoupler',
            'variables': {
                'soil_temperature': {'type': 'parameter', 'units': 'K', 'default': 285.0},
                'surface_resistance': {'type': 'parameter', 'units': 's/m', 'default': 100.0}
            },
            'subsystems': {
                'VegetationLayer': {
                    'variables': {
                        'leaf_area_index': {'type': 'parameter', 'units': 'm^2/m^2', 'default': 3.0},
                        'stomatal_resistance': {'type': 'parameter', 'units': 's/m', 'default': 200.0}
                    }
                }
            }
        }

        # Create data loaders section
        met_data_loader = {
            'type': 'gridded_data',
            'loader_id': 'WRF',
            'provides': {
                'temperature': {'units': 'K'},
                'pressure': {'units': 'Pa'},
                'wind_u': {'units': 'm/s'},
                'wind_v': {'units': 'm/s'}
            },
            'subsystems': {
                'QualityControl': {
                    'variables': {
                        'data_quality_flag': {'type': 'parameter', 'units': 'dimensionless', 'default': 1.0}
                    }
                }
            }
        }

        # Create operators section
        biogenic_operator = {
            'operator_id': 'MEGAN',
            'needed_vars': ['temperature', 'solar_radiation'],
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
            models={
                'AtmosphereModel': atmosphere_model,
                'SurfaceModel': surface_model
            },
            data_loaders={
                'MeteorologicalData': met_data_loader
            },
            operators={
                'BiogenicEmissions': biogenic_operator
            }
        )

        return esm_file

    def test_all_coupling_resolution_test_cases(self):
        """Test all coupling resolution algorithm test cases from the ESM file."""
        esm_file = self._create_coupling_resolution_test_data()
        resolver = ScopedReferenceResolver(esm_file)

        # TEST CASE 1: Two-level scoped references - AtmosphereModel.Chemistry
        result = resolver.resolve_reference("AtmosphereModel.Chemistry")
        assert result.path == ["AtmosphereModel", "Chemistry"]
        assert result.component_type == "model"

        # TEST CASE 2: Simple two-part scoped reference - MeteorologicalData.temperature
        # Note: This refers to a provided variable, not a subsystem variable
        # For now we'll test the subsystem resolution part

        # TEST CASE 3: Three-level hierarchy - AtmosphereModel.Chemistry.temperature
        result = resolver.resolve_reference("AtmosphereModel.Chemistry.temperature")
        assert result.path == ["AtmosphereModel", "Chemistry"]
        assert result.target == "temperature"
        assert result.component_type == "model"
        assert result.resolved_variable['type'] == 'parameter'
        assert result.resolved_variable['units'] == 'K'

        # TEST CASE 4: Four-level deep nesting - AtmosphereModel.Chemistry.FastReactions.k1
        result = resolver.resolve_reference("AtmosphereModel.Chemistry.FastReactions.k1")
        assert result.path == ["AtmosphereModel", "Chemistry", "FastReactions"]
        assert result.target == "k1"
        assert result.component_type == "model"
        assert result.resolved_variable['type'] == 'parameter'
        assert result.resolved_variable['units'] == '1/s'

        # TEST CASE 5: Four-level resolution in different subsystem branch
        result = resolver.resolve_reference("AtmosphereModel.Transport.Advection.u_wind")
        assert result.path == ["AtmosphereModel", "Transport", "Advection"]
        assert result.target == "u_wind"
        assert result.component_type == "model"
        assert result.resolved_variable['type'] == 'parameter'
        assert result.resolved_variable['units'] == 'm/s'

        # TEST CASE 6: Data loader subsystem resolution
        result = resolver.resolve_reference("MeteorologicalData.QualityControl.data_quality_flag")
        assert result.path == ["MeteorologicalData", "QualityControl"]
        assert result.target == "data_quality_flag"
        assert result.component_type == "data_loader"
        assert result.resolved_variable['type'] == 'parameter'

        # TEST CASE 7: Operator subsystem resolution
        result = resolver.resolve_reference("BiogenicEmissions.TemperatureDependence.beta")
        assert result.path == ["BiogenicEmissions", "TemperatureDependence"]
        assert result.target == "beta"
        assert result.component_type == "operator"
        assert result.resolved_variable['type'] == 'parameter'
        assert result.resolved_variable['units'] == '1/K'

    def test_error_cases(self):
        """Test error cases described in the coupling resolution test case."""
        esm_file = self._create_coupling_resolution_test_data()
        resolver = ScopedReferenceResolver(esm_file)

        # Invalid top-level system
        with pytest.raises(ValueError, match="Top-level component 'NonExistentModel' not found"):
            resolver.resolve_reference("NonExistentModel.Chemistry.O3")

        # Invalid subsystem
        with pytest.raises(ValueError, match="Subsystem 'NonExistentSub' not found"):
            resolver.resolve_reference("AtmosphereModel.NonExistentSub.O3")

        # Invalid variable
        with pytest.raises(ValueError, match="Target 'NonExistentVar' not found"):
            resolver.resolve_reference("AtmosphereModel.Chemistry.NonExistentVar")

    def test_algorithm_step_verification(self):
        """
        Verify the step-by-step algorithm execution as described in the test verification.

        This tests the specific algorithm steps:
        1. Split on '.' → [A, B, C, var]
        2. Final segment: variable name or system name
        3. Path: hierarchy to walk
        4. Find top-level component
        5. Walk subsystem hierarchy
        6. Resolve final target
        """
        esm_file = self._create_coupling_resolution_test_data()
        resolver = ScopedReferenceResolver(esm_file)

        # Test the four-level deep nesting case step by step
        reference = "AtmosphereModel.Chemistry.FastReactions.k1"

        # Step 1: Split should work correctly
        segments = reference.split('.')
        assert segments == ['AtmosphereModel', 'Chemistry', 'FastReactions', 'k1']

        # Full resolution should work
        result = resolver.resolve_reference(reference)

        # Verify the algorithm tracked the correct path and target
        assert result.original_reference == reference
        assert result.path == ['AtmosphereModel', 'Chemistry', 'FastReactions']
        assert result.target == 'k1'

        # Verify the resolved component is correct
        assert result.component_type == 'model'
        assert result.resolved_variable is not None
        assert result.resolved_variable['default'] == 1e-5

    def test_cross_section_resolution(self):
        """Test resolution across different ESM file sections (models, data_loaders, operators)."""
        esm_file = self._create_coupling_resolution_test_data()
        resolver = ScopedReferenceResolver(esm_file)

        # Test model section resolution
        model_result = resolver.resolve_reference("AtmosphereModel.Chemistry.O3")
        assert model_result.component_type == "model"

        # Test data_loaders section resolution
        data_loader_result = resolver.resolve_reference("MeteorologicalData.QualityControl.data_quality_flag")
        assert data_loader_result.component_type == "data_loader"

        # Test operators section resolution
        operator_result = resolver.resolve_reference("BiogenicEmissions.TemperatureDependence.beta")
        assert operator_result.component_type == "operator"

        # Verify each resolved to different sections
        assert len({model_result.component_type, data_loader_result.component_type, operator_result.component_type}) == 3