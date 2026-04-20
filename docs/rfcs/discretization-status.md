# Discretization RFC — Implementation Status

Audit status for [`discretization.md`](./discretization.md) sections, as they
land in `esm-schema.json` / `esm-spec.md` / bindings. Scope is the on-wire
schema surface — binding-side runtime work is tracked in the per-binding
beads.

## §6 Grids — landed (gt-5kq3, v2.1)

Top-level `grids` map with `cartesian` / `unstructured` / `cubed_sphere`
families is in `esm-schema.json`. Each grid declares `dimensions`,
`locations`, `metric_arrays`, `connectivity` (unstructured) and
`panel_connectivity` (cubed sphere). Loader-backed geometry works by
reference:

- `GridMetricGenerator.kind = "loader"` + `{loader, field}` (schema line ~1947–1986)
- `GridConnectivity.{loader, field}` (schema line ~2016–2040)
- `GridMetricGenerator.kind = "builtin"` with closed name set
  (`gnomonic_c6_neighbors`, `gnomonic_c6_d4_action`); unknown names reject
  with `E_UNKNOWN_BUILTIN`.

The `tests/grids/unstructured_mpas.esm` fixture rounds-trips in all five
bindings and exercises both loader-backed connectivity and loader-backed
metric arrays.

## §8 `data_loaders` — partial (audit gt-xboy)

### What's landed

Grid → loader wiring is end-to-end: a grid's `metric_arrays.<m>.generator.{loader, field}`
and `connectivity.<c>.{loader, field}` resolve by name against a top-level
`data_loaders` entry and pick a field that the loader declares under
`variables.<name>`. Pipeline Step 3 (§11) treats loader / builtin
generators as deferred handles — the rewrite engine does not materialize
bulk data, so the current schema surface is sufficient to drive discretization
without a separate mesh-loader kind.

The MPAS fixture uses `kind: "grid"` and declares each connectivity table
and metric array as an ordinary `variables` entry (with `units: "1"` for
integer connectivity). The existing `DataLoaderVariable` shape (`file_variable`
+ `units`) is enough for a binding to locate each field at load time.

### Gaps vs. RFC §8.A

The RFC's §8.A amendments (new `kind: "mesh"` with `mesh.topology`,
`mesh.connectivity_fields`, `mesh.metric_fields`, `mesh.dimension_sizes`,
and a top-level `determinism` block) are **not** yet present in the
schema or spec prose. Concretely:

| RFC §8.A item | Status |
|---|---|
| `DataLoader.kind` enum includes `"mesh"` | **missing** — enum is `["grid", "points", "static"]` (schema line 1301) |
| `DataLoader.mesh.{topology, connectivity_fields, metric_fields, dimension_sizes}` | **missing** — no `mesh` subobject on `DataLoader` |
| `DataLoader.determinism.{endian, float_format, integer_width}` | **missing** — no `determinism` subobject |
| §8.1 fields table lists `kind: "mesh"` | **missing** in `esm-spec.md` §8.1 |
| §8.7 "mesh connectivity out of scope" retracted | **not retracted** — `esm-spec.md` §8.7 still states mesh connectivity is out of scope |
| Integer vs float field separation for connectivity vs metric | **missing** — `DataLoaderVariable` has a single `units` string only; the fixture uses `"units": "1"` as a placeholder for integer tables |

### Adjacent gap — `Parameter.value: "from_loader"` (§6.6)

The `Grid.parameters` description (schema line 2092) claims grid-level
parameters "with `value='from_loader'` are resolved at load time from a
referenced data_loaders entry (§6.6)". The `Parameter` $def (schema line
658–671), however, does not declare a `value` field at all — only
`default: number`. The MPAS fixture works around this by providing
numeric defaults (`"nCells": 2562`) and a prose note. This is flagged
here for awareness; it is a §6 gap, not a §8 gap, and is out of scope
for gt-xboy.

### Material?

**Yes, but not blocking.** The existing `kind: "grid"` + loose-typed
`variables` pattern is enough to round-trip MPAS-style mesh metadata
through the schema and to feed the §6 grid accessors. What §8.A adds is:

1. A structured, schema-validated declaration of which fields are
   integer-typed connectivity vs float-typed metric.
2. A determinism / reproducibility contract that bindings can reject
   against at load (§14 item 4).
3. A dimension-sizes map that feeds `from_loader` parameter resolution
   without forcing authors to pick a numeric default.

None of these are required for Step-1 discretization (already landed)
or for the current MPAS conformance fixture. They become load-bearing
when:

- Bindings start enforcing reproducibility guarantees and need the
  `determinism` block to reject non-conforming loaders.
- `Parameter.value: "from_loader"` is wired (see §6.6 gap above) and
  the dimension-size map becomes the source of truth.
- Authors want structural validation that connectivity fields are
  integer-typed and metric fields are float-typed, rather than
  relying on out-of-band convention.

Follow-up work is tracked as a single amendment bead rather than broken
per-binding, because the schema change is small and binding-side
parsers already accept unknown enum values gracefully (regression risk
is low).

## §11 Pipeline — landed (gt-gbs2, gt-l3dg, gt-q7sh)

`discretize(esm)` end-to-end runner, DAE binding contract, and the
Julia reference pipeline are in. Not in audit scope for gt-xboy.
