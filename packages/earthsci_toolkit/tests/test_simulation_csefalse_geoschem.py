"""Inline test for cse=False on geoschem_fullchem (esm-5gk).

The Python canonical simulation pipeline must produce a finite, integrable
RHS on the GEOSChem full-chemistry mechanism (272 species, 819 reactions)
even when the lambdified RHS is built with ``cse=False`` — the cse=False
path is the chosen baseline for the upcoming Python live-repo inline-test
gate (peak RSS ~196 MB vs cse=True's OOM bomb on this size system, per
esm-9ms / esm-c6v).

Before esm-5gk this failed: sympy's lambdify under cse=False emitted
complex-arithmetic decompositions (``re(...)`` / ``im(...)`` /
``angle(...)`` formulas) for ``Abs``/``log``/rational-power expressions
when symbol assumptions did not assert positivity, and for integer-valued
``Float`` exponents (``x**Float(2.0)``). At any species concentration of 0,
those decompositions evaluated to ``inf*0 = NaN`` and the integrator
rejected the very first RHS evaluation as non-finite.

The fix lives in ``earthsci_toolkit.simulation``:

* state and parameter sympy symbols are created with ``positive=True``,
  which is physically correct for chemistry (concentrations,
  temperatures, number densities, pressures are all non-negative);
* ``_expr_to_sympy`` canonicalizes integer-valued ``sp.Float`` exponents
  to ``sp.Integer`` so ``x**2`` from ``"2.0"`` stays on sympy's
  real-domain power simplification path.

This test exercises the canonical ESS pipeline end-to-end (.esm → AST →
ESD rule application via ``flatten`` → official runner ``simulate``) on a
real-world mechanism, with cse=False enforced via a pre-built compile
cache. No shadow evaluator, no per-rule-shape dispatch (per CLAUDE.md
'Simulation Pathway — ABSOLUTE Rule').

OOM guardrails (per CLAUDE.md / esm-5gk):
- This test is opt-in via ``RUN_GEOSCHEM_FULLCHEM_INLINE=1`` because the
  one-shot lambdify on this mechanism takes ~50 s and ~200 MB. Day-to-day
  pytest invocations skip it; the future Python live-repo gate (separate
  ESM bead) sets the env var.
- tspan=60 s keeps the integrator under ~3 minutes wall on cold start.
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path

import numpy as np
import pytest
import sympy as sp


def _locate_geoschem_fullchem() -> Path | None:
    """Walk ancestors looking for the colocated EarthSciModels checkout.

    The .esm fixture lives outside the EarthSciSerialization repo (see the
    sibling EarthSciModels rig). Layouts vary across worktrees and CI
    runners, so we probe the canonical locations rather than hard-coding
    a depth.
    """
    rels = (
        ("EarthSciModels", "refinery", "rig", "components", "gaschem",
         "geoschem_fullchem.esm"),
        ("EarthSciModels", "components", "gaschem", "geoschem_fullchem.esm"),
    )
    here = Path(__file__).resolve()
    for ancestor in (here.parent, *here.parents):
        for rel in rels:
            cand = ancestor.joinpath(*rel)
            if cand.exists():
                return cand.resolve()
    return None


ESM_PATH = _locate_geoschem_fullchem()


# Three GEOSChem species appear in mass-action rate denominators (e.g. R12
# has rate = k_cld6/SO2). When their IC is 0 — which is the default in the
# inline-test ICs — the resulting RHS terms evaluate to 0/0 = NaN
# regardless of binding (Julia's mass_action_rate uses the identical
# substrate-detection heuristic). We seed them with small physically
# reasonable values to exercise the integrator. Tracked separately as a
# model-authoring issue (see esm-5gk notes).
_DENOM_SEED_PPB = {
    "SO2": 0.1,
    "SALAAL": 1e-3,
    "SALCAL": 1e-3,
}


@pytest.mark.skipif(
    os.environ.get("RUN_GEOSCHEM_FULLCHEM_INLINE") != "1",
    reason="opt-in (RUN_GEOSCHEM_FULLCHEM_INLINE=1); ~3 min wall, ~200 MB peak",
)
@pytest.mark.skipif(
    ESM_PATH is None,
    reason="requires a colocated EarthSciModels checkout providing "
           "components/gaschem/geoschem_fullchem.esm",
)
def test_geoschem_fullchem_cse_false_finite_rhs():
    import earthsci_toolkit as ek
    from earthsci_toolkit.simulation import (
        _CompiledRhs,
        _flat_to_sympy_rhs,
        simulate,
    )

    esm_file = ek.load(str(ESM_PATH))
    rs = esm_file.reaction_systems["GEOSChemGasPhase"]
    test_ic = rs.tests[0]
    flat = ek.flatten(esm_file)

    # Build the compile cache ourselves with cse=False — bypasses the
    # default cse=True path that OOMs on this mechanism (esm-c6v).
    (
        state_names,
        parameter_names,
        symbol_map,
        rhs_exprs,
        alg_state_names,
        alg_value_exprs,
    ) = _flat_to_sympy_rhs(flat)

    # Sanity check that the symbolic RHS is real-valued: any leftover
    # ``re``/``im``/``arg`` would re-introduce the cse=False NaN failure.
    for e in rhs_exprs:
        for sub in sp.preorder_traversal(e):
            assert not isinstance(sub, (sp.re, sp.im, sp.arg)), (
                "lambdify-time complex-domain decomposition leaked into "
                "rhs_exprs — see esm-5gk"
            )

    state_symbols = [symbol_map[n] for n in state_names]
    param_symbols = [symbol_map[n] for n in parameter_names]
    all_args = state_symbols + param_symbols

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        rhs_vec = sp.lambdify(all_args, rhs_exprs, "numpy", cse=False)
        if alg_state_names:
            alg_vec = sp.lambdify(
                all_args,
                [alg_value_exprs[n] for n in alg_state_names],
                "numpy",
                cse=False,
            )
        else:
            alg_vec = None

    flat._simulate_compile_cache = _CompiledRhs(
        state_names=state_names,
        parameter_names=parameter_names,
        symbol_map=symbol_map,
        algebraic_state_names=alg_state_names,
        rhs_vector_func=rhs_vec,
        algebraic_vector_func=alg_vec,
    )

    ic = dict(test_ic.initial_conditions)
    for short, seed in _DENOM_SEED_PPB.items():
        ic.setdefault(short, seed)

    res = simulate(
        flat,
        tspan=(0.0, 60.0),
        parameters=dict(test_ic.parameter_overrides),
        initial_conditions=ic,
    )

    assert res.success, f"integrator failed: {res.message!r}"
    assert res.y is not None and res.y.size > 0
    assert np.isfinite(res.y).all(), (
        f"non-finite values in integrated trajectory: "
        f"{(~np.isfinite(res.y)).sum()} / {res.y.size}"
    )

    # Mass-balance sanity: no concentration goes more than 1e-9 below zero
    # (the integrator may dip slightly negative on near-zero species
    # within numerical noise; a wholesale negative trajectory indicates
    # a sign-flip in the lowered RHS).
    assert (res.y >= -1e-9).all(), (
        f"states went substantially negative: min={res.y.min()}"
    )
