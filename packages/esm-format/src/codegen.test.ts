/**
 * Tests for code generation (Julia and Python)
 */

import { describe, it, expect } from 'vitest'
import { toJuliaCode, toPythonCode } from './codegen.js'
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

  it('should generate implementation code for coupling, domain, solver, and data loaders', () => {
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
        strategy: 'imex',
        config: {
          stiff_algorithm: 'CVODE_BDF',
          tolerances: { abstol: 1e-6, reltol: 1e-3 }
        }
      },
      data_loaders: {
        weather: {
          type: 'gridded_data',
          loader_id: 'weather',
          source: 'weather_data.nc',
          config: { format: 'netcdf' }
        }
      }
    }

    const code = toJuliaCode(file)

    // Check coupling implementation
    expect(code).toContain('# Coupling explicit: model1 -> model2')
    expect(code).toContain('model1_to_model2_coupling = ConnectorSystem([')
    expect(code).toContain('model1_system.x ~ model2_system.x,')
    expect(code).toContain('model1_system.y ~ model2_system.y,')

    // Check domain implementation
    expect(code).toContain('# Domain')
    expect(code).toContain('@variables t')
    expect(code).toContain('@variables x y')

    // Check solver implementation
    expect(code).toContain('# Solver')
    expect(code).toContain('solver_strategy = IMEXIntegrator()')
    expect(code).toContain('alg = CVODE_BDF()')

    // Check data loader implementation
    expect(code).toContain('# Data loader: weather')
    expect(code).toContain('weather_loader = GriddedDataLoader("weather")')
    expect(code).toContain('weather_data = load_gridded_data("weather_data.nc")')
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

describe('toPythonCode', () => {
  it('should generate basic Python script structure', () => {
    const file: EsmFile = {
      esm: '0.1.0',
      metadata: {
        title: 'Test Model',
        description: 'A test model for Python code generation'
      },
      models: {},
      reaction_systems: {}
    }

    const code = toPythonCode(file)

    expect(code).toContain('import sympy as sp')
    expect(code).toContain('import esm_format as esm')
    expect(code).toContain('import scipy')
    expect(code).toContain('# Title: Test Model')
    expect(code).toContain('# Description: A test model for Python code generation')
    expect(code).toContain('tspan = (0, 10)')
    expect(code).toContain('parameters = {}')
    expect(code).toContain('initial_conditions = {}')
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

    const code = toPythonCode(file)

    expect(code).toContain('t = sp.Symbol(\'t\')')
    expect(code).toContain('O3 = sp.Function(\'O3\')  # ppb')
    expect(code).toContain('k1 = sp.Symbol(\'k1\')')
    expect(code).toContain('eq1 = sp.Eq(sp.Derivative(O3(t), t), k1 * O3)')
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

    const code = toPythonCode(file)

    expect(code).toContain('NO = sp.Symbol(\'NO\')')
    expect(code).toContain('NO2 = sp.Symbol(\'NO2\')')
    expect(code).toContain('r1_rate = k1')
    expect(code).toContain('# Stoichiometry setup (TODO: Implement reaction network)')
  })

  it('should handle expression mappings correctly for Python', () => {
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

    const code = toPythonCode(file)

    expect(code).toContain('a + b')
    expect(code).toContain('x * y')
    expect(code).toContain('sp.Derivative(u(t), t)')
    expect(code).toContain('sp.exp(z)')
    expect(code).toContain('sp.Piecewise((a, x > 0), (b, True))')
    expect(code).toContain('Function(\'Pre\')(signal)')
    expect(code).toContain('x ** 2')
    expect(code).toContain('sp.Derivative(u, x)')
  })

  it('should generate implementation code for coupling, domain, and solver in Python', () => {
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
        strategy: 'imex',
        config: {
          stiff_algorithm: 'CVODE_BDF',
          tolerances: { abstol: 1e-6, reltol: 1e-3 }
        }
      },
      data_loaders: {
        weather: {
          type: 'gridded_data',
          loader_id: 'weather',
          source: 'weather_data.nc',
          config: { format: 'netcdf' }
        }
      }
    }

    const code = toPythonCode(file)

    // Check coupling implementation
    expect(code).toContain('# Coupling explicit: model1 -> model2')
    expect(code).toContain('model1_to_model2_coupling = esm.ExplicitCoupling(')
    expect(code).toContain('from_model="model1",')
    expect(code).toContain('to_model="model2",')
    expect(code).toContain('variables=["x","y"]')

    // Check domain implementation
    expect(code).toContain('# Domain')
    expect(code).toContain('x = sp.Symbol(\'x\')')
    expect(code).toContain('y = sp.Symbol(\'y\')')
    expect(code).toContain('domain = esm.Domain(')

    // Check solver implementation
    expect(code).toContain('# Solver')
    expect(code).toContain('solver = esm.IMEXSolver(')

    // Check data loader implementation
    expect(code).toContain('# Data loader: weather')
    expect(code).toContain('weather_loader = esm.GriddedDataLoader("weather")')
    expect(code).toContain('weather_data = weather_loader.load("weather_data.nc")')
  })

  it('should populate parameters and initial_conditions dictionaries with default values', () => {
    const file: EsmFile = {
      esm: '0.1.0',
      models: {
        test: {
          variables: {
            O3: {
              name: 'O3',
              type: 'state',
              default: 42.0,
              units: 'ppb'
            },
            k1: {
              name: 'k1',
              type: 'parameter',
              default: 0.123,
              units: 's^-1'
            }
          }
        }
      },
      reaction_systems: {
        chemistry: {
          species: {
            A: { name: 'A', initial_value: 1e-6 },
            B: { name: 'B', default: 2e-7 }
          }
        }
      }
    }

    const code = toPythonCode(file)

    // Check that parameters dictionary is populated with parameter defaults
    expect(code).toContain('parameters = {')
    expect(code).toContain('"k1": 0.123,')

    // Check that initial_conditions dictionary is populated with state defaults and species defaults
    expect(code).toContain('initial_conditions = {')
    expect(code).toContain('"O3": 42,')  // State variable default
    expect(code).toContain('"A": 0.000001,')  // Species initial_value (1e-6 in decimal)
    expect(code).toContain('"B": 2e-7,')  // Species default (takes precedence)
  })
})