# DAE binding strategies (RFC §12 companion — gt-q7sh)

This document records each binding's **strategy** for satisfying the
RFC §12 DAE binding contract. It is normative for binding authors and
informative for model authors who want to know what will happen when
their `.esm` contains algebraic equations alongside differential ones.

RFC §12 requires every binding that implements `discretize()` to
either (a) hand a mixed DAE to a DAE assembler, or (b) abort with
`E_NO_DAE_SUPPORT`. The binding's documentation MUST name its DAE
assembler; this file is that documentation, centralized.

## Strategy per binding

| Binding | Strategy | Assembler | Index reduction | Disable knob |
|---|---|---|---|---|
| **Julia** (`EarthSciSerialization.jl`) | **Direct DAE hand-off.** `discretize(esm; dae_support=true)` is the default; when the output is a DAE, `metadata.system_class` is stamped `"dae"` and the caller's MTK export path (`mtk2esm`'s inverse, `MockMTKSystem`, or a user-supplied `System` constructor) receives a mixed equation set that ModelingToolkit.jl handles natively. No index reduction is attempted; MTK performs any required structural simplification. | ModelingToolkit.jl (`System` / `ODESystem` with algebraic equations; `DAEProblem` on solve) | Delegated to MTK (`structural_simplify`) at solve time. | `discretize(esm; dae_support=false)` or env `ESM_DAE_SUPPORT=0`. |
| **Rust** (`earthsci-toolkit-rs`) | **Direct DAE hand-off (planned).** Until `discretize()` lands in Rust, the binding emits `E_NO_DAE_SUPPORT` on any discretize input containing algebraic equations. The target assembler is [`diffsol`](https://github.com/martinjrobins/diffsol), which has native DAE support. | diffsol (`Bdf` / `Sdirk` DAE paths) | Not planned for v0.2; deferred to later minor releases. | Binding-specific flag `DiscretizeOptions::dae_support = false` (TBD) or env `ESM_DAE_SUPPORT=0`. |
| **Python** (`earthsci_toolkit`) | **Stubbed.** v0.2.0 always emits `E_NO_DAE_SUPPORT` on mixed-DAE input; `discretize()` success path is ODE-only. A future release will delegate to SUNDIALS/IDA via scikits.odes or to diffrax's DAE mode. | Deferred. | Env `ESM_DAE_SUPPORT=0`; the DAE-enabled path is not yet implemented, so the knob is effectively one-way in v0.2.0. |
| **Go** (`esm-format-go`) | **Trivial-factor.** `ApplyDAEContract(*EsmFile)` symbolically substitutes every algebraic equation of the form `y ~ f(...)` (where `y` is a plain variable and `f` does not reference `y`) into downstream equations, removing the factored equation from the model. Factoring runs to a fixed point so transitive chains `z ~ g(y); y ~ h(x)` fold into pure-ODE form. If any algebraic equations remain after factoring (cyclic observed equations or genuine constraints like `x^2 + y^2 = 1`), the binding aborts with `E_NONTRIVIAL_DAE`; the error names each residual equation and points the author at the Julia binding. Go has no in-ecosystem DAE assembler, so non-trivial DAEs require a different binding. | None (trivial cases reduce to ODE; non-trivial cases abort). | None — the DAE contract is informational-only in Go: pure-ODE output after factoring classifies as `"ode"`, otherwise the binding errors. |
| **TypeScript** (`earthsci-toolkit`) | **Stubbed.** v0.2.0 always emits `E_NO_DAE_SUPPORT` on mixed-DAE input. No native DAE assembler in the JS/TS ecosystem; expected to remain a pure-ODE binding unless a WASM DAE solver is vendored. | Deferred (TBD). | Env `ESM_DAE_SUPPORT=0`. |

## What counts as "algebraic"

For the purpose of this contract, an equation in a discretized model
is **algebraic** iff at least one of the following holds:

1. It carries a `produces: "algebraic"` or `algebraic: true` marker on
   the equation object (the output form of a rule with
   `produces: algebraic`, per RFC §9.4).
2. Its LHS is not a time derivative `D(x, wrt=<indep>)`, where
   `<indep>` is the enclosing model's domain's `independent_variable`
   (default `"t"`). This covers authored observed equations and
   authored constraints of the form `0 = g(x)`.

This is deliberately inclusive. A binding that claims ODE-only
support and runs the system through an ODE-only integrator would
drop an observed-equation LHS just as surely as a true DAE
constraint; the contract "hand to a DAE assembler, or abort" applies
in either case.

## Stamped output metadata (normative)

When `discretize()` succeeds with DAE support enabled, the output
metadata MUST carry:

- `metadata.system_class` — `"ode"` if no algebraic equations were
  found anywhere in the output, else `"dae"`.
- `metadata.dae_info.algebraic_equation_count` — integer, total over
  all models.
- `metadata.dae_info.per_model` — map of `<model name>` →
  `<algebraic equation count>`.

The conformance harness reads these fields from
`tests/conformance/discretization/dae_missing/` fixtures.

## Error message requirements

When `discretize()` aborts with `E_NO_DAE_SUPPORT`, the error message
MUST contain:

- The exact code string `E_NO_DAE_SUPPORT` (upper-case, ASCII, one
  underscore between each word).
- At least one `<model>.equations[<i>]` path naming an algebraic
  equation.
- An identification of the binding's disable knob (e.g.,
  `dae_support=false` or `ESM_DAE_SUPPORT=0`) so the author knows how
  to enable DAE support when available.

See `tests/conformance/discretization/dae_missing/README.md` for the
exact conformance harness expectations.
