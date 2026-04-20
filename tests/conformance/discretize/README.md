# Discretize Conformance Harness (gt-l3dg)

End-to-end conformance runner for the RFC §11 `discretize()` pipeline.
Every binding that implements `discretize()` MUST run its output through
this harness and match the committed golden files byte-for-byte.

See `../README.md` for the general adapter pattern; the discretize
category adds a **byte-identical golden** contract that the round-trip
category intentionally does not require.

## Status

**Step 1** (this bead, gt-l3dg): Julia-only. The §11 pipeline has landed
in Julia (gt-gbs2); parallel ports to Python / Go / Rust / TypeScript are
tracked separately. As each binding lands its port, it MUST add an
adapter that satisfies the contract below and passes against the
committed goldens — no fixture forks, no per-binding goldens.

## Directory layout

```
tests/conformance/discretize/
├── README.md              # this file — adapter contract
├── manifest.json          # fixture list + default pipeline options
├── inputs/                # input ESM documents (parse-only; hand-written)
│   ├── scalar_ode.esm
│   ├── heat_1d_centered_grad.esm
│   └── bc_value_canonicalization.esm
└── golden/                # expected canonical-JSON output per fixture
    ├── scalar_ode.json
    ├── heat_1d_centered_grad.json
    └── bc_value_canonicalization.json
```

Paths inside `manifest.json` (`input`, `golden`) are relative to the
manifest's directory.

## Manifest schema

```json
{
  "category": "discretize",
  "version":  "1.0",
  "options":  { "max_passes": 32, "strict_unrewritten": true },
  "fixtures": [
    { "id": "<stable-id>",
      "input":  "inputs/<stable-id>.esm",
      "golden": "golden/<stable-id>.json",
      "tags":   ["step1", "..."] }
  ]
}
```

- `options` — default kwargs bindings MUST pass to `discretize()`. If a
  fixture needs different options in the future, it can override via a
  per-fixture `options` object (not used in Step 1).
- `tags` — free-form labels for filtering. Bindings MAY skip by tag if
  they have not yet implemented a feature, but they MUST NOT silently
  pass on a skipped fixture (emit a `broken`/skip in the native test
  framework).

## Adapter contract

Each binding MUST, for every fixture in the manifest:

1. **Parse** the input file into that binding's native ESM representation.
2. **Call** `discretize(esm, **options)` with the manifest's default
   options (and any per-fixture overrides).
3. **Emit** the returned document as **canonical JSON** (see below).
4. **Compare** the emitted bytes to the golden file byte-for-byte.
5. **Run twice** (determinism) — two calls on the same input MUST emit
   identical bytes.

Failures must surface as individual per-fixture failures in the binding's
native test framework, labeled by fixture `id`.

## Canonical JSON emission

For cross-binding byte-identity, every binding MUST serialize the
discretized document with:

- **Minified** output — no inter-token whitespace.
- **Sorted object keys** — lexicographic by UTF-8 code units at every
  nesting level.
- **Numbers** per RFC §5.4.6:
  - Integers: minimal decimal form, no leading zeros, `-0` preserved only
    for negative zero floats.
  - Floats: shortest round-trip decimal with `.0` disambiguation for
    integer-valued magnitudes; exponent form (`1e25`, `5e-324`) outside
    `[1e-6, 1e21)`; `-0.0` preserved.
- **Strings** JSON-escaped per RFC 8259.
- **Trailing newline**: golden files have a single trailing `\n`.
  Adapters SHOULD emit the same trailing newline, or strip the trailing
  newline from the golden before comparing — either rule is valid as
  long as the adapter is consistent.

Julia's existing `format_canonical_float` (from `canonicalize.jl`)
implements the float rules; other bindings have equivalent helpers
(per their §5.4 canonicalize ports).

## Adding a fixture

1. Drop the input under `inputs/<id>.esm`.
2. Append an entry to `manifest.json`. Keep `id` stable — it is the
   visible test label in every binding.
3. Regenerate the golden: run the Julia reference adapter with
   `UPDATE_DISCRETIZE_GOLDEN=1` (the adapter writes the golden and
   passes instead of failing on mismatch). Commit the golden.
4. Every other binding that has landed a discretize port must then
   re-run its adapter to confirm byte-identity. A binding that cannot
   reproduce the Julia golden is a legitimate cross-binding bug — file
   a bead, do not fork the golden.

## Regenerating goldens

Goldens are treated as source: they change only when a deliberate
pipeline or fixture change warrants it, in the same commit as the
change.

```bash
# From the repo root:
UPDATE_DISCRETIZE_GOLDEN=1 \
  julia --project=packages/EarthSciSerialization.jl \
  -e 'using Pkg; Pkg.test(; test_args=["conformance_discretize"])'
```

Or run the standalone runner:

```bash
UPDATE_DISCRETIZE_GOLDEN=1 \
  julia --project=packages/EarthSciSerialization.jl \
  scripts/run-julia-discretize-conformance.jl
```

## CI integration

`scripts/test-conformance.sh` invokes each binding's conformance test
suite. The Julia adapter (`conformance_discretize_test.jl`) is picked
up by `Pkg.test()` via `runtests.jl` and runs automatically in CI.
Cross-binding regression shows up as a fixture failure in whichever
binding drifts — no separate comparison step is required, since every
binding is checked against the same committed golden.
