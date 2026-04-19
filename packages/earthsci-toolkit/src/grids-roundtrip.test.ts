/**
 * Round-trip tests for the §6 grids top-level schema (gt-5kq3).
 *
 * Loads each of the three canonical grid fixtures (cartesian, unstructured,
 * cubed-sphere), serializes via save(), reloads, and asserts the `grids`
 * subtree survives the round-trip byte-equivalently at the JSON level. Also
 * exercises the negative case: a `kind='loader'` generator whose loader name
 * is absent from the top-level `data_loaders` map must throw
 * E_UNKNOWN_LOADER.
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'fs'
import { join } from 'path'
import { load, save, GridValidationError } from './index.js'

const gridsDir = join(__dirname, '../../../tests/grids')

function roundTrip(fixtureFile: string): { before: unknown; after: unknown } {
  const raw = readFileSync(join(gridsDir, fixtureFile), 'utf-8')
  const loaded = load(raw)
  const serialized = save(loaded)
  const reloaded = load(serialized)
  const original = JSON.parse(raw)
  return {
    before: (original as { grids?: unknown }).grids,
    after: (reloaded as unknown as { grids?: unknown }).grids,
  }
}

describe('§6 grids top-level schema — round-trip', () => {
  it('preserves the cartesian family (uniform + nonuniform z, rank-1 loader)', () => {
    const { before, after } = roundTrip('cartesian_uniform.esm')
    expect(after).toBeDefined()
    expect(after).toEqual(before)
  })

  it('preserves the unstructured family (MPAS-style loader-backed connectivity)', () => {
    const { before, after } = roundTrip('unstructured_mpas.esm')
    expect(after).toBeDefined()
    expect(after).toEqual(before)
  })

  it('preserves the cubed_sphere family (builtin panel_connectivity + analytic metric)', () => {
    const { before, after } = roundTrip('cubed_sphere_c48.esm')
    expect(after).toBeDefined()
    expect(after).toEqual(before)
  })
})

describe('§6 grids generator validation', () => {
  it('throws E_UNKNOWN_LOADER when a metric_arrays generator references a missing loader', () => {
    // Build a minimal v0.2.0 ESM file whose grid references a loader that
    // isn't declared in top-level data_loaders.
    const bad = {
      esm: '0.2.0',
      metadata: { name: 'BadLoaderRef' },
      models: {
        M: {
          reference: { notes: 'placeholder' },
          variables: { T: { type: 'state', units: 'K', default: 273.15 } },
          equations: [{ lhs: 'D(T)', rhs: '0' }],
        },
      },
      grids: {
        g: {
          family: 'cartesian',
          dimensions: ['x'],
          extents: { x: { n: 'Nx', spacing: 'nonuniform' } },
          metric_arrays: {
            dx: {
              rank: 1,
              dim: 'x',
              generator: { kind: 'loader', loader: 'does_not_exist', field: 'dx' },
            },
          },
        },
      },
    }

    expect(() => load(JSON.stringify(bad))).toThrow(GridValidationError)
    try {
      load(JSON.stringify(bad))
    } catch (e) {
      expect(e).toBeInstanceOf(GridValidationError)
      expect((e as GridValidationError).code).toBe('E_UNKNOWN_LOADER')
    }
  })

  it('throws E_UNKNOWN_BUILTIN for a builtin generator with an unrecognized name', () => {
    const bad = {
      esm: '0.2.0',
      metadata: { name: 'BadBuiltin' },
      models: {
        M: {
          reference: { notes: 'placeholder' },
          variables: { T: { type: 'state', units: 'K', default: 273.15 } },
          equations: [{ lhs: 'D(T)', rhs: '0' }],
        },
      },
      grids: {
        g: {
          family: 'cubed_sphere',
          dimensions: ['panel', 'i', 'j'],
          extents: {
            panel: { n: 6 },
            i: { n: 'Nc' },
            j: { n: 'Nc' },
          },
          panel_connectivity: {
            neighbors: {
              shape: [6, 4],
              rank: 2,
              generator: { kind: 'builtin', name: 'not_a_real_builtin' },
            },
          },
        },
      },
    }

    try {
      load(JSON.stringify(bad))
      expect.fail('expected GridValidationError')
    } catch (e) {
      expect(e).toBeInstanceOf(GridValidationError)
      expect((e as GridValidationError).code).toBe('E_UNKNOWN_BUILTIN')
    }
  })
})
