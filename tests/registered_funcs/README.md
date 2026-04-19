# Registered Functions Fixtures

Canonical fixtures for the `call` op + `registered_functions` registry introduced
in gt-p3ep. See `esm-spec.md` §4.4 and §9.2.

Each fixture declares one or more `registered_functions` entries and references
them from ODE RHS expressions via the `call` op. Handler bodies are
intentionally **not** specified in the serialized file — they are supplied by
the runtime through a handler registry (in Julia, via `@register_symbolic`).

All five bindings MUST:

1. Parse each fixture successfully.
2. Emit a `missing_registered_function` diagnostic when a `call` op references
   a `handler_id` not declared in `registered_functions`.
3. Round-trip each fixture losslessly under the idempotent-re-save contract
   (see `../conformance/README.md`).

Bindings that implement a numeric evaluator additionally supply a trivial
handler binding in their test suite (e.g. identity, constant return) and
verify that `call` dispatch works end-to-end.

## Fixtures

| File | Purpose |
|---|---|
| `pure_math.esm` | Trivial pure math registered function invoked from a scalar ODE RHS. |
| `one_d_interpolator.esm` | 1D interpolation-table handler invoked on a scalar driver variable. |
| `two_d_table_lookup.esm` | 2D table-lookup handler invoked with two scalar arguments plus a scalar coefficient prefactor. |
