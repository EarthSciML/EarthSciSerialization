"""
Tests for time synchronization algorithms.

This module tests the time synchronization functionality for coupled ESM
components with different time steps, including interpolation, extrapolation,
and time alignment strategies.
"""

import pytest
import math
from datetime import datetime, timedelta

from esm_format.time_synchronization import (
    TimeSynchronizer,
    TimeStep,
    TimePoint,
    TimeSeries,
    ComponentTimeState,
    TimeInterpolationMethod,
    TimeExtrapolationMethod,
    TimeAlignmentStrategy,
    synchronize_coupled_system,
    create_subcycling_synchronizer,
    validate_time_synchronization_config
)
from esm_format.types import CouplingEntry, CouplingType


class TestTimeStep:
    """Test the TimeStep class."""

    def test_time_step_creation(self):
        """Test creation of TimeStep objects."""
        ts = TimeStep(1.0, "seconds")
        assert ts.value == 1.0
        assert ts.units == "seconds"

    def test_time_step_conversion_to_seconds(self):
        """Test conversion of various time units to seconds."""
        test_cases = [
            (TimeStep(1.0, "seconds"), 1.0),
            (TimeStep(1.0, "minutes"), 60.0),
            (TimeStep(1.0, "hours"), 3600.0),
            (TimeStep(1.0, "days"), 86400.0),
            (TimeStep(1.0, "milliseconds"), 0.001),
            (TimeStep(2.5, "hours"), 9000.0),
        ]

        for time_step, expected_seconds in test_cases:
            assert abs(time_step.to_seconds() - expected_seconds) < 1e-9

    def test_invalid_time_units(self):
        """Test that invalid time units raise an error."""
        ts = TimeStep(1.0, "invalid_unit")
        with pytest.raises(ValueError, match="Unsupported time unit"):
            ts.to_seconds()


class TestTimeSeries:
    """Test the TimeSeries class."""

    def test_empty_time_series(self):
        """Test behavior of empty time series."""
        ts = TimeSeries()
        assert len(ts.points) == 0
        assert ts.get_time_range() == (0.0, 0.0)
        assert len(ts.get_variables()) == 0

    def test_add_points_and_sorting(self):
        """Test adding points maintains time ordering."""
        ts = TimeSeries()

        # Add points out of order
        ts.add_point(10.0, {"var1": 10.0})
        ts.add_point(5.0, {"var1": 5.0})
        ts.add_point(15.0, {"var1": 15.0})

        # Check they are sorted by time
        times = [p.time for p in ts.points]
        assert times == [5.0, 10.0, 15.0]

    def test_get_time_range(self):
        """Test getting time range of series."""
        ts = TimeSeries()
        ts.add_point(5.0, {"var1": 5.0})
        ts.add_point(15.0, {"var1": 15.0})
        ts.add_point(10.0, {"var1": 10.0})

        start_time, end_time = ts.get_time_range()
        assert start_time == 5.0
        assert end_time == 15.0

    def test_get_variables(self):
        """Test getting all variables in series."""
        ts = TimeSeries()
        ts.add_point(1.0, {"var1": 1.0, "var2": 2.0})
        ts.add_point(2.0, {"var1": 1.5, "var3": 3.0})

        variables = ts.get_variables()
        assert variables == {"var1", "var2", "var3"}


class TestComponentTimeState:
    """Test the ComponentTimeState class."""

    def test_component_creation_and_time_advancement(self):
        """Test component state creation and time advancement."""
        time_step = TimeStep(1.0, "seconds")
        comp = ComponentTimeState(
            component_name="test_comp",
            current_time=0.0,
            time_step=time_step,
            next_update_time=1.0
        )

        assert comp.component_name == "test_comp"
        assert comp.current_time == 0.0
        assert comp.next_update_time == 1.0

        # Advance time
        comp.advance_time()
        assert comp.current_time == 1.0
        assert comp.next_update_time == 2.0

    def test_add_data_point(self):
        """Test adding data points to component history."""
        time_step = TimeStep(1.0, "seconds")
        comp = ComponentTimeState(
            component_name="test_comp",
            current_time=0.0,
            time_step=time_step,
            next_update_time=1.0,
            max_history_length=3
        )

        # Add data points
        comp.add_data_point({"var1": 1.0})
        comp.advance_time()
        comp.add_data_point({"var1": 2.0})
        comp.advance_time()
        comp.add_data_point({"var1": 3.0})

        assert len(comp.history.points) == 3

        # Add another point - should trim history
        comp.advance_time()
        comp.add_data_point({"var1": 4.0})

        assert len(comp.history.points) == 3  # Should still be 3 due to max_history_length


class TestTimeSynchronizer:
    """Test the main TimeSynchronizer class."""

    def test_component_registration(self):
        """Test registering components with synchronizer."""
        sync = TimeSynchronizer()
        time_step = TimeStep(1.0, "seconds")

        sync.register_component("comp1", time_step, initial_time=0.0)

        assert "comp1" in sync.components
        assert sync.components["comp1"].component_name == "comp1"
        assert sync.components["comp1"].current_time == 0.0

    def test_coupling_registration(self):
        """Test registering couplings with synchronizer."""
        sync = TimeSynchronizer()

        coupling = CouplingEntry(
            source_model="comp1",
            target_model="comp2",
            source_variables=["var1"],
            target_variables=["var2"],
            coupling_type=CouplingType.DIRECT
        )

        sync.register_coupling(coupling)
        assert len(sync.couplings) == 1
        assert sync.couplings[0].source_model == "comp1"

    def test_sync_time_calculation_synchronous(self):
        """Test sync time calculation for synchronous strategy."""
        sync = TimeSynchronizer()
        sync.set_alignment_strategy(TimeAlignmentStrategy.SYNCHRONOUS)

        # Register components with different time steps
        sync.register_component("comp1", TimeStep(1.0, "seconds"), initial_time=0.0)
        sync.register_component("comp2", TimeStep(2.0, "seconds"), initial_time=0.0)

        # Next sync time should be the minimum next update time
        next_sync = sync.get_next_sync_time()
        assert next_sync == 1.0  # comp1 updates first

    def test_advance_to_sync_time(self):
        """Test advancing components to sync time."""
        sync = TimeSynchronizer()

        sync.register_component("comp1", TimeStep(1.0, "seconds"), initial_time=0.0)
        sync.register_component("comp2", TimeStep(2.0, "seconds"), initial_time=0.0)

        # Advance to first sync time
        sync_time = sync.advance_to_sync_time()
        assert sync_time == 1.0
        assert sync.components["comp1"].current_time == 1.0
        assert sync.components["comp2"].current_time == 0.0  # Shouldn't advance yet

        # Advance to second sync time
        sync_time = sync.advance_to_sync_time()
        assert sync_time == 2.0
        assert sync.components["comp1"].current_time == 2.0
        assert sync.components["comp2"].current_time == 2.0  # Both advance

    def test_linear_interpolation(self):
        """Test linear interpolation between data points."""
        sync = TimeSynchronizer()
        sync.register_component("comp1", TimeStep(2.0, "seconds"), initial_time=0.0)

        comp = sync.components["comp1"]
        comp.add_data_point({"var1": 0.0})  # t=0, var1=0
        comp.advance_time()
        comp.add_data_point({"var1": 4.0})  # t=2, var1=4

        # Interpolate at t=1 (halfway between)
        result = sync.interpolate_data("comp1", 1.0, ["var1"], TimeInterpolationMethod.LINEAR)
        assert result["var1"] == 2.0  # Should be halfway between 0 and 4

    def test_nearest_interpolation(self):
        """Test nearest neighbor interpolation."""
        sync = TimeSynchronizer()
        sync.register_component("comp1", TimeStep(2.0, "seconds"), initial_time=0.0)

        comp = sync.components["comp1"]
        comp.add_data_point({"var1": 10.0})  # t=0, var1=10
        comp.advance_time()
        comp.add_data_point({"var1": 20.0})  # t=2, var1=20

        # Test nearest neighbor at t=0.4 (closer to t=0)
        result = sync.interpolate_data("comp1", 0.4, ["var1"], TimeInterpolationMethod.NEAREST)
        assert result["var1"] == 10.0

        # Test nearest neighbor at t=1.6 (closer to t=2)
        result = sync.interpolate_data("comp1", 1.6, ["var1"], TimeInterpolationMethod.NEAREST)
        assert result["var1"] == 20.0

    def test_constant_extrapolation(self):
        """Test extrapolation beyond data range."""
        sync = TimeSynchronizer()
        sync.register_component("comp1", TimeStep(1.0, "seconds"), initial_time=0.0)

        comp = sync.components["comp1"]
        comp.add_data_point({"var1": 5.0})  # t=0, var1=5
        comp.advance_time()
        comp.add_data_point({"var1": 10.0})  # t=1, var1=10

        # Extrapolate beyond last point (should use linear extrapolation)
        # With LINEAR interpolation method, it does linear extrapolation
        # Slope is (10-5)/(1-0) = 5, so at t=5: 10 + 5*(5-1) = 30
        result = sync.interpolate_data("comp1", 5.0, ["var1"], TimeInterpolationMethod.LINEAR)
        assert result["var1"] == 30.0

    def test_no_data_interpolation(self):
        """Test interpolation when no data is available."""
        sync = TimeSynchronizer()
        sync.register_component("comp1", TimeStep(1.0, "seconds"), initial_time=0.0)

        # Try to interpolate with no historical data
        result = sync.interpolate_data("comp1", 1.0, ["var1"], TimeInterpolationMethod.LINEAR)
        assert result["var1"] == 0.0  # Should return 0 when no data available

    def test_synchronization_summary(self):
        """Test getting synchronization summary."""
        sync = TimeSynchronizer()
        sync.register_component("comp1", TimeStep(1.0, "seconds"), initial_time=0.0)
        sync.register_component("comp2", TimeStep(2.0, "seconds"), initial_time=0.0)

        coupling = CouplingEntry(
            source_model="comp1",
            target_model="comp2",
            source_variables=["var1"],
            target_variables=["var2"],
            coupling_type=CouplingType.DIRECT
        )
        sync.register_coupling(coupling)

        summary = sync.get_synchronization_summary()

        assert summary["master_time"] == 0.0
        assert summary["alignment_strategy"] == "synchronous"
        assert summary["num_components"] == 2
        assert summary["num_couplings"] == 1
        assert "comp1" in summary["components"]
        assert "comp2" in summary["components"]


class TestHighLevelFunctions:
    """Test high-level convenience functions."""

    def test_synchronize_coupled_system(self):
        """Test high-level system synchronization function."""
        # Define components
        components = {
            "atmosphere": (TimeStep(1.0, "seconds"), {"temperature": 273.0}),
            "ocean": (TimeStep(2.0, "seconds"), {"temperature": 283.0})
        }

        # Define coupling
        couplings = [
            CouplingEntry(
                source_model="atmosphere",
                target_model="ocean",
                source_variables=["temperature"],
                target_variables=["surface_temperature"],
                coupling_type=CouplingType.INTERPOLATED
            )
        ]

        # Run short simulation
        result = synchronize_coupled_system(
            components=components,
            couplings=couplings,
            simulation_duration=5.0,
            alignment_strategy=TimeAlignmentStrategy.SYNCHRONOUS
        )

        assert "simulation_steps" in result
        assert result["final_time"] >= 5.0
        assert result["num_components"] == 2
        assert result["num_couplings"] == 1

    def test_create_subcycling_synchronizer(self):
        """Test creating subcycling synchronizer."""
        fast_component = ("dynamics", TimeStep(0.1, "seconds"))
        slow_component = ("physics", TimeStep(1.0, "seconds"))
        coupling_vars = (["velocity"], ["wind_speed"])

        sync = create_subcycling_synchronizer(fast_component, slow_component, coupling_vars)

        assert sync.alignment_strategy == TimeAlignmentStrategy.SUBCYCLING
        assert len(sync.components) == 2
        assert len(sync.couplings) == 2  # Bidirectional coupling

    def test_validate_time_synchronization_config(self):
        """Test validation of synchronization configuration."""
        components = {
            "comp1": TimeStep(1.0, "seconds"),
            "comp2": TimeStep(2.0, "seconds")
        }

        valid_couplings = [
            CouplingEntry(
                source_model="comp1",
                target_model="comp2",
                source_variables=["var1"],
                target_variables=["var2"],
                coupling_type=CouplingType.DIRECT
            )
        ]

        # Valid configuration
        is_valid, errors = validate_time_synchronization_config(components, valid_couplings)
        assert is_valid
        assert len(errors) == 0

        # Invalid configuration - unknown component
        invalid_couplings = [
            CouplingEntry(
                source_model="unknown_comp",
                target_model="comp2",
                source_variables=["var1"],
                target_variables=["var2"],
                coupling_type=CouplingType.DIRECT
            )
        ]

        is_valid, errors = validate_time_synchronization_config(components, invalid_couplings)
        assert not is_valid
        assert len(errors) > 0
        assert "unknown_comp" in errors[0]

    def test_large_time_step_ratio_warning(self):
        """Test warning for large time step ratios."""
        components = {
            "fast": TimeStep(1e-6, "seconds"),  # 1 microsecond
            "slow": TimeStep(1.0, "seconds")    # 1 second (ratio = 1,000,000)
        }

        is_valid, errors = validate_time_synchronization_config(components, [])
        assert not is_valid
        assert any("Large time step ratio" in error for error in errors)


class TestTimeAlignmentStrategies:
    """Test different time alignment strategies."""

    def test_synchronous_alignment(self):
        """Test synchronous time alignment."""
        sync = TimeSynchronizer()
        sync.set_alignment_strategy(TimeAlignmentStrategy.SYNCHRONOUS)

        sync.register_component("comp1", TimeStep(1.0, "seconds"))
        sync.register_component("comp2", TimeStep(3.0, "seconds"))

        # In synchronous mode, next sync should be min of next update times
        next_sync = sync.get_next_sync_time()
        assert next_sync == 1.0

    def test_master_slave_alignment(self):
        """Test master-slave alignment strategy."""
        sync = TimeSynchronizer()
        sync.set_alignment_strategy(TimeAlignmentStrategy.MASTER_SLAVE)

        # First registered component becomes master
        sync.register_component("master", TimeStep(2.0, "seconds"))
        sync.register_component("slave", TimeStep(1.0, "seconds"))

        # Should use master's time step
        next_sync = sync.get_next_sync_time()
        assert next_sync == 2.0

    def test_subcycling_alignment(self):
        """Test subcycling alignment strategy."""
        sync = TimeSynchronizer()
        sync.set_alignment_strategy(TimeAlignmentStrategy.SUBCYCLING)

        # Components with time steps that have GCD
        sync.register_component("comp1", TimeStep(0.5, "seconds"))
        sync.register_component("comp2", TimeStep(1.0, "seconds"))

        next_sync = sync.get_next_sync_time()
        # GCD of 0.5 and 1.0 is 0.5
        assert abs(next_sync - 0.5) < 1e-9


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_interpolation_with_unknown_component(self):
        """Test interpolation with unknown component raises error."""
        sync = TimeSynchronizer()

        with pytest.raises(ValueError, match="Unknown source component"):
            sync.interpolate_data("unknown_comp", 1.0, ["var1"])

    def test_exact_time_match_interpolation(self):
        """Test interpolation when target time exactly matches data point."""
        sync = TimeSynchronizer()
        sync.register_component("comp1", TimeStep(1.0, "seconds"), initial_time=0.0)

        comp = sync.components["comp1"]
        comp.add_data_point({"var1": 42.0})  # t=0

        # Request interpolation at exact time
        result = sync.interpolate_data("comp1", 0.0, ["var1"])
        assert result["var1"] == 42.0

    def test_single_data_point_interpolation(self):
        """Test interpolation with only one data point."""
        sync = TimeSynchronizer()
        sync.register_component("comp1", TimeStep(1.0, "seconds"), initial_time=5.0)

        comp = sync.components["comp1"]
        comp.add_data_point({"var1": 100.0})  # t=5

        # Request at different time - should extrapolate
        result = sync.interpolate_data("comp1", 10.0, ["var1"])
        assert result["var1"] == 100.0  # Constant extrapolation

    def test_gcd_calculation(self):
        """Test GCD calculation for multiple float values."""
        sync = TimeSynchronizer()

        # Test with simple values
        gcd_result = sync._gcd_multiple([0.5, 1.0, 1.5])
        assert abs(gcd_result - 0.5) < 1e-6

        # Test with single value
        gcd_result = sync._gcd_multiple([2.0])
        assert abs(gcd_result - 2.0) < 1e-6

        # Test with empty list
        gcd_result = sync._gcd_multiple([])
        assert gcd_result == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])