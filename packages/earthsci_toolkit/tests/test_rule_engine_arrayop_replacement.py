"""Rule-engine support for arrayop (finite-difference stencil) replacements.

Regression tests for the cross-binding gap where ``_parse_expr`` dropped the
structural fields of compound ops (``output_idx`` / ``expr`` / ``ranges`` / …)
and ``apply_bindings`` did not substitute pattern variables inside them. The
symptom was that a finite-difference discretization rule whose ``replacement``
is an ``arrayop`` fired but lowered to a content-free ``arrayop{args:[…]}``
marker, leaving the spatial operator un-discretized (the Julia binding fixed the
same bug under esd-3d7). These tests pin the Python binding to parity.
"""

from __future__ import annotations

import numpy as np

from earthsci_toolkit.rule_engine import parse_rule, rewrite, _parse_expr
from earthsci_toolkit.esm_types import ExprNode
from earthsci_toolkit.numpy_interpreter import eval_expr, EvalContext


# An ESD-shaped centered 2nd-derivative stencil rule:
#   d2(u, x)  ->  arrayop[x] ( u[x-1] - 2 u[x] + u[x+1] ) / dx^2
_STENCIL_RULE = {
    "pattern": {"op": "d2", "args": ["$u"], "dim": "$x"},
    "replacement": {
        "op": "arrayop",
        "output_idx": ["$x"],
        "args": ["$u"],
        "expr": {
            "op": "/",
            "args": [
                {
                    "op": "+",
                    "args": [
                        {"op": "index", "args": ["$u", {"op": "-", "args": ["$x", 1]}]},
                        {
                            "op": "*",
                            "args": [
                                -2,
                                {"op": "index", "args": ["$u", "$x"]},
                            ],
                        },
                        {"op": "index", "args": ["$u", {"op": "+", "args": ["$x", 1]}]},
                    ],
                },
                {"op": "*", "args": ["dx", "dx"]},
            ],
        },
    },
}


def test_parse_expr_preserves_arrayop_fields() -> None:
    """``_parse_expr`` must carry output_idx / expr / ranges, not drop them."""
    node = _parse_expr(
        {
            "op": "arrayop",
            "output_idx": ["i"],
            "args": ["u"],
            "expr": {"op": "index", "args": ["u", "i"]},
            "ranges": {"i": [1, 3]},
        }
    )
    assert isinstance(node, ExprNode)
    assert node.output_idx == ["i"]
    assert node.ranges == {"i": [1, 3]}
    assert isinstance(node.expr, ExprNode) and node.expr.op == "index"


def test_apply_bindings_substitutes_inside_arrayop_body() -> None:
    """Pattern vars in output_idx / ranges keys / body must be substituted."""
    rule = parse_rule(_STENCIL_RULE, name="centered_2nd_deriv")
    out = rewrite(_parse_expr({"op": "d2", "args": ["u"], "dim": "x"}), [rule])

    assert out.op == "arrayop"
    assert out.output_idx == ["x"]          # $x -> x
    assert out.expr is not None             # body preserved

    # No pattern variable may leak through into the lowered AST.
    def _walk(e):
        if isinstance(e, ExprNode):
            yield from (e.op,)
            for a in e.args or []:
                yield from _walk(a)
            if e.expr is not None:
                yield from _walk(e.expr)
            for idx in e.output_idx or []:
                yield idx
        elif isinstance(e, str):
            yield e

    leaked = [tok for tok in _walk(out) if isinstance(tok, str) and tok.startswith("$")]
    assert leaked == [], f"pattern variables leaked: {leaked}"


def test_rewrite_stencil_then_numpy_interpreter_eval() -> None:
    """End-to-end: rewrite d2 -> arrayop, evaluate it via numpy_interpreter,
    and match a hand-computed centered finite difference."""
    rule = parse_rule(_STENCIL_RULE, name="centered_2nd_deriv")
    disc = rewrite(_parse_expr({"op": "d2", "args": ["u"], "dim": "x"}), [rule])

    # Bound the output index to the interior positions 2..5 of a length-6 vector
    # (1-based indexing; positions 1 and 6 act as Dirichlet ghosts).
    disc = ExprNode(
        op="arrayop",
        args=list(disc.args),
        output_idx=disc.output_idx,
        expr=disc.expr,
        ranges={disc.output_idx[0]: [2, 5]},
    )

    u = np.array([0.0, 1.0, 4.0, 9.0, 16.0, 0.0])  # ghosts at ends
    dx = 0.5
    ctx = EvalContext(
        state_layout={"u": slice(0, u.size)},
        state_shapes={"u": (u.size,)},
        param_values={"dx": dx},
        observed_values={},
        y=u.copy(),
        t=0.0,
        index_sets={},
    )
    got = np.asarray(eval_expr(disc, ctx), dtype=float)

    # Hand-computed (u[i-1] - 2u[i] + u[i+1]) / dx^2 over interior nodes.
    want = np.array(
        [(u[i - 1] - 2 * u[i] + u[i + 1]) / dx**2 for i in range(1, 5)]
    )
    np.testing.assert_allclose(got, want, rtol=1e-12, atol=0.0)
