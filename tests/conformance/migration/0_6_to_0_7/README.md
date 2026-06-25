# Migration fixtures: v0.6.0 → v0.7.0 (pure-I/O data loaders, hard break)

Cross-binding fixtures for the v0.6.0 → v0.7.0 hard break defined by
`docs/rfcs/pure-io-data-loaders.md` §4.1 (bead ess-v9a.7).

In v0.7.0 the `DataLoader` is reduced to **pure I/O**: it locates, reads, and
slices bytes and describes its native grid as a GDD `Grid` under `grid`. The
loader-level `regridding` and `spatial` blocks (and the `DataLoaderRegridding` /
`DataLoaderSpatial` / `DataLoaderStaggering` `$defs`) are **removed** —
regridding/reprojection are now per-variable concerns on the owning model
(`Model.regrid`, esm-spec.md §6.2 / §8.6).

Unlike `../0_1_to_0_2/` (a *transformation* fixture set with `input` →
`expected`), this directory is a **rejection** contract.

## Rejection fixtures

Each is a pre-0.7.0 loader file that still carries a removed block. Every
binding MUST reject it at load with the named, version-keyed diagnostic — the
same shape as `apply_expression_template_version_too_old`: the check reads the
file's declared `esm` version, and when it is `< 0.7.0` and a loader still
carries the removed block, it fails the load with a clear, RFC-pointing error
rather than a bare schema rejection.

| Fixture | Removed block | Diagnostic |
|---|---|---|
| `loader_regridding_removed.esm` | `data_loaders.<n>.regridding` | `data_loader_regridding_removed` |
| `loader_spatial_removed.esm`    | `data_loaders.<n>.spatial`    | `data_loader_spatial_removed` |

Both fixtures also fail JSON-Schema validation (the pure-I/O `DataLoader`
declares `additionalProperties: false`), so a schema-validating binding has two
independent reasons to reject. The named binding diagnostic is the
migration-directing layer on top of that.

## Acceptance fixture

`loader_migrated.esm` is the post-migration 0.7.0 shape of the same loader: the
native grid is a GDD `Grid` under `grid`, and there is no `regridding`/`spatial`
block. Every binding MUST load it without error — the positive counterpart
proving the version bump accepts migrated files.

## Migration recipe

1. Set `esm` to `"0.7.0"`.
2. Delete each `data_loaders.<n>.spatial` block; describe the native grid as a
   GDD `Grid` under `data_loaders.<n>.grid` (omit it entirely when the native
   grid is resolved at runtime).
3. Delete each `data_loaders.<n>.regridding` block; move any per-variable
   regridding choice (`method`, point-loader `missing_value`) to the owning
   model's `Model.regrid` map.

See `manifest.json` for the machine-readable fixture index and the exact
rejection rule.
