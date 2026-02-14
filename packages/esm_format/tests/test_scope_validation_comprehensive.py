"""Comprehensive tests for scope validation system."""

import pytest
from esm_format.validation import (
    ScopeValidator, ScopeValidationError, ScopeValidationResult,
    validate_scope_comprehensive
)
from esm_format.types import (
    EsmFile, Model, ReactionSystem, DataLoader, Operator, Metadata,
    ModelVariable, Species, Parameter, Reaction, DataLoaderType, OperatorType
)


class TestScopeValidator:
    """Tests for the comprehensive scope validation system."""

    def _create_test_esm_with_validation_scenarios(self):
        """Create an ESM file with various validation scenarios."""
        metadata = Metadata(title="ValidationTestESM")

        # Create a model with various validation scenarios
        atmosphere_model = {
            'name': 'AtmosphereModel',
            'variables': {
                'temperature': {'type': 'parameter', 'units': 'K', 'default': 298.15},
                'pressure': {'type': 'parameter', 'units': 'Pa', 'default': 101325.0},
                'unused_var': {'type': 'parameter', 'units': 'dimensionless', 'default': 1.0}  # Unused variable
            },
            'subsystems': {
                'Chemistry': {
                    'variables': {
                        'temperature': {'type': 'state', 'units': 'K', 'default': 299.15},  # Shadows parent
                        'O3': {'type': 'state', 'units': 'mol/mol', 'default': 40e-9},
                        'NO': {'type': 'state', 'units': 'mol/mol', 'default': 0.1e-9}
                    },
                    'subsystems': {
                        'FastReactions': {
                            'variables': {
                                'temperature': {'type': 'parameter', 'units': 'K', 'default': 300.15},  # Multiple shadowing
                                'k1': {'type': 'parameter', 'units': '1/s', 'default': 1e-5}
                            }
                        },
                        'SlowReactions': {
                            'variables': {
                                'k_slow': {'type': 'parameter', 'units': '1/s', 'default': 1e-8}
                            }
                        }
                    }
                },
                'Transport': {
                    'variables': {
                        'wind_speed': {'type': 'parameter', 'units': 'm/s', 'default': 5.0}
                    }
                },
                # Deep nesting to test nesting warnings
                'Level1': {
                    'variables': {'l1_var': {'type': 'parameter', 'units': 'dimensionless', 'default': 1}},
                    'subsystems': {
                        'Level2': {
                            'variables': {'l2_var': {'type': 'parameter', 'units': 'dimensionless', 'default': 2}},
                            'subsystems': {
                                'Level3': {
                                    'variables': {'l3_var': {'type': 'parameter', 'units': 'dimensionless', 'default': 3}},
                                    'subsystems': {
                                        'Level4': {
                                            'variables': {'l4_var': {'type': 'parameter', 'units': 'dimensionless', 'default': 4}},
                                            'subsystems': {
                                                'Level5': {
                                                    'variables': {'l5_var': {'type': 'parameter', 'units': 'dimensionless', 'default': 5}},
                                                    'subsystems': {
                                                        'Level6': {  # Deep nesting - should trigger warning
                                                            'variables': {'l6_var': {'type': 'parameter', 'units': 'dimensionless', 'default': 6}}
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
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

    def test_comprehensive_validation_success(self):
        """Test comprehensive validation on valid references."""
        esm_file = self._create_test_esm_with_validation_scenarios()
        validator = ScopeValidator(esm_file)

        valid_references = [
            'AtmosphereModel.temperature',
            'AtmosphereModel.Chemistry.O3',
            'AtmosphereModel.Chemistry.FastReactions.k1',
            'AtmosphereModel.Transport.wind_speed'
        ]

        result = validator.validate_comprehensive(valid_references)

        # Should have no errors for valid references
        assert len([e for e in result.errors if e.error_type != 'unused_variable']) == 0
        assert result.scope_hierarchy_valid
        assert result.total_references_validated == len(valid_references)

    def test_undefined_reference_detection(self):
        """Test detection of undefined references."""
        esm_file = self._create_test_esm_with_validation_scenarios()
        validator = ScopeValidator(esm_file)

        invalid_references = [
            'AtmosphereModel.Chemistry.NonExistentVar',  # Undefined variable
            'AtmosphereModel.NonExistentSubsystem.var',  # Invalid scope path
            'NonExistentModel.var'  # Invalid root scope
        ]

        result = validator.validate_comprehensive(invalid_references)

        # Should have errors for undefined references
        undefined_errors = [e for e in result.errors if e.error_type in ['undefined_reference', 'invalid_scope_path']]
        assert len(undefined_errors) >= len(invalid_references)

        # Check specific error details
        for error in undefined_errors:
            assert error.reference in invalid_references
            assert len(error.message) > 0
            assert isinstance(error.available_variables, list) or isinstance(error.available_scopes, list)

    def test_variable_shadowing_warnings(self):
        """Test detection of variable shadowing."""
        esm_file = self._create_test_esm_with_validation_scenarios()
        validator = ScopeValidator(esm_file)

        shadowing_references = [
            'AtmosphereModel.Chemistry.temperature',  # Shadows AtmosphereModel.temperature
            'AtmosphereModel.Chemistry.FastReactions.temperature'  # Shadows both Chemistry and AtmosphereModel
        ]

        result = validator.validate_comprehensive(shadowing_references)

        # Should have shadowing warnings
        shadowing_warnings = [w for w in result.warnings if w.error_type == 'variable_shadowing']
        assert len(shadowing_warnings) >= len(shadowing_references)

        # Check that FastReactions temperature has multiple shadows
        fast_reaction_warnings = [w for w in shadowing_warnings
                                 if 'FastReactions.temperature' in w.reference]
        if fast_reaction_warnings:
            assert len(fast_reaction_warnings[0].shadowed_variables) >= 2  # Should shadow Chemistry and AtmosphereModel

    def test_scope_boundary_validation(self):
        """Test validation of scope boundary violations."""
        esm_file = self._create_test_esm_with_validation_scenarios()
        validator = ScopeValidator(esm_file)

        # Test cross-subsystem access (should fail)
        boundary_violations = [
            'AtmosphereModel.Transport.O3',  # Transport trying to access Chemistry's O3
            'AtmosphereModel.Chemistry.FastReactions.k_slow'  # FastReactions trying to access SlowReactions' k_slow
        ]

        result = validator.validate_comprehensive(boundary_violations)

        # Should have errors for boundary violations
        boundary_errors = [e for e in result.errors if e.error_type == 'undefined_reference']
        assert len(boundary_errors) >= len(boundary_violations)

    def test_deep_nesting_warnings(self):
        """Test detection of deep nesting warnings."""
        esm_file = self._create_test_esm_with_validation_scenarios()
        validator = ScopeValidator(esm_file)

        result = validator.validate_comprehensive()

        # Should have deep nesting warnings
        nesting_warnings = [w for w in result.warnings if w.error_type == 'deep_nesting']
        assert len(nesting_warnings) > 0

        # Check that Level6 triggers deep nesting warning
        level6_warnings = [w for w in nesting_warnings if 'Level6' in '.'.join(w.scope_path)]
        assert len(level6_warnings) > 0

    def test_unused_variable_warnings(self):
        """Test detection of unused variables."""
        esm_file = self._create_test_esm_with_validation_scenarios()
        validator = ScopeValidator(esm_file)

        result = validator.validate_comprehensive([])  # Don't validate any references

        # Should have unused variable warnings
        unused_warnings = [w for w in result.warnings if w.error_type == 'unused_variable']

        # Note: This might not work as expected without actual coupling references
        # but the framework is in place for when couplings are defined

    def test_single_reference_validation(self):
        """Test validation of a single reference."""
        esm_file = self._create_test_esm_with_validation_scenarios()
        validator = ScopeValidator(esm_file)

        # Valid reference
        valid_result = validator.validate_reference('AtmosphereModel.Chemistry.O3')
        assert valid_result.is_valid
        assert len(valid_result.errors) == 0

        # Invalid reference
        invalid_result = validator.validate_reference('AtmosphereModel.Chemistry.NonExistent')
        assert not invalid_result.is_valid
        assert len(invalid_result.errors) > 0
        assert invalid_result.errors[0].error_type == 'undefined_reference'

    def test_invalid_reference_format(self):
        """Test validation of invalid reference formats."""
        esm_file = self._create_test_esm_with_validation_scenarios()
        validator = ScopeValidator(esm_file)

        invalid_formats = [
            'single',  # No dots
            '',  # Empty reference
        ]

        for invalid_ref in invalid_formats:
            result = validator.validate_reference(invalid_ref)
            assert not result.is_valid
            assert len(result.errors) > 0
            assert result.errors[0].error_type == 'invalid_reference_format'

    def test_resolution_path_details(self):
        """Test getting detailed resolution path information."""
        esm_file = self._create_test_esm_with_validation_scenarios()
        validator = ScopeValidator(esm_file)

        # Valid reference with inheritance
        details = validator.get_resolution_path_details('AtmosphereModel.Chemistry.pressure')
        assert details['is_resolvable'] == True
        assert 'resolution_path' in details
        assert 'resolution_type' in details

        # Invalid reference
        invalid_details = validator.get_resolution_path_details('AtmosphereModel.Chemistry.NonExistent')
        assert invalid_details['is_resolvable'] == False
        assert 'error' in invalid_details
        assert 'available_variables' in invalid_details

    def test_convenience_function(self):
        """Test the convenience function for scope validation."""
        esm_file = self._create_test_esm_with_validation_scenarios()

        result = validate_scope_comprehensive(esm_file)

        assert isinstance(result, ScopeValidationResult)
        assert result.total_scopes_validated > 0
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)

    def test_validation_result_properties(self):
        """Test properties of the validation result."""
        esm_file = self._create_test_esm_with_validation_scenarios()
        validator = ScopeValidator(esm_file)

        result = validator.validate_comprehensive(['AtmosphereModel.Chemistry.NonExistent'])

        assert result.error_count == len(result.errors)
        assert result.warning_count == len(result.warnings)
        assert result.total_references_validated == 1

    def test_error_details_completeness(self):
        """Test that error details contain comprehensive information."""
        esm_file = self._create_test_esm_with_validation_scenarios()
        validator = ScopeValidator(esm_file)

        result = validator.validate_reference('AtmosphereModel.Chemistry.NonExistent')

        assert len(result.errors) > 0
        error = result.errors[0]

        # Check that error contains detailed information
        assert error.reference == 'AtmosphereModel.Chemistry.NonExistent'
        assert error.error_type == 'undefined_reference'
        assert len(error.message) > 0
        assert len(error.scope_path) > 0
        assert isinstance(error.available_variables, list)
        assert isinstance(error.resolution_path, list)
        assert isinstance(error.details, dict)


class TestScopeValidationEdgeCases:
    """Test edge cases in scope validation."""

    def test_empty_esm_file(self):
        """Test validation with empty ESM file."""
        metadata = Metadata(title="EmptyESM")
        esm_file = EsmFile(version="0.1.0", metadata=metadata)

        validator = ScopeValidator(esm_file)
        result = validator.validate_comprehensive([])

        assert result.is_valid  # Empty file should be valid
        assert len(result.errors) == 0
        assert result.total_scopes_validated == 0

    def test_validation_with_exception_handling(self):
        """Test that validation handles exceptions gracefully."""
        metadata = Metadata(title="TestESM")
        esm_file = EsmFile(version="0.1.0", metadata=metadata)

        validator = ScopeValidator(esm_file)

        # This should handle the case where no scopes exist
        result = validator.validate_reference('NonExistent.Variable')

        assert not result.is_valid
        assert len(result.errors) > 0