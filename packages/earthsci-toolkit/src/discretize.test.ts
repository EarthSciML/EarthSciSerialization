/**
 * Unit tests for discretize() — mirrors
 * `packages/EarthSciSerialization.jl/test/discretize_test.jl` so the
 * TypeScript binding emits behaviorally identical output on the Step 1
 * fixtures (RFC §11, gt-gbs2; RFC §12, gt-q7sh).
 */

import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { canonicalJson } from './canonicalize.js'
import {
  discretize,
  E_DISCRETIZE_UNREWRITTEN_PDE_OP,
  E_NO_DAE_SUPPORT,
} from './index.js'
import { RuleEngineError, parseExpr } from './rule-engine.js'

function scalarOdeEsm(): Record<string, unknown> {
  return {
    esm: '0.2.0',
    metadata: {
      name: 'scalar_ode',
      description: 'dx/dt = -k * x',
    },
    models: {
      M: {
        variables: {
          x: { type: 'state', default: 1.0, units: '1' },
          k: { type: 'parameter', default: 0.5, units: '1/s' },
        },
        equations: [
          {
            lhs: { op: 'D', args: ['x'], wrt: 't' },
            rhs: { op: '*', args: [{ op: '-', args: ['k'] }, 'x'] },
          },
        ],
      },
    },
  }
}

function heat1dEsm(opts: { withRule?: boolean } = {}): Record<string, unknown> {
  const withRule = opts.withRule ?? true
  const esm: Record<string, unknown> = {
    esm: '0.2.0',
    metadata: { name: 'heat_1d' },
    grids: {
      gx: {
        family: 'cartesian',
        dimensions: [{ name: 'i', size: 8, periodic: true, spacing: 'uniform' }],
      },
    },
    models: {
      M: {
        grid: 'gx',
        variables: {
          u: {
            type: 'state',
            default: 0.0,
            units: '1',
            shape: ['i'],
            location: 'cell_center',
          },
        },
        equations: [
          {
            lhs: { op: 'D', args: ['u'], wrt: 't' },
            rhs: { op: 'grad', args: ['u'], dim: 'i' },
          },
        ],
      },
    },
  }
  if (withRule) {
    esm.rules = [
      {
        name: 'centered_grad',
        pattern: { op: 'grad', args: ['$u'], dim: '$x' },
        replacement: {
          op: '+',
          args: [
            { op: '-', args: [{ op: 'index', args: ['$u', { op: '-', args: ['$x', 1] }] }] },
            { op: 'index', args: ['$u', { op: '+', args: ['$x', 1] }] },
          ],
        },
      },
    ]
  }
  return esm
}

function mixedDaeEsm(): Record<string, unknown> {
  return {
    esm: '0.2.0',
    metadata: { name: 'mixed_dae' },
    models: {
      M: {
        variables: {
          x: { type: 'state', default: 1.0, units: '1' },
          y: { type: 'observed', units: '1' },
          k: { type: 'parameter', default: 0.5, units: '1/s' },
        },
        equations: [
          {
            lhs: { op: 'D', args: ['x'], wrt: 't' },
            rhs: { op: '*', args: [{ op: '-', args: ['k'] }, 'x'] },
          },
          {
            lhs: 'y',
            rhs: { op: '^', args: ['x', 2] },
          },
        ],
      },
    },
  }
}

describe('discretize() — RFC §11 pipeline', () => {
  it('runs end-to-end on a scalar ODE and records provenance', () => {
    const esm = scalarOdeEsm()
    const out = discretize(esm) as Record<string, unknown>
    const meta = out.metadata as Record<string, unknown>
    expect(meta).toBeDefined()
    const prov = meta.discretized_from as Record<string, unknown>
    expect(prov.name).toBe('scalar_ode')
    expect(meta.tags).toContain('discretized')
    // Input not mutated.
    expect((esm.metadata as Record<string, unknown>).discretized_from).toBeUndefined()
  })

  it('runs end-to-end on a 1D PDE with a matching rule', () => {
    const out = discretize(heat1dEsm({ withRule: true })) as Record<string, unknown>
    const models = out.models as Record<string, unknown>
    const m = models.M as Record<string, unknown>
    const eqns = m.equations as Record<string, unknown>[]
    const rhs = eqns[0]!.rhs
    const s = JSON.stringify(rhs)
    expect(s).not.toContain('"grad"')
    expect(s).toContain('"index"')
  })

  it('is deterministic — two calls produce canonically-identical output', () => {
    const a = discretize(heat1dEsm({ withRule: true })) as Record<string, unknown>
    const b = discretize(heat1dEsm({ withRule: true })) as Record<string, unknown>
    const rhsA = ((a.models as Record<string, unknown>).M as Record<string, unknown>)
      .equations as Record<string, unknown>[]
    const rhsB = ((b.models as Record<string, unknown>).M as Record<string, unknown>)
      .equations as Record<string, unknown>[]
    expect(canonicalJson(parseExpr(rhsA[0]!.rhs))).toBe(
      canonicalJson(parseExpr(rhsB[0]!.rhs)),
    )
    expect(
      JSON.stringify((a.metadata as Record<string, unknown>).discretized_from),
    ).toBe(JSON.stringify((b.metadata as Record<string, unknown>).discretized_from))
  })

  it('output re-parses through parseExpr', () => {
    const out = discretize(scalarOdeEsm()) as Record<string, unknown>
    const eqns = ((out.models as Record<string, unknown>).M as Record<string, unknown>)
      .equations as Record<string, unknown>[]
    const parsed = parseExpr(eqns[0]!.rhs)
    expect(parsed).toBeDefined()
  })

  it('raises E_UNREWRITTEN_PDE_OP on unmatched PDE op', () => {
    let err: unknown = null
    try {
      discretize(heat1dEsm({ withRule: false }))
    } catch (e) {
      err = e
    }
    expect(err).toBeInstanceOf(RuleEngineError)
    expect((err as RuleEngineError).code).toBe(E_DISCRETIZE_UNREWRITTEN_PDE_OP)
  })

  it('strictUnrewritten=false stamps passthrough and retains op', () => {
    const out = discretize(heat1dEsm({ withRule: false }), {
      strictUnrewritten: false,
    }) as Record<string, unknown>
    const eqn = (((out.models as Record<string, unknown>).M as Record<string, unknown>)
      .equations as Record<string, unknown>[])[0]!
    expect(eqn.passthrough).toBe(true)
    expect(JSON.stringify(eqn.rhs)).toContain('"grad"')
  })

  it('passthrough=true on input skips the coverage check', () => {
    const esm = heat1dEsm({ withRule: false })
    const eqn0 = (((esm.models as Record<string, unknown>).M as Record<string, unknown>)
      .equations as Record<string, unknown>[])[0]!
    eqn0.passthrough = true
    const out = discretize(esm) as Record<string, unknown>
    const outEqn = (((out.models as Record<string, unknown>).M as Record<string, unknown>)
      .equations as Record<string, unknown>[])[0]!
    expect(outEqn.passthrough).toBe(true)
  })

  it('canonicalizes BC value with no matching rule', () => {
    const esm: Record<string, unknown> = {
      esm: '0.2.0',
      metadata: { name: 'bc_plain' },
      models: {
        M: {
          variables: {
            u: { type: 'state', default: 0.0, units: '1' },
          },
          equations: [
            {
              lhs: { op: 'D', args: ['u'], wrt: 't' },
              rhs: 0.0,
            },
          ],
          boundary_conditions: {
            u_dirichlet_xmin: {
              variable: 'u',
              side: 'xmin',
              kind: 'dirichlet',
              value: { op: '+', args: [1, 0] },
            },
          },
        },
      },
    }
    const out = discretize(esm) as Record<string, unknown>
    const bcs = ((out.models as Record<string, unknown>).M as Record<string, unknown>)
      .boundary_conditions as Record<string, unknown>
    const bc = bcs.u_dirichlet_xmin as Record<string, unknown>
    expect(bc.value).toBe(1)
  })

  it('raises E_RULES_NOT_CONVERGED when max_passes is exceeded', () => {
    const esm: Record<string, unknown> = {
      esm: '0.2.0',
      metadata: { name: 'loop' },
      rules: [
        {
          name: 'never',
          pattern: '$a',
          replacement: { op: '+', args: ['$a', 1] },
        },
      ],
      models: {
        M: {
          variables: { y: { type: 'state', default: 0.0, units: '1' } },
          equations: [
            {
              lhs: { op: 'D', args: ['y'], wrt: 't' },
              rhs: 'y',
            },
          ],
        },
      },
    }
    let err: unknown = null
    try {
      discretize(esm, { maxPasses: 3 })
    } catch (e) {
      err = e
    }
    expect(err).toBeInstanceOf(RuleEngineError)
    expect((err as RuleEngineError).code).toBe('E_RULES_NOT_CONVERGED')
  })
})

describe('discretize() — RFC §12 DAE binding contract', () => {
  const envSaved = process.env.ESM_DAE_SUPPORT
  beforeEach(() => {
    delete process.env.ESM_DAE_SUPPORT
  })
  afterEach(() => {
    if (envSaved === undefined) delete process.env.ESM_DAE_SUPPORT
    else process.env.ESM_DAE_SUPPORT = envSaved
  })

  it('pure ODE stamps system_class=ode', () => {
    const out = discretize(scalarOdeEsm()) as Record<string, unknown>
    const meta = out.metadata as Record<string, unknown>
    expect(meta.system_class).toBe('ode')
    const info = meta.dae_info as Record<string, unknown>
    expect(info.algebraic_equation_count).toBe(0)
    expect((info.per_model as Record<string, number>).M).toBe(0)
  })

  it('mixed DAE stamps system_class=dae', () => {
    const out = discretize(mixedDaeEsm()) as Record<string, unknown>
    const meta = out.metadata as Record<string, unknown>
    expect(meta.system_class).toBe('dae')
    const info = meta.dae_info as Record<string, unknown>
    expect(info.algebraic_equation_count).toBe(1)
    expect((info.per_model as Record<string, number>).M).toBe(1)
  })

  it('daeSupport=false aborts with E_NO_DAE_SUPPORT', () => {
    let err: unknown = null
    try {
      discretize(mixedDaeEsm(), { daeSupport: false })
    } catch (e) {
      err = e
    }
    expect(err).toBeInstanceOf(RuleEngineError)
    expect((err as RuleEngineError).code).toBe(E_NO_DAE_SUPPORT)
    expect((err as RuleEngineError).message).toContain('models.M.equations[1]')
    expect((err as RuleEngineError).message).toContain('RFC §12')
  })

  it('pure ODE passes even with daeSupport=false', () => {
    const out = discretize(scalarOdeEsm(), { daeSupport: false }) as Record<string, unknown>
    expect((out.metadata as Record<string, unknown>).system_class).toBe('ode')
  })

  it('explicit produces:algebraic marker is algebraic', () => {
    const esm = scalarOdeEsm()
    const eqns = (((esm.models as Record<string, unknown>).M as Record<string, unknown>)
      .equations as Record<string, unknown>[])
    eqns[0]!.produces = 'algebraic'
    const out = discretize(esm) as Record<string, unknown>
    const meta = out.metadata as Record<string, unknown>
    expect(meta.system_class).toBe('dae')
    expect((meta.dae_info as Record<string, unknown>).algebraic_equation_count).toBe(1)
  })

  it('ESM_DAE_SUPPORT=0 env var disables by default', () => {
    process.env.ESM_DAE_SUPPORT = '0'
    let err: unknown = null
    try {
      discretize(mixedDaeEsm())
    } catch (e) {
      err = e
    }
    expect(err).toBeInstanceOf(RuleEngineError)
    expect((err as RuleEngineError).code).toBe(E_NO_DAE_SUPPORT)
    const out = discretize(scalarOdeEsm()) as Record<string, unknown>
    expect((out.metadata as Record<string, unknown>).system_class).toBe('ode')
  })

  it('explicit daeSupport=true overrides ESM_DAE_SUPPORT=0', () => {
    process.env.ESM_DAE_SUPPORT = '0'
    const out = discretize(mixedDaeEsm(), { daeSupport: true }) as Record<string, unknown>
    expect((out.metadata as Record<string, unknown>).system_class).toBe('dae')
  })

  it('independent_variable from domain is respected', () => {
    const esm: Record<string, unknown> = {
      esm: '0.2.0',
      metadata: { name: 'tau_indep' },
      domains: { d: { independent_variable: 'tau' } },
      models: {
        M: {
          domain: 'd',
          variables: { x: { type: 'state', default: 0.0, units: '1' } },
          equations: [
            {
              lhs: { op: 'D', args: ['x'], wrt: 'tau' },
              rhs: 0.0,
            },
          ],
        },
      },
    }
    const out = discretize(esm) as Record<string, unknown>
    expect((out.metadata as Record<string, unknown>).system_class).toBe('ode')

    // Flip wrt to "t" — now algebraic under tau-indep domain.
    const eqns = (((esm.models as Record<string, unknown>).M as Record<string, unknown>)
      .equations as Record<string, unknown>[])
    ;(eqns[0]!.lhs as Record<string, unknown>).wrt = 't'
    const out2 = discretize(esm) as Record<string, unknown>
    expect((out2.metadata as Record<string, unknown>).system_class).toBe('dae')
  })
})
