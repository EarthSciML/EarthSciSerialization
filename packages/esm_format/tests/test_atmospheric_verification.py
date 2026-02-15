"""
Tests for atmospheric chemistry verification framework.

This module provides comprehensive tests for the atmospheric chemistry
verification capabilities including all test scenarios, validation methods,
and performance benchmarks.
"""

import pytest
import numpy as np
import time
from unittest.mock import patch, MagicMock

from esm_format.atmospheric_verification import (
    AtmosphericChemistryVerifier, AtmosphericChemistryScenario, VerificationResult,
    verify_ozone_nox_cycle, verify_urban_chemistry, run_atmospheric_chemistry_verification_suite
)
from esm_format.simulation import SimulationResult, simulate
from esm_format.types import ReactionSystem, Species, Parameter, Reaction


class TestAtmosphericChemistryScenarios:
    """Test atmospheric chemistry scenario creation and setup."""

    def test_verifier_initialization(self):
        """Test verifier initialization with default and custom tolerances."""
        # Default initialization
        verifier = AtmosphericChemistryVerifier()
        assert 'mass_conservation' in verifier.tolerance
        assert 'energy_conservation' in verifier.tolerance
        assert len(verifier.scenarios) > 0

        # Custom tolerances
        custom_tolerances = {
            'mass_conservation': 1e-8,
            'energy_conservation': 1e-7,
            'analytical_accuracy': 1e-5
        }
        verifier_custom = AtmosphericChemistryVerifier(tolerance=custom_tolerances)
        assert verifier_custom.tolerance['mass_conservation'] == 1e-8

    def test_ozone_nox_scenario_creation(self):
        """Test O3-NO-NO2 scenario creation and structure."""
        verifier = AtmosphericChemistryVerifier()
        scenario = verifier.scenarios['ozone_nox_cycle']

        assert scenario.name == 'ozone_nox_cycle'
        assert isinstance(scenario.reaction_system, ReactionSystem)
        assert len(scenario.reaction_system.species) >= 3  # O3, NO, NO2, O2
        assert len(scenario.reaction_system.reactions) == 2  # Forward and reverse reactions

        # Check species are present
        species_names = {spec.name for spec in scenario.reaction_system.species}
        required_species = {'O3', 'NO', 'NO2', 'O2'}
        assert required_species.issubset(species_names)

        # Check initial conditions
        assert 'O3' in scenario.initial_conditions
        assert 'NO' in scenario.initial_conditions
        assert 'NO2' in scenario.initial_conditions

        # Check verification criteria
        assert 'mass_conservation' in scenario.verification_criteria
        assert 'photostationary_state' in scenario.verification_criteria

    def test_urban_chemistry_scenario_creation(self):
        """Test urban chemistry scenario creation."""
        verifier = AtmosphericChemistryVerifier()
        scenario = verifier.scenarios['urban_chemistry']

        assert scenario.name == 'urban_chemistry'
        assert len(scenario.reaction_system.species) >= 10  # Complex chemistry

        # Check for key urban species
        species_names = {spec.name for spec in scenario.reaction_system.species}
        urban_species = {'NO', 'NO2', 'O3', 'OH', 'HO2', 'CO', 'CH4'}
        assert urban_species.issubset(species_names)

        # Check time span is appropriate for diurnal cycle
        assert scenario.time_span[1] >= 12*3600  # At least 12 hours

    def test_stratospheric_scenario_creation(self):
        """Test stratospheric ozone depletion scenario."""
        verifier = AtmosphericChemistryVerifier()
        scenario = verifier.scenarios['stratospheric_ozone']

        # Check for halogen species
        species_names = {spec.name for spec in scenario.reaction_system.species}
        halogen_species = {'Cl', 'ClO', 'Br', 'BrO'}
        assert halogen_species.issubset(species_names)

        # Check for ozone depletion criteria
        assert 'ozone_depletion' in scenario.verification_criteria


class TestVerificationMethods:
    """Test individual verification methods."""

    @pytest.fixture
    def simple_scenario(self):
        """Create a simple test scenario."""
        species = [
            Species(name="A", units="mol/mol"),
            Species(name="B", units="mol/mol")
        ]
        parameters = [
            Parameter(name="k", value=0.1, units="1/s")
        ]
        reactions = [
            Reaction(name="A_to_B", reactants={"A": 1}, products={"B": 1}, rate_constant="k")
        ]

        reaction_system = ReactionSystem(
            name="simple_test",
            species=species,
            parameters=parameters,
            reactions=reactions
        )

        return AtmosphericChemistryScenario(
            name="simple_test",
            description="Simple A -> B reaction",
            reaction_system=reaction_system,
            initial_conditions={"A": 1.0, "B": 0.0},
            time_span=(0, 10),
            verification_criteria={'mass_conservation': ['A', 'B']}
        )

    @pytest.fixture
    def mock_simulation_result(self):
        """Create a mock simulation result."""
        # Simple exponential decay A -> B
        t = np.linspace(0, 10, 100)
        k = 0.1
        A = np.exp(-k * t)
        B = 1 - A
        y = np.array([A, B])

        return SimulationResult(
            t=t,
            y=y,
            success=True,
            message="Mock simulation success",
            nfev=100,
            njev=10,
            nlu=5
        )

    def test_mass_conservation_check(self, simple_scenario, mock_simulation_result):
        """Test mass conservation verification."""
        verifier = AtmosphericChemistryVerifier()

        error = verifier._check_mass_conservation(
            simple_scenario, mock_simulation_result, ['A', 'B']
        )

        # A + B should be conserved (= 1.0) throughout simulation
        assert error < 1e-10  # Very small numerical error expected

    def test_mass_conservation_with_empty_species(self, simple_scenario, mock_simulation_result):
        """Test mass conservation with empty species list."""
        verifier = AtmosphericChemistryVerifier()

        error = verifier._check_mass_conservation(
            simple_scenario, mock_simulation_result, []
        )

        assert error == 0.0  # Should return 0 for empty list

    def test_photostationary_state_check(self):
        """Test photostationary state verification."""
        verifier = AtmosphericChemistryVerifier()

        # Create mock scenario and result for photostationary test
        species = [Species(name="NO"), Species(name="NO2"), Species(name="O3")]
        scenario = AtmosphericChemistryScenario(
            name="photo_test",
            description="Photostationary test",
            reaction_system=ReactionSystem("test", species=species, reactions=[]),
            initial_conditions={"NO": 1e-9, "NO2": 2e-9, "O3": 40e-9},
            time_span=(0, 3600)
        )

        # Mock result showing approach to steady state
        t = np.linspace(0, 3600, 100)
        # Exponential approach to equilibrium
        NO_eq, NO2_eq = 0.5e-9, 1.5e-9  # Equilibrium values
        NO = NO_eq + (1e-9 - NO_eq) * np.exp(-t/1000)
        NO2 = NO2_eq + (2e-9 - NO2_eq) * np.exp(-t/1000)
        O3 = np.full_like(t, 40e-9)  # Constant O3 (excess)

        result = SimulationResult(
            t=t, y=np.array([NO, NO2, O3]), success=True,
            message="", nfev=100, njev=10, nlu=5
        )

        is_steady = verifier._check_photostationary_state(scenario, result)
        assert is_steady  # Should detect steady state

    def test_ozone_production_check(self):
        """Test ozone production verification."""
        verifier = AtmosphericChemistryVerifier()

        species = [Species(name="O3")]
        scenario = AtmosphericChemistryScenario(
            name="o3_prod_test",
            description="Ozone production test",
            reaction_system=ReactionSystem("test", species=species, reactions=[]),
            initial_conditions={"O3": 60e-9},
            time_span=(0, 12*3600)
        )

        # Mock result showing ozone production
        t = np.linspace(0, 12*3600, 100)
        O3 = 60e-9 + 20e-9 * (1 - np.exp(-t/7200))  # 60 -> 80 ppb production

        result = SimulationResult(
            t=t, y=np.array([O3]), success=True,
            message="", nfev=100, njev=10, nlu=5
        )

        has_production = verifier._check_ozone_production(scenario, result)
        assert has_production  # Should detect >10% increase

    def test_ozone_depletion_check(self):
        """Test ozone depletion verification."""
        verifier = AtmosphericChemistryVerifier()

        species = [Species(name="O3")]
        scenario = AtmosphericChemistryScenario(
            name="o3_depl_test",
            description="Ozone depletion test",
            reaction_system=ReactionSystem("test", species=species, reactions=[]),
            initial_conditions={"O3": 8e-6},
            time_span=(0, 86400)
        )

        # Mock result showing ozone depletion
        t = np.linspace(0, 86400, 100)
        O3 = 8e-6 * np.exp(-t/43200)  # Exponential depletion

        result = SimulationResult(
            t=t, y=np.array([O3]), success=True,
            message="", nfev=100, njev=10, nlu=5
        )

        has_depletion = verifier._check_ozone_depletion(scenario, result)
        assert has_depletion  # Should detect >10% decrease

    def test_steady_state_radicals_check(self):
        """Test steady state radical verification."""
        verifier = AtmosphericChemistryVerifier()

        species = [Species(name="OH"), Species(name="HO2")]
        scenario = AtmosphericChemistryScenario(
            name="radical_test",
            description="Radical steady state test",
            reaction_system=ReactionSystem("test", species=species, reactions=[]),
            initial_conditions={"OH": 1e-12, "HO2": 10e-12},
            time_span=(0, 3600)
        )

        # Mock result showing radicals reaching steady state
        t = np.linspace(0, 3600, 100)
        OH_eq, HO2_eq = 2e-12, 15e-12
        OH = OH_eq + (1e-12 - OH_eq) * np.exp(-t/300)  # Fast equilibration
        HO2 = HO2_eq + (10e-12 - HO2_eq) * np.exp(-t/300)

        result = SimulationResult(
            t=t, y=np.array([OH, HO2]), success=True,
            message="", nfev=100, njev=10, nlu=5
        )

        is_steady = verifier._check_steady_state_radicals(scenario, result, ['OH', 'HO2'])
        assert is_steady


class TestScenarioVerification:
    """Test full scenario verification process."""

    @patch('esm_format.atmospheric_verification.simulate')
    def test_successful_scenario_verification(self, mock_simulate):
        """Test successful verification of a scenario."""
        # Mock successful simulation
        t = np.linspace(0, 3600, 100)
        # O3-NO-NO2 system with mass conservation
        NO_initial, NO2_initial = 5e-9, 20e-9
        NOx_total = NO_initial + NO2_initial

        # Photostationary equilibrium approach
        NO_eq = NOx_total * 0.3  # Equilibrium partition
        NO2_eq = NOx_total * 0.7

        NO = NO_eq + (NO_initial - NO_eq) * np.exp(-t/600)
        NO2 = NO2_eq + (NO2_initial - NO2_eq) * np.exp(-t/600)
        O3 = np.full_like(t, 80e-9)  # Constant excess O3
        O2 = np.full_like(t, 0.21)   # Background O2

        y = np.array([O3, NO, NO2, O2])

        mock_simulate.return_value = SimulationResult(
            t=t, y=y, success=True, message="Success",
            nfev=500, njev=50, nlu=10
        )

        verifier = AtmosphericChemistryVerifier()
        result = verifier.verify_scenario('ozone_nox_cycle')

        assert result.success
        assert result.scenario_name == 'ozone_nox_cycle'
        assert 'mass_conservation' in result.verification_tests
        assert 'photostationary_state' in result.verification_tests
        assert result.mass_conservation_error < verifier.tolerance['mass_conservation']

    @patch('esm_format.atmospheric_verification.simulate')
    def test_failed_simulation_verification(self, mock_simulate):
        """Test verification when simulation fails."""
        mock_simulate.return_value = SimulationResult(
            t=np.array([]), y=np.array([[]]), success=False,
            message="Integration failed", nfev=0, njev=0, nlu=0
        )

        verifier = AtmosphericChemistryVerifier()
        result = verifier.verify_scenario('ozone_nox_cycle')

        assert not result.success
        assert "Simulation failed" in result.message

    def test_nonexistent_scenario_verification(self):
        """Test verification of non-existent scenario."""
        verifier = AtmosphericChemistryVerifier()
        result = verifier.verify_scenario('nonexistent_scenario')

        assert not result.success
        assert "not found" in result.message

    @patch('esm_format.atmospheric_verification.simulate')
    def test_verification_with_solver_options(self, mock_simulate):
        """Test verification with custom solver options."""
        mock_simulate.return_value = SimulationResult(
            t=np.linspace(0, 3600, 50), y=np.random.rand(4, 50),
            success=True, message="Success", nfev=200, njev=20, nlu=5
        )

        verifier = AtmosphericChemistryVerifier()
        result = verifier.verify_scenario('ozone_nox_cycle', rtol=1e-8, atol=1e-10)

        # Check that solver options were passed through
        mock_simulate.assert_called_once()
        call_kwargs = mock_simulate.call_args[1]
        assert call_kwargs['rtol'] == 1e-8
        assert call_kwargs['atol'] == 1e-10


class TestFullVerificationSuite:
    """Test the complete verification suite."""

    @patch('esm_format.atmospheric_verification.simulate')
    def test_run_full_verification_suite(self, mock_simulate):
        """Test running the full verification suite."""
        # Mock successful simulations for all scenarios
        mock_result = SimulationResult(
            t=np.linspace(0, 3600, 100),
            y=np.random.rand(5, 100),  # Random data for simplicity
            success=True,
            message="Success",
            nfev=500,
            njev=50,
            nlu=10
        )
        mock_simulate.return_value = mock_result

        verifier = AtmosphericChemistryVerifier()
        results = verifier.run_full_verification_suite()

        # Should have results for all scenarios
        expected_scenarios = {'ozone_nox_cycle', 'urban_chemistry', 'stratospheric_ozone'}
        assert expected_scenarios.issubset(set(results.keys()))

        # All results should be VerificationResult objects
        for result in results.values():
            assert isinstance(result, VerificationResult)

    def test_verification_report_generation(self):
        """Test verification report generation."""
        # Create mock results
        results = {
            'test_scenario_1': VerificationResult(
                scenario_name='test_scenario_1',
                success=True,
                simulation_result=SimulationResult(
                    t=np.array([0, 1]), y=np.array([[1, 0.5]]),
                    success=True, message="", nfev=100, njev=10, nlu=5
                ),
                verification_tests={'mass_conservation': True, 'energy_conservation': True},
                error_metrics={'analytical_error': 1e-5},
                mass_conservation_error=1e-7,
                energy_conservation_error=1e-6,
                runtime=2.5
            ),
            'test_scenario_2': VerificationResult(
                scenario_name='test_scenario_2',
                success=False,
                simulation_result=None,
                message="Simulation failed",
                runtime=0.1
            )
        }

        verifier = AtmosphericChemistryVerifier()
        report = verifier.generate_verification_report(results)

        assert "ATMOSPHERIC CHEMISTRY VERIFICATION REPORT" in report
        assert "1/2 scenarios passed" in report
        assert "test_scenario_1" in report
        assert "test_scenario_2" in report
        assert "PASSED" in report
        assert "FAILED" in report


class TestConvenienceFunctions:
    """Test convenience functions for quick verification."""

    @patch('esm_format.atmospheric_verification.simulate')
    def test_verify_ozone_nox_cycle(self, mock_simulate):
        """Test quick ozone-NOx cycle verification."""
        mock_simulate.return_value = SimulationResult(
            t=np.linspace(0, 3600, 100), y=np.random.rand(4, 100),
            success=True, message="Success", nfev=500, njev=50, nlu=10
        )

        result = verify_ozone_nox_cycle(rtol=1e-7)

        assert isinstance(result, VerificationResult)
        assert result.scenario_name == 'ozone_nox_cycle'

    @patch('esm_format.atmospheric_verification.simulate')
    def test_verify_urban_chemistry(self, mock_simulate):
        """Test quick urban chemistry verification."""
        mock_simulate.return_value = SimulationResult(
            t=np.linspace(0, 12*3600, 200), y=np.random.rand(10, 200),
            success=True, message="Success", nfev=1000, njev=100, nlu=20
        )

        result = verify_urban_chemistry()

        assert isinstance(result, VerificationResult)
        assert result.scenario_name == 'urban_chemistry'

    @patch('esm_format.atmospheric_verification.simulate')
    def test_run_atmospheric_chemistry_verification_suite(self, mock_simulate):
        """Test running the complete suite via convenience function."""
        mock_simulate.return_value = SimulationResult(
            t=np.linspace(0, 3600, 100), y=np.random.rand(5, 100),
            success=True, message="Success", nfev=500, njev=50, nlu=10
        )

        results = run_atmospheric_chemistry_verification_suite()

        assert isinstance(results, dict)
        assert len(results) >= 2  # At least ozone_nox and urban_chemistry scenarios


class TestPerformanceBenchmarking:
    """Test performance benchmarking capabilities."""

    def test_verification_timing(self):
        """Test that verification timing is recorded."""
        verifier = AtmosphericChemistryVerifier()

        # Mock a quick scenario for timing test
        with patch('esm_format.atmospheric_verification.simulate') as mock_simulate:
            # Simulate some computation time
            def slow_simulate(*args, **kwargs):
                time.sleep(0.01)  # 10ms delay
                return SimulationResult(
                    t=np.array([0, 1]), y=np.array([[1, 0.5]]),
                    success=True, message="", nfev=100, njev=10, nlu=5
                )

            mock_simulate.side_effect = slow_simulate

            result = verifier.verify_scenario('ozone_nox_cycle')

            # Should have recorded runtime
            assert result.runtime > 0.0
            assert result.runtime < 1.0  # Should be quick

    def test_large_system_performance(self):
        """Test performance with larger systems (mock)."""
        # This would test performance with larger reaction systems
        # For now, just ensure the framework can handle it
        verifier = AtmosphericChemistryVerifier()

        # The urban chemistry scenario is our "large" system test
        with patch('esm_format.atmospheric_verification.simulate') as mock_simulate:
            # Mock result for large system
            mock_simulate.return_value = SimulationResult(
                t=np.linspace(0, 12*3600, 1000),  # Many time points
                y=np.random.rand(15, 1000),       # Many species
                success=True,
                message="Large system success",
                nfev=10000,  # Many function evaluations
                njev=1000,
                nlu=100
            )

            result = verifier.verify_scenario('urban_chemistry')

            assert result.success
            assert result.simulation_result.nfev == 10000


class TestErrorHandling:
    """Test error handling in verification framework."""

    def test_verification_with_exception(self):
        """Test verification when an exception occurs."""
        verifier = AtmosphericChemistryVerifier()

        with patch('esm_format.atmospheric_verification.simulate') as mock_simulate:
            mock_simulate.side_effect = Exception("Simulation crashed")

            result = verifier.verify_scenario('ozone_nox_cycle')

            assert not result.success
            assert "exception" in result.message.lower()
            assert "crashed" in result.message

    def test_mass_conservation_with_invalid_data(self):
        """Test mass conservation check with invalid data."""
        verifier = AtmosphericChemistryVerifier()

        # Create scenario with species that don't match result
        species = [Species(name="NONEXISTENT")]
        scenario = AtmosphericChemistryScenario(
            name="invalid_test",
            description="Invalid test",
            reaction_system=ReactionSystem("test", species=species, reactions=[]),
            initial_conditions={},
            time_span=(0, 1)
        )

        result = SimulationResult(
            t=np.array([0, 1]), y=np.array([[1, 0.5]]),
            success=True, message="", nfev=100, njev=10, nlu=5
        )

        error = verifier._check_mass_conservation(scenario, result, ['NONEXISTENT'])

        # Should handle gracefully and return 0 (no conserved species found)
        assert error == 0.0

    def test_photostationary_check_with_missing_species(self):
        """Test photostationary check when required species are missing."""
        verifier = AtmosphericChemistryVerifier()

        # Scenario without NO/NO2/O3
        species = [Species(name="OTHER")]
        scenario = AtmosphericChemistryScenario(
            name="missing_species_test",
            description="Test without required species",
            reaction_system=ReactionSystem("test", species=species, reactions=[]),
            initial_conditions={},
            time_span=(0, 1)
        )

        result = SimulationResult(
            t=np.array([0, 1]), y=np.array([[1, 0.5]]),
            success=True, message="", nfev=100, njev=10, nlu=5
        )

        is_steady = verifier._check_photostationary_state(scenario, result)
        assert not is_steady  # Should return False for missing species


if __name__ == "__main__":
    pytest.main([__file__, "-v"])