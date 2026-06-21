/**
 * Round-trip tests for the §7 discretizations top-level schema.
 *
 * Loads each canonical discretization fixture, serializes via save(), reloads,
 * and asserts the `discretizations` subtree survives the round-trip at the
 * JSON-value level.
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

  it('preserves the multi-output PPM reconstruction fixture (§7.9)', () => {
    const { before, after } = roundTrip('multi_output_ppm_reconstruction.esm')
    expect(after).toBeDefined()
    expect(after).toEqual(before)

    type DiscMap = Record<string, Record<string, unknown>>
    const afterDiscs = after as DiscMap

    // Provider: ppm_reconstruction — stencil is an object, not an array
    const provider = afterDiscs['ppm_reconstruction']
    expect(provider).toBeDefined()
    expect(provider.kind).toBe('multi_output_stencil')
    expect(Array.isArray(provider.outputs)).toBe(true)
    expect(provider.outputs as string[]).toEqual(['q_left_edge', 'q_right_edge'])
    // stencil must be an object (not array)
    expect(typeof provider.stencil).toBe('object')
    expect(Array.isArray(provider.stencil)).toBe(false)
    const stencilObj = provider.stencil as Record<string, unknown[]>
    expect(Array.isArray(stencilObj['q_left_edge'])).toBe(true)
    expect((stencilObj['q_left_edge'] as unknown[]).length).toBe(2)
    expect(Array.isArray(stencilObj['q_right_edge'])).toBe(true)
    expect((stencilObj['q_right_edge'] as unknown[]).length).toBe(2)
    expect(provider.emits_location).toBe('face')
    // primary is explicitly null
    expect(provider.primary).toBeNull()

    // Consumer: ppm_flux — carries a requires map
    const consumer = afterDiscs['ppm_flux']
    expect(consumer).toBeDefined()
    expect(consumer.kind).toBe('stencil')
    expect(typeof consumer.requires).toBe('object')
    const req = consumer.requires as Record<string, string>
    expect(req['q_left_edge']).toBe('ppm_reconstruction#q_left_edge')
    expect(req['q_right_edge']).toBe('ppm_reconstruction#q_right_edge')
  })
})
