# Function Tables Conformance Fixtures (esm-spec §9.5)

These fixtures exercise the `function_tables` top-level block and the
`table_lookup` AST op landed in v0.4.0 (RFC `docs/content/rfcs/sampled-tables.md`,
bead esm-jcj / esm-hid).

## Fixtures

### `linear/fixture.esm`

A single-output 1-axis linear function table — the canonical 1-D blend.
The single equation lowers to `interp.linear(table=data, axis=axis_values, x=lambda)`
and MUST be bit-equivalent to a hand-written inline-const `interp.linear` invocation
on the same arrays at the same query point (esm-spec §9.2 tolerance contract).

### `bilinear/fixture.esm`

A multi-output 2-axis bilinear function table with named outputs
(`["NO2", "O3", "HCHO"]`). Two `table_lookup` equations: one selects by output name
(`"NO2"`), the other by integer index (`1` → `"O3"`). Both lower to
`interp.bilinear` invocations and must agree numerically with the equivalent
hand-written inline-const form.

### `roundtrip/fixture.esm`

A mixed file carrying both a `function_tables`-driven `table_lookup` and a
hand-written inline-const `interp.linear` invocation referencing identical
data. **Round-trip MUST preserve the authored form of each equation**:
loaders MUST NOT auto-promote the inline-const lookup into a `table_lookup`,
and MUST NOT demote the `table_lookup` into an inline-const lookup. This
property is pinned by esm-spec §9.5.4 ("Round-tripping").

## Per-binding contract

All five language bindings (Julia, Python, TypeScript, Rust, Go) MUST:

1. Load each fixture without error.
2. Materialize the `table_lookup` to a structurally-equivalent
   `interp.linear` / `interp.bilinear` form whose numerical evaluation agrees
   bit-exactly with the hand-written inline-const equivalent (`abs: 0,
   rel: 0` non-FMA, `abs: 0, rel: 4e-16` mixed-FMA cross-binding —
   esm-spec §9.2 tolerance contract).
3. Round-trip the loaded file: `parse → serialize → parse → serialize`
   yields bit-identical bytes (modulo whitespace), preserving the authored
   `function_tables` block and `table_lookup` nodes.
