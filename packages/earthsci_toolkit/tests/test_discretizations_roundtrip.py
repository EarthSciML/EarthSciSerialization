"""
Round-trip tests for the §7 ``discretizations`` top-level schema, including
the §7.4 ``CrossMetricStencilRule`` composite variant (esm-vwo).

Exercises the Python binding's parse + round-trip contract for each
shared discretization fixture at ``tests/discretizations/*.esm``. The
Python binding holds discretization entries opaquely as plain dicts
because stencil coefficients and applies_to patterns carry pattern-
variable strings that don't map onto the Expression coercion pipeline;
the round-trip contract is structural equivalence of the top-level
``discretizations`` subtree.
"""

import json
from pathlib import Path

import pytest

from earthsci_toolkit import load, save


REPO_ROOT = Path(__file__).resolve().parents[3]
DISC_DIR = REPO_ROOT / "tests" / "discretizations"


FIXTURES = [
    "centered_2nd_uniform",
    "upwind_1st_advection",
    "periodic_bc",
    "mpas_cell_div",
    "cross_metric_cartesian",
]


@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_discretization_roundtrip(fixture_name: str) -> None:
    """discretizations subtree survives load -> save -> reload unchanged."""
    fixture_path = DISC_DIR / f"{fixture_name}.esm"
    original = json.loads(fixture_path.read_text())

    esm = load(fixture_path)
    reserialized = json.loads(save(esm))

    assert "discretizations" in reserialized, (
        f"{fixture_name}: `discretizations` dropped on save"
    )
    assert reserialized["discretizations"] == original["discretizations"], (
        f"{fixture_name}: discretizations subtree drifted on round-trip"
    )

    # Second hop must also be a fixed point (guards against normalization
    # that only applies on the first pass).
    esm2 = load(json.dumps(reserialized))
    reserialized2 = json.loads(save(esm2))
    assert reserialized2["discretizations"] == original["discretizations"], (
        f"{fixture_name}: drift on second-hop round-trip"
    )


def test_cross_metric_composite_structure() -> None:
    """The §7.4 composite entry is structurally recognizable after parse."""
    fixture_path = DISC_DIR / "cross_metric_cartesian.esm"
    esm = load(fixture_path)

    assert "laplacian_full_covariant_toy" in esm.discretizations
    composite = esm.discretizations["laplacian_full_covariant_toy"]
    assert composite["kind"] == "cross_metric"
    assert composite["axes"] == ["xi", "eta"]
    assert isinstance(composite["terms"], list)
    assert len(composite["terms"]) == 2
    # Composite entries do NOT carry a stencil key (it is the standard-
    # discretization variant's discriminator).
    assert "stencil" not in composite

    # Per-axis stencils should still be present and carry a stencil key.
    assert esm.discretizations["d2_dxi2_uniform"]["stencil"]
    assert esm.discretizations["d2_deta2_uniform"]["stencil"]
