/**
 * Tests for Julia code generation
 */

import { describe, it, expect } from 'vitest'
import { toJuliaCode } from './codegen.js'
import type { EsmFile, Model, ReactionSystem, Expression, ExpressionNode } from './types.js'

describe('toJuliaCode', () => {
  it('should generate basic Julia script structure', () => {
    const file: EsmFile = {
      esm: '0.1.0',
      metadata: {
        title: 'Test Model',
        description: 'A test model for code generation'
      },
      models: {},
      reaction_systems: {}
    }

    const code = toJuliaCode(file)

    expect(code).toContain('using ModelingToolkit')
    expect(code).toContain('using Catalyst')
    expect(code).toContain('using EarthSciMLBase')
    expect(code).toContain('using OrdinaryDiffEq')
    expect(code).toContain('using Unitful')
    expect(code).toContain('# Title: Test Model')
    expect(code).toContain('# Description: A test model for code generation')
  })

  it('should generate model code with variables and equations', () => {
    const file: EsmFile = {
      esm: '0.1.0',
      models: {
        atmospheric: {
          variables: {
            O3: {
              name: 'O3',
              type: 'state',
              default: 50.0,
              unit: 'ppb'
            },
            k1: {
              name: 'k1',
              type: 'parameter',
              default: 1e-3
            }
          },
          equations: [
            {
              lhs: {
                op: 'D',
                args: ['O3'],
                wrt: 't'
              } as ExpressionNode,
              rhs: {
                op: '*',
                args: ['k1', 'O3']
              } as ExpressionNode
            }
          ]
        }
      },
      reaction_systems: {}
    }

    const code = toJuliaCode(file)

    expect(code).toContain('@variables t O3(50.0, u"ppb")')
    expect(code).toContain('@parameters k1(0.001)')
    expect(code).toContain('D(O3) ~ k1 * O3')
    expect(code).toContain('@named atmospheric_system = ODESystem(eqs)')
  })

  it('should generate reaction system code', () => {
    const file: EsmFile = {
      esm: '0.1.0',
      models: {},
      reaction_systems: {
        chemistry: {
          species: {
            NO: {
              name: 'NO',
              initial_value: 10.0
            },
            NO2: {
              name: 'NO2',
              initial_value: 5.0
            }
          },
          reactions: {
            r1: {
              reactants: [
                { species: 'NO', stoichiometry: 1 }
              ],
              products: [
                { species: 'NO2', stoichiometry: 1 }
              ],
              rate: 'k1'
            }
          }
        }
      }
    }

    const code = toJuliaCode(file)

    expect(code).toContain('@species NO(10.0) NO2(5.0)')
    expect(code).toContain('@parameters k1')
    expect(code).toContain('Reaction(k1, [NO], [NO2])')
    expect(code).toContain('@named chemistry_system = ReactionSystem(rxs)')
  })

  it('should handle expression mappings correctly', () => {
    const expressions: { [key: string]: Expression } = {
      addition: { op: '+', args: ['a', 'b'] } as ExpressionNode,
      multiplication: { op: '*', args: ['x', 'y'] } as ExpressionNode,
      derivative: { op: 'D', args: ['u'], wrt: 't' } as ExpressionNode,
      exponential: { op: 'exp', args: ['z'] } as ExpressionNode,
      ifelse: { op: 'ifelse', args: [{ op: '>', args: ['x', 0] } as ExpressionNode, 'a', 'b'] } as ExpressionNode,
      pre: { op: 'Pre', args: ['signal'] } as ExpressionNode,
      power: { op: '^', args: ['x', 2] } as ExpressionNode,
      gradient: { op: 'grad', args: ['u', 'x'] } as ExpressionNode
    }

    const file: EsmFile = {
      esm: '0.1.0',
      models: {
        test: {
          variables: {
            a: { name: 'a', type: 'state' },
            b: { name: 'b', type: 'state' },
            x: { name: 'x', type: 'state' },
            y: { name: 'y', type: 'state' },
            u: { name: 'u', type: 'state' },
            z: { name: 'z', type: 'state' },
            signal: { name: 'signal', type: 'state' }
          },
          equations: Object.entries(expressions).map(([key, expr], i) => ({
            lhs: `var${i}` as Expression,
            rhs: expr
          }))
        }
      },
      reaction_systems: {}
    }

    const code = toJuliaCode(file)

    expect(code).toContain('a + b')
    expect(code).toContain('x * y')
    expect(code).toContain('D(u)')
    expect(code).toContain('exp(z)')
    expect(code).toContain('ifelse(x > 0, a, b)')
    expect(code).toContain('Pre(signal)')
    expect(code).toContain('x ^ 2')
    expect(code).toContain('Differential(x)(u)')
  })

  it('should generate TODO comments for unsupported features', () => {
    const file: EsmFile = {
      esm: '0.1.0',
      models: {},
      reaction_systems: {},
      coupling: [
        {
          type: 'explicit',
          from: 'model1',
          to: 'model2',
          variables: ['x', 'y']
        }
      ],
      domain: {
        spatial_coordinates: ['x', 'y'],
        temporal_coordinates: ['t']
      },
      solver: {
        algorithm: 'CVODE_BDF',
        tolerances: { abstol: 1e-6, reltol: 1e-3 }
      },
      data_loaders: {
        weather: {
          source: 'weather_data.nc',
          format: 'netcdf'
        }
      }
    }

    const code = toJuliaCode(file)

    expect(code).toContain('# TODO: Implement coupling explicit')
    expect(code).toContain('# TODO: Implement domain')
    expect(code).toContain('# TODO: Implement solver')
    expect(code).toContain('# TODO: Implement data loader weather')
    expect(code).toContain('#   Spatial coordinates: x, y')
    expect(code).toContain('#   Algorithm: CVODE_BDF')
    expect(code).toContain('#   Source: weather_data.nc')
  })

  it('should handle complex expressions with nested operations', () => {
    const complexExpr: ExpressionNode = {
      op: '+',
      args: [
        {
          op: '*',
          args: [
            'k1',
            {
              op: 'exp',
              args: [
                {
                  op: '/',
                  args: [
                    {
                      op: '-',
                      args: ['E', 'R']
                    },
                    'T'
                  ]
                }
              ]
            }
          ]
        },
        {
          op: 'ifelse',
          args: [
            {
              op: '>',
              args: ['T', 298]
            },
            'rate_hot',
            'rate_cold'
          ]
        }
      ]
    }

    const file: EsmFile = {
      esm: '0.1.0',
      models: {
        kinetics: {
          variables: {
            rate: { name: 'rate', type: 'state' }
          },
          equations: [
            {
              lhs: 'rate',
              rhs: complexExpr
            }
          ]
        }
      },
      reaction_systems: {}
    }

    const code = toJuliaCode(file)

    expect(code).toContain('k1 * exp(E - R / T) + ifelse(T > 298, rate_hot, rate_cold)')
  })

  it('should handle events', () => {
    const file: EsmFile = {
      esm: '0.1.0',
      models: {},
      reaction_systems: {},
      events: {
        reset_event: {
          condition: { op: '>', args: ['x', 100] } as ExpressionNode,
          affect: {
            lhs: 'x',
            rhs: 0
          }
        }
      }
    }

    const code = toJuliaCode(file)

    expect(code).toContain('reset_event_event = SymbolicContinuousCallback(x > 100,')
    expect(code).toContain('# Continuous Event: reset_event')
  })

  it('should handle species with stoichiometry in reactions', () => {
    const file: EsmFile = {
      esm: '0.1.0',
      models: {},
      reaction_systems: {
        combustion: {
          species: {
            CH4: { name: 'CH4' },
            O2: { name: 'O2' },
            CO2: { name: 'CO2' },
            H2O: { name: 'H2O' }
          },
          reactions: {
            combustion: {
              reactants: [
                { species: 'CH4', stoichiometry: 1 },
                { species: 'O2', stoichiometry: 2 }
              ],
              products: [
                { species: 'CO2', stoichiometry: 1 },
                { species: 'H2O', stoichiometry: 2 }
              ],
              rate: { op: '*', args: ['k', 'CH4', 'O2'] } as ExpressionNode
            }
          }
        }
      }
    }

    const code = toJuliaCode(file)

    expect(code).toContain('Reaction(k * CH4 * O2, [CH4 + 2*O2], [CO2 + 2*H2O])')
  })
})