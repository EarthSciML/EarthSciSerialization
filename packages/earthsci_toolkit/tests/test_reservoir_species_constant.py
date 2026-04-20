"""Round-trip coverage for Species.constant (reservoir species) — gt-ertm."""

import json
from pathlib import Path

from earthsci_toolkit import load, save


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "tests" / "valid" / "reservoir_species_constant.esm"


def test_reservoir_species_constant_round_trip():
    assert FIXTURE_PATH.is_file(), f"fixture missing: {FIXTURE_PATH}"

    original_json = json.loads(FIXTURE_PATH.read_text())
    parsed = load(str(FIXTURE_PATH))

    rs = parsed.reaction_systems["SuperFastSubset"]
    species_by_name = {sp.name: sp for sp in rs.species}

    for name in ("O2", "CH4", "H2O"):
        assert species_by_name[name].constant is True, f"{name} should be constant=true"
    for name in ("O3", "OH", "HO2"):
        assert species_by_name[name].constant is None, f"{name} should have no constant flag"

    reserialized = json.loads(save(parsed))
    # Scope the equality check to the species map — the Python binding has
    # unrelated key-ordering quirks on parameter objects and drops
    # `element_type` from domain (tracked separately).
    assert (
        reserialized["reaction_systems"]["SuperFastSubset"]["species"]
        == original_json["reaction_systems"]["SuperFastSubset"]["species"]
    ), "species subtree must round-trip byte-identical"
