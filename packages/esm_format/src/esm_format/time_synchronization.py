"""
Time synchronization algorithms for coupled ESM components with different time steps.

This module provides algorithms for synchronizing data exchange between coupled
components that operate on different temporal scales, including interpolation,
extrapolation, and time alignment strategies required for multi-physics coupling.
"""

from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import math
from datetime import datetime, timedelta
import logging

from .esm_types import TemporalDomain, CouplingEntry, CouplingType

# Set up logging
logger = logging.getLogger(__name__)


class TimeInterpolationMethod(Enum):
    """Methods for time interpolation."""
    LINEAR = "linear"
    CUBIC_SPLINE = "cubic_spline"
    NEAREST = "nearest"
    WEIGHTED_AVERAGE = "weighted_average"


class TimeExtrapolationMethod(Enum):
    """Methods for time extrapolation."""
    CONSTANT = "constant"  # Hold last known value
    LINEAR = "linear"      # Linear extrapolation from last two points
    PERIODIC = "periodic"  # Assume periodic behavior
    ZERO = "zero"         # Set to zero


class TimeAlignmentStrategy(Enum):
    """Strategies for aligning time between components."""
    SYNCHRONOUS = "synchronous"           # Components advance in lockstep
    ASYNCHRONOUS = "asynchronous"         # Components can advance independently
    MASTER_SLAVE = "master_slave"         # One component drives the time progression
    SUBCYCLING = "subcycling"            # Fine-grained component subcycles within coarser time steps


@dataclass
class TimeStep:
    """Represents a time step with value and units."""
    value: float
    units: str  # e.g., "seconds", "minutes", "hours", "days"

    def to_seconds(self) -> float:
        """Convert time step to seconds."""
        unit_conversions = {
            "seconds": 1.0,
            "minutes": 60.0,
            "hours": 3600.0,
            "days": 86400.0,
            "years": 365.25 * 86400.0,
            "milliseconds": 0.001,
            "microseconds": 1e-6,
            "nanoseconds": 1e-9
        }

        conversion = unit_conversions.get(self.units.lower())
        if conversion is None:
            raise ValueError(f"Unsupported time unit: {self.units}")

        return self.value * conversion


@dataclass
class TimePoint:
    """Represents a point in time with associated data."""
    time: float  # Time in seconds since reference
    data: Dict[str, Any]  # Variable name -> value mapping
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimeSeries:
    """A time series of data points."""
    points: List[TimePoint] = field(default_factory=list)
    reference_time: Optional[datetime] = None

    def add_point(self, time: float, data: Dict[str, Any], metadata: Dict[str, Any] = None) -> None:
        """Add a data point to the time series."""
        self.points.append(TimePoint(time, data, metadata or {}))
        # Keep points sorted by time
        self.points.sort(key=lambda p: p.time)

    def get_time_range(self) -> Tuple[float, float]:
        """Get the time range covered by this series."""
        if not self.points:
            return (0.0, 0.0)
        return (self.points[0].time, self.points[-1].time)

    def get_variables(self) -> set:
        """Get all variable names present in this time series."""
        variables = set()
        for point in self.points:
            variables.update(point.data.keys())
        return variables


@dataclass
class ComponentTimeState:
    """Tracks the temporal state of a coupled component."""
    component_name: str
    current_time: float  # Current simulation time in seconds
    time_step: TimeStep  # Component's native time step
    next_update_time: float  # When this component next needs to update
    history: TimeSeries = field(default_factory=TimeSeries)  # Historical data
    max_history_length: int = 100  # Maximum number of historical points to keep

    def advance_time(self) -> None:
        """Advance the component to its next update time."""
        self.current_time = self.next_update_time
        self.next_update_time += self.time_step.to_seconds()

    def add_data_point(self, data: Dict[str, Any], metadata: Dict[str, Any] = None) -> None:
        """Add a data point at the current time."""
        self.history.add_point(self.current_time, data, metadata)

        # Trim history if it gets too long
        if len(self.history.points) > self.max_history_length:
            self.history.points = self.history.points[-self.max_history_length:]


class TimeSynchronizer:
    """
    Main class for synchronizing time between coupled components.

    This class manages the temporal coordination of multiple components
    with potentially different time steps, handling data interpolation
    and extrapolation as needed for coupling.
    """

    def __init__(self):
        """Initialize the time synchronizer."""
        self.components: Dict[str, ComponentTimeState] = {}
        self.couplings: List[CouplingEntry] = []
        self.master_time: float = 0.0  # Global simulation time
        self.alignment_strategy: TimeAlignmentStrategy = TimeAlignmentStrategy.SYNCHRONOUS

    def register_component(
        self,
        name: str,
        time_step: TimeStep,
        initial_time: float = 0.0,
        max_history: int = 100
    ) -> None:
        """
        Register a component with the synchronizer.

        Args:
            name: Component identifier
            time_step: Component's native time step
            initial_time: Initial simulation time
            max_history: Maximum number of historical data points to keep
        """
        component = ComponentTimeState(
            component_name=name,
            current_time=initial_time,
            time_step=time_step,
            next_update_time=initial_time + time_step.to_seconds(),
            max_history_length=max_history
        )
        self.components[name] = component
        logger.info(f"Registered component '{name}' with time step {time_step.value} {time_step.units}")

    def register_coupling(self, coupling: CouplingEntry) -> None:
        """Register a coupling relationship between components."""
        self.couplings.append(coupling)
        logger.info(f"Registered coupling: {coupling.source_model} -> {coupling.target_model}")

    def set_alignment_strategy(self, strategy: TimeAlignmentStrategy) -> None:
        """Set the time alignment strategy."""
        self.alignment_strategy = strategy
        logger.info(f"Set time alignment strategy to {strategy.value}")

    def get_next_sync_time(self) -> float:
        """
        Determine the next synchronization time based on alignment strategy.

        Returns:
            Next time at which components should synchronize
        """
        if not self.components:
            return self.master_time

        if self.alignment_strategy == TimeAlignmentStrategy.SYNCHRONOUS:
            # Find the earliest next update time
            return min(comp.next_update_time for comp in self.components.values())

        elif self.alignment_strategy == TimeAlignmentStrategy.ASYNCHRONOUS:
            # Each component can advance independently
            return min(comp.next_update_time for comp in self.components.values())

        elif self.alignment_strategy == TimeAlignmentStrategy.MASTER_SLAVE:
            # Use the master component's time step (assume first registered is master)
            master_name = next(iter(self.components))
            return self.components[master_name].next_update_time

        elif self.alignment_strategy == TimeAlignmentStrategy.SUBCYCLING:
            # Find the greatest common divisor of all time steps
            return self._get_subcycling_sync_time()

        else:
            raise ValueError(f"Unknown alignment strategy: {self.alignment_strategy}")

    def _get_subcycling_sync_time(self) -> float:
        """Calculate next sync time for subcycling strategy."""
        # For subcycling, we sync at the GCD of all component time steps
        time_steps_seconds = [comp.time_step.to_seconds() for comp in self.components.values()]
        gcd_timestep = self._gcd_multiple(time_steps_seconds)
        return self.master_time + gcd_timestep

    def _gcd_multiple(self, values: List[float]) -> float:
        """Calculate GCD of multiple float values (approximated)."""
        if not values:
            return 1.0

        # Convert to integer representation for GCD calculation
        # Assume precision to microseconds
        PRECISION = 1e-6
        int_values = [int(v / PRECISION) for v in values]

        result = int_values[0]
        for i in range(1, len(int_values)):
            result = math.gcd(result, int_values[i])

        return result * PRECISION

    def advance_to_sync_time(self) -> float:
        """
        Advance all components to the next synchronization time.

        Returns:
            The new synchronization time
        """
        sync_time = self.get_next_sync_time()
        self.master_time = sync_time

        # Advance each component that should update at this time
        for component in self.components.values():
            if abs(component.next_update_time - sync_time) < 1e-9:  # Floating point tolerance
                component.advance_time()

        logger.debug(f"Advanced to sync time: {sync_time}")
        return sync_time

    def interpolate_data(
        self,
        source_component: str,
        target_time: float,
        variables: List[str],
        method: TimeInterpolationMethod = TimeInterpolationMethod.LINEAR
    ) -> Dict[str, Any]:
        """
        Interpolate data from source component to target time.

        Args:
            source_component: Name of source component
            target_time: Time at which to interpolate
            variables: List of variables to interpolate
            method: Interpolation method

        Returns:
            Dictionary of interpolated variable values
        """
        if source_component not in self.components:
            raise ValueError(f"Unknown source component: {source_component}")

        component = self.components[source_component]
        history = component.history

        if not history.points:
            logger.warning(f"No historical data available for component '{source_component}'")
            return {var: 0.0 for var in variables}

        # Find the bracketing time points
        left_point = None
        right_point = None

        for i, point in enumerate(history.points):
            if point.time <= target_time:
                left_point = point
            if point.time >= target_time and right_point is None:
                right_point = point
                break

        # Handle extrapolation cases
        if left_point is None:
            # Before first data point - use extrapolation
            return self._extrapolate_data(history.points[:2], target_time, variables,
                                        TimeExtrapolationMethod.LINEAR)

        if right_point is None:
            # After last data point - use extrapolation
            return self._extrapolate_data(history.points[-2:], target_time, variables,
                                        TimeExtrapolationMethod.LINEAR)

        # Exact match
        if abs(left_point.time - target_time) < 1e-9:
            return {var: left_point.data.get(var, 0.0) for var in variables}

        if abs(right_point.time - target_time) < 1e-9:
            return {var: right_point.data.get(var, 0.0) for var in variables}

        # Interpolation between two points
        return self._interpolate_between_points(left_point, right_point, target_time, variables, method)

    def _interpolate_between_points(
        self,
        left_point: TimePoint,
        right_point: TimePoint,
        target_time: float,
        variables: List[str],
        method: TimeInterpolationMethod
    ) -> Dict[str, Any]:
        """Interpolate between two time points."""
        result = {}

        # Time interpolation factor
        dt = right_point.time - left_point.time
        if dt == 0:
            # Same time point
            return {var: left_point.data.get(var, 0.0) for var in variables}

        alpha = (target_time - left_point.time) / dt

        for var in variables:
            left_val = left_point.data.get(var, 0.0)
            right_val = right_point.data.get(var, 0.0)

            if method == TimeInterpolationMethod.LINEAR:
                result[var] = left_val + alpha * (right_val - left_val)

            elif method == TimeInterpolationMethod.NEAREST:
                result[var] = right_val if alpha > 0.5 else left_val

            elif method == TimeInterpolationMethod.WEIGHTED_AVERAGE:
                # Weighted by inverse distance
                w_left = 1.0 - alpha
                w_right = alpha
                result[var] = w_left * left_val + w_right * right_val

            elif method == TimeInterpolationMethod.CUBIC_SPLINE:
                # For cubic spline, we'd need more points - fall back to linear for now
                logger.warning("Cubic spline interpolation not fully implemented, using linear")
                result[var] = left_val + alpha * (right_val - left_val)

            else:
                raise ValueError(f"Unknown interpolation method: {method}")

        return result

    def _extrapolate_data(
        self,
        points: List[TimePoint],
        target_time: float,
        variables: List[str],
        method: TimeExtrapolationMethod
    ) -> Dict[str, Any]:
        """Extrapolate data beyond available time points."""
        if not points:
            return {var: 0.0 for var in variables}

        result = {}

        for var in variables:
            if method == TimeExtrapolationMethod.CONSTANT:
                # Use the last known value
                result[var] = points[-1].data.get(var, 0.0)

            elif method == TimeExtrapolationMethod.ZERO:
                result[var] = 0.0

            elif method == TimeExtrapolationMethod.LINEAR:
                if len(points) < 2:
                    # Not enough points for linear extrapolation - use constant
                    result[var] = points[-1].data.get(var, 0.0)
                else:
                    # Linear extrapolation using last two points
                    p1, p2 = points[-2], points[-1]
                    dt = p2.time - p1.time
                    if dt != 0:
                        dv = p2.data.get(var, 0.0) - p1.data.get(var, 0.0)
                        slope = dv / dt
                        result[var] = p2.data.get(var, 0.0) + slope * (target_time - p2.time)
                    else:
                        result[var] = p2.data.get(var, 0.0)

            elif method == TimeExtrapolationMethod.PERIODIC:
                # Assume periodic behavior - this would need more sophisticated implementation
                logger.warning("Periodic extrapolation not fully implemented, using constant")
                result[var] = points[-1].data.get(var, 0.0)

            else:
                raise ValueError(f"Unknown extrapolation method: {method}")

        return result

    def exchange_data(
        self,
        coupling: CouplingEntry,
        interpolation_method: TimeInterpolationMethod = TimeInterpolationMethod.LINEAR
    ) -> None:
        """
        Exchange data between coupled components according to coupling specification.

        Args:
            coupling: Coupling specification
            interpolation_method: Method for time interpolation
        """
        source_comp = coupling.source_model
        target_comp = coupling.target_model

        if source_comp not in self.components or target_comp not in self.components:
            raise ValueError(f"Unknown component in coupling: {source_comp} -> {target_comp}")

        target_component = self.components[target_comp]
        target_time = target_component.current_time

        # Get interpolated data from source
        interpolated_data = self.interpolate_data(
            source_comp,
            target_time,
            coupling.source_variables,
            interpolation_method
        )

        # Map source variables to target variables
        mapped_data = {}
        for i, (source_var, target_var) in enumerate(zip(coupling.source_variables, coupling.target_variables)):
            mapped_data[target_var] = interpolated_data.get(source_var, 0.0)

        # Apply transformation if specified
        if coupling.transformation:
            mapped_data = self._apply_transformation(mapped_data, coupling.transformation)

        logger.debug(f"Exchanged data from {source_comp} to {target_comp}: {list(mapped_data.keys())}")

        # Note: In a real implementation, this data would be passed to the target component
        # For now, we just log the successful exchange

    def _apply_transformation(self, data: Dict[str, Any], transformation) -> Dict[str, Any]:
        """Apply transformation to coupling data."""
        # This is a placeholder - in a real implementation, this would apply
        # the mathematical transformation specified in the coupling
        logger.debug(f"Applied transformation to coupling data")
        return data

    def get_synchronization_summary(self) -> Dict[str, Any]:
        """Get a summary of current synchronization state."""
        component_states = {}
        for name, comp in self.components.items():
            component_states[name] = {
                'current_time': comp.current_time,
                'next_update_time': comp.next_update_time,
                'time_step_seconds': comp.time_step.to_seconds(),
                'history_length': len(comp.history.points)
            }

        return {
            'master_time': self.master_time,
            'alignment_strategy': self.alignment_strategy.value,
            'next_sync_time': self.get_next_sync_time(),
            'num_components': len(self.components),
            'num_couplings': len(self.couplings),
            'components': component_states
        }


def synchronize_coupled_system(
    components: Dict[str, Tuple[TimeStep, Dict[str, Any]]],
    couplings: List[CouplingEntry],
    simulation_duration: float,
    alignment_strategy: TimeAlignmentStrategy = TimeAlignmentStrategy.SYNCHRONOUS,
    interpolation_method: TimeInterpolationMethod = TimeInterpolationMethod.LINEAR
) -> Dict[str, Any]:
    """
    High-level function to synchronize a coupled system simulation.

    Args:
        components: Dict mapping component names to (time_step, initial_data) tuples
        couplings: List of coupling relationships
        simulation_duration: Total simulation time in seconds
        alignment_strategy: Time alignment strategy
        interpolation_method: Method for temporal interpolation

    Returns:
        Dictionary containing simulation results and timing information
    """
    synchronizer = TimeSynchronizer()
    synchronizer.set_alignment_strategy(alignment_strategy)

    # Register components
    for name, (time_step, initial_data) in components.items():
        synchronizer.register_component(name, time_step)
        # Add initial data point
        synchronizer.components[name].add_data_point(initial_data)

    # Register couplings
    for coupling in couplings:
        synchronizer.register_coupling(coupling)

    # Run simulation
    simulation_steps = 0
    while synchronizer.master_time < simulation_duration:
        # Advance to next sync time
        current_time = synchronizer.advance_to_sync_time()

        # Process couplings at sync time
        for coupling in couplings:
            try:
                synchronizer.exchange_data(coupling, interpolation_method)
            except Exception as e:
                logger.warning(f"Failed to exchange data for coupling {coupling.source_model}->{coupling.target_model}: {e}")

        simulation_steps += 1

        # Safety check to prevent infinite loops
        if simulation_steps > 1000000:
            logger.warning("Simulation exceeded maximum steps, terminating")
            break

    # Return summary
    summary = synchronizer.get_synchronization_summary()
    summary['simulation_steps'] = simulation_steps
    summary['final_time'] = synchronizer.master_time

    return summary


# Convenience functions for common use cases

def create_subcycling_synchronizer(
    fast_component: Tuple[str, TimeStep],
    slow_component: Tuple[str, TimeStep],
    coupling_variables: Tuple[List[str], List[str]]
) -> TimeSynchronizer:
    """
    Create a synchronizer for a typical fast-slow subcycling scenario.

    Args:
        fast_component: (name, time_step) for the fast component
        slow_component: (name, time_step) for the slow component
        coupling_variables: (fast_vars, slow_vars) for coupling

    Returns:
        Configured TimeSynchronizer
    """
    synchronizer = TimeSynchronizer()
    synchronizer.set_alignment_strategy(TimeAlignmentStrategy.SUBCYCLING)

    # Register components
    fast_name, fast_timestep = fast_component
    slow_name, slow_timestep = slow_component
    synchronizer.register_component(fast_name, fast_timestep)
    synchronizer.register_component(slow_name, slow_timestep)

    # Create bidirectional coupling
    fast_vars, slow_vars = coupling_variables

    # Fast -> Slow coupling (typically aggregated)
    fast_to_slow = CouplingEntry(
        source_model=fast_name,
        target_model=slow_name,
        source_variables=fast_vars,
        target_variables=slow_vars,
        coupling_type=CouplingType.AGGREGATED
    )
    synchronizer.register_coupling(fast_to_slow)

    # Slow -> Fast coupling (typically interpolated)
    slow_to_fast = CouplingEntry(
        source_model=slow_name,
        target_model=fast_name,
        source_variables=slow_vars,
        target_variables=fast_vars,
        coupling_type=CouplingType.INTERPOLATED
    )
    synchronizer.register_coupling(slow_to_fast)

    return synchronizer


def validate_time_synchronization_config(
    components: Dict[str, TimeStep],
    couplings: List[CouplingEntry]
) -> Tuple[bool, List[str]]:
    """
    Validate a time synchronization configuration.

    Args:
        components: Component name -> TimeStep mapping
        couplings: List of couplings

    Returns:
        (is_valid, list_of_errors)
    """
    errors = []

    # Check that all coupling components are defined
    for coupling in couplings:
        if coupling.source_model not in components:
            errors.append(f"Coupling source '{coupling.source_model}' not found in components")
        if coupling.target_model not in components:
            errors.append(f"Coupling target '{coupling.target_model}' not found in components")

    # Check for reasonable time step ratios
    if len(components) >= 2:
        time_steps = [ts.to_seconds() for ts in components.values()]
        max_ratio = max(time_steps) / min(time_steps)
        if max_ratio > 1000:
            errors.append(f"Large time step ratio detected ({max_ratio:.1f}), may cause numerical issues")

    # Check for circular dependencies (simplified check)
    component_deps = {name: set() for name in components.keys()}
    for coupling in couplings:
        component_deps[coupling.target_model].add(coupling.source_model)

    # Simple cycle detection using DFS
    def has_cycle(node, visited, rec_stack):
        visited.add(node)
        rec_stack.add(node)

        for neighbor in component_deps.get(node, []):
            if neighbor not in visited:
                if has_cycle(neighbor, visited, rec_stack):
                    return True
            elif neighbor in rec_stack:
                return True

        rec_stack.remove(node)
        return False

    visited = set()
    for component in components:
        if component not in visited:
            if has_cycle(component, visited, set()):
                errors.append("Circular dependency detected in coupling graph")
                break

    return len(errors) == 0, errors