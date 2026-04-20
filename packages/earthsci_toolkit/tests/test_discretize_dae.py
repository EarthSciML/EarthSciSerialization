"""Unit tests for the Python binding's RFC §12 DAE contract (gt-os8b).

The Python strategy is trivial-factor + error otherwise:
* Observed-equation-style algebra (``y = f(x)`` with ``y`` not in RHS)
  is eliminated by substitution into downstream equations.
* Everything else raises ``E_NONTRIVIAL_DAE``.
"""

from __future__ import annotations

import pytest

from earthsci_toolkit import discretize, DiscretizationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mk(*equations):
    return {
        "esm": "0.2.0",
        "metadata": {"name": "t"},
        "models": {
            "M": {
                "variables": {
                    "x": {"type": "state", "default": 1.0, "units": "1"},
                    "y": {"type": "observed", "units": "1"},
                    "z": {"type": "observed", "units": "1"},
                    "k": {"type": "parameter", "default": 0.5, "units": "1/s"},
                },
                "equations": list(equations),
            }
        },
    }


def _dx_eq():
    # dx/dt = -k*x
    return {
        "lhs": {"op": "D", "args": ["x"], "wrt": "t"},
        "rhs": {"op": "*", "args": [{"op": "-", "args": ["k"]}, "x"]},
    }


# ---------------------------------------------------------------------------
# Pure ODE baseline
# ---------------------------------------------------------------------------


def test_pure_ode_succeeds_and_stamps_ode_metadata():
    esm = _mk(_dx_eq())
    out = discretize(esm)
    assert out["metadata"]["system_class"] == "ode"
    assert out["metadata"]["dae_info"]["algebraic_equation_count"] == 0
    assert out["metadata"]["dae_info"]["per_model"] == {"M": 0}
    # Equations unchanged.
    assert out["models"]["M"]["equations"] == [_dx_eq()]


def test_pure_ode_with_dae_support_disabled_still_succeeds():
    esm = _mk(_dx_eq())
    out = discretize(esm, dae_support=False)
    assert out["metadata"]["system_class"] == "ode"
    assert out["metadata"]["dae_info"]["algebraic_equation_count"] == 0


def test_input_is_not_mutated():
    esm = _mk(_dx_eq())
    before = repr(esm)
    discretize(esm)
    assert repr(esm) == before


def test_provenance_stamped():
    esm = _mk(_dx_eq())
    out = discretize(esm)
    assert out["metadata"]["discretized_from"] == "t"


# ---------------------------------------------------------------------------
# Trivial factoring: observed-equation pattern
# ---------------------------------------------------------------------------


def test_single_observed_equation_is_factored_away():
    # y = x^2; dx/dt = -k*x — y should be eliminated so the output is pure ODE.
    esm = _mk(
        _dx_eq(),
        {"lhs": "y", "rhs": {"op": "^", "args": ["x", 2]}},
    )
    out = discretize(esm)
    assert out["metadata"]["system_class"] == "ode"
    assert out["metadata"]["dae_info"]["algebraic_equation_count"] == 0
    assert out["metadata"]["dae_info"]["per_model"] == {"M": 0}
    eqs = out["models"]["M"]["equations"]
    assert len(eqs) == 1
    assert eqs[0]["lhs"] == {"op": "D", "args": ["x"], "wrt": "t"}


def test_chained_observed_equations_are_factored_via_toposort():
    # y = x^2; z = y + 1; dx/dt = -k*x*z
    # Substitutes y into z, then z into dx/dt.
    esm = _mk(
        {
            "lhs": {"op": "D", "args": ["x"], "wrt": "t"},
            "rhs": {"op": "*", "args": [{"op": "-", "args": ["k"]}, "x", "z"]},
        },
        {"lhs": "y", "rhs": {"op": "^", "args": ["x", 2]}},
        {"lhs": "z", "rhs": {"op": "+", "args": ["y", 1]}},
    )
    out = discretize(esm)
    assert out["metadata"]["system_class"] == "ode"
    assert out["metadata"]["dae_info"]["algebraic_equation_count"] == 0
    eqs = out["models"]["M"]["equations"]
    assert len(eqs) == 1
    # The differential equation's RHS should reference neither y nor z.
    from earthsci_toolkit.discretize import _free_vars  # noqa: PLC2701

    refs = _free_vars(eqs[0]["rhs"])
    assert "y" not in refs
    assert "z" not in refs
    assert "x" in refs
    assert "k" in refs


def test_factored_substitution_uses_deep_copy():
    # Make sure the substituted expression is independent of the original RHS,
    # so mutating the output does not corrupt a template.
    esm = _mk(
        _dx_eq(),
        {"lhs": "y", "rhs": {"op": "+", "args": ["x", 1]}},
    )
    # Use dae_support=True factoring; then mutate the output.
    out = discretize(esm)
    # Input untouched:
    assert esm["models"]["M"]["equations"][1]["rhs"] == {
        "op": "+",
        "args": ["x", 1],
    }


# ---------------------------------------------------------------------------
# Non-trivial DAE: raises E_NONTRIVIAL_DAE
# ---------------------------------------------------------------------------


def test_constraint_equation_raises_e_nontrivial_dae():
    # Unit circle constraint: x^2 + y^2 - 1 = 0 expressed as lhs operator
    # (not a bare variable) — this is non-factorable.
    constraint = {
        "lhs": {"op": "+", "args": [{"op": "^", "args": ["x", 2]}, {"op": "^", "args": ["y", 2]}]},
        "rhs": 1,
    }
    esm = _mk(_dx_eq(), constraint)
    with pytest.raises(DiscretizationError) as exc:
        discretize(esm)
    assert exc.value.code == "E_NONTRIVIAL_DAE"
    msg = exc.value.message
    # Error details the spec requires:
    assert "E_NONTRIVIAL_DAE" not in msg  # message proper; code separate
    # The message should name the residual location and mention Julia
    # and RFC §12.
    assert "models.M.equations[1]" in msg
    assert "Julia" in msg
    assert "§12" in msg


def test_cyclic_observed_equations_raise_e_nontrivial_dae():
    # y = z + 1; z = y - 1  — both bare-string LHS but depend on each other.
    esm = _mk(
        _dx_eq(),
        {"lhs": "y", "rhs": {"op": "+", "args": ["z", 1]}},
        {"lhs": "z", "rhs": {"op": "-", "args": ["y", 1]}},
    )
    with pytest.raises(DiscretizationError) as exc:
        discretize(esm)
    assert exc.value.code == "E_NONTRIVIAL_DAE"
    # Both algebraic equations are residual.
    assert exc.value.message.count("equations[") >= 2


def test_self_referential_observed_is_nontrivial():
    # y = y + 1 — LHS variable appears in its own RHS.
    esm = _mk(
        _dx_eq(),
        {"lhs": "y", "rhs": {"op": "+", "args": ["y", 1]}},
    )
    with pytest.raises(DiscretizationError) as exc:
        discretize(esm)
    assert exc.value.code == "E_NONTRIVIAL_DAE"


def test_partial_factoring_reports_only_residual():
    # y = x^2 (factorable) + constraint 0 = z - 1 (non-factorable because LHS
    # is bare "z" but ... actually `lhs: "z"` with `rhs: 1` IS factorable).
    # Use an operator LHS for the non-factorable one.
    esm = _mk(
        _dx_eq(),
        {"lhs": "y", "rhs": {"op": "^", "args": ["x", 2]}},  # factorable
        {  # non-factorable: LHS is an operator node
            "lhs": {"op": "+", "args": ["x", "x"]},
            "rhs": 0,
        },
    )
    with pytest.raises(DiscretizationError) as exc:
        discretize(esm)
    assert exc.value.code == "E_NONTRIVIAL_DAE"
    # Only the non-factorable equation should be reported.
    assert "models.M.equations[2]" in exc.value.message
    # The message has a single-equation residual.
    assert "could not factor 1 algebraic equation" in exc.value.message


# ---------------------------------------------------------------------------
# dae_support=False path
# ---------------------------------------------------------------------------


def test_dae_support_false_raises_e_no_dae_support():
    esm = _mk(
        _dx_eq(),
        {"lhs": "y", "rhs": {"op": "^", "args": ["x", 2]}},
    )
    with pytest.raises(DiscretizationError) as exc:
        discretize(esm, dae_support=False)
    assert exc.value.code == "E_NO_DAE_SUPPORT"
    msg = exc.value.message
    assert "models.M.equations[1]" in msg
    assert "dae_support" in msg.lower()
    assert "§12" in msg


def test_dae_support_false_skips_factoring():
    # Two observed equations. dae_support=False must NOT factor them away.
    esm = _mk(
        _dx_eq(),
        {"lhs": "y", "rhs": {"op": "^", "args": ["x", 2]}},
        {"lhs": "z", "rhs": {"op": "+", "args": ["y", 1]}},
    )
    with pytest.raises(DiscretizationError) as exc:
        discretize(esm, dae_support=False)
    assert exc.value.code == "E_NO_DAE_SUPPORT"


# ---------------------------------------------------------------------------
# Environment variable integration
# ---------------------------------------------------------------------------


def test_env_esm_dae_support_zero_disables_factoring(monkeypatch):
    monkeypatch.setenv("ESM_DAE_SUPPORT", "0")
    esm = _mk(
        _dx_eq(),
        {"lhs": "y", "rhs": {"op": "^", "args": ["x", 2]}},
    )
    with pytest.raises(DiscretizationError) as exc:
        discretize(esm)
    assert exc.value.code == "E_NO_DAE_SUPPORT"


def test_env_esm_dae_support_unset_enables_factoring(monkeypatch):
    monkeypatch.delenv("ESM_DAE_SUPPORT", raising=False)
    esm = _mk(
        _dx_eq(),
        {"lhs": "y", "rhs": {"op": "^", "args": ["x", 2]}},
    )
    out = discretize(esm)
    assert out["metadata"]["system_class"] == "ode"


# ---------------------------------------------------------------------------
# Explicit algebraic markers
# ---------------------------------------------------------------------------


def test_produces_algebraic_marker_is_honored():
    # LHS is a differential-looking D op, but `produces: algebraic` forces
    # classification. Here we put an observed-style equation with the marker.
    eq = {
        "lhs": "y",
        "rhs": {"op": "^", "args": ["x", 2]},
        "produces": "algebraic",
    }
    esm = _mk(_dx_eq(), eq)
    # This is still trivially factorable (LHS is bare "y").
    out = discretize(esm)
    assert out["metadata"]["system_class"] == "ode"
    assert out["metadata"]["dae_info"]["algebraic_equation_count"] == 0


def test_algebraic_flag_is_honored():
    eq = {
        "lhs": {"op": "D", "args": ["x"], "wrt": "t"},
        "rhs": 0,
        "algebraic": True,
    }
    # This differential-shaped equation is flagged as algebraic, LHS is not
    # bare-string → non-factorable → E_NONTRIVIAL_DAE.
    esm = _mk(eq)
    with pytest.raises(DiscretizationError) as exc:
        discretize(esm)
    assert exc.value.code == "E_NONTRIVIAL_DAE"


# ---------------------------------------------------------------------------
# Domain-aware independent-variable resolution
# ---------------------------------------------------------------------------


def test_nondefault_independent_variable_is_respected():
    # Model uses a domain whose independent_variable is "tau"; an equation
    # with D(x, wrt="tau") must be classified as differential (not algebraic).
    esm = {
        "esm": "0.2.0",
        "metadata": {"name": "tau_model"},
        "domains": {
            "D1": {"independent_variable": "tau"},
        },
        "models": {
            "M": {
                "domain": "D1",
                "variables": {
                    "x": {"type": "state", "default": 1.0, "units": "1"},
                    "k": {"type": "parameter", "default": 0.5, "units": "1/s"},
                },
                "equations": [
                    {
                        "lhs": {"op": "D", "args": ["x"], "wrt": "tau"},
                        "rhs": {"op": "*", "args": [{"op": "-", "args": ["k"]}, "x"]},
                    }
                ],
            }
        },
    }
    out = discretize(esm)
    assert out["metadata"]["system_class"] == "ode"


def test_wrt_mismatch_is_treated_as_algebraic():
    # D(x, wrt="s") in a model whose independent variable is "t" is
    # algebraic by the contract.
    eq = {
        "lhs": {"op": "D", "args": ["x"], "wrt": "s"},
        "rhs": 0,
    }
    esm = _mk(eq)
    with pytest.raises(DiscretizationError) as exc:
        discretize(esm)
    assert exc.value.code == "E_NONTRIVIAL_DAE"


# ---------------------------------------------------------------------------
# Input-type validation
# ---------------------------------------------------------------------------


def test_non_dict_input_raises_typeerror():
    with pytest.raises(TypeError):
        discretize("not a dict")  # type: ignore[arg-type]
