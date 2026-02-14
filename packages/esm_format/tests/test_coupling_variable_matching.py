"""Tests for coupling variable matching algorithm."""

import pytest
from esm_format.coupling_graph import (
    match_coupling_variables, validate_coupling_variables,
    VariableMatchResult, CouplingGraph, CouplingNode, CouplingEdge, NodeType
)
from esm_format.types import (
    EsmFile, Model, ReactionSystem, CouplingEntry, CouplingType,
    Metadata, ModelVariable, Species, Parameter
)


class TestVariableMatchResult:
    """Tests for VariableMatchResult dataclass."""

    def test_variable_match_result_creation(self):
        """Test creating a VariableMatchResult."""
        result = VariableMatchResult(
            is_compatible=True,
            source_variable={"name": "temp", "type": "state", "units": "K"},
            target_variable={"name": "temperature", "type": "state", "units": "K"},
            unit_conversion_factor=1.0,
            type_compatibility=True,
            unit_compatibility=True,
            interface_compatibility=True
        )

        assert result.is_compatible
        assert result.source_variable["name"] == "temp"
        assert result.target_variable["name"] == "temperature"
        assert result.unit_conversion_factor == 1.0
        assert result.type_compatibility
        assert result.unit_compatibility
        assert result.interface_compatibility
        assert len(result.errors) == 0
        assert len(result.warnings) == 0


class TestMatchCouplingVariables:
    """Tests for match_coupling_variables function."""

    def test_compatible_model_variables(self):
        """Test matching compatible model variables."""
        # Create source model
        source_model = Model(
            name="AtmosphereModel",
            variables={
                "temperature": ModelVariable(
                    type="state",
                    units="kelvin",
                    description="Air temperature"
                )
            }
        )

        # Create target model
        target_model = Model(
            name="OceanModel",
            variables={
                "sea_surface_temp": ModelVariable(
                    type="state",
                    units="celsius",
                    description="Sea surface temperature"
                )
            }
        )

        result = match_coupling_variables(
            "temperature", "sea_surface_temp",
            source_model, target_model,
            CouplingType.DIRECT
        )

        assert result.is_compatible
        assert result.type_compatibility
        assert result.unit_compatibility  # Should be true even with unit conversion
        assert result.interface_compatibility
        assert result.unit_conversion_factor is not None  # Kelvin to Celsius conversion

    def test_incompatible_type_variables(self):
        """Test matching incompatible variable types."""
        source_model = Model(
            name="Model1",
            variables={
                "param1": ModelVariable(
                    type="parameter",
                    units="dimensionless",
                    description="A parameter"
                )
            }
        )

        # Create reaction system
        target_system = ReactionSystem(
            name="Chemistry",
            species=[
                Species(
                    name="O3",
                    units="mol/m**3",
                    description="Ozone concentration"
                )
            ]
        )

        result = match_coupling_variables(
            "param1", "O3",
            source_model, target_system,
            CouplingType.DIRECT
        )

        assert not result.is_compatible
        assert not result.type_compatibility
        assert len(result.errors) > 0

    def test_unit_conversion_required(self):
        """Test variables requiring unit conversion."""
        source_model = Model(
            name="Model1",
            variables={
                "velocity": ModelVariable(
                    type="state",
                    units="meter/second",
                    description="Wind velocity"
                )
            }
        )

        target_model = Model(
            name="Model2",
            variables={
                "wind_speed": ModelVariable(
                    type="state",
                    units="kilometer/hour",
                    description="Wind speed"
                )
            }
        )

        result = match_coupling_variables(
            "velocity", "wind_speed",
            source_model, target_model,
            CouplingType.DIRECT
        )

        assert result.is_compatible
        assert result.unit_compatibility
        assert result.unit_conversion_factor == pytest.approx(3.6)  # m/s to km/h
        assert len(result.warnings) > 0  # Should warn about unit conversion

    def test_incompatible_units(self):
        """Test variables with incompatible units."""
        source_model = Model(
            name="Model1",
            variables={
                "mass": ModelVariable(
                    type="state",
                    units="kilogram",
                    description="Mass"
                )
            }
        )

        target_model = Model(
            name="Model2",
            variables={
                "length": ModelVariable(
                    type="state",
                    units="meter",
                    description="Length"
                )
            }
        )

        result = match_coupling_variables(
            "mass", "length",
            source_model, target_model,
            CouplingType.DIRECT
        )

        assert not result.is_compatible
        assert not result.unit_compatibility
        assert len(result.errors) > 0

    def test_missing_variables(self):
        """Test error handling for missing variables."""
        source_model = Model(name="Model1", variables={})
        target_model = Model(name="Model2", variables={})

        result = match_coupling_variables(
            "nonexistent", "also_nonexistent",
            source_model, target_model,
            CouplingType.DIRECT
        )

        assert not result.is_compatible
        assert len(result.errors) > 0
        assert "not found" in result.errors[0]

    def test_reaction_system_variables(self):
        """Test matching reaction system variables."""
        # Source reaction system
        source_system = ReactionSystem(
            name="ChemistryA",
            species=[
                Species(
                    name="CO2",
                    formula="CO2",
                    units="mol/liter",
                    description="Carbon dioxide concentration"
                )
            ]
        )

        # Target model
        target_model = Model(
            name="TransportModel",
            variables={
                "co2_conc": ModelVariable(
                    type="state",
                    units="mol/meter**3",
                    description="CO2 concentration"
                )
            }
        )

        result = match_coupling_variables(
            "CO2", "co2_conc",
            source_system, target_model,
            CouplingType.DIRECT
        )

        assert result.is_compatible
        assert result.type_compatibility  # Species to state is allowed
        assert result.unit_compatibility  # mol/L to mol/m³ conversion
        assert result.unit_conversion_factor == pytest.approx(1000.0)  # L to m³

    def test_feedback_coupling_warnings(self):
        """Test that feedback couplings generate appropriate warnings."""
        source_model = Model(
            name="Model1",
            variables={
                "var1": ModelVariable(type="state", units="dimensionless")
            }
        )

        target_model = Model(
            name="Model2",
            variables={
                "var2": ModelVariable(type="state", units="dimensionless")
            }
        )

        result = match_coupling_variables(
            "var1", "var2",
            source_model, target_model,
            CouplingType.FEEDBACK
        )

        assert result.is_compatible
        assert len(result.warnings) > 0
        assert any("feedback" in warning.lower() for warning in result.warnings)

    def test_interpolated_coupling_spatial_warnings(self):
        """Test that interpolated couplings generate spatial domain warnings."""
        source_model = Model(
            name="GridModel",
            variables={
                "grid_var": ModelVariable(
                    type="state",
                    units="pascal",
                    description="Pressure on computational grid"  # Has spatial keyword
                )
            }
        )

        target_model = Model(
            name="PointModel",
            variables={
                "point_var": ModelVariable(
                    type="state",
                    units="pascal",
                    description="Point pressure measurement"  # No spatial keywords
                )
            }
        )

        result = match_coupling_variables(
            "grid_var", "point_var",
            source_model, target_model,
            CouplingType.INTERPOLATED
        )

        assert result.is_compatible
        # Should have warning about missing spatial domain info for target
        spatial_warnings = [w for w in result.warnings if "spatial domain" in w]
        assert len(spatial_warnings) > 0


class TestValidateCouplingVariables:
    """Tests for validate_coupling_variables function."""

    def test_validate_simple_coupling(self):
        """Test validation of a simple valid coupling."""
        # Create ESM file with models
        metadata = Metadata(title="Test ESM")

        model1 = Model(
            name="AtmosphereModel",
            variables={
                "temperature": ModelVariable(
                    type="state",
                    units="kelvin",
                    description="Air temperature"
                )
            }
        )

        model2 = Model(
            name="OceanModel",
            variables={
                "sea_surface_temp": ModelVariable(
                    type="state",
                    units="kelvin",
                    description="Sea surface temperature"
                )
            }
        )

        esm_file = EsmFile(
            version="0.1.0",
            metadata=metadata,
            models=[model1, model2]
        )

        # Create coupling graph
        graph = CouplingGraph()

        node1 = CouplingNode(
            id="model:AtmosphereModel",
            name="AtmosphereModel",
            type=NodeType.MODEL,
            variables=["temperature"]
        )
        node2 = CouplingNode(
            id="model:OceanModel",
            name="OceanModel",
            type=NodeType.MODEL,
            variables=["sea_surface_temp"]
        )

        graph.add_node(node1)
        graph.add_node(node2)

        edge = CouplingEdge(
            source_node="model:AtmosphereModel",
            target_node="model:OceanModel",
            source_variables=["temperature"],
            target_variables=["sea_surface_temp"],
            coupling_type=CouplingType.DIRECT
        )
        graph.add_edge(edge)

        # Validate
        is_valid, errors, detailed_results = validate_coupling_variables(
            graph, esm_file, detailed=True
        )

        assert is_valid
        assert len(errors) == 0
        assert detailed_results is not None
        assert len(detailed_results) == 1
        assert detailed_results[0].is_compatible

    def test_validate_incompatible_coupling(self):
        """Test validation of an incompatible coupling."""
        metadata = Metadata(title="Test ESM")

        model1 = Model(
            name="Model1",
            variables={
                "mass": ModelVariable(
                    type="state",
                    units="kilogram",
                    description="Mass"
                )
            }
        )

        model2 = Model(
            name="Model2",
            variables={
                "temperature": ModelVariable(
                    type="state",
                    units="kelvin",
                    description="Temperature"
                )
            }
        )

        esm_file = EsmFile(
            version="0.1.0",
            metadata=metadata,
            models=[model1, model2]
        )

        # Create coupling graph with incompatible variables
        graph = CouplingGraph()

        node1 = CouplingNode(
            id="model:Model1",
            name="Model1",
            type=NodeType.MODEL,
            variables=["mass"]
        )
        node2 = CouplingNode(
            id="model:Model2",
            name="Model2",
            type=NodeType.MODEL,
            variables=["temperature"]
        )

        graph.add_node(node1)
        graph.add_node(node2)

        edge = CouplingEdge(
            source_node="model:Model1",
            target_node="model:Model2",
            source_variables=["mass"],
            target_variables=["temperature"],
            coupling_type=CouplingType.DIRECT
        )
        graph.add_edge(edge)

        # Validate
        is_valid, errors, detailed_results = validate_coupling_variables(
            graph, esm_file, detailed=True
        )

        assert not is_valid
        assert len(errors) > 0
        assert detailed_results is not None
        assert len(detailed_results) == 1
        assert not detailed_results[0].is_compatible

    def test_validate_missing_component(self):
        """Test validation with missing component references."""
        metadata = Metadata(title="Test ESM")
        esm_file = EsmFile(version="0.1.0", metadata=metadata, models=[])

        # Create coupling graph with non-existent components
        graph = CouplingGraph()

        node1 = CouplingNode(
            id="model:NonExistent1",
            name="NonExistent1",
            type=NodeType.MODEL,
            variables=["var1"]
        )
        node2 = CouplingNode(
            id="model:NonExistent2",
            name="NonExistent2",
            type=NodeType.MODEL,
            variables=["var2"]
        )

        graph.add_node(node1)
        graph.add_node(node2)

        edge = CouplingEdge(
            source_node="model:NonExistent1",
            target_node="model:NonExistent2",
            source_variables=["var1"],
            target_variables=["var2"],
            coupling_type=CouplingType.DIRECT
        )
        graph.add_edge(edge)

        # Validate
        is_valid, errors, detailed_results = validate_coupling_variables(
            graph, esm_file, detailed=False
        )

        assert not is_valid
        assert len(errors) >= 2  # Should have errors for both missing components
        assert detailed_results is None  # detailed=False


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_variables_without_units(self):
        """Test handling of variables without unit specifications."""
        source_model = Model(
            name="Model1",
            variables={
                "dimensionless_var": ModelVariable(
                    type="state",
                    units=None,  # No units specified
                    description="A dimensionless variable"
                )
            }
        )

        target_model = Model(
            name="Model2",
            variables={
                "another_var": ModelVariable(
                    type="state",
                    units=None,  # No units specified
                    description="Another dimensionless variable"
                )
            }
        )

        result = match_coupling_variables(
            "dimensionless_var", "another_var",
            source_model, target_model,
            CouplingType.DIRECT
        )

        # Should be compatible but with warnings
        assert result.is_compatible
        assert len(result.warnings) > 0

    def test_mixed_units_specification(self):
        """Test handling when only one variable has units."""
        source_model = Model(
            name="Model1",
            variables={
                "with_units": ModelVariable(
                    type="state",
                    units="pascal",
                    description="Pressure"
                )
            }
        )

        target_model = Model(
            name="Model2",
            variables={
                "without_units": ModelVariable(
                    type="state",
                    units=None,
                    description="Some variable"
                )
            }
        )

        result = match_coupling_variables(
            "with_units", "without_units",
            source_model, target_model,
            CouplingType.DIRECT
        )

        assert not result.is_compatible
        assert not result.unit_compatibility
        assert len(result.errors) > 0

    def test_unsupported_component_type(self):
        """Test error handling for unsupported component types."""
        # Test with None which should return an error result
        source_model = Model(name="ValidModel", variables={"var": ModelVariable(type="state")})

        result = match_coupling_variables(
            "var", "some_var",
            source_model, None,  # Invalid component type
            CouplingType.DIRECT
        )

        assert not result.is_compatible
        assert len(result.errors) > 0
        assert "Component cannot be None" in result.errors[0]


# Integration test combining the functionality
class TestIntegratedVariableMatching:
    """Integration tests for the complete variable matching workflow."""

    def test_complete_atmospheric_chemistry_coupling(self):
        """Test a complete atmospheric chemistry coupling scenario."""
        # Atmospheric physics model
        atmosphere_model = Model(
            name="AtmospherePhysics",
            variables={
                "temperature": ModelVariable(
                    type="state",
                    units="kelvin",
                    description="Air temperature"
                ),
                "pressure": ModelVariable(
                    type="state",
                    units="pascal",
                    description="Air pressure"
                ),
                "humidity": ModelVariable(
                    type="state",
                    units="kilogram/kilogram",
                    description="Specific humidity"
                )
            }
        )

        # Chemistry reaction system
        chemistry_system = ReactionSystem(
            name="TroposphericChemistry",
            species=[
                Species(
                    name="O3",
                    formula="O3",
                    units="mol/meter**3",
                    description="Ozone concentration"
                ),
                Species(
                    name="NO2",
                    formula="NO2",
                    units="mol/meter**3",
                    description="Nitrogen dioxide concentration"
                )
            ],
            parameters=[
                Parameter(
                    name="k_photo",
                    value=1e-5,
                    units="1/second",
                    description="Photolysis rate constant"
                )
            ]
        )

        # Test multiple variable matchings
        temp_result = match_coupling_variables(
            "temperature", "k_photo",
            atmosphere_model, chemistry_system,
            CouplingType.DIRECT
        )

        # This should fail - temperature (state) to rate constant (parameter) is not generally compatible
        assert not temp_result.is_compatible

        # Test compatible coupling: atmosphere humidity affecting chemistry (indirectly)
        # This would work if we had appropriate variables, but the test demonstrates the concept

        # The algorithm correctly identifies incompatible couplings while allowing reasonable ones
        assert len(temp_result.errors) > 0
        assert not temp_result.type_compatibility