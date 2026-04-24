/**
 * Rule-engine cross-binding conformance.
 *
 * Walks `tests/conformance/discretization/infra/rule_engine/manifest.json`,
 * loads each fixture with `losslessJsonParse` so JSON integer tokens are
 * preserved as `intLit` leaves (per RFC §5.4.1), runs
 * `rewrite(input, rules, ctx, max_passes)`, and asserts byte-for-byte
 * equality with the fixture's `expect.canonical_json` (or that the
 * declared error code is raised). Julia and Rust must emit the same
 * bytes for the same fixtures (RFC §13.1 Step 1).
 */

import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { canonicalJson } from './canonicalize.js'
import { losslessJsonParse } from './numeric-literal.js'
import {
  DEFAULT_MAX_PASSES,
  RuleEngineError,
  emptyContext,
  parseExpr,
  parseRules,
  rewrite,
  type RuleContext,
} from './rule-engine.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const REPO_ROOT = resolve(__dirname, '..', '..', '..')
const FIXTURES_DIR = resolve(
  REPO_ROOT,
  'tests',
  'conformance',
  'discretization',
  'infra',
  'rule_engine',
)

interface ManifestEntry {
  id: string
  path: string
  tags?: string[]
}
interface Manifest {
  fixtures: ManifestEntry[]
}

const manifest = losslessJsonParse(
  readFileSync(resolve(FIXTURES_DIR, 'manifest.json'), 'utf-8'),
) as unknown as Manifest

function buildContext(fixture: Record<string, unknown>): RuleContext {
  const ctx = emptyContext()
  const raw = fixture.context
  if (typeof raw !== 'object' || raw === null) return ctx
  const c = raw as Record<string, unknown>
  if (typeof c.grids === 'object' && c.grids !== null) {
    for (const [k, v] of Object.entries(c.grids as Record<string, unknown>)) {
      const meta = v as Record<string, unknown>
      ctx.grids[k] = {
        spatial_dims: asStringArray(meta.spatial_dims),
        periodic_dims: asStringArray(meta.periodic_dims),
        nonuniform_dims: asStringArray(meta.nonuniform_dims),
      }
    }
  }
  if (typeof c.variables === 'object' && c.variables !== null) {
    for (const [k, v] of Object.entries(c.variables as Record<string, unknown>)) {
      const meta = v as Record<string, unknown>
      ctx.variables[k] = {
        grid: typeof meta.grid === 'string' ? meta.grid : undefined,
        location: typeof meta.location === 'string' ? meta.location : undefined,
        shape: asStringArray(meta.shape),
      }
    }
  }
  return ctx
}

function asStringArray(x: unknown): string[] | undefined {
  if (!Array.isArray(x)) return undefined
  return x.filter((s): s is string => typeof s === 'string')
}

describe('rule engine cross-binding conformance (§13.1 Step 1)', () => {
  expect(manifest.fixtures.length).toBeGreaterThan(0)
  for (const entry of manifest.fixtures) {
    it(entry.id, () => {
      const fixture = losslessJsonParse(
        readFileSync(resolve(FIXTURES_DIR, entry.path), 'utf-8'),
      ) as unknown as Record<string, unknown>

      const rules = parseRules(fixture.rules)
      const input = parseExpr(fixture.input)
      const ctx = buildContext(fixture)
      // RFC §5.2.7: fixtures requiring a per-query-point scope evaluator
      // are parse-only for the TypeScript binding — parseRules above has
      // already asserted the fixture loads; skip the evaluation check.
      if (fixture.requires_per_point_scope === true) {
        return
      }
      const maxPassesRaw = fixture.max_passes
      const maxPasses =
        typeof maxPassesRaw === 'number'
          ? maxPassesRaw
          : (maxPassesRaw && typeof maxPassesRaw === 'object' &&
              'value' in maxPassesRaw
              ? (maxPassesRaw as { value: number }).value
              : DEFAULT_MAX_PASSES)

      const expect_ = fixture.expect as Record<string, unknown>
      const kind = expect_.kind

      if (kind === 'output') {
        const out = rewrite(input, rules, ctx, maxPasses)
        const got = canonicalJson(out)
        expect(got).toBe(expect_.canonical_json as string)
      } else if (kind === 'error') {
        try {
          rewrite(input, rules, ctx, maxPasses)
          throw new Error(`fixture ${entry.id}: expected error, got output`)
        } catch (e) {
          expect(e).toBeInstanceOf(RuleEngineError)
          expect((e as RuleEngineError).code).toBe(expect_.code as string)
        }
      } else {
        throw new Error(`fixture ${entry.id}: unknown expect.kind ${String(kind)}`)
      }
    })
  }
})
