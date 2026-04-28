/**
 * Tests for parse-time expansion of expression_templates (RFC v2 §4, esm-giy).
 */

import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { load, SchemaValidationError } from './parse.js'

const FIXTURE = resolve(
  __dirname,
  '../../../tests/valid/expression_templates_arrhenius.esm',
)

function arrheniusInline(aPre: number, ea: number) {
  return {
    op: '*',
    args: [
      aPre,
      {
        op: 'exp',
        args: [{ op: '/', args: [{ op: '-', args: [ea] }, 'T'] }],
      },
      'num_density',
    ],
  }
}

function readFixture(): string {
  return readFileSync(FIXTURE, 'utf8')
}

describe('expression_templates parse-time expansion', () => {
  it('loads the fixture with rates expanded to inline AST', () => {
    const esm = load(readFixture())
    const rs = esm.reaction_systems!.ToyArrhenius
    expect((rs as unknown as Record<string, unknown>).expression_templates).toBeUndefined()
    const cases: Array<[string, number, number]> = [
      ['R1', 1.8e-12, 1500],
      ['R2', 3e-13, 460],
      ['R3', 4.5e-14, 920],
    ]
    for (const [id, a, ea] of cases) {
      const r = rs.reactions.find((x) => x.id === id)!
      expect(r.rate).toEqual(arrheniusInline(a, ea))
    }
  })

  it('rejects apply_expression_template in pre-0.4.0 files', () => {
    const data = JSON.parse(readFixture()) as Record<string, unknown>
    data.esm = '0.3.0'
    expect(() => load(data)).toThrow(SchemaValidationError)
  })

  it('rejects unknown template names', () => {
    const data = JSON.parse(readFixture()) as Record<string, unknown>
    const rs = (data.reaction_systems as Record<string, Record<string, unknown>>).ToyArrhenius
    const reactions = rs.reactions as Array<Record<string, unknown>>
    reactions[0].rate = {
      op: 'apply_expression_template',
      args: [],
      name: 'no_such_template',
      bindings: { A_pre: 1.0, Ea: 1.0 },
    }
    expect(() => load(data)).toThrow(SchemaValidationError)
  })

  it('rejects missing bindings', () => {
    const data = JSON.parse(readFixture()) as Record<string, unknown>
    const rs = (data.reaction_systems as Record<string, Record<string, unknown>>).ToyArrhenius
    const reactions = rs.reactions as Array<Record<string, unknown>>
    reactions[0].rate = {
      op: 'apply_expression_template',
      args: [],
      name: 'arrhenius',
      bindings: { A_pre: 1.0 },
    }
    expect(() => load(data)).toThrow(SchemaValidationError)
  })

  it('rejects extra bindings', () => {
    const data = JSON.parse(readFixture()) as Record<string, unknown>
    const rs = (data.reaction_systems as Record<string, Record<string, unknown>>).ToyArrhenius
    const reactions = rs.reactions as Array<Record<string, unknown>>
    reactions[0].rate = {
      op: 'apply_expression_template',
      args: [],
      name: 'arrhenius',
      bindings: { A_pre: 1.0, Ea: 1.0, Junk: 2.0 },
    }
    expect(() => load(data)).toThrow(SchemaValidationError)
  })

  it('two loads produce structurally identical expansions', () => {
    const esm1 = load(readFixture())
    const esm2 = load(readFixture())
    for (let i = 0; i < esm1.reaction_systems!.ToyArrhenius.reactions.length; i++) {
      expect(esm1.reaction_systems!.ToyArrhenius.reactions[i].rate).toEqual(
        esm2.reaction_systems!.ToyArrhenius.reactions[i].rate,
      )
    }
  })
})
