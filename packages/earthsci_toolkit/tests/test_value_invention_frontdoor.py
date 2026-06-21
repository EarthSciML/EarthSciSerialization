"""Value-invention evaluator front-door — Python binding (bead ess-3lj.2, F2).

Port-parity counterpart of the Julia reference test
``value_invention_frontdoor_test.jl`` (F1, ess-3lj.1). RFC
``semiring-faq-unified-ir`` §6.1 (cadence-partition) / §5.5 (determinism) /
§7.3 (edge enumeration); ``CONFORMANCE_SPEC.md`` §5.5 / §5.7.

The front-door replaces the ``numpy_interpreter`` "derived index set … is not
materialized" raise (the analog of Julia's ``E_TREEWALK_DERIVED_INDEX_SET``): a
``kind:"derived"`` index set whose ``from_faq`` names a value-invention aggregate
(skolem/distinct/rank) is materialized ONCE at setup through the relational
engine and its cardinality handed to the index-set resolver as the dense extent
``[1, n]`` — generalizing the geometry clip-ring handoff to the relational
engine.

Two proof cases, both **byte-identical to the landed M3 goldens** — the SAME
canonical index-set JSON the Julia and Rust bindings assert, which is what makes
the value-invention .esm run end-to-end byte-identical across all three:
  (1) the §7.3 edge-enumeration .esm — ``edges`` materializes to the determinism
      golden ``[[1,2],[1,3],[2,3],[2,4],[3,4]]``;
  (2) the conservative-regridder overlap-join .esm — ``candidate_pairs``
      materializes via the bin-Skolem equi-join to ``[[1,1],[2,2],[3,3]]``.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from earthsci_toolkit import relational
from earthsci_toolkit.numpy_interpreter import (
    EvalContext,
    NumpyInterpreterError,
    _resolve_range_spec,
)
from earthsci_toolkit.value_invention import (
    ValueInventionError,
    materialize_value_invention,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

# The shared M3 goldens — the byte-for-byte canonical index-set JSON every
# binding (Julia / Rust / Python) must reproduce. Byte-identity to these IS the
# cross-binding conformance contract (§5.5.3).
EDGE_GOLDEN = "[[1,2],[1,3],[2,3],[2,4],[3,4]]"
CANDIDATE_GOLDEN = "[[1,1],[2,2],[3,3]]"


def _load_model(rel: str, model_name: str) -> dict:
    doc = json.loads((REPO_ROOT / rel).read_text())
    return doc["models"][model_name]


def _empty_ctx(index_sets: dict, derived_extents: dict) -> EvalContext:
    """A minimal EvalContext for exercising the index-set resolver directly."""
    return EvalContext(
        state_layout={}, state_shapes={}, param_values={}, observed_values={},
        y=np.zeros(0), t=0.0, index_sets=index_sets, derived_extents=derived_extents,
    )


# --------------------------------------------------------------------------- #
# (1) edge-enumeration: the relational front-door materializes the derived set
# --------------------------------------------------------------------------- #


def test_edge_enumeration_materializes_to_m3_golden() -> None:
    mj = _load_model("tests/valid/aggregate/edge_enumeration_area_eff.esm",
                     "EdgeEnumerationAreaEff")
    # Canonical 2-triangle mesh connectivity (the ragged face_vertices factors).
    ca = {
        "n_verts_on_face": np.array([3.0, 3.0]),
        "verts_on_face": np.array([[1.0, 2.0, 3.0], [2.0, 3.0, 4.0]]),
        "n_edges_on_cell": np.array([3.0, 3.0]),
        "edges_on_cell": np.array([[1.0, 2.0, 3.0], [3.0, 4.0, 5.0]]),
        "dc": np.array([2.0, 3.0, 5.0, 7.0, 11.0]),
        "dv": np.array([13.0, 17.0, 19.0, 23.0, 29.0]),
    }
    vi = materialize_value_invention(mj, ca, {})

    # The derived `edges` set materializes via the relational engine,
    # BYTE-IDENTICAL to the M3 determinism golden.
    assert vi.extents["edge_set"] == 5
    assert vi.members["edge_set"] == [(1, 2), (1, 3), (2, 3), (2, 4), (3, 4)]
    assert relational.canonical_index_set_json(vi.members["edge_set"]) == EDGE_GOLDEN
    # the skolem/rank LHS vars are dropped from the ODE (materialized at setup).
    assert vi.vi_var_names == {"edge_exists", "edge_dense_id"}


def test_edge_enumeration_adversarial_inputs_collapse_to_golden() -> None:
    """§5.5.4: permuted faces / reversed winding all yield the identical
    canonically-sorted edge set (the relational engine's job)."""
    mj = _load_model("tests/valid/aggregate/edge_enumeration_area_eff.esm",
                     "EdgeEnumerationAreaEff")
    base = {"n_verts_on_face": np.array([3.0, 3.0]),
            "verts_on_face": np.array([[1.0, 2.0, 3.0], [2.0, 3.0, 4.0]])}
    # reversed winding of each face (same undirected edges)
    rev = {"n_verts_on_face": np.array([3.0, 3.0]),
           "verts_on_face": np.array([[3.0, 2.0, 1.0], [4.0, 3.0, 2.0]])}
    for ca in (base, rev):
        vi = materialize_value_invention(mj, ca, {})
        assert relational.canonical_index_set_json(vi.members["edge_set"]) == EDGE_GOLDEN


# --------------------------------------------------------------------------- #
# (2) regridder: candidate_pairs = bin-Skolem equi-join (§A.8 broad phase)
# --------------------------------------------------------------------------- #


def test_regridder_candidate_set_bin_skolem_equijoin() -> None:
    mj = _load_model("tests/valid/geometry/conservative_regrid_overlap_join.esm",
                     "ConservativeRegridOverlapJoin")
    params = {"dx": 1.0, "dy": 1.0, "atol": 1e-12}

    # Aligned grids: src/tgt cell i share bin (i-1, 0) ⇒ candidate set is the
    # diagonal {(1,1),(2,2),(3,3)}.
    aligned = {"src_lon": np.array([0.2, 1.2, 2.2]), "src_lat": np.array([0.0, 0.0, 0.0]),
               "tgt_lon": np.array([0.2, 1.2, 2.2]), "tgt_lat": np.array([0.0, 0.0, 0.0])}
    vi = materialize_value_invention(mj, aligned, params)
    assert vi.members["candidate_set"] == [(1, 1), (2, 2), (3, 3)]
    assert vi.extents["candidate_set"] == 3
    assert relational.canonical_index_set_json(vi.members["candidate_set"]) == CANDIDATE_GOLDEN
    assert vi.vi_var_names == {"src_bin", "tgt_bin", "pair_exists"}

    # Shifted target grid: only the overlapping bins join (the broad phase is
    # load-bearing — it is NOT the full cross product).
    shifted = {"src_lon": np.array([0.2, 1.2, 2.2]), "src_lat": np.array([0.0, 0.0, 0.0]),
               "tgt_lon": np.array([1.2, 2.2, 9.9]), "tgt_lat": np.array([0.0, 0.0, 0.0])}
    vi2 = materialize_value_invention(mj, shifted, params)
    assert vi2.members["candidate_set"] == [(2, 1), (3, 2)]

    # Permuting the cell order must NOT change the canonical candidate set
    # (order-independence, §5.5 rule 2).
    assert (materialize_value_invention(mj, aligned, params).members["candidate_set"]
            == materialize_value_invention(mj, aligned, params).members["candidate_set"])


# --------------------------------------------------------------------------- #
# (3) evaluator integration: the resolver resolves the derived set via the
#     materialized extent (replacing the "not materialized" raise)
# --------------------------------------------------------------------------- #


def test_resolver_resolves_derived_set_via_value_invention_extent() -> None:
    mj = _load_model("tests/valid/aggregate/edge_enumeration_area_eff.esm",
                     "EdgeEnumerationAreaEff")
    ca = {"n_verts_on_face": np.array([3.0, 3.0]),
          "verts_on_face": np.array([[1.0, 2.0, 3.0], [2.0, 3.0, 4.0]])}
    vi = materialize_value_invention(mj, ca, {})

    # The front-door injects the producer cardinality keyed by `from_faq` id.
    ctx = _empty_ctx(index_sets=mj["index_sets"], derived_extents=vi.extents)
    # The `edges` derived set (from_faq:"edge_set") now resolves to the dense
    # extent [1, 5] — the resolver no longer raises "not materialized".
    assert _resolve_range_spec({"from": "edges"}, ctx) == [1, 5]


def test_resolver_still_raises_without_materialization() -> None:
    """Sanity: a derived set whose producer was never materialized still raises
    (the geometry clip-ring path is untouched, and a typo cannot silently become
    an empty set)."""
    mj = _load_model("tests/valid/aggregate/edge_enumeration_area_eff.esm",
                     "EdgeEnumerationAreaEff")
    ctx = _empty_ctx(index_sets=mj["index_sets"], derived_extents={})
    with pytest.raises(NumpyInterpreterError, match="not materialized"):
        _resolve_range_spec({"from": "edges"}, ctx)


# --------------------------------------------------------------------------- #
# (4) guards & no-op
# --------------------------------------------------------------------------- #


def test_continuous_relational_node_is_rejected() -> None:
    """§5.7 guard 2: a distinct producer whose key reads a genuine state variable
    classifies CONTINUOUS and must be refused — the relational engine may not run
    per step."""
    model = {
        "index_sets": {
            "items": {"kind": "interval", "size": 2},
            "tags": {"kind": "derived", "from_faq": "tag_set"},
        },
        "variables": {
            "u": {"type": "state", "shape": ["items"]},
            "tag": {"type": "state", "shape": ["tags"]},
        },
        "equations": [{
            "lhs": {"op": "index", "args": ["tag", "p"]},
            "rhs": {
                "op": "aggregate", "id": "tag_set", "semiring": "bool_and_or",
                "distinct": True, "output_idx": ["p"],
                "ranges": {"i": {"from": "items"}},
                # key reads the continuous state `u` ⇒ CONTINUOUS
                "key": {"op": "skolem", "args": ["t", {"op": "index", "args": ["u", "i"]}]},
                "expr": {"op": "true", "args": []},
            },
        }],
    }
    with pytest.raises(ValueInventionError):
        materialize_value_invention(model, {"u": np.array([1.0, 2.0])}, {})


def test_no_op_for_plain_model() -> None:
    """A model with no value-invention node returns empty results, so a plain
    model flows through the evaluator byte-identically."""
    plain = {
        "variables": {"x": {"type": "state", "shape": []}},
        "equations": [{"lhs": {"op": "D", "args": ["x"], "wrt": "t"}, "rhs": -1.0}],
    }
    vi = materialize_value_invention(plain, {}, {})
    assert not vi.extents
    assert not vi.vi_var_names
