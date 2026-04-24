/**
 * Round-trip tests for the §7.4 staggering_rules top-level schema (esm-15f).
 *
 * Loads the MPAS C-grid staggering fixture, serializes via save(), reloads,
 * and asserts the `staggering_rules` subtree survives the round-trip byte-
 * equivalently at the JSON level.
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'fs'
import { join } from 'path'
import { load, save } from './index.js'

const fixturePath = join(__dirname, '../../../tests/grids/mpas_c_grid_staggering.esm')

describe('§7.4 staggering_rules top-level schema — round-trip', () => {
  it('preserves the mpas_c_grid_staggering rule across load/save/load', () => {
    const raw = readFileSync(fixturePath, 'utf-8')
    const loaded = load(raw)
    const serialized = save(loaded)
    const reloaded = load(serialized)
    const original = JSON.parse(raw) as { staggering_rules?: unknown }
    const after = (reloaded as unknown as { staggering_rules?: unknown }).staggering_rules
    expect(after).toBeDefined()
    expect(after).toEqual(original.staggering_rules)
  })

  it('exposes the rule fields on the typed model', () => {
    const raw = readFileSync(fixturePath, 'utf-8')
    const loaded = load(raw) as unknown as {
      staggering_rules?: Record<string, {
        kind: string
        grid: string
        edge_normal_convention?: string
        cell_quantity_locations?: Record<string, string>
      }>
    }
    expect(loaded.staggering_rules).toBeDefined()
    const rule = loaded.staggering_rules!['mpas_c_grid_staggering']
    expect(rule.kind).toBe('unstructured_c_grid')
    expect(rule.grid).toBe('mpas_cvmesh')
    expect(rule.edge_normal_convention).toBe('outward_from_first_cell')
    expect(rule.cell_quantity_locations?.u).toBe('edge_midpoint')
    expect(rule.cell_quantity_locations?.zeta).toBe('vertex')
  })
})
