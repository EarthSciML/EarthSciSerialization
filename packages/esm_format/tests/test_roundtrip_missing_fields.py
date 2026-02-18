"""Test for round-trip preservation of previously missing fields: events, data_loaders, operators, couplings, solvers."""

import json
import pytest

from esm_format.esm_types import (
    EsmFile, Metadata, DataLoader, DataLoaderType, Operator,
    CouplingEntry, CouplingType, Solver, SolverType, ContinuousEvent, AffectEquation
)
from esm_format.serialize import save


def test_roundtrip_preserves_data_loaders():
    """Test that data loaders are preserved through serialization."""
    # Create minimal metadata
    metadata = Metadata(
        title="Data Loader Test",
        description="Test data loader preservation",
        authors=[],
        created=None,
        modified=None,
        version="1.0",
        references=[],
        keywords=[]
    )

    # Create data loader
    data_loader = DataLoader(
        name="test_loader",
        type=DataLoaderType.GRIDDED_DATA,
        source="test_data.nc",
        format_options={"param1": "value1"},
        variables=["temperature", "pressure"]
    )

    # Create ESM file
    esm_file = EsmFile(
        version="0.1.0",
        metadata=metadata,
        models=[],
        reaction_systems=[],
        events=[],
        data_loaders=[data_loader],
        operators=[],
        couplings=[],
        domains=[],
        solvers=[]
    )

    # Serialize to JSON
    json_str = save(esm_file)
    data = json.loads(json_str)

    # Verify data_loaders field is present
    assert "data_loaders" in data
    assert "test_loader" in data["data_loaders"]

    loader_data = data["data_loaders"]["test_loader"]
    assert loader_data["type"] == "gridded_data"  # NETCDF maps to gridded_data
    assert loader_data["loader_id"] == "test_data.nc"
    assert "config" in loader_data
    assert "provides" in loader_data


def test_roundtrip_preserves_operators():
    """Test that operators are preserved through serialization."""
    metadata = Metadata(
        title="Operator Test",
        description="Test operator preservation",
        authors=[],
        created=None,
        modified=None,
        version="1.0",
        references=[],
        keywords=[]
    )

    # Create operator
    operator = Operator(
        operator_id="test_operator",
        needed_vars=["x", "y"],
        modifies=["z"],
        config={"param1": "value1", "param2": 42}
    )

    # Create ESM file
    esm_file = EsmFile(
        version="0.1.0",
        metadata=metadata,
        models=[],
        reaction_systems=[],
        events=[],
        data_loaders=[],
        operators=[operator],
        couplings=[],
        domains=[],
        solvers=[]
    )

    # Serialize to JSON
    json_str = save(esm_file)
    data = json.loads(json_str)

    # Verify operators field is present
    assert "operators" in data
    assert "test_operator" in data["operators"]

    operator_data = data["operators"]["test_operator"]
    assert operator_data["operator_id"] == "test_operator"
    assert operator_data["config"]["param1"] == "value1"
    assert operator_data["config"]["param2"] == 42
    assert operator_data["needed_vars"] == ["x", "y"]
    assert operator_data["modifies"] == ["z"]


def test_roundtrip_preserves_couplings():
    """Test that coupling entries are preserved through serialization."""
    metadata = Metadata(
        title="Coupling Test",
        description="Test coupling preservation",
        authors=[],
        created=None,
        modified=None,
        version="1.0",
        references=[],
        keywords=[]
    )

    # Create coupling entry
    coupling = CouplingEntry(
        source_model="model1",
        target_model="model2",
        source_variables=["x"],
        target_variables=["y"],
        coupling_type=CouplingType.DIRECT,
        transformation=None
    )

    # Create ESM file
    esm_file = EsmFile(
        version="0.1.0",
        metadata=metadata,
        models=[],
        reaction_systems=[],
        events=[],
        data_loaders=[],
        operators=[],
        couplings=[coupling],
        domains=[],
        solvers=[]
    )

    # Serialize to JSON
    json_str = save(esm_file)
    data = json.loads(json_str)

    # Verify coupling field is present
    assert "coupling" in data
    assert len(data["coupling"]) == 1

    coupling_data = data["coupling"][0]
    assert coupling_data["type"] == "variable_map"
    assert coupling_data["from"] == "model1.x"
    assert coupling_data["to"] == "model2.y"


def test_roundtrip_preserves_solvers():
    """Test that solvers are preserved through serialization."""
    metadata = Metadata(
        title="Solver Test",
        description="Test solver preservation",
        authors=[],
        created=None,
        modified=None,
        version="1.0",
        references=[],
        keywords=[]
    )

    # Create solver
    solver = Solver(
        name="test_solver",
        type=SolverType.ODE,
        algorithm="imex",
        parameters={"max_steps": 1000},
        tolerances={"absolute": 1e-8, "relative": 1e-6}
    )

    # Create ESM file
    esm_file = EsmFile(
        version="0.1.0",
        metadata=metadata,
        models=[],
        reaction_systems=[],
        events=[],
        data_loaders=[],
        operators=[],
        couplings=[],
        domains=[],
        solvers=[solver]
    )

    # Serialize to JSON
    json_str = save(esm_file)
    data = json.loads(json_str)

    # Verify solver field is present
    assert "solver" in data

    solver_data = data["solver"]
    assert solver_data["strategy"] == "imex"
    assert solver_data["config"]["max_steps"] == 1000
    assert solver_data["config"]["stiff_kwargs"]["abstol"] == 1e-8
    assert solver_data["config"]["stiff_kwargs"]["reltol"] == 1e-6


def test_roundtrip_preserves_events():
    """Test that events are preserved through serialization."""
    metadata = Metadata(
        title="Event Test",
        description="Test event preservation",
        authors=[],
        created=None,
        modified=None,
        version="1.0",
        references=[],
        keywords=[]
    )

    # Create continuous event
    event = ContinuousEvent(
        name="test_event",
        conditions=["x > 5.0"],  # Changed to array
        affects=[AffectEquation(lhs="y", rhs="0.0")],
        priority=1
    )

    # Create ESM file
    esm_file = EsmFile(
        version="0.1.0",
        metadata=metadata,
        models=[],
        reaction_systems=[],
        events=[event],
        data_loaders=[],
        operators=[],
        couplings=[],
        domains=[],
        solvers=[]
    )

    # Serialize to JSON
    json_str = save(esm_file)
    data = json.loads(json_str)

    # Verify events are present
    assert "continuous_events" in data
    assert len(data["continuous_events"]) == 1

    event_data = data["continuous_events"][0]
    assert event_data["name"] == "test_event"
    assert event_data["priority"] == 1
    assert len(event_data["conditions"]) == 1
    assert len(event_data["affects"]) == 1


def test_roundtrip_preserves_all_missing_fields():
    """Test that all previously missing fields are preserved together."""
    metadata = Metadata(
        title="Complete Test",
        description="Test all missing field preservation",
        authors=[],
        created=None,
        modified=None,
        version="1.0",
        references=[],
        keywords=[]
    )

    # Create all components
    data_loader = DataLoader(
        name="loader",
        type=DataLoaderType.EMISSIONS,
        source="data.csv",
        format_options={},
        variables=["temp"]
    )

    operator = Operator(
        operator_id="operator",
        needed_vars=["temp"],
        modifies=["processed_temp"],
        config={}
    )

    coupling = CouplingEntry(
        source_model="m1",
        target_model="m2",
        source_variables=["a"],
        target_variables=["b"],
        coupling_type=CouplingType.DIRECT,
        transformation=None
    )

    solver = Solver(
        name="solver",
        type=SolverType.ODE,
        algorithm="strang_serial",
        parameters={},
        tolerances={}
    )

    event = ContinuousEvent(
        name="event",
        conditions=["t > 10"],  # Changed to array
        affects=[AffectEquation(lhs="x", rhs="1.0")],
        priority=0
    )

    # Create ESM file with all components
    esm_file = EsmFile(
        version="0.1.0",
        metadata=metadata,
        models=[],
        reaction_systems=[],
        events=[event],
        data_loaders=[data_loader],
        operators=[operator],
        couplings=[coupling],
        domains=[],
        solvers=[solver]
    )

    # Serialize to JSON
    json_str = save(esm_file)
    data = json.loads(json_str)

    # Verify all fields are present
    assert "data_loaders" in data
    assert "operators" in data
    assert "coupling" in data
    assert "solver" in data
    assert "continuous_events" in data

    # Verify they have the expected content
    assert "loader" in data["data_loaders"]
    assert "operator" in data["operators"]
    assert len(data["coupling"]) == 1
    assert data["solver"]["strategy"] == "strang_serial"
    assert len(data["continuous_events"]) == 1