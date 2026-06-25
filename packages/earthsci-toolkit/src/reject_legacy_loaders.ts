/**
 * Load-time rejection of pre-0.7.0 data-loader shapes
 * (RFC pure-io-data-loaders §4.1, bead ess-v9a.7).
 *
 * The v0.7.0 pure-I/O hard break removed two blocks from `DataLoader`:
 *   - `DataLoader.regridding` — regridding is now a per-variable model
 *     concern (see `Model.regrid`).
 *   - `DataLoader.spatial` — the native grid is now a GDD `Grid` under
 *     `grid`.
 *
 * Files declaring `esm` < 0.7.0 that still carry these removed blocks are
 * rejected at load time with named, version-keyed diagnostics — mirroring
 * `rejectExpressionTemplatesPreV04` so the user sees a stable migration
 * hint instead of a generic schema "extra property" error.
 *
 * Operates on the pre-coercion JSON view (plain objects) — runs in
 * `load()` after `rejectExpressionTemplatesPreV04` but before schema
 * validation.
 *
 * Errors:
 *   - data_loader_regridding_removed
 *   - data_loader_spatial_removed
 */

import { isNumericLiteral } from './numeric-literal.js'

export class LegacyDataLoaderError extends Error {
  constructor(public code: string, message: string) {
    super(`[${code}] ${message}`)
    this.name = 'LegacyDataLoaderError'
  }
}

function isObject(v: unknown): v is Record<string, unknown> {
  return (
    typeof v === 'object' && v !== null && !Array.isArray(v) && !isNumericLiteral(v)
  )
}

function parseSemver(v: unknown): { major: number; minor: number; patch: number } | null {
  if (typeof v !== 'string') return null
  const m = /^(\d+)\.(\d+)\.(\d+)$/.exec(v)
  if (!m) return null
  return { major: Number(m[1]), minor: Number(m[2]), patch: Number(m[3]) }
}

/**
 * Reject `DataLoader.regridding` / `DataLoader.spatial` in files declaring
 * `esm` < 0.7.0. Operates on the pre-coercion JSON view.
 */
export function rejectLegacyDataLoaderShapes(view: unknown): void {
  if (!isObject(view)) return
  const esm = (view as { esm?: unknown }).esm
  const v = parseSemver(esm)
  if (!v) return
  // Version gate: only pre-0.7.0 files can carry the removed blocks.
  if (!(v.major === 0 && v.minor < 7)) return

  const loaders = (view as { data_loaders?: unknown }).data_loaders
  if (!isObject(loaders)) return

  const regriddingPaths: string[] = []
  const spatialPaths: string[] = []
  for (const [name, loader] of Object.entries(loaders)) {
    if (!isObject(loader)) continue
    if ('regridding' in loader) regriddingPaths.push(`/data_loaders/${name}/regridding`)
    if ('spatial' in loader) spatialPaths.push(`/data_loaders/${name}/spatial`)
  }

  if (regriddingPaths.length > 0) {
    throw new LegacyDataLoaderError(
      'data_loader_regridding_removed',
      `DataLoader \`regridding\` was removed in esm 0.7.0 (regridding is now a per-variable model concern — see \`Model.regrid\`; RFC pure-io-data-loaders §4.1); file declares ${esm}. Migrate by deleting the block and moving the per-variable regridding choice to the owning model. Offending paths: ${regriddingPaths.join(', ')}`,
    )
  }
  if (spatialPaths.length > 0) {
    throw new LegacyDataLoaderError(
      'data_loader_spatial_removed',
      `DataLoader \`spatial\` was removed in esm 0.7.0 (the native grid is now a GDD \`Grid\` under \`grid\`; RFC pure-io-data-loaders §4.1); file declares ${esm}. Migrate by replacing the block with a \`grid\` GDD Grid. Offending paths: ${spatialPaths.join(', ')}`,
    )
  }
}
