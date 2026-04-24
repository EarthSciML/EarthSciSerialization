"""Round-trip tests for §7.4 `staggering_rules` top-level schema (esm-15f)."""

import copy
import json
from pathlib import Path

import pytest

from earthsci_toolkit import load, save
from earthsci_toolkit.esm_types import StaggeringRule


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = REPO_ROOT / "tests" / "grids" / "mpas_c_grid_staggering.esm"


def test_mpas_c_grid_staggering_loads():
    esm = load(FIXTURE)
    assert "mpas_c_grid_staggering" in esm.staggering_rules
    rule = esm.staggering_rules["mpas_c_grid_staggering"]
    assert isinstance(rule, StaggeringRule)
    assert rule.kind == "unstructured_c_grid"
    assert rule.grid == "mpas_cvmesh"
    assert rule.edge_normal_convention == "outward_from_first_cell"
    assert rule.cell_quantity_locations["u"] == "edge_midpoint"
    assert rule.cell_quantity_locations["zeta"] == "vertex"
    assert rule.cell_quantity_locations["h"] == "cell_center"


def test_mpas_c_grid_staggering_roundtrip():
    esm = load(FIXTURE)
    reserialized = json.loads(save(esm))
    original = json.loads(FIXTURE.read_text())
    assert "staggering_rules" in reserialized
    assert reserialized["staggering_rules"] == original["staggering_rules"]


def test_unstructured_c_grid_requires_unstructured_family():
    """kind='unstructured_c_grid' must reject a cartesian grid reference."""
    data = json.loads(FIXTURE.read_text())
    data["grids"]["mpas_cvmesh"]["family"] = "cartesian"
    data["grids"]["mpas_cvmesh"]["extents"] = {
        "cell": {"n": "nCells", "spacing": "uniform"}
    }
    data["grids"]["mpas_cvmesh"].pop("connectivity", None)
    with pytest.raises(ValueError, match="requires grid family 'unstructured'"):
        load(data)


def test_unstructured_c_grid_rejects_unknown_grid():
    data = json.loads(FIXTURE.read_text())
    data["staggering_rules"]["mpas_c_grid_staggering"]["grid"] = "does_not_exist"
    with pytest.raises(ValueError, match="references unknown grid"):
        load(data)
