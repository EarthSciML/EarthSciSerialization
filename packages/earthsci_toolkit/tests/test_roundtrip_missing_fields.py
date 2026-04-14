"""Test for round-trip preservation of previously missing fields: events, data_loaders, operators, couplings, solvers."""

import json
import pytest

from earthsci_toolkit.esm_types import (
    EsmFile, Metadata, DataLoader, DataLoaderKind, DataLoaderSource,
    DataLoaderVariable, DataLoaderTemporal, DataLoaderSpatial, Operator,
    VariableMapCoupling, CouplingType, ContinuousEvent, AffectEquation
)
from earthsci_toolkit.serialize import save


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
        kind=DataLoaderKind.GRID,
        source=DataLoaderSource(url_template="file:///data/test_{date:%Y%m%d}.nc"),
        variables={
            "temperature": DataLoaderVariable(
                file_variable="T", units="K", description="Air temperature"
            ),
            "pressure": DataLoaderVariable(
                file_variable="P", units="Pa", description="Air pressure"
            ),
        },
        spatial=DataLoaderSpatial(crs="EPSG:4326", grid_type="latlon"),
    )

    # Create ESM file
    esm_file = EsmFile(
        version="0.1.0",
        metadata=metadata,
        models={},
        reaction_systems={},
        events=[],
        data_loaders={"test_loader": data_loader},
        operators=[],
        coupling=[],
        domains={},
    )

    # Serialize to JSON
    json_str = save(esm_file)
    data = json.loads(json_str)

    # Verify data_loaders field is present
    assert "data_loaders" in data
    assert "test_loader" in data["data_loaders"]

    loader_data = data["data_loaders"]["test_loader"]
    assert loader_data["kind"] == "grid"
    assert loader_data["source"]["url_template"] == "file:///data/test_{date:%Y%m%d}.nc"
    assert "variables" in loader_data
    assert loader_data["variables"]["temperature"]["file_variable"] == "T"
    assert loader_data["variables"]["temperature"]["units"] == "K"


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
        models={},
        reaction_systems={},
        events=[],
        data_loaders={},
        operators=[operator],
        coupling=[],
        domains={},
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
    coupling = VariableMapCoupling(
        from_var="model1.x",
        to_var="model2.y",
    )

    # Create ESM file
    esm_file = EsmFile(
        version="0.1.0",
        metadata=metadata,
        models={},
        reaction_systems={},
        events=[],
        data_loaders={},
        operators=[],
        coupling=[coupling],
        domains={},
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
        models={},
        reaction_systems={},
        events=[event],
        data_loaders={},
        operators=[],
        coupling=[],
        domains={},
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
        kind=DataLoaderKind.GRID,
        source=DataLoaderSource(url_template="file:///data/emissions_{date:%Y%m}.nc"),
        variables={
            "temp": DataLoaderVariable(file_variable="T", units="K"),
        },
    )

    operator = Operator(
        operator_id="operator",
        needed_vars=["temp"],
        modifies=["processed_temp"],
        config={}
    )

    coupling = VariableMapCoupling(
        from_var="m1.a",
        to_var="m2.b",
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
        models={},
        reaction_systems={},
        events=[event],
        data_loaders={"loader": data_loader},
        operators=[operator],
        coupling=[coupling],
        domains={},
    )

    # Serialize to JSON
    json_str = save(esm_file)
    data = json.loads(json_str)

    # Verify all fields are present
    assert "data_loaders" in data
    assert "operators" in data
    assert "coupling" in data
    assert "continuous_events" in data

    # Verify they have the expected content
    assert "loader" in data["data_loaders"]
    assert "operator" in data["operators"]
    assert len(data["coupling"]) == 1
    assert len(data["continuous_events"]) == 1