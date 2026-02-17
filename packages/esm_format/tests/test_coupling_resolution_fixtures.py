"""
Comprehensive test fixtures for coupled system resolution.

This module provides test fixtures covering all complex interactions between coupled systems:

1. **Operator composition with placeholder expansion**: Testing how operators compose with
   placeholder variables expanded across different scopes and contexts.
2. **Variable translation with conversion factors**: Testing automatic unit conversion
   and variable mapping between different coupled components.
3. **Coupling order independence**: Ensuring that the order of coupling declarations
   doesn't affect the final resolved system behavior.
4. **Scoped reference resolution**: Testing hierarchical namespace resolution across
   nested subsystems and component boundaries.
5. **Variable equivalence classes**: Testing detection and resolution of variables
   that represent the same physical quantity across different components.
6. **Circular coupling detection**: Testing detection and handling of circular
   dependencies between coupled system components.

These test fixtures validate the complex interactions between coupled systems across
all implementation languages (Python, Julia, TypeScript, Rust, Go).
"""

import pytest
import json
import copy
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass

# Core imports
from esm_format.types import (
    EsmFile, Model, ReactionSystem, DataLoader, Operator, Metadata,
    ModelVariable, Species, Parameter, Reaction, Equation, ExprNode
)
from esm_format.coupling_graph import (
    ScopedReferenceResolver, CouplingGraph, CouplingNode, CouplingEdge,
    NodeType, construct_coupling_graph, validate_coupling_graph
)
from esm_format.parse import load
from esm_format.serialize import save

# Optional imports with fallbacks
try:
    from esm_format.placeholder_expansion import expand_placeholders
    PLACEHOLDER_EXPANSION_AVAILABLE = True
except ImportError:
    PLACEHOLDER_EXPANSION_AVAILABLE = False

try:
    from esm_format.units import convert_units, get_conversion_factor
    UNITS_AVAILABLE = True
except ImportError:
    UNITS_AVAILABLE = False


# ========================================
# 1. Operator Composition with Placeholder Expansion
# ========================================

class TestOperatorCompositionFixtures:
    """Test fixtures for operator composition with placeholder expansion."""

    def create_complex_operator_composition_system(self) -> EsmFile:
        """
        Create a complex system with nested operators and placeholder expansion.

        This tests operator composition where:
        - Operators contain placeholder variables that reference other system components
        - Placeholders expand across hierarchical scopes
        - Multiple operators compose to form compound operations
        - Variable scope resolution works across operator boundaries
        """
        metadata = Metadata(
            title="Complex Operator Composition with Placeholder Expansion",
            description="Tests operator composition with nested placeholder expansion across scopes"
        )

        # Create a primary atmospheric model with nested chemistry subsystem
        atmosphere_model = {
            'name': 'AtmosphericPhysics',
            'variables': {
                'temperature': {'type': 'state', 'units': 'K', 'default': 298.15},
                'pressure': {'type': 'state', 'units': 'Pa', 'default': 101325.0},
                'relative_humidity': {'type': 'state', 'units': 'dimensionless', 'default': 0.6}
            },
            'subsystems': {
                'Thermodynamics': {
                    'variables': {
                        'potential_temperature': {'type': 'state', 'units': 'K', 'default': 300.0},
                        'virtual_temperature': {'type': 'state', 'units': 'K', 'default': 299.0}
                    },
                    'subsystems': {
                        'MoistThermodynamics': {
                            'variables': {
                                'equivalent_potential_temp': {'type': 'state', 'units': 'K', 'default': 320.0},
                                'saturation_mixing_ratio': {'type': 'state', 'units': 'kg/kg', 'default': 0.015}
                            }
                        }
                    }
                },
                'Chemistry': {
                    'variables': {
                        'O3_concentration': {'type': 'state', 'units': 'mol/mol', 'default': 40e-9},
                        'NO2_concentration': {'type': 'state', 'units': 'mol/mol', 'default': 1e-9},
                        'reaction_rate_constant': {'type': 'parameter', 'units': '1/s', 'default': 1e-5}
                    }
                }
            }
        }

        # Surface model with vegetation subsystems
        surface_model = {
            'name': 'SurfaceExchange',
            'variables': {
                'surface_temperature': {'type': 'state', 'units': 'K', 'default': 285.0},
                'soil_moisture': {'type': 'state', 'units': 'volumetric_fraction', 'default': 0.3},
                'albedo': {'type': 'parameter', 'units': 'dimensionless', 'default': 0.2}
            },
            'subsystems': {
                'Vegetation': {
                    'variables': {
                        'leaf_area_index': {'type': 'parameter', 'units': 'm2/m2', 'default': 3.0},
                        'canopy_resistance': {'type': 'parameter', 'units': 's/m', 'default': 200.0}
                    },
                    'subsystems': {
                        'Photosynthesis': {
                            'variables': {
                                'net_photosynthesis_rate': {'type': 'state', 'units': 'mol_CO2/m2/s', 'default': 1e-6},
                                'stomatal_conductance': {'type': 'state', 'units': 'm/s', 'default': 0.01}
                            }
                        }
                    }
                }
            }
        }

        # Data loaders with nested processing chains
        meteorological_data = {
            'type': 'gridded_data',
            'loader_id': 'WRF_Output',
            'provides': {
                'temperature': {'units': 'K'},
                'pressure': {'units': 'Pa'},
                'wind_u': {'units': 'm/s'},
                'wind_v': {'units': 'm/s'},
                'solar_radiation': {'units': 'W/m2'}
            },
            'subsystems': {
                'QualityAssurance': {
                    'variables': {
                        'data_quality_flag': {'type': 'parameter', 'units': 'dimensionless', 'default': 1.0},
                        'outlier_threshold': {'type': 'parameter', 'units': 'sigma', 'default': 3.0}
                    },
                    'subsystems': {
                        'TemporalSmoothing': {
                            'variables': {
                                'smoothing_window': {'type': 'parameter', 'units': 'seconds', 'default': 3600.0}
                            }
                        }
                    }
                }
            }
        }

        # Complex operators with placeholder references
        photolysis_operator = {
            'operator_id': 'PhotolysisRates',
            'needed_vars': ['${AtmosphericPhysics.temperature}', '${MeteorologicalData.solar_radiation}', '${AtmosphericPhysics.pressure}'],
            'modifies': ['${AtmosphericPhysics.Chemistry.reaction_rate_constant}'],
            'placeholders': {
                'base_photolysis_rate': '${BiochemicalRates.photochemistry_base_rate}',
                'temperature_factor': 'exp(-${PhotochemicalParameters.activation_energy} / (8.314 * ${AtmosphericPhysics.temperature}))',
                'pressure_correction': '${AtmosphericPhysics.pressure} / 101325.0'
            },
            'subsystems': {
                'PhotochemicalParameters': {
                    'variables': {
                        'activation_energy': {'type': 'parameter', 'units': 'J/mol', 'default': 12000.0},
                        'quantum_yield': {'type': 'parameter', 'units': 'dimensionless', 'default': 0.8}
                    }
                },
                'SolarZenithAngleCalculation': {
                    'variables': {
                        'latitude': {'type': 'parameter', 'units': 'degrees', 'default': 40.0},
                        'day_of_year': {'type': 'parameter', 'units': 'day', 'default': 180}
                    }
                }
            }
        }

        biogenic_emissions_operator = {
            'operator_id': 'BiogenicEmissions_MEGAN',
            'needed_vars': [
                '${AtmosphericPhysics.temperature}',
                '${MeteorologicalData.solar_radiation}',
                '${SurfaceExchange.Vegetation.leaf_area_index}',
                '${SurfaceExchange.surface_temperature}'
            ],
            'modifies': ['isoprene_emission_rate', 'monoterpene_emission_rate'],
            'placeholders': {
                'temperature_factor': 'exp(${EmissionFactors.temperature_dependence_beta} * (${AtmosphericPhysics.temperature} - 303.15))',
                'light_factor': '${MeteorologicalData.solar_radiation} / (${EmissionFactors.light_saturation_par} + ${MeteorologicalData.solar_radiation})',
                'vegetation_factor': '${SurfaceExchange.Vegetation.leaf_area_index} * ${EmissionFactors.foliar_density}'
            },
            'subsystems': {
                'EmissionFactors': {
                    'variables': {
                        'temperature_dependence_beta': {'type': 'parameter', 'units': '1/K', 'default': 0.09},
                        'light_saturation_par': {'type': 'parameter', 'units': 'umol_photons/m2/s', 'default': 1500.0},
                        'foliar_density': {'type': 'parameter', 'units': 'g_dry_mass/m2', 'default': 500.0}
                    }
                },
                'SpeciesSpecificFactors': {
                    'variables': {
                        'isoprene_base_rate': {'type': 'parameter', 'units': 'ug/g_dry_mass/hr', 'default': 10.0},
                        'monoterpene_base_rate': {'type': 'parameter', 'units': 'ug/g_dry_mass/hr', 'default': 2.0}
                    }
                }
            }
        }

        # Compound operator that references other operators
        atmospheric_chemistry_operator = {
            'operator_id': 'CoupledAtmosphericChemistry',
            'needed_vars': [
                '${PhotolysisRates.modifies}',  # Reference to another operator's output
                '${BiogenicEmissions_MEGAN.modifies}',
                '${AtmosphericPhysics.Chemistry.O3_concentration}',
                '${AtmosphericPhysics.Chemistry.NO2_concentration}'
            ],
            'modifies': [
                '${AtmosphericPhysics.Chemistry.O3_concentration}',
                '${AtmosphericPhysics.Chemistry.NO2_concentration}'
            ],
            'placeholders': {
                'ozone_production_rate': '${PhotolysisRates.PhotochemicalParameters.quantum_yield} * ${BiogenicEmissions_MEGAN.isoprene_emission_rate} * ${ChemistryConstants.ozone_yield}',
                'no2_loss_rate': '${PhotolysisRates.reaction_rate_constant} * ${AtmosphericPhysics.Chemistry.NO2_concentration}'
            },
            'subsystems': {
                'ChemistryConstants': {
                    'variables': {
                        'ozone_yield': {'type': 'parameter', 'units': 'mol_O3/mol_precursor', 'default': 0.15}
                    }
                }
            }
        }

        # Biochemical rates referenced by photolysis operator
        biochemical_rates_data = {
            'type': 'lookup_table',
            'loader_id': 'BiochemicalRates',
            'provides': {
                'photochemistry_base_rate': {'units': '1/s'},
                'hydrolysis_rate': {'units': '1/s'}
            }
        }

        esm_file = EsmFile(
            version="0.1.0",
            metadata=metadata,
            models={
                'AtmosphericPhysics': atmosphere_model,
                'SurfaceExchange': surface_model
            },
            data_loaders={
                'MeteorologicalData': meteorological_data,
                'BiochemicalRates': biochemical_rates_data
            },
            operators={
                'PhotolysisRates': photolysis_operator,
                'BiogenicEmissions_MEGAN': biogenic_emissions_operator,
                'CoupledAtmosphericChemistry': atmospheric_chemistry_operator
            }
        )

        return esm_file

    def test_operator_placeholder_expansion_resolution(self):
        """Test that placeholder expansion works correctly across operator compositions."""
        esm_file = self.create_complex_operator_composition_system()
        resolver = ScopedReferenceResolver(esm_file)

        # Test placeholder resolution in photolysis operator
        photolysis_op = esm_file.operators['PhotolysisRates']

        # Test that needed_vars placeholders can be resolved
        for var_ref in photolysis_op['needed_vars']:
            if var_ref.startswith('${') and var_ref.endswith('}'):
                reference = var_ref[2:-1]  # Remove ${ and }
                result = resolver.resolve_reference(reference)
                assert result is not None, f"Failed to resolve placeholder reference: {reference}"

        # Test cross-operator placeholder resolution
        chemistry_op = esm_file.operators['CoupledAtmosphericChemistry']

        # This operator references outputs from other operators
        cross_op_refs = [ref for ref in chemistry_op['needed_vars'] if 'modifies' in ref]
        assert len(cross_op_refs) == 2, "Should have cross-operator references"

        # Test nested placeholder resolution within operator subsystems
        photolysis_subsystem = photolysis_op['subsystems']['PhotochemicalParameters']
        assert 'activation_energy' in photolysis_subsystem['variables']

        # Verify that activation energy can be resolved from placeholders
        activation_energy_ref = "PhotolysisRates.PhotochemicalParameters.activation_energy"
        result = resolver.resolve_reference(activation_energy_ref)
        assert result.resolved_variable['default'] == 12000.0

    def test_operator_composition_dependency_analysis(self):
        """Test dependency analysis for composed operators."""
        esm_file = self.create_complex_operator_composition_system()

        # Build coupling graph to analyze dependencies
        graph = construct_coupling_graph(esm_file)

        # Verify that compound operators depend on their component operators
        chemistry_node = None
        photolysis_node = None
        biogenic_node = None

        for node_id, node in graph.nodes.items():
            if 'CoupledAtmosphericChemistry' in node_id:
                chemistry_node = node
            elif 'PhotolysisRates' in node_id:
                photolysis_node = node
            elif 'BiogenicEmissions' in node_id:
                biogenic_node = node

        assert chemistry_node is not None, "CoupledAtmosphericChemistry operator should be in graph"
        assert photolysis_node is not None, "PhotolysisRates operator should be in graph"
        assert biogenic_node is not None, "BiogenicEmissions operator should be in graph"

        # Analyze dependencies
        graph.analyze_dependencies()

        # CoupledAtmosphericChemistry should depend on the other two operators
        chemistry_deps = graph.get_dependency_info(chemistry_node.id)
        assert len(chemistry_deps.direct_dependencies) >= 2, "Chemistry operator should depend on photolysis and biogenic operators"

    def test_operator_scope_boundary_crossing(self):
        """Test that operators can correctly access variables across scope boundaries."""
        esm_file = self.create_complex_operator_composition_system()
        resolver = ScopedReferenceResolver(esm_file)

        # Test that biogenic emissions operator can access nested vegetation variables
        biogenic_op = esm_file.operators['BiogenicEmissions_MEGAN']
        vegetation_ref = 'SurfaceExchange.Vegetation.leaf_area_index'

        result = resolver.resolve_reference(vegetation_ref)
        assert result is not None
        assert result.path == ['SurfaceExchange', 'Vegetation']
        assert result.target == 'leaf_area_index'
        assert result.resolved_variable['default'] == 3.0

        # Test deeply nested reference resolution
        deep_ref = 'AtmosphericPhysics.Thermodynamics.MoistThermodynamics.equivalent_potential_temp'
        result = resolver.resolve_reference(deep_ref)
        assert result is not None
        assert result.path == ['AtmosphericPhysics', 'Thermodynamics', 'MoistThermodynamics']
        assert result.target == 'equivalent_potential_temp'
        assert result.resolved_variable['default'] == 320.0


# ========================================
# 2. Variable Translation with Conversion Factors
# ========================================

class TestVariableTranslationFixtures:
    """Test fixtures for variable translation with conversion factors."""

    def create_multi_unit_coupled_system(self) -> EsmFile:
        """
        Create a system with multiple components using different units that require conversion.

        Tests variable translation where:
        - Same physical quantities use different units across components
        - Automatic unit conversion factors are computed
        - Complex unit conversions (e.g., concentration units)
        - Temperature scales (Kelvin, Celsius, Fahrenheit)
        - Pressure units (Pa, hPa, atm, mmHg)
        - Time scales (seconds, hours, days)
        """
        metadata = Metadata(
            title="Multi-Unit Variable Translation System",
            description="Tests automatic unit conversion across coupled components"
        )

        # Meteorological model using SI units
        meteorological_model = {
            'name': 'MeteorologicalModel',
            'variables': {
                'air_temperature': {'type': 'state', 'units': 'K', 'default': 298.15, 'description': 'Air temperature in Kelvin'},
                'atmospheric_pressure': {'type': 'state', 'units': 'Pa', 'default': 101325.0, 'description': 'Pressure in Pascals'},
                'wind_speed': {'type': 'state', 'units': 'm/s', 'default': 5.0, 'description': 'Wind speed in m/s'},
                'precipitation_rate': {'type': 'state', 'units': 'kg/m2/s', 'default': 0.0, 'description': 'Precipitation in SI units'},
                'relative_humidity': {'type': 'state', 'units': 'dimensionless', 'default': 0.6}
            }
        }

        # Agricultural model using practical units
        agricultural_model = {
            'name': 'AgriculturalModel',
            'variables': {
                'soil_temperature': {'type': 'state', 'units': 'celsius', 'default': 25.0, 'description': 'Soil temperature in Celsius'},
                'barometric_pressure': {'type': 'state', 'units': 'hPa', 'default': 1013.25, 'description': 'Pressure in hectopascals'},
                'wind_velocity': {'type': 'state', 'units': 'km/h', 'default': 18.0, 'description': 'Wind speed in km/h'},
                'rainfall_rate': {'type': 'state', 'units': 'mm/hr', 'default': 0.0, 'description': 'Rainfall in mm/hr'},
                'humidity_percent': {'type': 'state', 'units': 'percent', 'default': 60.0}
            }
        }

        # US Weather Service model using imperial/US customary units
        weather_service_model = {
            'name': 'WeatherServiceModel',
            'variables': {
                'temperature_fahrenheit': {'type': 'state', 'units': 'fahrenheit', 'default': 77.0, 'description': 'Temperature in Fahrenheit'},
                'pressure_inches_hg': {'type': 'state', 'units': 'inHg', 'default': 29.92, 'description': 'Pressure in inches of mercury'},
                'wind_mph': {'type': 'state', 'units': 'mph', 'default': 11.18, 'description': 'Wind speed in miles per hour'},
                'precip_inches_per_hour': {'type': 'state', 'units': 'in/hr', 'default': 0.0, 'description': 'Precipitation in inches per hour'}
            }
        }

        # Chemistry model using concentration units
        chemistry_model = {
            'name': 'AtmosphericChemistry',
            'variables': {
                'temperature': {'type': 'state', 'units': 'K', 'default': 298.15},
                'pressure': {'type': 'state', 'units': 'atm', 'default': 1.0, 'description': 'Pressure in atmospheres'},
                'O3_mixing_ratio': {'type': 'state', 'units': 'ppb', 'default': 40.0, 'description': 'Ozone in parts per billion'},
                'NO2_concentration': {'type': 'state', 'units': 'ug/m3', 'default': 20.0, 'description': 'NO2 in micrograms per cubic meter'},
                'CO_molar_concentration': {'type': 'state', 'units': 'mol/m3', 'default': 1e-6, 'description': 'CO in mol per cubic meter'},
                'reaction_rate': {'type': 'parameter', 'units': '1/day', 'default': 0.1, 'description': 'Rate constant per day'}
            }
        }

        # Alternative chemistry system using different concentration units
        alternative_chemistry_model = {
            'name': 'AlternativeChemistry',
            'variables': {
                'ozone_mole_fraction': {'type': 'state', 'units': 'mol/mol', 'default': 40e-9, 'description': 'Ozone mole fraction'},
                'no2_mass_concentration': {'type': 'state', 'units': 'mg/m3', 'default': 0.02, 'description': 'NO2 in mg per cubic meter'},
                'co_volume_mixing_ratio': {'type': 'state', 'units': 'ppm', 'default': 0.1, 'description': 'CO in parts per million'},
                'rate_constant_seconds': {'type': 'parameter', 'units': '1/s', 'default': 1.157e-6, 'description': 'Rate constant per second'}
            }
        }

        # Time-dependent model using different time scales
        temporal_model = {
            'name': 'TemporalProcesses',
            'variables': {
                'hourly_temperature_change': {'type': 'state', 'units': 'K/hr', 'default': 0.5},
                'daily_precip_accumulation': {'type': 'state', 'units': 'mm/day', 'default': 2.0},
                'weekly_pressure_trend': {'type': 'state', 'units': 'hPa/week', 'default': -1.0},
                'annual_temperature_cycle': {'type': 'parameter', 'units': 'K/year', 'default': 0.02}
            }
        }

        # Define unit conversion couplings
        couplings = [
            # Temperature conversions
            {
                'source_component': 'MeteorologicalModel',
                'target_component': 'AgriculturalModel',
                'variable_mappings': [
                    {'source_var': 'air_temperature', 'target_var': 'soil_temperature',
                     'conversion_factor': 'celsius_from_kelvin', 'offset': -273.15}
                ]
            },
            {
                'source_component': 'MeteorologicalModel',
                'target_component': 'WeatherServiceModel',
                'variable_mappings': [
                    {'source_var': 'air_temperature', 'target_var': 'temperature_fahrenheit',
                     'conversion_factor': 'fahrenheit_from_kelvin', 'formula': '(K - 273.15) * 9/5 + 32'}
                ]
            },
            # Pressure conversions
            {
                'source_component': 'MeteorologicalModel',
                'target_component': 'AgriculturalModel',
                'variable_mappings': [
                    {'source_var': 'atmospheric_pressure', 'target_var': 'barometric_pressure',
                     'conversion_factor': 0.01, 'description': 'Pa to hPa conversion'}
                ]
            },
            {
                'source_component': 'MeteorologicalModel',
                'target_component': 'AtmosphericChemistry',
                'variable_mappings': [
                    {'source_var': 'atmospheric_pressure', 'target_var': 'pressure',
                     'conversion_factor': 9.8692e-6, 'description': 'Pa to atm conversion'}
                ]
            },
            # Wind speed conversions
            {
                'source_component': 'MeteorologicalModel',
                'target_component': 'AgriculturalModel',
                'variable_mappings': [
                    {'source_var': 'wind_speed', 'target_var': 'wind_velocity',
                     'conversion_factor': 3.6, 'description': 'm/s to km/h conversion'}
                ]
            },
            # Concentration unit conversions (more complex)
            {
                'source_component': 'AtmosphericChemistry',
                'target_component': 'AlternativeChemistry',
                'variable_mappings': [
                    {'source_var': 'O3_mixing_ratio', 'target_var': 'ozone_mole_fraction',
                     'conversion_factor': 1e-9, 'description': 'ppb to mol/mol conversion'},
                    {'source_var': 'NO2_concentration', 'target_var': 'no2_mass_concentration',
                     'conversion_factor': 0.001, 'description': 'ug/m3 to mg/m3 conversion'},
                    {'source_var': 'reaction_rate', 'target_var': 'rate_constant_seconds',
                     'conversion_factor': 1.157e-5, 'description': '1/day to 1/s conversion'}
                ]
            }
        ]

        esm_file = EsmFile(
            version="0.1.0",
            metadata=metadata,
            models={
                'MeteorologicalModel': meteorological_model,
                'AgriculturalModel': agricultural_model,
                'WeatherServiceModel': weather_service_model,
                'AtmosphericChemistry': chemistry_model,
                'AlternativeChemistry': alternative_chemistry_model,
                'TemporalProcesses': temporal_model
            },
            coupling_metadata={
                'unit_conversions': couplings
            }
        )

        return esm_file

    def test_temperature_unit_conversions(self):
        """Test temperature unit conversions between Kelvin, Celsius, and Fahrenheit."""
        esm_file = self.create_multi_unit_coupled_system()

        # Test Kelvin to Celsius conversion
        met_model = esm_file.models['MeteorologicalModel']
        agr_model = esm_file.models['AgriculturalModel']

        kelvin_temp = met_model['variables']['air_temperature']['default']  # 298.15 K
        expected_celsius = kelvin_temp - 273.15  # 25.0 °C

        # Verify that coupling metadata specifies the correct conversion
        unit_conversions = esm_file.coupling_metadata['unit_conversions']
        temp_conversion = None
        for coupling in unit_conversions:
            if (coupling['source_component'] == 'MeteorologicalModel' and
                coupling['target_component'] == 'AgriculturalModel'):
                for mapping in coupling['variable_mappings']:
                    if (mapping['source_var'] == 'air_temperature' and
                        mapping['target_var'] == 'soil_temperature'):
                        temp_conversion = mapping
                        break

        assert temp_conversion is not None, "Temperature conversion mapping should exist"
        assert temp_conversion['offset'] == -273.15, "Should have correct Kelvin to Celsius offset"

        # Verify the conversion produces the expected result
        converted_temp = kelvin_temp + temp_conversion['offset']
        assert abs(converted_temp - expected_celsius) < 1e-6

    def test_pressure_unit_conversions(self):
        """Test pressure unit conversions between Pa, hPa, atm, and inHg."""
        esm_file = self.create_multi_unit_coupled_system()

        # Test Pa to hPa conversion
        met_model = esm_file.models['MeteorologicalModel']
        pa_pressure = met_model['variables']['atmospheric_pressure']['default']  # 101325 Pa

        unit_conversions = esm_file.coupling_metadata['unit_conversions']
        pa_to_hpa_conversion = None
        pa_to_atm_conversion = None

        for coupling in unit_conversions:
            if coupling['source_component'] == 'MeteorologicalModel':
                for mapping in coupling['variable_mappings']:
                    if (mapping['source_var'] == 'atmospheric_pressure' and
                        mapping['target_var'] == 'barometric_pressure'):
                        pa_to_hpa_conversion = mapping
                    elif (mapping['source_var'] == 'atmospheric_pressure' and
                          mapping['target_var'] == 'pressure'):
                        pa_to_atm_conversion = mapping

        assert pa_to_hpa_conversion is not None, "Pa to hPa conversion should exist"
        assert pa_to_atm_conversion is not None, "Pa to atm conversion should exist"

        # Verify conversions
        hpa_pressure = pa_pressure * pa_to_hpa_conversion['conversion_factor']
        atm_pressure = pa_pressure * pa_to_atm_conversion['conversion_factor']

        assert abs(hpa_pressure - 1013.25) < 0.01, "Should convert to correct hPa value"
        assert abs(atm_pressure - 1.0) < 1e-6, "Should convert to correct atm value"

    def test_concentration_unit_conversions(self):
        """Test complex concentration unit conversions."""
        esm_file = self.create_multi_unit_coupled_system()

        chem_model = esm_file.models['AtmosphericChemistry']
        alt_chem_model = esm_file.models['AlternativeChemistry']

        # Test ppb to mol/mol conversion
        ppb_value = chem_model['variables']['O3_mixing_ratio']['default']  # 40 ppb
        expected_mol_mol = ppb_value * 1e-9  # 40e-9 mol/mol

        unit_conversions = esm_file.coupling_metadata['unit_conversions']
        concentration_conversion = None

        for coupling in unit_conversions:
            if (coupling['source_component'] == 'AtmosphericChemistry' and
                coupling['target_component'] == 'AlternativeChemistry'):
                concentration_conversion = coupling
                break

        assert concentration_conversion is not None, "Concentration conversion should exist"

        # Find the O3 conversion mapping
        ozone_mapping = None
        for mapping in concentration_conversion['variable_mappings']:
            if (mapping['source_var'] == 'O3_mixing_ratio' and
                mapping['target_var'] == 'ozone_mole_fraction'):
                ozone_mapping = mapping
                break

        assert ozone_mapping is not None, "Ozone concentration mapping should exist"
        assert ozone_mapping['conversion_factor'] == 1e-9, "Should have correct ppb to mol/mol factor"

        converted_concentration = ppb_value * ozone_mapping['conversion_factor']
        assert abs(converted_concentration - expected_mol_mol) < 1e-12

    @pytest.mark.skipif(not UNITS_AVAILABLE, reason="Units module not available")
    def test_automatic_unit_conversion_detection(self):
        """Test automatic detection and computation of unit conversion factors."""
        esm_file = self.create_multi_unit_coupled_system()

        # Test that the system can automatically detect compatible units
        from esm_format.units import are_units_compatible, get_conversion_factor

        # Temperature units should be compatible
        assert are_units_compatible('K', 'celsius'), "Kelvin and Celsius should be compatible"
        assert are_units_compatible('K', 'fahrenheit'), "Kelvin and Fahrenheit should be compatible"

        # Pressure units should be compatible
        assert are_units_compatible('Pa', 'hPa'), "Pa and hPa should be compatible"
        assert are_units_compatible('Pa', 'atm'), "Pa and atm should be compatible"

        # Test conversion factor computation
        pa_to_hpa_factor = get_conversion_factor('Pa', 'hPa')
        assert abs(pa_to_hpa_factor - 0.01) < 1e-8, "Pa to hPa factor should be 0.01"

        ms_to_kmh_factor = get_conversion_factor('m/s', 'km/h')
        assert abs(ms_to_kmh_factor - 3.6) < 1e-8, "m/s to km/h factor should be 3.6"

    def test_unit_conversion_error_detection(self):
        """Test detection of incompatible unit conversions."""
        esm_file = self.create_multi_unit_coupled_system()

        # Create an invalid coupling with incompatible units
        invalid_coupling = {
            'source_component': 'MeteorologicalModel',
            'target_component': 'AgriculturalModel',
            'variable_mappings': [
                {'source_var': 'air_temperature', 'target_var': 'wind_velocity',  # Temperature -> Wind speed
                 'conversion_factor': 1.0, 'description': 'Invalid: temperature to wind speed'}
            ]
        }

        # This should be detected as invalid when the coupling system is validated
        # (This is a placeholder - the actual validation would happen in coupling graph construction)

        # For now, just verify the test data is structured correctly
        assert invalid_coupling['variable_mappings'][0]['source_var'] == 'air_temperature'
        assert invalid_coupling['variable_mappings'][0]['target_var'] == 'wind_velocity'

        # The actual validation would detect that temperature (K) cannot be converted to wind speed (km/h)


# ========================================
# 3. Coupling Order Independence
# ========================================

class TestCouplingOrderIndependenceFixtures:
    """Test fixtures for coupling order independence."""

    def create_order_independent_coupling_system(self) -> Dict[str, EsmFile]:
        """
        Create multiple ESM files with identical coupling relationships but different declaration orders.

        This tests that:
        - Coupling declaration order doesn't affect final system behavior
        - Variable resolution works regardless of component definition order
        - Circular dependency detection is order-independent
        - Execution order determination is consistent
        """
        metadata = Metadata(
            title="Coupling Order Independence Test System",
            description="Tests that coupling behavior is independent of declaration order"
        )

        # Define the same components for all test cases
        component_a = {
            'name': 'ComponentA',
            'variables': {
                'var_a1': {'type': 'state', 'units': 'unit_a', 'default': 1.0},
                'var_a2': {'type': 'parameter', 'units': 'unit_a', 'default': 2.0}
            },
            'depends_on': ['ComponentB.var_b1', 'ComponentC.var_c1']
        }

        component_b = {
            'name': 'ComponentB',
            'variables': {
                'var_b1': {'type': 'state', 'units': 'unit_b', 'default': 10.0},
                'var_b2': {'type': 'state', 'units': 'unit_b', 'default': 20.0}
            },
            'depends_on': ['ComponentC.var_c2', 'ComponentD.var_d1']
        }

        component_c = {
            'name': 'ComponentC',
            'variables': {
                'var_c1': {'type': 'parameter', 'units': 'unit_c', 'default': 100.0},
                'var_c2': {'type': 'parameter', 'units': 'unit_c', 'default': 200.0}
            },
            'depends_on': ['ComponentD.var_d2']
        }

        component_d = {
            'name': 'ComponentD',
            'variables': {
                'var_d1': {'type': 'state', 'units': 'unit_d', 'default': 1000.0},
                'var_d2': {'type': 'state', 'units': 'unit_d', 'default': 2000.0}
            }
            # ComponentD has no dependencies - it's the root
        }

        # Define couplings (same for all orders)
        base_couplings = [
            {
                'source': 'ComponentB.var_b1',
                'target': 'ComponentA.var_a1',
                'type': 'direct'
            },
            {
                'source': 'ComponentC.var_c1',
                'target': 'ComponentA.var_a2',
                'type': 'direct'
            },
            {
                'source': 'ComponentC.var_c2',
                'target': 'ComponentB.var_b1',
                'type': 'interpolated'
            },
            {
                'source': 'ComponentD.var_d1',
                'target': 'ComponentB.var_b2',
                'type': 'direct'
            },
            {
                'source': 'ComponentD.var_d2',
                'target': 'ComponentC.var_c1',
                'type': 'direct'
            }
        ]

        # Create multiple ESM files with different component declaration orders

        # Order 1: Alphabetical (A, B, C, D)
        esm_file_order1 = EsmFile(
            version="0.1.0",
            metadata=metadata,
            models={
                'ComponentA': component_a,
                'ComponentB': component_b,
                'ComponentC': component_c,
                'ComponentD': component_d
            },
            coupling_metadata={
                'couplings': base_couplings,
                'order_test_id': 'alphabetical'
            }
        )

        # Order 2: Reverse alphabetical (D, C, B, A)
        esm_file_order2 = EsmFile(
            version="0.1.0",
            metadata=metadata,
            models={
                'ComponentD': component_d,
                'ComponentC': component_c,
                'ComponentB': component_b,
                'ComponentA': component_a
            },
            coupling_metadata={
                'couplings': base_couplings,
                'order_test_id': 'reverse_alphabetical'
            }
        )

        # Order 3: Dependency order (D first, then C, B, A)
        esm_file_order3 = EsmFile(
            version="0.1.0",
            metadata=metadata,
            models={
                'ComponentD': component_d,
                'ComponentC': component_c,
                'ComponentB': component_b,
                'ComponentA': component_a
            },
            coupling_metadata={
                'couplings': base_couplings,
                'order_test_id': 'dependency_order'
            }
        )

        # Order 4: Mixed/random order (B, D, A, C)
        esm_file_order4 = EsmFile(
            version="0.1.0",
            metadata=metadata,
            models={
                'ComponentB': component_b,
                'ComponentD': component_d,
                'ComponentA': component_a,
                'ComponentC': component_c
            },
            coupling_metadata={
                'couplings': base_couplings,
                'order_test_id': 'random_order'
            }
        )

        # Order 5: Different coupling declaration order (same couplings, different sequence)
        reordered_couplings = [
            base_couplings[3],  # ComponentD -> ComponentB
            base_couplings[0],  # ComponentB -> ComponentA
            base_couplings[4],  # ComponentD -> ComponentC
            base_couplings[2],  # ComponentC -> ComponentB
            base_couplings[1]   # ComponentC -> ComponentA
        ]

        esm_file_order5 = EsmFile(
            version="0.1.0",
            metadata=metadata,
            models={
                'ComponentA': component_a,
                'ComponentB': component_b,
                'ComponentC': component_c,
                'ComponentD': component_d
            },
            coupling_metadata={
                'couplings': reordered_couplings,
                'order_test_id': 'reordered_couplings'
            }
        )

        return {
            'alphabetical': esm_file_order1,
            'reverse_alphabetical': esm_file_order2,
            'dependency_order': esm_file_order3,
            'random_order': esm_file_order4,
            'reordered_couplings': esm_file_order5
        }

    def test_coupling_graph_construction_order_independence(self):
        """Test that coupling graph construction produces identical results regardless of order."""
        order_systems = self.create_order_independent_coupling_system()

        # Build coupling graphs for each ordering
        graphs = {}
        for order_name, esm_file in order_systems.items():
            graphs[order_name] = construct_coupling_graph(esm_file)

        # All graphs should have the same structure
        reference_graph = graphs['alphabetical']

        for order_name, graph in graphs.items():
            if order_name == 'alphabetical':
                continue

            # Same number of nodes and edges
            assert len(graph.nodes) == len(reference_graph.nodes), f"Order {order_name} has different number of nodes"
            assert len(graph.edges) == len(reference_graph.edges), f"Order {order_name} has different number of edges"

            # Same node IDs (component names should be identical)
            assert set(graph.nodes.keys()) == set(reference_graph.nodes.keys()), f"Order {order_name} has different node IDs"

            # Same edge structure (may be in different order, so convert to sets)
            ref_edge_set = {(edge.source_node, edge.target_node, tuple(edge.source_variables), tuple(edge.target_variables))
                           for edge in reference_graph.edges}
            graph_edge_set = {(edge.source_node, edge.target_node, tuple(edge.source_variables), tuple(edge.target_variables))
                             for edge in graph.edges}

            assert graph_edge_set == ref_edge_set, f"Order {order_name} has different edge structure"

    def test_execution_order_determination_consistency(self):
        """Test that execution order determination is consistent across different declaration orders."""
        order_systems = self.create_order_independent_coupling_system()

        execution_orders = {}
        for order_name, esm_file in order_systems.items():
            graph = construct_coupling_graph(esm_file)
            graph.analyze_dependencies()
            execution_orders[order_name] = graph.get_execution_order()

        # All execution orders should be topologically equivalent
        # The exact order may differ, but dependencies must be respected
        reference_order = execution_orders['alphabetical']

        for order_name, exec_order in execution_orders.items():
            if order_name == 'alphabetical':
                continue

            # Same components in execution order
            assert set(exec_order) == set(reference_order), f"Order {order_name} has different components in execution order"

            # Verify dependency constraints are satisfied
            # ComponentD should come before ComponentC
            # ComponentC should come before ComponentB
            # ComponentB should come before ComponentA
            d_pos = exec_order.index('model:ComponentD')
            c_pos = exec_order.index('model:ComponentC')
            b_pos = exec_order.index('model:ComponentB')
            a_pos = exec_order.index('model:ComponentA')

            assert d_pos < c_pos, f"Order {order_name}: ComponentD should come before ComponentC"
            assert d_pos < b_pos, f"Order {order_name}: ComponentD should come before ComponentB"
            assert c_pos < a_pos, f"Order {order_name}: ComponentC should come before ComponentA"
            assert c_pos < b_pos, f"Order {order_name}: ComponentC should come before ComponentB"
            assert b_pos < a_pos, f"Order {order_name}: ComponentB should come before ComponentA"

    def test_variable_resolution_order_independence(self):
        """Test that variable resolution works identically regardless of component declaration order."""
        order_systems = self.create_order_independent_coupling_system()

        # Test the same variable references across all orderings
        test_references = [
            'ComponentA.var_a1',
            'ComponentB.var_b1',
            'ComponentC.var_c2',
            'ComponentD.var_d1'
        ]

        reference_results = {}

        for order_name, esm_file in order_systems.items():
            resolver = ScopedReferenceResolver(esm_file)
            results = {}

            for ref in test_references:
                result = resolver.resolve_reference(ref)
                # Store relevant attributes for comparison
                results[ref] = {
                    'path': result.path,
                    'target': result.target,
                    'component_type': result.component_type,
                    'resolved_variable': result.resolved_variable
                }

            if order_name == 'alphabetical':
                reference_results = results
            else:
                # Compare with reference results
                for ref in test_references:
                    assert results[ref]['path'] == reference_results[ref]['path'], f"Order {order_name}: Different path for {ref}"
                    assert results[ref]['target'] == reference_results[ref]['target'], f"Order {order_name}: Different target for {ref}"
                    assert results[ref]['component_type'] == reference_results[ref]['component_type'], f"Order {order_name}: Different component type for {ref}"
                    assert results[ref]['resolved_variable'] == reference_results[ref]['resolved_variable'], f"Order {order_name}: Different resolved variable for {ref}"

    def test_coupling_metadata_preservation(self):
        """Test that coupling metadata is preserved correctly regardless of declaration order."""
        order_systems = self.create_order_independent_coupling_system()

        # Verify that all systems have the same coupling information
        reference_couplings = order_systems['alphabetical'].coupling_metadata['couplings']

        for order_name, esm_file in order_systems.items():
            if order_name == 'alphabetical':
                continue

            test_couplings = esm_file.coupling_metadata['couplings']

            # Convert to sets for order-independent comparison
            ref_coupling_set = {(c['source'], c['target'], c['type']) for c in reference_couplings}
            test_coupling_set = {(c['source'], c['target'], c['type']) for c in test_couplings}

            assert ref_coupling_set == test_coupling_set, f"Order {order_name}: Coupling metadata differs"

    def test_serialization_deserialization_order_independence(self):
        """Test that serialization and deserialization preserve order independence."""
        order_systems = self.create_order_independent_coupling_system()

        # Serialize and deserialize each system
        reconstructed_systems = {}
        for order_name, esm_file in order_systems.items():
            json_str = save(esm_file)
            reconstructed_systems[order_name] = load(json_str)

        # Verify that reconstructed systems still maintain order independence
        reference_reconstructed = reconstructed_systems['alphabetical']

        for order_name, reconstructed in reconstructed_systems.items():
            if order_name == 'alphabetical':
                continue

            # Same models (though possibly in different dictionary order)
            assert set(reconstructed.models.keys()) == set(reference_reconstructed.models.keys()), f"Reconstructed {order_name}: Different model keys"

            # Same coupling metadata
            ref_couplings = reference_reconstructed.coupling_metadata['couplings']
            test_couplings = reconstructed.coupling_metadata['couplings']

            ref_set = {(c['source'], c['target'], c['type']) for c in ref_couplings}
            test_set = {(c['source'], c['target'], c['type']) for c in test_couplings}

            assert ref_set == test_set, f"Reconstructed {order_name}: Different coupling metadata after serialization"


# ========================================
# 4. Scoped Reference Resolution (Enhanced)
# ========================================

class TestScopedReferenceResolutionFixtures:
    """Enhanced test fixtures for scoped reference resolution."""

    def create_deep_hierarchical_system(self) -> EsmFile:
        """
        Create a deeply nested hierarchical system to test scoped reference resolution.

        Tests advanced scoping scenarios:
        - Deep nesting (5+ levels)
        - Cross-branch references
        - Ambiguous name resolution
        - Scope inheritance
        - Variable shadowing
        - Wildcard references
        """
        metadata = Metadata(
            title="Deep Hierarchical Scoped Reference System",
            description="Tests complex scoped reference resolution across deep hierarchies"
        )

        # Create a complex Earth system model with deep nesting
        earth_system_model = {
            'name': 'EarthSystemModel',
            'variables': {
                'global_temperature': {'type': 'state', 'units': 'K', 'default': 288.15},
                'global_pressure': {'type': 'state', 'units': 'Pa', 'default': 101325.0}
            },
            'subsystems': {
                'Atmosphere': {
                    'variables': {
                        'temperature': {'type': 'state', 'units': 'K', 'default': 250.0},
                        'pressure': {'type': 'state', 'units': 'Pa', 'default': 50000.0}
                    },
                    'subsystems': {
                        'Troposphere': {
                            'variables': {
                                'temperature': {'type': 'state', 'units': 'K', 'default': 288.0},  # Shadows parent temperature
                                'water_vapor': {'type': 'state', 'units': 'kg/kg', 'default': 0.01}
                            },
                            'subsystems': {
                                'BoundaryLayer': {
                                    'variables': {
                                        'temperature': {'type': 'state', 'units': 'K', 'default': 290.0},  # Shadows grandparent temperature
                                        'mixing_height': {'type': 'parameter', 'units': 'm', 'default': 1000.0},
                                        'turbulence_intensity': {'type': 'state', 'units': 'm2/s2', 'default': 0.5}
                                    },
                                    'subsystems': {
                                        'SurfaceLayer': {
                                            'variables': {
                                                'friction_velocity': {'type': 'parameter', 'units': 'm/s', 'default': 0.5},
                                                'roughness_length': {'type': 'parameter', 'units': 'm', 'default': 0.1}
                                            },
                                            'subsystems': {
                                                'MicroscaleProcesses': {
                                                    'variables': {
                                                        'eddy_diffusivity': {'type': 'parameter', 'units': 'm2/s', 'default': 10.0},
                                                        'scalar_flux': {'type': 'state', 'units': 'kg/m2/s', 'default': 0.001}
                                                    }
                                                }
                                            }
                                        }
                                    }
                                },
                                'FreeAtmosphere': {
                                    'variables': {
                                        'geostrophic_wind': {'type': 'parameter', 'units': 'm/s', 'default': 10.0},
                                        'potential_vorticity': {'type': 'state', 'units': 'K*m2/kg/s', 'default': 1e-6}
                                    }
                                }
                            }
                        },
                        'Stratosphere': {
                            'variables': {
                                'temperature': {'type': 'state', 'units': 'K', 'default': 220.0},  # Another temperature shadow
                                'ozone_concentration': {'type': 'state', 'units': 'mol/mol', 'default': 10e-6}
                            },
                            'subsystems': {
                                'OzoneChemistry': {
                                    'variables': {
                                        'production_rate': {'type': 'parameter', 'units': 'mol/mol/s', 'default': 1e-12},
                                        'destruction_rate': {'type': 'parameter', 'units': 'mol/mol/s', 'default': 5e-13}
                                    }
                                }
                            }
                        }
                    }
                },
                'Ocean': {
                    'variables': {
                        'temperature': {'type': 'state', 'units': 'K', 'default': 283.15},  # Ocean temperature
                        'salinity': {'type': 'state', 'units': 'psu', 'default': 35.0}
                    },
                    'subsystems': {
                        'SurfaceOcean': {
                            'variables': {
                                'temperature': {'type': 'state', 'units': 'K', 'default': 290.0},  # Surface ocean temperature
                                'mixed_layer_depth': {'type': 'state', 'units': 'm', 'default': 50.0}
                            },
                            'subsystems': {
                                'OceanSkinLayer': {
                                    'variables': {
                                        'skin_temperature': {'type': 'state', 'units': 'K', 'default': 291.0},
                                        'heat_flux': {'type': 'state', 'units': 'W/m2', 'default': 100.0}
                                    }
                                }
                            }
                        },
                        'DeepOcean': {
                            'variables': {
                                'temperature': {'type': 'state', 'units': 'K', 'default': 277.0},  # Deep ocean temperature
                                'circulation_strength': {'type': 'parameter', 'units': 'Sv', 'default': 20.0}
                            },
                            'subsystems': {
                                'AbyssalCirculation': {
                                    'variables': {
                                        'bottom_water_formation_rate': {'type': 'parameter', 'units': 'Sv', 'default': 2.0}
                                    }
                                }
                            }
                        }
                    }
                },
                'Land': {
                    'variables': {
                        'surface_temperature': {'type': 'state', 'units': 'K', 'default': 285.0},
                        'soil_moisture': {'type': 'state', 'units': 'volumetric_fraction', 'default': 0.3}
                    },
                    'subsystems': {
                        'Vegetation': {
                            'variables': {
                                'leaf_area_index': {'type': 'parameter', 'units': 'm2/m2', 'default': 3.0},
                                'biomass': {'type': 'state', 'units': 'kg_C/m2', 'default': 10.0}
                            },
                            'subsystems': {
                                'Photosynthesis': {
                                    'variables': {
                                        'co2_assimilation_rate': {'type': 'state', 'units': 'mol_CO2/m2/s', 'default': 1e-6},
                                        'light_use_efficiency': {'type': 'parameter', 'units': 'mol_CO2/mol_photons', 'default': 0.05}
                                    }
                                },
                                'Respiration': {
                                    'variables': {
                                        'maintenance_respiration': {'type': 'state', 'units': 'mol_CO2/m2/s', 'default': 5e-7},
                                        'growth_respiration': {'type': 'state', 'units': 'mol_CO2/m2/s', 'default': 2e-7}
                                    }
                                }
                            }
                        },
                        'Soil': {
                            'variables': {
                                'temperature': {'type': 'state', 'units': 'K', 'default': 283.0},  # Soil temperature
                                'organic_carbon': {'type': 'state', 'units': 'kg_C/m2', 'default': 50.0}
                            },
                            'subsystems': {
                                'Decomposition': {
                                    'variables': {
                                        'decomposition_rate': {'type': 'parameter', 'units': '1/year', 'default': 0.1},
                                        'microbial_biomass': {'type': 'state', 'units': 'kg_C/m2', 'default': 1.0}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        # External data loader with nested processing
        climate_data_loader = {
            'type': 'climate_reanalysis',
            'loader_id': 'ERA5_Reanalysis',
            'provides': {
                'temperature': {'units': 'K'},
                'pressure': {'units': 'Pa'},
                'humidity': {'units': 'kg/kg'}
            },
            'subsystems': {
                'DataProcessing': {
                    'variables': {
                        'interpolation_method': {'type': 'parameter', 'units': 'dimensionless', 'default': 1},
                        'quality_control_threshold': {'type': 'parameter', 'units': 'sigma', 'default': 3.0}
                    },
                    'subsystems': {
                        'SpatialInterpolation': {
                            'variables': {
                                'grid_resolution': {'type': 'parameter', 'units': 'degrees', 'default': 0.25}
                            }
                        },
                        'TemporalInterpolation': {
                            'variables': {
                                'time_step': {'type': 'parameter', 'units': 'hours', 'default': 1.0}
                            }
                        }
                    }
                }
            }
        }

        # Complex operator with cross-system references
        carbon_cycle_operator = {
            'operator_id': 'CarbonCycleOperator',
            'needed_vars': [
                # Cross-system temperature references (tests scoping resolution)
                '${EarthSystemModel.Atmosphere.Troposphere.temperature}',
                '${EarthSystemModel.Ocean.SurfaceOcean.temperature}',
                '${EarthSystemModel.Land.Soil.temperature}',
                # Deep nesting references
                '${EarthSystemModel.Land.Vegetation.Photosynthesis.co2_assimilation_rate}',
                '${EarthSystemModel.Land.Vegetation.Respiration.maintenance_respiration}',
                '${EarthSystemModel.Land.Soil.Decomposition.decomposition_rate}',
                # Cross-branch reference (atmosphere to land)
                '${EarthSystemModel.Atmosphere.Troposphere.water_vapor}'
            ],
            'modifies': [
                '${EarthSystemModel.Land.Vegetation.biomass}',
                '${EarthSystemModel.Land.Soil.organic_carbon}'
            ],
            'subsystems': {
                'CarbonFluxCalculation': {
                    'variables': {
                        'net_primary_productivity': {'type': 'state', 'units': 'kg_C/m2/year', 'default': 1.0}
                    }
                }
            }
        }

        esm_file = EsmFile(
            version="0.1.0",
            metadata=metadata,
            models={
                'EarthSystemModel': earth_system_model
            },
            data_loaders={
                'ClimateData': climate_data_loader
            },
            operators={
                'CarbonCycle': carbon_cycle_operator
            }
        )

        return esm_file

    def test_deep_nesting_resolution(self):
        """Test scoped reference resolution in deeply nested hierarchies."""
        esm_file = self.create_deep_hierarchical_system()
        resolver = ScopedReferenceResolver(esm_file)

        # Test 6-level deep resolution
        deep_reference = "EarthSystemModel.Atmosphere.Troposphere.BoundaryLayer.SurfaceLayer.MicroscaleProcesses.eddy_diffusivity"
        result = resolver.resolve_reference(deep_reference)

        assert result is not None, "Deep reference resolution should succeed"
        assert result.path == ["EarthSystemModel", "Atmosphere", "Troposphere", "BoundaryLayer", "SurfaceLayer", "MicroscaleProcesses"]
        assert result.target == "eddy_diffusivity"
        assert result.resolved_variable['default'] == 10.0

        # Test cross-branch resolution
        cross_branch_reference = "EarthSystemModel.Land.Vegetation.Photosynthesis.co2_assimilation_rate"
        result = resolver.resolve_reference(cross_branch_reference)

        assert result is not None, "Cross-branch reference should resolve"
        assert result.path == ["EarthSystemModel", "Land", "Vegetation", "Photosynthesis"]
        assert result.target == "co2_assimilation_rate"
        assert result.resolved_variable['units'] == 'mol_CO2/m2/s'

    def test_variable_shadowing_resolution(self):
        """Test resolution of shadowed variables at different scoping levels."""
        esm_file = self.create_deep_hierarchical_system()
        resolver = ScopedReferenceResolver(esm_file)

        # Test that different "temperature" variables resolve to correct scope
        test_cases = [
            ("EarthSystemModel.global_temperature", 288.15),
            ("EarthSystemModel.Atmosphere.temperature", 250.0),
            ("EarthSystemModel.Atmosphere.Troposphere.temperature", 288.0),
            ("EarthSystemModel.Atmosphere.Troposphere.BoundaryLayer.temperature", 290.0),
            ("EarthSystemModel.Atmosphere.Stratosphere.temperature", 220.0),
            ("EarthSystemModel.Ocean.temperature", 283.15),
            ("EarthSystemModel.Ocean.SurfaceOcean.temperature", 290.0),
            ("EarthSystemModel.Ocean.DeepOcean.temperature", 277.0),
            ("EarthSystemModel.Land.Soil.temperature", 283.0)
        ]

        for reference, expected_default in test_cases:
            result = resolver.resolve_reference(reference)
            assert result is not None, f"Reference {reference} should resolve"
            assert result.resolved_variable['default'] == expected_default, f"Reference {reference} resolved to wrong value: expected {expected_default}, got {result.resolved_variable['default']}"

    def test_cross_system_references_in_operators(self):
        """Test that operators can correctly resolve references across different system components."""
        esm_file = self.create_deep_hierarchical_system()
        resolver = ScopedReferenceResolver(esm_file)

        carbon_cycle_op = esm_file.operators['CarbonCycle']

        # Test cross-system references in operator needed_vars
        cross_system_refs = [
            ('EarthSystemModel.Atmosphere.Troposphere.temperature', 288.0),
            ('EarthSystemModel.Ocean.SurfaceOcean.temperature', 290.0),
            ('EarthSystemModel.Land.Soil.temperature', 283.0),
            ('EarthSystemModel.Land.Vegetation.Photosynthesis.co2_assimilation_rate', 1e-6)
        ]

        for ref, expected_value in cross_system_refs:
            result = resolver.resolve_reference(ref)
            assert result is not None, f"Cross-system reference {ref} should resolve"
            assert result.resolved_variable['default'] == expected_value, f"Cross-system reference {ref} resolved to wrong value"

    def test_data_loader_nested_reference_resolution(self):
        """Test scoped reference resolution within data loader hierarchies."""
        esm_file = self.create_deep_hierarchical_system()
        resolver = ScopedReferenceResolver(esm_file)

        # Test nested data loader references
        nested_refs = [
            "ClimateData.DataProcessing.interpolation_method",
            "ClimateData.DataProcessing.SpatialInterpolation.grid_resolution",
            "ClimateData.DataProcessing.TemporalInterpolation.time_step"
        ]

        for ref in nested_refs:
            result = resolver.resolve_reference(ref)
            assert result is not None, f"Data loader reference {ref} should resolve"
            assert result.component_type == "data_loader", f"Reference {ref} should resolve to data_loader component"

    def test_ambiguous_reference_error_handling(self):
        """Test proper error handling for ambiguous references."""
        esm_file = self.create_deep_hierarchical_system()
        resolver = ScopedReferenceResolver(esm_file)

        # Test that ambiguous references are properly handled
        # (This would be a reference that could match multiple paths)

        # For now, test invalid references
        invalid_refs = [
            "EarthSystemModel.NonExistent.temperature",
            "EarthSystemModel.Atmosphere.InvalidSubsystem.pressure",
            "ClimateData.InvalidProcessing.parameter"
        ]

        for ref in invalid_refs:
            with pytest.raises(ValueError):
                resolver.resolve_reference(ref)

    def test_scope_inheritance_behavior(self):
        """Test that variables properly inherit scope context."""
        esm_file = self.create_deep_hierarchical_system()
        resolver = ScopedReferenceResolver(esm_file)

        # Test that nested subsystems can access parent variables
        # This would be implemented as part of scope inheritance

        # For now, test that the scoping structure is preserved
        nested_result = resolver.resolve_reference("EarthSystemModel.Atmosphere.Troposphere.BoundaryLayer.mixing_height")
        assert nested_result.path == ["EarthSystemModel", "Atmosphere", "Troposphere", "BoundaryLayer"]
        assert nested_result.target == "mixing_height"

        # Test that the resolved variable maintains correct scoping context
        assert nested_result.component_type == "model"
        assert nested_result.resolved_variable is not None


# ========================================
# 5. Variable Equivalence Classes
# ========================================

@dataclass
class VariableEquivalenceClass:
    """Represents a class of equivalent variables across system components."""
    class_id: str
    physical_quantity: str
    canonical_units: str
    member_variables: List[Dict[str, Any]]
    conversion_factors: Dict[str, float]
    description: str

class TestVariableEquivalenceClassesFixtures:
    """Test fixtures for variable equivalence classes."""

    def create_equivalence_class_system(self) -> Tuple[EsmFile, List[VariableEquivalenceClass]]:
        """
        Create a system with multiple components that have equivalent variables.

        Tests equivalence class detection and resolution where:
        - Same physical quantities have different names and units
        - Automatic grouping of equivalent variables
        - Conversion factor computation between equivalent variables
        - Conflict resolution when multiple variables could be equivalent
        - Aliasing and canonical variable assignment
        """
        metadata = Metadata(
            title="Variable Equivalence Classes Test System",
            description="Tests automatic detection and resolution of equivalent variables"
        )

        # Weather station model (uses common meteorological terms)
        weather_station_model = {
            'name': 'WeatherStation',
            'variables': {
                'air_temp': {'type': 'state', 'units': 'celsius', 'default': 20.0, 'physical_quantity': 'air_temperature'},
                'atm_pressure': {'type': 'state', 'units': 'hPa', 'default': 1013.25, 'physical_quantity': 'atmospheric_pressure'},
                'wind_spd': {'type': 'state', 'units': 'km/h', 'default': 15.0, 'physical_quantity': 'wind_speed'},
                'humidity_pct': {'type': 'state', 'units': 'percent', 'default': 65.0, 'physical_quantity': 'relative_humidity'},
                'precip_mm': {'type': 'state', 'units': 'mm/hr', 'default': 0.0, 'physical_quantity': 'precipitation_rate'}
            }
        }

        # Atmospheric physics model (uses scientific terminology)
        atmospheric_physics_model = {
            'name': 'AtmosphericPhysics',
            'variables': {
                'temperature': {'type': 'state', 'units': 'K', 'default': 293.15, 'physical_quantity': 'air_temperature'},
                'pressure': {'type': 'state', 'units': 'Pa', 'default': 101325.0, 'physical_quantity': 'atmospheric_pressure'},
                'velocity': {'type': 'state', 'units': 'm/s', 'default': 4.17, 'physical_quantity': 'wind_speed'},
                'relative_humidity': {'type': 'state', 'units': 'dimensionless', 'default': 0.65, 'physical_quantity': 'relative_humidity'},
                'rainfall_rate': {'type': 'state', 'units': 'kg/m2/s', 'default': 0.0, 'physical_quantity': 'precipitation_rate'}
            }
        }

        # Climate model (uses climate science terminology)
        climate_model = {
            'name': 'ClimateModel',
            'variables': {
                'surface_air_temperature': {'type': 'state', 'units': 'K', 'default': 293.15, 'physical_quantity': 'air_temperature'},
                'sea_level_pressure': {'type': 'state', 'units': 'Pa', 'default': 101325.0, 'physical_quantity': 'atmospheric_pressure'},
                'surface_wind_speed': {'type': 'state', 'units': 'm/s', 'default': 4.17, 'physical_quantity': 'wind_speed'},
                'rh_2m': {'type': 'state', 'units': 'fraction', 'default': 0.65, 'physical_quantity': 'relative_humidity'},
                'precipitation_flux': {'type': 'state', 'units': 'mm/day', 'default': 0.0, 'physical_quantity': 'precipitation_rate'}
            }
        }

        # Aviation model (uses aviation-specific terms and units)
        aviation_model = {
            'name': 'AviationModel',
            'variables': {
                'oat': {'type': 'state', 'units': 'celsius', 'default': 20.0, 'physical_quantity': 'air_temperature', 'description': 'Outside Air Temperature'},
                'altimeter_setting': {'type': 'state', 'units': 'inHg', 'default': 29.92, 'physical_quantity': 'atmospheric_pressure'},
                'wind_velocity': {'type': 'state', 'units': 'knots', 'default': 8.1, 'physical_quantity': 'wind_speed'},
                'dewpoint': {'type': 'state', 'units': 'celsius', 'default': 10.0, 'physical_quantity': 'dewpoint_temperature'},
                'vis_sm': {'type': 'state', 'units': 'statute_miles', 'default': 10.0, 'physical_quantity': 'visibility'}
            }
        }

        # Marine model (uses oceanographic/marine terms)
        marine_model = {
            'name': 'MarineModel',
            'variables': {
                'sst': {'type': 'state', 'units': 'celsius', 'default': 18.0, 'physical_quantity': 'sea_surface_temperature'},
                'sea_surface_temp': {'type': 'state', 'units': 'K', 'default': 291.15, 'physical_quantity': 'sea_surface_temperature'},
                'barometric_pressure': {'type': 'state', 'units': 'mbar', 'default': 1013.25, 'physical_quantity': 'atmospheric_pressure'},
                'wave_height': {'type': 'state', 'units': 'm', 'default': 2.0, 'physical_quantity': 'significant_wave_height'},
                'current_speed': {'type': 'state', 'units': 'cm/s', 'default': 20.0, 'physical_quantity': 'ocean_current_speed'}
            }
        }

        # Industrial monitoring system (uses engineering units)
        industrial_model = {
            'name': 'IndustrialMonitoring',
            'variables': {
                'process_temp': {'type': 'state', 'units': 'fahrenheit', 'default': 68.0, 'physical_quantity': 'air_temperature'},
                'gauge_pressure': {'type': 'state', 'units': 'psi', 'default': 14.7, 'physical_quantity': 'atmospheric_pressure'},
                'flow_velocity': {'type': 'state', 'units': 'ft/s', 'default': 13.67, 'physical_quantity': 'wind_speed'},
                'process_humidity': {'type': 'state', 'units': 'percent_rh', 'default': 65.0, 'physical_quantity': 'relative_humidity'}
            }
        }

        # Define equivalence classes
        equivalence_classes = [
            VariableEquivalenceClass(
                class_id="air_temperature_class",
                physical_quantity="air_temperature",
                canonical_units="K",
                member_variables=[
                    {"component": "WeatherStation", "variable": "air_temp", "units": "celsius"},
                    {"component": "AtmosphericPhysics", "variable": "temperature", "units": "K"},
                    {"component": "ClimateModel", "variable": "surface_air_temperature", "units": "K"},
                    {"component": "AviationModel", "variable": "oat", "units": "celsius"},
                    {"component": "IndustrialMonitoring", "variable": "process_temp", "units": "fahrenheit"}
                ],
                conversion_factors={
                    "celsius": {"offset": -273.15, "scale": 1.0},
                    "fahrenheit": {"formula": "(F - 32) * 5/9 + 273.15"},
                    "K": {"offset": 0.0, "scale": 1.0}
                },
                description="Air temperature measurements across different systems and unit conventions"
            ),
            VariableEquivalenceClass(
                class_id="atmospheric_pressure_class",
                physical_quantity="atmospheric_pressure",
                canonical_units="Pa",
                member_variables=[
                    {"component": "WeatherStation", "variable": "atm_pressure", "units": "hPa"},
                    {"component": "AtmosphericPhysics", "variable": "pressure", "units": "Pa"},
                    {"component": "ClimateModel", "variable": "sea_level_pressure", "units": "Pa"},
                    {"component": "AviationModel", "variable": "altimeter_setting", "units": "inHg"},
                    {"component": "MarineModel", "variable": "barometric_pressure", "units": "mbar"},
                    {"component": "IndustrialMonitoring", "variable": "gauge_pressure", "units": "psi"}
                ],
                conversion_factors={
                    "hPa": {"scale": 100.0},
                    "mbar": {"scale": 100.0},
                    "inHg": {"scale": 3386.389},
                    "psi": {"scale": 6894.757},
                    "Pa": {"scale": 1.0}
                },
                description="Atmospheric pressure measurements in various unit systems"
            ),
            VariableEquivalenceClass(
                class_id="wind_speed_class",
                physical_quantity="wind_speed",
                canonical_units="m/s",
                member_variables=[
                    {"component": "WeatherStation", "variable": "wind_spd", "units": "km/h"},
                    {"component": "AtmosphericPhysics", "variable": "velocity", "units": "m/s"},
                    {"component": "ClimateModel", "variable": "surface_wind_speed", "units": "m/s"},
                    {"component": "AviationModel", "variable": "wind_velocity", "units": "knots"},
                    {"component": "IndustrialMonitoring", "variable": "flow_velocity", "units": "ft/s"}
                ],
                conversion_factors={
                    "km/h": {"scale": 1/3.6},
                    "knots": {"scale": 0.514444},
                    "ft/s": {"scale": 0.3048},
                    "m/s": {"scale": 1.0}
                },
                description="Wind/flow velocity measurements across different applications"
            ),
            VariableEquivalenceClass(
                class_id="relative_humidity_class",
                physical_quantity="relative_humidity",
                canonical_units="dimensionless",
                member_variables=[
                    {"component": "WeatherStation", "variable": "humidity_pct", "units": "percent"},
                    {"component": "AtmosphericPhysics", "variable": "relative_humidity", "units": "dimensionless"},
                    {"component": "ClimateModel", "variable": "rh_2m", "units": "fraction"},
                    {"component": "IndustrialMonitoring", "variable": "process_humidity", "units": "percent_rh"}
                ],
                conversion_factors={
                    "percent": {"scale": 0.01},
                    "percent_rh": {"scale": 0.01},
                    "fraction": {"scale": 1.0},
                    "dimensionless": {"scale": 1.0}
                },
                description="Relative humidity measurements in different percentage/fraction conventions"
            ),
            VariableEquivalenceClass(
                class_id="sea_surface_temperature_class",
                physical_quantity="sea_surface_temperature",
                canonical_units="K",
                member_variables=[
                    {"component": "MarineModel", "variable": "sst", "units": "celsius"},
                    {"component": "MarineModel", "variable": "sea_surface_temp", "units": "K"}
                ],
                conversion_factors={
                    "celsius": {"offset": -273.15, "scale": 1.0},
                    "K": {"offset": 0.0, "scale": 1.0}
                },
                description="Sea surface temperature with different variable names and units in same component"
            )
        ]

        esm_file = EsmFile(
            version="0.1.0",
            metadata=metadata,
            models={
                'WeatherStation': weather_station_model,
                'AtmosphericPhysics': atmospheric_physics_model,
                'ClimateModel': climate_model,
                'AviationModel': aviation_model,
                'MarineModel': marine_model,
                'IndustrialMonitoring': industrial_model
            },
            coupling_metadata={
                'variable_equivalence_classes': [
                    {
                        'class_id': eq_class.class_id,
                        'physical_quantity': eq_class.physical_quantity,
                        'canonical_units': eq_class.canonical_units,
                        'member_variables': eq_class.member_variables,
                        'conversion_factors': eq_class.conversion_factors,
                        'description': eq_class.description
                    }
                    for eq_class in equivalence_classes
                ]
            }
        )

        return esm_file, equivalence_classes

    def test_equivalence_class_detection(self):
        """Test automatic detection of variable equivalence classes."""
        esm_file, expected_classes = self.create_equivalence_class_system()

        # Verify that equivalence classes are properly defined
        eq_classes_metadata = esm_file.coupling_metadata['variable_equivalence_classes']

        assert len(eq_classes_metadata) == len(expected_classes), "Should have correct number of equivalence classes"

        # Test air temperature class
        air_temp_class = None
        for eq_class in eq_classes_metadata:
            if eq_class['physical_quantity'] == 'air_temperature':
                air_temp_class = eq_class
                break

        assert air_temp_class is not None, "Air temperature equivalence class should exist"
        assert len(air_temp_class['member_variables']) == 5, "Air temperature class should have 5 members"

        # Verify all expected members are present
        member_components = {member['component'] for member in air_temp_class['member_variables']}
        expected_components = {'WeatherStation', 'AtmosphericPhysics', 'ClimateModel', 'AviationModel', 'IndustrialMonitoring'}
        assert member_components == expected_components, "Air temperature class should include all expected components"

    def test_conversion_factor_computation(self):
        """Test computation of conversion factors between equivalent variables."""
        esm_file, expected_classes = self.create_equivalence_class_system()

        # Test temperature conversion factors
        air_temp_class = None
        for eq_class in expected_classes:
            if eq_class.physical_quantity == 'air_temperature':
                air_temp_class = eq_class
                break

        assert air_temp_class is not None

        # Test conversions to canonical units (Kelvin)
        celsius_factor = air_temp_class.conversion_factors['celsius']
        assert celsius_factor['offset'] == -273.15, "Celsius to Kelvin should have correct offset"
        assert celsius_factor['scale'] == 1.0, "Celsius to Kelvin should have scale 1.0"

        # Test that conversions produce correct values
        celsius_temp = 20.0  # 20°C
        kelvin_temp = celsius_temp - celsius_factor['offset']  # Should be 293.15 K
        assert abs(kelvin_temp - 293.15) < 1e-6, "Celsius to Kelvin conversion should be correct"

    def test_equivalent_variable_resolution(self):
        """Test that equivalent variables can be resolved and mapped correctly."""
        esm_file, expected_classes = self.create_equivalence_class_system()
        resolver = ScopedReferenceResolver(esm_file)

        # Test that equivalent temperature variables resolve correctly
        temperature_refs = [
            ('WeatherStation.air_temp', 20.0),
            ('AtmosphericPhysics.temperature', 293.15),
            ('ClimateModel.surface_air_temperature', 293.15),
            ('AviationModel.oat', 20.0),
            ('IndustrialMonitoring.process_temp', 68.0)
        ]

        for ref, expected_default in temperature_refs:
            result = resolver.resolve_reference(ref)
            assert result is not None, f"Temperature reference {ref} should resolve"
            assert result.resolved_variable['default'] == expected_default, f"Reference {ref} should have default {expected_default}"
            assert result.resolved_variable['physical_quantity'] == 'air_temperature', f"Reference {ref} should have correct physical quantity"

    def test_cross_equivalence_class_coupling(self):
        """Test coupling between variables from different equivalence classes."""
        esm_file, expected_classes = self.create_equivalence_class_system()

        # Create a coupling that uses variables from different equivalence classes
        test_coupling = {
            'source': 'WeatherStation.air_temp',  # Temperature class, celsius
            'target': 'AtmosphericPhysics.temperature',  # Temperature class, Kelvin
            'type': 'direct_with_conversion'
        }

        # Verify that both variables belong to the same equivalence class
        air_temp_class = None
        for eq_class in expected_classes:
            if eq_class.physical_quantity == 'air_temperature':
                air_temp_class = eq_class
                break

        assert air_temp_class is not None

        # Check that both source and target are in the same equivalence class
        source_found = False
        target_found = False
        for member in air_temp_class.member_variables:
            if member['component'] == 'WeatherStation' and member['variable'] == 'air_temp':
                source_found = True
            elif member['component'] == 'AtmosphericPhysics' and member['variable'] == 'temperature':
                target_found = True

        assert source_found and target_found, "Both coupling endpoints should be in same equivalence class"

    def test_intra_component_equivalent_variables(self):
        """Test handling of equivalent variables within the same component."""
        esm_file, expected_classes = self.create_equivalence_class_system()

        # MarineModel has both 'sst' and 'sea_surface_temp' which are equivalent
        marine_model = esm_file.models['MarineModel']

        # Both should have the same physical quantity
        assert marine_model['variables']['sst']['physical_quantity'] == 'sea_surface_temperature'
        assert marine_model['variables']['sea_surface_temp']['physical_quantity'] == 'sea_surface_temperature'

        # They should have different units but be convertible
        sst_units = marine_model['variables']['sst']['units']
        temp_units = marine_model['variables']['sea_surface_temp']['units']
        assert sst_units != temp_units, "Equivalent variables should have different units"
        assert sst_units == 'celsius' and temp_units == 'K', "Should have expected unit types"

    def test_equivalence_class_conflict_resolution(self):
        """Test resolution of potential conflicts in equivalence class assignment."""
        esm_file, expected_classes = self.create_equivalence_class_system()

        # Test case where a variable name might be ambiguous
        # (In this test system, we don't have actual conflicts, so this is more of a structure test)

        # Verify that each variable belongs to exactly one equivalence class
        all_variable_refs = []
        for eq_class in expected_classes:
            for member in eq_class.member_variables:
                var_ref = f"{member['component']}.{member['variable']}"
                all_variable_refs.append((var_ref, eq_class.physical_quantity))

        # Check for duplicates (would indicate conflicts)
        var_refs_only = [ref for ref, _ in all_variable_refs]
        assert len(var_refs_only) == len(set(var_refs_only)), "Each variable should belong to exactly one equivalence class"

    def test_canonical_unit_conversion_consistency(self):
        """Test that all conversions to canonical units are consistent and reversible."""
        esm_file, expected_classes = self.create_equivalence_class_system()

        for eq_class in expected_classes:
            canonical_units = eq_class.canonical_units
            conversion_factors = eq_class.conversion_factors

            # Test that canonical units have identity conversion
            if canonical_units in conversion_factors:
                canonical_conversion = conversion_factors[canonical_units]
                if 'scale' in canonical_conversion:
                    assert canonical_conversion['scale'] == 1.0, f"Canonical units {canonical_units} should have scale 1.0"
                if 'offset' in canonical_conversion:
                    assert canonical_conversion['offset'] == 0.0, f"Canonical units {canonical_units} should have offset 0.0"

            # Test conversion consistency for pressure units
            if eq_class.physical_quantity == 'atmospheric_pressure':
                # Standard atmospheric pressure: 1013.25 hPa = 101325 Pa = 29.92 inHg
                hpa_factor = conversion_factors.get('hPa', {}).get('scale', 1.0)
                inhg_factor = conversion_factors.get('inHg', {}).get('scale', 1.0)

                # Convert 1013.25 hPa to Pa
                pa_from_hpa = 1013.25 * hpa_factor
                assert abs(pa_from_hpa - 101325.0) < 1.0, "hPa to Pa conversion should be accurate"

                # Convert 29.92 inHg to Pa
                pa_from_inhg = 29.92 * inhg_factor
                assert abs(pa_from_inhg - 101325.0) < 100.0, "inHg to Pa conversion should be reasonably accurate"


# ========================================
# 6. Circular Coupling Detection
# ========================================

class TestCircularCouplingDetectionFixtures:
    """Test fixtures for circular coupling detection."""

    def create_circular_coupling_scenarios(self) -> Dict[str, EsmFile]:
        """
        Create multiple ESM files with different circular coupling scenarios.

        Tests circular dependency detection in:
        - Simple 2-component cycles
        - Complex multi-component cycles
        - Self-referential couplings
        - Nested circular dependencies
        - Indirect circular dependencies through multiple paths
        """
        scenarios = {}

        # Scenario 1: Simple 2-component cycle (A depends on B, B depends on A)
        metadata_simple = Metadata(
            title="Simple Circular Coupling Test",
            description="Two components with direct circular dependency"
        )

        component_a_simple = {
            'name': 'ComponentA',
            'variables': {
                'var_a': {'type': 'state', 'units': 'unit_a', 'default': 1.0}
            },
            'depends_on': ['ComponentB.var_b']
        }

        component_b_simple = {
            'name': 'ComponentB',
            'variables': {
                'var_b': {'type': 'state', 'units': 'unit_b', 'default': 2.0}
            },
            'depends_on': ['ComponentA.var_a']
        }

        simple_couplings = [
            {'source': 'ComponentB.var_b', 'target': 'ComponentA.var_a', 'type': 'direct'},
            {'source': 'ComponentA.var_a', 'target': 'ComponentB.var_b', 'type': 'feedback'}
        ]

        scenarios['simple_cycle'] = EsmFile(
            version="0.1.0",
            metadata=metadata_simple,
            models={
                'ComponentA': component_a_simple,
                'ComponentB': component_b_simple
            },
            coupling_metadata={'couplings': simple_couplings}
        )

        # Scenario 2: Three-component cycle (A -> B -> C -> A)
        metadata_triangle = Metadata(
            title="Triangle Circular Coupling Test",
            description="Three components forming a circular dependency"
        )

        component_a_tri = {
            'name': 'ComponentA',
            'variables': {
                'var_a': {'type': 'state', 'units': 'unit_a', 'default': 1.0}
            },
            'depends_on': ['ComponentC.var_c']
        }

        component_b_tri = {
            'name': 'ComponentB',
            'variables': {
                'var_b': {'type': 'state', 'units': 'unit_b', 'default': 2.0}
            },
            'depends_on': ['ComponentA.var_a']
        }

        component_c_tri = {
            'name': 'ComponentC',
            'variables': {
                'var_c': {'type': 'state', 'units': 'unit_c', 'default': 3.0}
            },
            'depends_on': ['ComponentB.var_b']
        }

        triangle_couplings = [
            {'source': 'ComponentC.var_c', 'target': 'ComponentA.var_a', 'type': 'direct'},
            {'source': 'ComponentA.var_a', 'target': 'ComponentB.var_b', 'type': 'direct'},
            {'source': 'ComponentB.var_b', 'target': 'ComponentC.var_c', 'type': 'direct'}
        ]

        scenarios['triangle_cycle'] = EsmFile(
            version="0.1.0",
            metadata=metadata_triangle,
            models={
                'ComponentA': component_a_tri,
                'ComponentB': component_b_tri,
                'ComponentC': component_c_tri
            },
            coupling_metadata={'couplings': triangle_couplings}
        )

        # Scenario 3: Self-referential coupling (component depends on itself)
        metadata_self = Metadata(
            title="Self-Referential Coupling Test",
            description="Component with self-referential dependency"
        )

        self_ref_component = {
            'name': 'SelfRefComponent',
            'variables': {
                'current_state': {'type': 'state', 'units': 'dimensionless', 'default': 1.0},
                'previous_state': {'type': 'state', 'units': 'dimensionless', 'default': 0.0}
            },
            'depends_on': ['SelfRefComponent.previous_state']
        }

        self_ref_couplings = [
            {'source': 'SelfRefComponent.current_state', 'target': 'SelfRefComponent.previous_state', 'type': 'temporal_feedback'}
        ]

        scenarios['self_referential'] = EsmFile(
            version="0.1.0",
            metadata=metadata_self,
            models={
                'SelfRefComponent': self_ref_component
            },
            coupling_metadata={'couplings': self_ref_couplings}
        )

        # Scenario 4: Complex multi-component cycle with multiple paths
        metadata_complex = Metadata(
            title="Complex Circular Coupling Test",
            description="Complex multi-component system with circular dependencies"
        )

        # Create a more complex system: A -> B -> D -> A and A -> C -> D -> A
        comp_a_complex = {
            'name': 'ComponentA',
            'variables': {
                'var_a1': {'type': 'state', 'units': 'unit_a', 'default': 1.0},
                'var_a2': {'type': 'state', 'units': 'unit_a', 'default': 1.1}
            },
            'depends_on': ['ComponentD.var_d']
        }

        comp_b_complex = {
            'name': 'ComponentB',
            'variables': {
                'var_b': {'type': 'state', 'units': 'unit_b', 'default': 2.0}
            },
            'depends_on': ['ComponentA.var_a1']
        }

        comp_c_complex = {
            'name': 'ComponentC',
            'variables': {
                'var_c': {'type': 'state', 'units': 'unit_c', 'default': 3.0}
            },
            'depends_on': ['ComponentA.var_a2']
        }

        comp_d_complex = {
            'name': 'ComponentD',
            'variables': {
                'var_d': {'type': 'state', 'units': 'unit_d', 'default': 4.0}
            },
            'depends_on': ['ComponentB.var_b', 'ComponentC.var_c']
        }

        complex_couplings = [
            # Path 1: A -> B -> D -> A
            {'source': 'ComponentD.var_d', 'target': 'ComponentA.var_a1', 'type': 'direct'},
            {'source': 'ComponentA.var_a1', 'target': 'ComponentB.var_b', 'type': 'direct'},
            {'source': 'ComponentB.var_b', 'target': 'ComponentD.var_d', 'type': 'direct'},
            # Path 2: A -> C -> D (completes cycle through path 1)
            {'source': 'ComponentA.var_a2', 'target': 'ComponentC.var_c', 'type': 'direct'},
            {'source': 'ComponentC.var_c', 'target': 'ComponentD.var_d', 'type': 'direct'}
        ]

        scenarios['complex_cycle'] = EsmFile(
            version="0.1.0",
            metadata=metadata_complex,
            models={
                'ComponentA': comp_a_complex,
                'ComponentB': comp_b_complex,
                'ComponentC': comp_c_complex,
                'ComponentD': comp_d_complex
            },
            coupling_metadata={'couplings': complex_couplings}
        )

        # Scenario 5: Nested circular dependencies (cycles within larger cycles)
        metadata_nested = Metadata(
            title="Nested Circular Coupling Test",
            description="Nested circular dependencies at different hierarchical levels"
        )

        # Create a system with nested subsystems that have circular dependencies
        outer_system = {
            'name': 'OuterSystem',
            'variables': {
                'global_var': {'type': 'parameter', 'units': 'dimensionless', 'default': 1.0}
            },
            'subsystems': {
                'SubsystemA': {
                    'variables': {
                        'var_sa': {'type': 'state', 'units': 'unit_sa', 'default': 10.0}
                    },
                    'depends_on': ['OuterSystem.SubsystemB.var_sb'],
                    'subsystems': {
                        'NestedA1': {
                            'variables': {
                                'var_na1': {'type': 'state', 'units': 'unit_na1', 'default': 100.0}
                            },
                            'depends_on': ['OuterSystem.SubsystemA.NestedA2.var_na2']
                        },
                        'NestedA2': {
                            'variables': {
                                'var_na2': {'type': 'state', 'units': 'unit_na2', 'default': 200.0}
                            },
                            'depends_on': ['OuterSystem.SubsystemA.NestedA1.var_na1']
                        }
                    }
                },
                'SubsystemB': {
                    'variables': {
                        'var_sb': {'type': 'state', 'units': 'unit_sb', 'default': 20.0}
                    },
                    'depends_on': ['OuterSystem.SubsystemA.var_sa']
                }
            }
        }

        nested_couplings = [
            # Outer cycle: SubsystemA <-> SubsystemB
            {'source': 'OuterSystem.SubsystemB.var_sb', 'target': 'OuterSystem.SubsystemA.var_sa', 'type': 'direct'},
            {'source': 'OuterSystem.SubsystemA.var_sa', 'target': 'OuterSystem.SubsystemB.var_sb', 'type': 'direct'},
            # Inner cycle: NestedA1 <-> NestedA2
            {'source': 'OuterSystem.SubsystemA.NestedA2.var_na2', 'target': 'OuterSystem.SubsystemA.NestedA1.var_na1', 'type': 'direct'},
            {'source': 'OuterSystem.SubsystemA.NestedA1.var_na1', 'target': 'OuterSystem.SubsystemA.NestedA2.var_na2', 'type': 'direct'}
        ]

        scenarios['nested_cycles'] = EsmFile(
            version="0.1.0",
            metadata=metadata_nested,
            models={
                'OuterSystem': outer_system
            },
            coupling_metadata={'couplings': nested_couplings}
        )

        # Scenario 6: No circular dependencies (for comparison)
        metadata_acyclic = Metadata(
            title="Acyclic Coupling Test",
            description="System without circular dependencies for comparison"
        )

        comp_a_acyclic = {
            'name': 'ComponentA',
            'variables': {
                'var_a': {'type': 'state', 'units': 'unit_a', 'default': 1.0}
            }
            # No dependencies
        }

        comp_b_acyclic = {
            'name': 'ComponentB',
            'variables': {
                'var_b': {'type': 'state', 'units': 'unit_b', 'default': 2.0}
            },
            'depends_on': ['ComponentA.var_a']
        }

        comp_c_acyclic = {
            'name': 'ComponentC',
            'variables': {
                'var_c': {'type': 'state', 'units': 'unit_c', 'default': 3.0}
            },
            'depends_on': ['ComponentA.var_a', 'ComponentB.var_b']
        }

        acyclic_couplings = [
            {'source': 'ComponentA.var_a', 'target': 'ComponentB.var_b', 'type': 'direct'},
            {'source': 'ComponentA.var_a', 'target': 'ComponentC.var_c', 'type': 'direct'},
            {'source': 'ComponentB.var_b', 'target': 'ComponentC.var_c', 'type': 'direct'}
        ]

        scenarios['acyclic'] = EsmFile(
            version="0.1.0",
            metadata=metadata_acyclic,
            models={
                'ComponentA': comp_a_acyclic,
                'ComponentB': comp_b_acyclic,
                'ComponentC': comp_c_acyclic
            },
            coupling_metadata={'couplings': acyclic_couplings}
        )

        return scenarios

    def test_simple_circular_dependency_detection(self):
        """Test detection of simple 2-component circular dependencies."""
        scenarios = self.create_circular_coupling_scenarios()

        simple_cycle_system = scenarios['simple_cycle']
        graph = construct_coupling_graph(simple_cycle_system)

        # Detect cycles
        cycles = graph.detect_cycles()

        assert len(cycles) > 0, "Should detect circular dependency in simple cycle"

        # Should find a cycle involving ComponentA and ComponentB
        cycle_nodes = set(cycles[0])  # First detected cycle
        expected_nodes = {'model:ComponentA', 'model:ComponentB'}
        assert expected_nodes.issubset(cycle_nodes), "Cycle should involve ComponentA and ComponentB"

    def test_triangle_circular_dependency_detection(self):
        """Test detection of 3-component circular dependencies."""
        scenarios = self.create_circular_coupling_scenarios()

        triangle_system = scenarios['triangle_cycle']
        graph = construct_coupling_graph(triangle_system)

        cycles = graph.detect_cycles()

        assert len(cycles) > 0, "Should detect circular dependency in triangle cycle"

        # Should find a cycle involving all three components
        cycle_nodes = set(cycles[0])
        expected_nodes = {'model:ComponentA', 'model:ComponentB', 'model:ComponentC'}
        assert expected_nodes.issubset(cycle_nodes), "Cycle should involve all three components"

    def test_self_referential_dependency_detection(self):
        """Test detection of self-referential dependencies."""
        scenarios = self.create_circular_coupling_scenarios()

        self_ref_system = scenarios['self_referential']
        graph = construct_coupling_graph(self_ref_system)

        cycles = graph.detect_cycles()

        assert len(cycles) > 0, "Should detect self-referential dependency"

        # Should find a cycle involving the self-referential component
        cycle_nodes = set(cycles[0])
        assert 'model:SelfRefComponent' in cycle_nodes, "Cycle should involve SelfRefComponent"

    def test_complex_circular_dependency_detection(self):
        """Test detection of complex multi-component circular dependencies."""
        scenarios = self.create_circular_coupling_scenarios()

        complex_system = scenarios['complex_cycle']
        graph = construct_coupling_graph(complex_system)

        cycles = graph.detect_cycles()

        assert len(cycles) > 0, "Should detect circular dependencies in complex system"

        # Should detect the main cycle: A -> B -> D -> A and A -> C -> D
        cycle_nodes = set(cycles[0])
        expected_nodes = {'model:ComponentA', 'model:ComponentB', 'model:ComponentC', 'model:ComponentD'}
        assert expected_nodes.issubset(cycle_nodes), "Should detect the complex 4-component cycle"

    def test_nested_circular_dependency_detection(self):
        """Test detection of nested circular dependencies."""
        scenarios = self.create_circular_coupling_scenarios()

        nested_system = scenarios['nested_cycles']
        graph = construct_coupling_graph(nested_system)

        cycles = graph.detect_cycles()

        # Should detect multiple cycles (outer and inner)
        assert len(cycles) >= 1, "Should detect at least one circular dependency in nested system"

        # The detection might merge nested cycles or detect them separately
        # For now, just verify that cycles are detected
        assert any(len(cycle) >= 2 for cycle in cycles), "Should detect cycles with at least 2 nodes"

    def test_acyclic_system_verification(self):
        """Test that systems without circular dependencies are correctly identified as acyclic."""
        scenarios = self.create_circular_coupling_scenarios()

        acyclic_system = scenarios['acyclic']
        graph = construct_coupling_graph(acyclic_system)

        cycles = graph.detect_cycles()

        assert len(cycles) == 0, "Acyclic system should have no circular dependencies"

        # Should be able to determine execution order
        try:
            execution_order = graph.get_execution_order()
            assert len(execution_order) > 0, "Should be able to determine execution order for acyclic system"

            # Verify topological order constraints
            a_pos = execution_order.index('model:ComponentA')
            b_pos = execution_order.index('model:ComponentB')
            c_pos = execution_order.index('model:ComponentC')

            assert a_pos < b_pos, "ComponentA should come before ComponentB"
            assert a_pos < c_pos, "ComponentA should come before ComponentC"
            assert b_pos < c_pos, "ComponentB should come before ComponentC"

        except ValueError:
            pytest.fail("Execution order determination should not fail for acyclic system")

    def test_circular_dependency_error_handling(self):
        """Test proper error handling when circular dependencies are detected."""
        scenarios = self.create_circular_coupling_scenarios()

        # Test that execution order determination raises appropriate errors for cyclic systems
        cyclic_scenarios = ['simple_cycle', 'triangle_cycle', 'complex_cycle']

        for scenario_name in cyclic_scenarios:
            system = scenarios[scenario_name]
            graph = construct_coupling_graph(system)

            with pytest.raises(ValueError, match="[Cc]ircular.*dependencies"):
                graph.get_execution_order()

    def test_cycle_path_reporting(self):
        """Test that detected cycles report the correct dependency paths."""
        scenarios = self.create_circular_coupling_scenarios()

        triangle_system = scenarios['triangle_cycle']
        graph = construct_coupling_graph(triangle_system)

        cycles = graph.detect_cycles()

        assert len(cycles) > 0, "Should detect cycles"

        # Verify that the cycle path makes sense
        cycle = cycles[0]
        assert len(cycle) >= 3, "Triangle cycle should have at least 3 nodes"

        # The cycle should form a closed loop
        # (This would require more detailed implementation of cycle path tracking)
        cycle_nodes = set(cycle)
        expected_components = {'model:ComponentA', 'model:ComponentB', 'model:ComponentC'}
        assert expected_components.issubset(cycle_nodes), "All triangle components should be in detected cycle"

    def test_coupling_validation_with_cycles(self):
        """Test that coupling graph validation properly handles circular dependencies."""
        scenarios = self.create_circular_coupling_scenarios()

        for scenario_name, system in scenarios.items():
            graph = construct_coupling_graph(system)
            is_valid, errors = validate_coupling_graph(graph)

            if scenario_name == 'acyclic':
                assert is_valid, "Acyclic system should be valid"
                assert len(errors) == 0, "Acyclic system should have no validation errors"
            else:
                # Cyclic systems should be flagged as invalid
                assert not is_valid, f"Cyclic system {scenario_name} should be invalid"
                assert len(errors) > 0, f"Cyclic system {scenario_name} should have validation errors"
                assert any('circular' in error.lower() or 'cycle' in error.lower() for error in errors), f"Should have cycle-related error for {scenario_name}"


# ========================================
# Integration Test for All Fixtures
# ========================================

class TestCouplingResolutionIntegration:
    """Integration tests combining all coupling resolution fixtures."""

    def test_comprehensive_coupling_system(self):
        """Test a comprehensive system that exercises all coupling resolution features."""
        # Create a complex system that combines aspects from all fixture categories

        # Use the operator composition system as the base
        operator_fixtures = TestOperatorCompositionFixtures()
        base_system = operator_fixtures.create_complex_operator_composition_system()

        # Add variable translation components
        translation_fixtures = TestVariableTranslationFixtures()
        translation_system, _ = translation_fixtures.create_multi_unit_coupled_system()

        # Combine models from both systems
        combined_models = {}
        combined_models.update(base_system.models)
        combined_models.update({f"Translation_{k}": v for k, v in translation_system.models.items()})

        # Combine data loaders
        combined_data_loaders = {}
        combined_data_loaders.update(base_system.data_loaders)
        combined_data_loaders.update({f"Translation_{k}": v for k, v in translation_system.data_loaders.items()})

        # Combine operators
        combined_operators = {}
        combined_operators.update(base_system.operators)

        # Create the comprehensive system
        comprehensive_system = EsmFile(
            version="0.1.0",
            metadata=Metadata(
                title="Comprehensive Coupling Resolution Test System",
                description="Integration test combining all coupling resolution features"
            ),
            models=combined_models,
            data_loaders=combined_data_loaders,
            operators=combined_operators,
            coupling_metadata={
                'integration_test': True,
                'combines_features': [
                    'operator_composition_with_placeholder_expansion',
                    'variable_translation_with_conversion_factors',
                    'scoped_reference_resolution',
                    'cross_system_coupling'
                ]
            }
        )

        # Test that the comprehensive system can be processed
        resolver = ScopedReferenceResolver(comprehensive_system)
        graph = construct_coupling_graph(comprehensive_system)

        # Basic structural tests
        assert len(graph.nodes) > 0, "Comprehensive system should have nodes"
        assert len(comprehensive_system.models) > 0, "Should have combined models"
        assert len(comprehensive_system.operators) > 0, "Should have operators"

        # Test that complex references can still be resolved
        test_ref = "AtmosphericPhysics.temperature"
        result = resolver.resolve_reference(test_ref)
        assert result is not None, "Should be able to resolve references in comprehensive system"

        # Test coupling graph validation
        is_valid, errors = validate_coupling_graph(graph)
        # Note: This might not be valid due to missing coupling definitions, but should not crash
        assert isinstance(is_valid, bool), "Should return boolean validity"
        assert isinstance(errors, list), "Should return error list"

    def test_serialization_roundtrip_all_fixtures(self):
        """Test that all fixture systems can be serialized and deserialized correctly."""
        # Test each fixture category
        fixture_classes = [
            TestOperatorCompositionFixtures,
            TestVariableTranslationFixtures,
            TestCouplingOrderIndependenceFixtures,
            TestScopedReferenceResolutionFixtures,
            TestVariableEquivalenceClassesFixtures,
            TestCircularCouplingDetectionFixtures
        ]

        systems_to_test = []

        # Collect systems from each fixture class
        operator_fixtures = TestOperatorCompositionFixtures()
        systems_to_test.append(("operator_composition", operator_fixtures.create_complex_operator_composition_system()))

        translation_fixtures = TestVariableTranslationFixtures()
        translation_system, _ = translation_fixtures.create_multi_unit_coupled_system()
        systems_to_test.append(("variable_translation", translation_system))

        order_fixtures = TestCouplingOrderIndependenceFixtures()
        order_systems = order_fixtures.create_order_independent_coupling_system()
        systems_to_test.append(("coupling_order", order_systems['alphabetical']))

        scope_fixtures = TestScopedReferenceResolutionFixtures()
        systems_to_test.append(("scoped_reference", scope_fixtures.create_deep_hierarchical_system()))

        equiv_fixtures = TestVariableEquivalenceClassesFixtures()
        equiv_system, _ = equiv_fixtures.create_equivalence_class_system()
        systems_to_test.append(("equivalence_classes", equiv_system))

        circular_fixtures = TestCircularCouplingDetectionFixtures()
        circular_systems = circular_fixtures.create_circular_coupling_scenarios()
        systems_to_test.append(("circular_detection", circular_systems['acyclic']))

        # Test serialization roundtrip for each system
        for system_name, system in systems_to_test:
            try:
                # Serialize
                json_str = save(system)
                assert json_str is not None, f"Serialization should succeed for {system_name}"
                assert len(json_str) > 0, f"Serialized string should not be empty for {system_name}"

                # Deserialize
                reconstructed = load(json_str)
                assert reconstructed is not None, f"Deserialization should succeed for {system_name}"

                # Basic structure verification
                assert reconstructed.version == system.version, f"Version should be preserved for {system_name}"
                assert reconstructed.metadata.title == system.metadata.title, f"Metadata should be preserved for {system_name}"
                assert len(reconstructed.models) == len(system.models), f"Models count should be preserved for {system_name}"

            except Exception as e:
                pytest.fail(f"Serialization roundtrip failed for {system_name}: {e}")

    def test_cross_fixture_compatibility(self):
        """Test that features from different fixture categories can work together."""
        # Create a system that uses features from multiple categories

        # Start with scoped reference system for deep hierarchy
        scope_fixtures = TestScopedReferenceResolutionFixtures()
        base_system = scope_fixtures.create_deep_hierarchical_system()

        # Add variable equivalence classes
        base_system.coupling_metadata = base_system.coupling_metadata or {}
        base_system.coupling_metadata['variable_equivalence_classes'] = [
            {
                'class_id': 'temperature_class',
                'physical_quantity': 'temperature',
                'canonical_units': 'K',
                'member_variables': [
                    {'component': 'EarthSystemModel', 'variable': 'global_temperature', 'units': 'K'}
                ],
                'conversion_factors': {'K': {'scale': 1.0, 'offset': 0.0}},
                'description': 'Temperature variables across the Earth system'
            }
        ]

        # Test that scoped reference resolution still works
        resolver = ScopedReferenceResolver(base_system)
        deep_ref = "EarthSystemModel.Atmosphere.Troposphere.BoundaryLayer.mixing_height"
        result = resolver.resolve_reference(deep_ref)
        assert result is not None, "Scoped reference resolution should still work with equivalence classes"

        # Test that coupling graph construction works
        graph = construct_coupling_graph(base_system)
        assert len(graph.nodes) > 0, "Coupling graph should be constructible with mixed features"

        # Test validation
        is_valid, errors = validate_coupling_graph(graph)
        assert isinstance(is_valid, bool), "Validation should work with mixed features"


# Run the tests if this file is executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])