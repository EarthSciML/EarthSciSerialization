# Migration fixtures: v0.1.x → v0.2.0

Cross-binding fixtures for the v0.1 → v0.2 migration defined by
`docs/rfcs/discretization.md` §10.1 and §16.1.

Each fixture has:

- `input` — a pre-0.2 `.esm` document carrying `domains.<d>.boundary_conditions`
- `expected` — the byte-exact document each binding's `esm migrate` /
  `esm-migrate` tool must produce

The migration rule is:

1. For each `domains.<d>.boundary_conditions[k]` of the form
   `{type, dimensions: [axis...], value?, robin_*?}`:
   - For each axis, expand to sides. Closed short axes (`x`/`y`/`z`/`t`) use
     `<axis>min`/`<axis>max`; other axes use `<axis>_min`/`<axis>_max`.
     `periodic` emits only the min side (RFC §9.2.1).
   - For every model whose `domain` matches `<d>` (or is `null` and `<d>` is
     `"default"`), for every *state* variable, emit a
     `models.<M>.boundary_conditions["<var>_<kind>_<side>"]` entry carrying
     `variable`/`side`/`kind` plus the copied `value`/`robin_*` fields.
2. Remove `domains.<d>.boundary_conditions`.
3. Set `esm` to `"0.2.0"`.
4. Append `"migrated_from_v01"` to `metadata.tags` and append the source
   version to `metadata.description` for provenance (the top-level schema
   is closed, so this is where provenance goes).

See `manifest.json` for the fixture index.
