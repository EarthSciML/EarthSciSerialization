# DAE-missing conformance fixtures (RFC §12 / gt-q7sh)

Each fixture is a JSON document that describes one `discretize()` input
and the cross-binding expectations for both a DAE-support-enabled and a
DAE-support-disabled run of the binding. The layout:

- `id` — short identifier.
- `description` — human-readable note about what this fixture exercises.
- `input` — an `.esm`-shaped document that, when passed through
  `discretize()`, yields zero or more algebraic equations alongside any
  differential equations.
- `expect` — a list of two modes. Each entry has `mode`
  (`dae_support_enabled` / `dae_support_disabled`) plus either:
  - `{"kind": "output", "system_class": "<ode|dae>",
     "algebraic_equation_count": <int>, "per_model": {<model>: <int>}}`
    The binding's `discretize()` MUST succeed and produce an output whose
    `metadata.system_class`, `metadata.dae_info.algebraic_equation_count`,
    and `metadata.dae_info.per_model` match these fields. Silent success
    with `system_class` missing, or equal to `"ode"` when the fixture
    expects `"dae"`, is a test failure.
  - `{"kind": "error", "code": "E_NO_DAE_SUPPORT",
     "message_must_contain": [<string>, …]}`
    The binding MUST abort with the exact error code `E_NO_DAE_SUPPORT`
    (upper-case, ASCII, single underscore between each word) and the
    emitted message MUST contain every listed substring.

## How to exercise the fixtures

Each binding loads each fixture, then runs `discretize()` **twice**:

1. Once with the binding's DAE support *enabled* — for Julia, the
   default `discretize(esm)` (or `discretize(esm; dae_support=true)`).
   Assert the `dae_support_enabled` expectation.
2. Once with the binding's DAE support *disabled* — for Julia, either
   `discretize(esm; dae_support=false)` or the env var
   `ESM_DAE_SUPPORT=0`. Assert the `dae_support_disabled` expectation.

RFC §12's "disabled-DAE" knob is mandatory for every binding that
implements `discretize()`. The knob name may be binding-idiomatic
(kwarg, flag, env var) as long as the binding documents it.

## Minimum set

- `mixed_dae_observed.json` — authored observed-equation algebraic
  alongside a scalar ODE.
- `pure_ode_baseline.json` — baseline ODE-only fixture that guards
  against false-positive `E_NO_DAE_SUPPORT` emission.

Further fixtures will land as `produces: algebraic` rule output
becomes available (RFC §13.1 Step 1b+).
