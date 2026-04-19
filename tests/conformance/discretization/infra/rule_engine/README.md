# Rule-engine conformance fixtures (RFC §5.2 / §13.1 Step 1)

Each fixture is a JSON document with:

- `id` — short identifier.
- `description` — human-readable note about what this fixture exercises.
- `rules` — an ordered list of rule objects per RFC §5.2.5 (array form).
  Each rule has `name`, `pattern`, `replacement`, and optional `where`.
- `input` — the seed expression on which to run the rule engine.
- `max_passes` — optional; defaults to 32 per RFC §5.2.5. Set lower to
  exercise `E_RULES_NOT_CONVERGED`.
- `expect` — one of:
  - `{"kind": "output", "canonical_json": "<string>"}` — the byte-exact
    canonical JSON each binding's `canonical_json(rewrite(input, rules))`
    must produce.
  - `{"kind": "error", "code": "<E_…>"}` — the rule engine MUST abort
    with this stable error code. Bindings do not emit an output for
    these fixtures.
- `tags` — categorization (`match_once`, `fixed_point`, `not_converged`,
  `guard`, `nonlinear`, `sibling_field`, …).

Bindings load each fixture, parse the expressions via their wire form,
run `rewrite(input, rules)` (with any supplied `max_passes`),
canonicalize the output, and assert byte-for-byte equality with
`expect.canonical_json` — or that the error code matches.

## Minimum set (per RFC §13.1 Step 1)

- `match_once.json` — a pattern that matches exactly once.
- `fixed_point.json` — a pattern that requires multiple passes to
  converge.
- `not_converged.json` — a pattern that hits `E_RULES_NOT_CONVERGED` at
  `max_passes = 3`.

Additional fixtures exercise the §5.2.4 guard vocabulary, non-linear
patterns (§5.2.2), and sibling-field pattern variables (§5.2.4).
