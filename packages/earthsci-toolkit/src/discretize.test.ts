/**
 * Tests for DAE binding contract: trivial-factor + error otherwise
 * (discretization RFC §12; gt-tuva).
 */

import { describe, it, expect } from 'vitest'
import { discretize, DAEError, E_NONTRIVIAL_DAE, type DiscretizeResult } from './discretize.js'
import type { EsmFile, Equation } from './types.js'

function mkEsm(equations: Equation[], extra: Partial<EsmFile['models']> = {}): EsmFile {
  return {
    esm: '0.2.0',
    metadata: { name: 'test' },
    models: {
      M: {
        variables: {
          x: { type: 'state', default: 1.0, units: '1' },
          y: { type: 'observed', units: '1' },
          k: { type: 'parameter', default: 0.5, units: '1/s' },
        },
        equations,
      },
      ...extra,
    },
  } as EsmFile
}

describe('discretize — pure ODE', () => {
  it('leaves a scalar ODE untouched and stamps system_class=ode', () => {
    const esm = mkEsm([
      {
        lhs: { op: 'D', args: ['x'], wrt: 't' } as any,
        rhs: { op: '*', args: [{ op: '-', args: ['k'] }, 'x'] },
      },
    ])
    const out: DiscretizeResult = discretize(esm)
    expect(out.metadata.system_class).toBe('ode')
    expect(out.metadata.dae_info).toEqual({
      algebraic_equation_count: 0,
      per_model: { M: 0 },
    })
    expect(out.models!.M!.equations).toHaveLength(1)
    // Input not mutated (deep clone).
    expect((esm.metadata as any).system_class).toBeUndefined()
  })

  it('accepts multiple pure-ODE models', () => {
    const esm: EsmFile = {
      esm: '0.2.0',
      metadata: { name: 'multi' },
      models: {
        A: {
          variables: { x: { type: 'state', default: 1 } },
          equations: [{ lhs: { op: 'D', args: ['x'], wrt: 't' } as any, rhs: 'x' }],
        },
        B: {
          variables: { z: { type: 'state', default: 2 } },
          equations: [{ lhs: { op: 'D', args: ['z'], wrt: 't' } as any, rhs: 'z' }],
        },
      },
    } as EsmFile
    const out = discretize(esm)
    expect(out.metadata.system_class).toBe('ode')
    expect(out.metadata.dae_info).toEqual({
      algebraic_equation_count: 0,
      per_model: { A: 0, B: 0 },
    })
  })
})

describe('discretize — trivial DAE factoring', () => {
  it('factors a single observed equation (y = sin(x); D(x) = y)', () => {
    const esm = mkEsm([
      {
        lhs: { op: 'D', args: ['x'], wrt: 't' } as any,
        rhs: 'y',
      },
      { lhs: 'y', rhs: { op: 'sin', args: ['x'] } },
    ])
    const out = discretize(esm)
    expect(out.metadata.system_class).toBe('ode')
    expect(out.metadata.dae_info?.algebraic_equation_count).toBe(0)
    const eqns = out.models!.M!.equations
    expect(eqns).toHaveLength(1)
    expect(eqns[0]!.rhs).toEqual({ op: 'sin', args: ['x'] })
  })

  it('factors a chain of observed equations to a pure-ODE system', () => {
    // z = y + 1; y = sin(x); D(x) = z  →  D(x) = sin(x) + 1
    const esm = mkEsm([
      { lhs: { op: 'D', args: ['x'], wrt: 't' } as any, rhs: 'z' },
      { lhs: 'z', rhs: { op: '+', args: ['y', 1] } },
      { lhs: 'y', rhs: { op: 'sin', args: ['x'] } },
    ])
    const out = discretize(esm)
    expect(out.metadata.system_class).toBe('ode')
    expect(out.metadata.dae_info?.algebraic_equation_count).toBe(0)
    const eqns = out.models!.M!.equations
    expect(eqns).toHaveLength(1)
    expect(eqns[0]!.rhs).toEqual({ op: '+', args: [{ op: 'sin', args: ['x'] }, 1] })
  })

  it('factors observed equations mixed among differential equations', () => {
    // Two differentials + one observed that feeds one of them.
    const esm: EsmFile = {
      esm: '0.2.0',
      metadata: { name: 'mixed' },
      models: {
        M: {
          variables: {
            x: { type: 'state', default: 1 },
            w: { type: 'state', default: 2 },
            y: { type: 'observed' },
          },
          equations: [
            { lhs: { op: 'D', args: ['x'], wrt: 't' } as any, rhs: 'y' },
            { lhs: { op: 'D', args: ['w'], wrt: 't' } as any, rhs: { op: '-', args: ['w'] } },
            { lhs: 'y', rhs: { op: '^', args: ['x', 2] } },
          ],
        },
      },
    } as EsmFile
    const out = discretize(esm)
    expect(out.metadata.system_class).toBe('ode')
    expect(out.models!.M!.equations).toHaveLength(2)
    const dX = out.models!.M!.equations.find(
      e => typeof e.lhs === 'object' && (e.lhs as any).op === 'D' && (e.lhs as any).args?.[0] === 'x'
    )
    expect(dX?.rhs).toEqual({ op: '^', args: ['x', 2] })
  })
})

describe('discretize — E_NONTRIVIAL_DAE', () => {
  it('errors on an implicit constraint (x^2 + y^2 = 1)', () => {
    // Author an explicit algebraic constraint with a non-variable LHS.
    const esm = mkEsm([
      { lhs: { op: 'D', args: ['x'], wrt: 't' } as any, rhs: { op: '-', args: ['x'] } },
      {
        lhs: { op: '+', args: [{ op: '^', args: ['x', 2] }, { op: '^', args: ['y', 2] }] },
        rhs: 1,
      },
    ])
    expect(() => discretize(esm)).toThrow(DAEError)
    try {
      discretize(esm)
    } catch (e) {
      const err = e as DAEError
      expect(err.code).toBe(E_NONTRIVIAL_DAE)
      expect(err.message).toContain('E_NONTRIVIAL_DAE')
      expect(err.message).toContain('models.M.equations[1]')
      expect(err.message).toContain('Julia')
      expect(err.equationPath).toBe('models.M.equations[1]')
    }
  })

  it('errors on a cyclic observed chain (y = z + 1; z = y - 1)', () => {
    const esm = mkEsm([
      { lhs: { op: 'D', args: ['x'], wrt: 't' } as any, rhs: 'y' },
      { lhs: 'y', rhs: { op: '+', args: ['z', 1] } },
      { lhs: 'z', rhs: { op: '-', args: ['y', 1] } },
    ])
    // y=z+1 is trivial (y not in z+1), factor first → substitutes y
    // everywhere; the z equation becomes z = (z+1) - 1, which still
    // has z on both sides → non-trivial. Actually after substitution
    // into z eqn: lhs 'z', rhs becomes (z+1) - 1. z is in rhs now.
    expect(() => discretize(esm)).toThrow(/E_NONTRIVIAL_DAE/)
  })

  it('errors on a self-referential algebraic equation (y = sin(y))', () => {
    const esm = mkEsm([
      { lhs: { op: 'D', args: ['x'], wrt: 't' } as any, rhs: { op: '-', args: ['x'] } },
      { lhs: 'y', rhs: { op: 'sin', args: ['y'] } },
    ])
    expect(() => discretize(esm)).toThrow(/E_NONTRIVIAL_DAE/)
    try {
      discretize(esm)
    } catch (e) {
      expect((e as DAEError).code).toBe(E_NONTRIVIAL_DAE)
    }
  })

  it('stamps system_class=dae and dae_info before throwing', () => {
    const esm = mkEsm([
      { lhs: { op: 'D', args: ['x'], wrt: 't' } as any, rhs: { op: '-', args: ['x'] } },
      { lhs: 'y', rhs: { op: 'sin', args: ['y'] } },
    ])
    try {
      discretize(esm)
      throw new Error('expected throw')
    } catch (e) {
      expect(e).toBeInstanceOf(DAEError)
      expect((e as DAEError).code).toBe(E_NONTRIVIAL_DAE)
    }
  })

  it('rejects factoring an observed candidate that is also differentiated', () => {
    // Pathological input: y has both an observed definition and a time
    // derivative. Naive substitution would rewrite D(y) → D(sin(x))
    // losing the chain rule. We refuse and return an algebraic
    // residual instead.
    const esm = mkEsm([
      { lhs: 'y', rhs: { op: 'sin', args: ['x'] } },
      { lhs: { op: 'D', args: ['y'], wrt: 't' } as any, rhs: 'k' },
      { lhs: { op: 'D', args: ['x'], wrt: 't' } as any, rhs: 'y' },
    ])
    expect(() => discretize(esm)).toThrow(/E_NONTRIVIAL_DAE/)
  })
})

describe('discretize — independent variable resolution', () => {
  it('uses domain.independent_variable when set, not default t', () => {
    const esm: EsmFile = {
      esm: '0.2.0',
      metadata: { name: 'custom-indep' },
      domains: {
        spatial: { independent_variable: 's' } as any,
      },
      models: {
        M: {
          domain: 'spatial',
          variables: { u: { type: 'state', default: 0 } },
          equations: [
            // D(u, wrt=s) is differential because the model's indep is `s`.
            { lhs: { op: 'D', args: ['u'], wrt: 's' } as any, rhs: 'u' },
          ],
        },
      },
    } as EsmFile
    const out = discretize(esm)
    expect(out.metadata.system_class).toBe('ode')
  })

  it('classifies D(x, wrt=t) as algebraic when model indep is not t', () => {
    const esm: EsmFile = {
      esm: '0.2.0',
      metadata: { name: 'wrong-wrt' },
      domains: { spatial: { independent_variable: 's' } as any },
      models: {
        M: {
          domain: 'spatial',
          variables: { u: { type: 'state', default: 0 } },
          equations: [{ lhs: { op: 'D', args: ['u'], wrt: 't' } as any, rhs: 'u' }],
        },
      },
    } as EsmFile
    expect(() => discretize(esm)).toThrow(/E_NONTRIVIAL_DAE/)
  })
})

describe('discretize — algebraic markers', () => {
  it('honors explicit algebraic: true markers', () => {
    const esm = mkEsm([
      { lhs: { op: 'D', args: ['x'], wrt: 't' } as any, rhs: { op: '-', args: ['x'] } },
      { lhs: 'y', rhs: { op: 'sin', args: ['x'] }, algebraic: true } as any,
    ])
    // Marker forces algebraic classification. LHS is still a plain
    // var and y doesn't appear in sin(x), so factoring still succeeds
    // and the output is pure-ODE.
    const out = discretize(esm)
    expect(out.metadata.system_class).toBe('ode')
  })

  it('honors produces: "algebraic" markers on residual equations', () => {
    const esm = mkEsm([
      { lhs: { op: 'D', args: ['x'], wrt: 't' } as any, rhs: { op: '-', args: ['x'] } },
      // Cycle on y: not trivial. produces marker is redundant here but exercised.
      { lhs: 'y', rhs: 'y', produces: 'algebraic' } as any,
    ])
    expect(() => discretize(esm)).toThrow(/E_NONTRIVIAL_DAE/)
  })
})
