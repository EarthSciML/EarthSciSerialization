# Canonical-form conformance fixtures (RFC §5.4)

Each fixture is a JSON document with:

- `id` — short identifier.
- `description` — human-readable note about what this fixture exercises.
- `input` — an ESM expression in the wire form (number | string |
  ExpressionNode). Integer literals appear as JSON integers; float literals
  contain `.` or `e`/`E`.
- `expected` — the byte-exact canonical JSON string each binding must produce
  from `canonical_json(input)`.
- `tags` — categorization (`integer`, `float`, `subnormal`, `flatten`,
  `zero_elim`, `ordering`, `nonleaf`, `signed_zero`, ...).

Bindings load each fixture, parse `input` per their wire form, run
`canonicalize(input)` (or `canonical_json(input)` directly), and assert that
the output matches `expected` byte-for-byte.

## TypeScript exception

The TypeScript binding cannot distinguish integer from float literals until
gt-ca2u (rep refactor) lands. Fixtures whose `expected` contains a
JSON-integer token (no `.`, no `e`) are skipped for TypeScript and tracked
under gt-z8k0's TS follow-up bead.
