/**
 * Round-trip tests for the §7 discretizations top-level schema, including
 * the §7.4 CrossMetricStencilRule composite variant (esm-vwo).
 *
 * Loads each canonical discretization fixture, serializes via save(), reloads,
 * and asserts the `discretizations` subtree survives the round-trip at the
 * JSON-value level. Anchors the cross-metric composite parse+round-trip
 * contract for the TypeScript binding.
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'fs'
import { join } from 'path'
import { load, save } from './index.js'

const discDir = join(__dirname, '../../../tests/discretizations')

function roundTrip(fixtureFile: string): { before: unknown; after: unknown } {
  const raw = readFileSync(join(discDir, fixtureFile), 'utf-8')
  const loaded = load(raw)
  const serialized = save(loaded)
  const reloaded = load(serialized)
  const original = JSON.parse(raw)
  return {
    before: (original as { discretizations?: unknown }).discretizations,
    after: (reloaded as unknown as { discretizations?: unknown }).discretizations,
  }
}

describe('§7 discretizations — round-trip', () => {
  it('preserves the standard centered_2nd_uniform scheme', () => {
    const { before, after } = roundTrip('centered_2nd_uniform.esm')
    expect(after).toBeDefined()
    expect(after).toEqual(before)
  })

  it('preserves the MPAS cell divergence (reduction-selector) scheme', () => {
    const { before, after } = roundTrip('mpas_cell_div.esm')
    expect(after).toBeDefined()
    expect(after).toEqual(before)
  })

  it('preserves the cross-metric cartesian composite (§7.4)', () => {
    const { before, after } = roundTrip('cross_metric_cartesian.esm')
    expect(after).toBeDefined()
    expect(after).toEqual(before)

    // Sanity-check that the composite entry is structurally recognizable
    // after round-trip: it carries the cross_metric discriminator, an axes
    // list, and a terms array (not a stencil).
    const composite = (after as Record<string, Record<string, unknown>>)[
      'laplacian_full_covariant_toy'
    ]
    expect(composite).toBeDefined()
    expect(composite.kind).toBe('cross_metric')
    expect(Array.isArray(composite.axes)).toBe(true)
    expect((composite.axes as string[])).toEqual(['xi', 'eta'])
    expect(Array.isArray(composite.terms)).toBe(true)
    expect((composite.terms as unknown[]).length).toBe(2)
    expect(composite.stencil).toBeUndefined()
  })
})
