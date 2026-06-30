/**
 * Unit tests for expression_templates / apply_expression_template
 * (esm-spec §9.6, docs/rfcs/ast-expression-templates.md, esm-giy).
 */
import * as fs from 'node:fs'
import * as path from 'node:path'
import { describe, it, expect } from 'vitest'
import { load } from './parse.js'
import {
  lowerExpressionTemplates,
  ExpressionTemplateError,
} from './lower_expression_templates.js'

// Canonical Arrhenius template fixture: 5 reactions sharing one
// `arrhenius` template and one inline rate, plus an arithmetic check.
const ARRHENIUS_FIXTURE = {
  esm: '0.4.0',
  metadata: { name: 'expr_template_smoke', authors: ['esm-giy'] },
  reaction_systems: {
    chem: {
      species: {
        A: { default: 1.0 },
        B: { default: 0.5 },
        C: { default: 0.0 },
      },
      parameters: {
        T: { default: 298.15 },
        num_density: { default: 2.5e19 },
      },
      expression_templates: {
        arrhenius: {
          params: ['A_pre', 'Ea'],
          body: {
            op: '*',
            args: [
              'A_pre',
              {
                op: 'exp',
                args: [
                  { op: '/', args: [{ op: '-', args: ['Ea'] }, 'T'] },
                ],
              },
              'num_density',
            ],
          },
        },
      },
      reactions: [
        {
          id: 'R1',
          substrates: [{ species: 'A', stoichiometry: 1 }],
          products: [{ species: 'B', stoichiometry: 1 }],
          rate: {
            op: 'apply_expression_template',
            args: [],
            name: 'arrhenius',
            bindings: { A_pre: 1.8e-12, Ea: 1500 },
          },
        },
        {
          id: 'R2',
          substrates: [{ species: 'B', stoichiometry: 1 }],
          products: [{ species: 'C', stoichiometry: 1 }],
          rate: {
            op: 'apply_expression_template',
            args: [],
            name: 'arrhenius',
            bindings: { A_pre: 3.4e-13, Ea: 800 },
          },
        },
      ],
    },
  },
}

function inlineArrhenius(A: number, Ea: number) {
  return {
    op: '*',
    args: [
      A,
      { op: 'exp', args: [{ op: '/', args: [{ op: '-', args: [Ea] }, 'T'] }] },
      'num_density',
    ],
  }
}

describe('expression_templates / apply_expression_template (esm-giy)', () => {
  it('expands apply_expression_template at load time and strips the templates block', () => {
    const file = load(JSON.parse(JSON.stringify(ARRHENIUS_FIXTURE)))
    const sys = file.reaction_systems!.chem as Record<string, unknown>
    expect('expression_templates' in sys).toBe(false)
    // Both reactions should have a rate AST identical to the inline form.
    const reactions = sys.reactions as Array<{ rate: unknown }>
    expect(reactions[0].rate).toEqual(inlineArrhenius(1.8e-12, 1500))
    expect(reactions[1].rate).toEqual(inlineArrhenius(3.4e-13, 800))
  })

  it('expansion is structurally identical to inlining (determinism)', () => {
    const a = lowerExpressionTemplates(JSON.parse(JSON.stringify(ARRHENIUS_FIXTURE)))
    const b = lowerExpressionTemplates(JSON.parse(JSON.stringify(ARRHENIUS_FIXTURE)))
    expect(a).toEqual(b)
  })

  it('files without templates parse unchanged', () => {
    const noTemplates = {
      esm: '0.4.0',
      metadata: { name: 'no_templates', authors: ['t'] },
      reaction_systems: {
        chem: {
          species: { A: {} },
          parameters: { k: { default: 1.0 } },
          reactions: [
            {
              id: 'R1',
              substrates: [{ species: 'A', stoichiometry: 1 }],
              products: null,
              rate: 'k',
            },
          ],
        },
      },
    }
    const file = load(JSON.parse(JSON.stringify(noTemplates)))
    expect(file.reaction_systems!.chem.reactions[0].rate).toBe('k')
  })

  it('rejects apply_expression_template when esm < 0.4.0', () => {
    const oldVersion = {
      ...JSON.parse(JSON.stringify(ARRHENIUS_FIXTURE)),
      esm: '0.3.5',
    }
    expect(() => load(oldVersion)).toThrow(/version_too_old|0\.4\.0/)
  })

  it('rejects unknown template name', () => {
    const fixture = JSON.parse(JSON.stringify(ARRHENIUS_FIXTURE))
    fixture.reaction_systems.chem.reactions[0].rate.name = 'unknown_form'
    expect(() => load(fixture)).toThrow(/unknown_template/)
  })

  it('rejects bindings with extra params', () => {
    const fixture = JSON.parse(JSON.stringify(ARRHENIUS_FIXTURE))
    fixture.reaction_systems.chem.reactions[0].rate.bindings.bogus = 99
    expect(() => load(fixture)).toThrow(/bindings_mismatch/)
  })

  it('rejects bindings missing a param', () => {
    const fixture = JSON.parse(JSON.stringify(ARRHENIUS_FIXTURE))
    delete fixture.reaction_systems.chem.reactions[0].rate.bindings.Ea
    expect(() => load(fixture)).toThrow(/bindings_mismatch/)
  })

  it('rejects nested apply_expression_template inside a template body', () => {
    const fixture = JSON.parse(JSON.stringify(ARRHENIUS_FIXTURE))
    // Inject a recursive body
    fixture.reaction_systems.chem.expression_templates.arrhenius.body = {
      op: 'apply_expression_template',
      args: [],
      name: 'arrhenius',
      bindings: { A_pre: 1, Ea: 1 },
    }
    expect(() => load(fixture)).toThrow(/recursive_body/)
  })

  it('expansion accepts AST-valued bindings (not just scalars)', () => {
    const fixture = JSON.parse(JSON.stringify(ARRHENIUS_FIXTURE))
    fixture.reaction_systems.chem.reactions[0].rate.bindings.Ea = {
      op: '*',
      args: [3, 'T'],
    }
    const file = load(fixture)
    const rate = file.reaction_systems!.chem.reactions[0].rate as Record<string, unknown>
    expect(rate.op).toBe('*')
    // The inner exp's argument should be (-(3*T))/T (post-substitution).
    const args = rate.args as Array<unknown>
    expect(args[0]).toBe(1.8e-12)
    expect((args[1] as Record<string, unknown>).op).toBe('exp')
  })

  it('conformance fixture matches the canonical expanded form (cross-binding pin)', () => {
    const root = path.resolve(__dirname, '../../..')
    const fixturePath = path.join(
      root,
      'tests/conformance/expression_templates/arrhenius_smoke/fixture.esm',
    )
    const expandedPath = path.join(
      root,
      'tests/conformance/expression_templates/arrhenius_smoke/expanded.esm',
    )
    const file = load(fs.readFileSync(fixturePath, 'utf8'))
    const expanded = JSON.parse(fs.readFileSync(expandedPath, 'utf8'))
    expect(file.reaction_systems!.chem.reactions).toEqual(
      expanded.reaction_systems.chem.reactions,
    )
  })

  it('ExpressionTemplateError is thrown with stable diagnostic codes', () => {
    const fixture = JSON.parse(JSON.stringify(ARRHENIUS_FIXTURE))
    fixture.reaction_systems.chem.reactions[0].rate.name = 'missing'
    try {
      load(fixture)
      throw new Error('expected error')
    } catch (e) {
      expect(e).toBeInstanceOf(ExpressionTemplateError)
      expect((e as ExpressionTemplateError).code).toBe(
        'apply_expression_template_unknown_template',
      )
    }
  })
})

// ---------------------------------------------------------------------------
// Auto-applied `match` rewrite rules (esm-spec §9.6, §9.6.8).
// ---------------------------------------------------------------------------

function gradModel(templates: Record<string, unknown>, rhs: unknown) {
  return {
    esm: '0.4.0',
    metadata: { name: 'rewrite_rules', authors: ['t'] },
    models: {
      M: {
        expression_templates: templates,
        equations: [{ lhs: 'q', rhs }],
      },
    },
  }
}

describe('match rewrite rules (esm-spec §9.6 auto-applied lowering)', () => {
  it('auto-applies an operator-lowering rule: binds operand, passes through unbound params', () => {
    const file = gradModel(
      {
        central_grad_x: {
          params: ['f', 'dx'],
          match: { op: 'grad', args: ['f'], dim: 'x' },
          body: { op: '/', args: [{ op: '-', args: ['f', 'f'] }, 'dx'] },
        },
      },
      { op: 'grad', args: ['c'], dim: 'x' },
    )
    const out = lowerExpressionTemplates(file) as any
    expect('expression_templates' in out.models.M).toBe(false)
    // f → "c" (operand); dx unbound by `match`, so it stays a bare ref.
    expect(out.models.M.equations[0].rhs).toEqual({
      op: '/',
      args: [{ op: '-', args: ['c', 'c'] }, 'dx'],
    })
  })

  it('binds an operand metavariable to a full sub-AST (repeated occurrences)', () => {
    const file = gradModel(
      {
        dup: {
          params: ['f'],
          match: { op: 'grad', args: ['f'], dim: 'x' },
          body: { op: 'makearray', args: ['f', 'f'] },
        },
      },
      { op: 'grad', args: [{ op: '+', args: ['a', 'b'] }], dim: 'x' },
    )
    const out = lowerExpressionTemplates(file) as any
    expect(out.models.M.equations[0].rhs).toEqual({
      op: 'makearray',
      args: [
        { op: '+', args: ['a', 'b'] },
        { op: '+', args: ['a', 'b'] },
      ],
    })
  })

  it('binds a scalar-field metavariable (dim) to the matched literal', () => {
    const file = gradModel(
      {
        grad_any: {
          params: ['f', 'd'],
          match: { op: 'grad', args: ['f'], dim: 'd' },
          body: { op: 'index', args: ['f'], along: 'd' },
        },
      },
      { op: 'grad', args: ['c'], dim: 'y' },
    )
    const out = lowerExpressionTemplates(file) as any
    // d → "y" (scalar field literal), substituted into the body's `along` field.
    expect(out.models.M.equations[0].rhs).toEqual({ op: 'index', args: ['c'], along: 'y' })
  })

  it('applies match rules in declaration order (first match wins)', () => {
    const file = gradModel(
      {
        rule_a: { params: ['f'], match: { op: 'grad', args: ['f'], dim: 'x' }, body: { op: 'sin', args: ['f'] } },
        rule_b: { params: ['g'], match: { op: 'grad', args: ['g'], dim: 'x' }, body: { op: 'cos', args: ['g'] } },
      },
      { op: 'grad', args: ['c'], dim: 'x' },
    )
    const out = lowerExpressionTemplates(file) as any
    expect(out.models.M.equations[0].rhs).toEqual({ op: 'sin', args: ['c'] })
  })

  it('does not re-scan a replacement body (single pass, no recursion)', () => {
    const file = gradModel(
      {
        g2d: { params: ['f'], match: { op: 'grad', args: ['f'], dim: 'x' }, body: { op: 'div', args: ['f'], dim: 'x' } },
        d2z: { params: ['f'], match: { op: 'div', args: ['f'], dim: 'x' }, body: { op: 'abs', args: ['f'] } },
      },
      { op: 'grad', args: ['c'], dim: 'x' },
    )
    const out = lowerExpressionTemplates(file) as any
    // grad → div fires; the freshly produced div is NOT re-scanned, so d2z never runs.
    expect(out.models.M.equations[0].rhs).toEqual({ op: 'div', args: ['c'], dim: 'x' })
  })

  it('rejects a match rule whose body re-introduces its own pattern (rewrite_rule_nonterminating)', () => {
    const file = gradModel(
      {
        bad: {
          params: ['f'],
          match: { op: 'grad', args: ['f'], dim: 'x' },
          body: { op: '+', args: [{ op: 'grad', args: ['f'], dim: 'x' }, 'f'] },
        },
      },
      { op: 'grad', args: ['c'], dim: 'x' },
    )
    expect(() => lowerExpressionTemplates(file)).toThrow(/rewrite_rule_nonterminating/)
    try {
      lowerExpressionTemplates(gradModel(
        {
          bad: {
            params: ['f'],
            match: { op: 'grad', args: ['f'], dim: 'x' },
            body: { op: 'grad', args: ['f'], dim: 'x' },
          },
        },
        'c',
      ))
      throw new Error('expected error')
    } catch (e) {
      expect((e as ExpressionTemplateError).code).toBe('rewrite_rule_nonterminating')
    }
  })

  it('ignores node fields the pattern omits; leaves non-matching nodes untouched', () => {
    const file = {
      esm: '0.4.0',
      metadata: { name: 'partial_match', authors: ['t'] },
      models: {
        M: {
          expression_templates: {
            grad_x: {
              params: ['f'],
              match: { op: 'grad', args: ['f'], dim: 'x' },
              body: { op: 'makearray', args: ['f'] },
            },
          },
          equations: [
            // Matches despite carrying an extra field absent from the pattern.
            { lhs: 'p', rhs: { op: 'grad', args: ['c'], dim: 'x', note: 'keep' } },
            // Does not match (dim differs) — left untouched.
            { lhs: 'q', rhs: { op: 'grad', args: ['c'], dim: 'y' } },
          ],
        },
      },
    }
    const out = lowerExpressionTemplates(file) as any
    expect(out.models.M.equations[0].rhs).toEqual({ op: 'makearray', args: ['c'] })
    expect(out.models.M.equations[1].rhs).toEqual({ op: 'grad', args: ['c'], dim: 'y' })
  })

  it('accepts the `match` field through load() and auto-applies the rule', () => {
    const fixture = {
      esm: '0.4.0',
      metadata: { name: 'match_load', authors: ['t'] },
      reaction_systems: {
        chem: {
          species: { A: { default: 1.0 }, B: { default: 0.0 } },
          parameters: { T: { default: 298.15 }, num_density: { default: 2.5e19 } },
          expression_templates: {
            max_to_sum: {
              params: ['a', 'b'],
              match: { op: 'max', args: ['a', 'b'] },
              body: { op: '+', args: ['a', 'b'] },
            },
          },
          reactions: [
            {
              id: 'R1',
              substrates: [{ species: 'A', stoichiometry: 1 }],
              products: [{ species: 'B', stoichiometry: 1 }],
              rate: { op: 'max', args: ['T', 'num_density'] },
            },
          ],
        },
      },
    }
    const file = load(fixture)
    expect(file.reaction_systems!.chem.reactions[0].rate).toEqual({
      op: '+',
      args: ['T', 'num_density'],
    })
    expect('expression_templates' in (file.reaction_systems!.chem as Record<string, unknown>)).toBe(
      false,
    )
  })
})
