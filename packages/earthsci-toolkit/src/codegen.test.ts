/**
 * Tests for code generation (Julia and Python)
 */

import { describe, it, expect } from 'vitest'
import { toJuliaCode, toPythonCode, compileExpression, evaluateExpression } from './codegen.js'
import type { EsmFile, Expr, Model, ReactionSystem, Expression, ExpressionNode } from './types.js'

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

  it('should generate implementation code for coupling, domain, and data loaders', () => {
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
      data_loaders: {
        weather: {
          kind: 'grid',
          source: {
            url_template: 'weather_data.nc'
          },
          variables: {
            T: { file_variable: 'T2', units: 'K' }
          }
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

    // Check data loader implementation
    expect(code).toContain('# Data loader: weather')
    expect(code).toContain('weather_loader = DataLoader(')
    expect(code).toContain('kind = "grid"')
    expect(code).toContain('url_template = "weather_data.nc"')
    expect(code).toContain('T <- T2 (K)')
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
    expect(code).toContain('import earthsci_toolkit as esm')
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

  it('should generate implementation code for coupling, domain, and data loaders in Python', () => {
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
      data_loaders: {
        weather: {
          kind: 'grid',
          source: {
            url_template: 'weather_data.nc'
          },
          variables: {
            T: { file_variable: 'T2', units: 'K' }
          }
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

    // Check data loader implementation
    expect(code).toContain('# Data loader: weather')
    expect(code).toContain('weather_loader = esm.DataLoader(')
    expect(code).toContain('kind="grid"')
    expect(code).toContain('url_template="weather_data.nc"')
    expect(code).toContain('T <- T2 (K)')
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

describe('compileExpression / evaluateExpression — TS scalar runner', () => {
  // Migrated from expression.test.ts under esm-3r4: this is the
  // sanctioned TS in-process evaluator (AGENTS.md "Official per-binding
  // runners"). The runner walks canonical-form AST generically — no
  // per-rule-shape dispatch.
  const bindings = new Map<string, number>([
    ['x', 2],
    ['y', 3],
    ['pi', Math.PI],
  ])

  it('returns numbers as-is', () => {
    expect(evaluateExpression(42, bindings)).toBe(42)
  })

  it('resolves bound variables', () => {
    expect(evaluateExpression('x', bindings)).toBe(2)
    expect(evaluateExpression('y', bindings)).toBe(3)
  })

  it('throws for unbound variables', () => {
    expect(() => evaluateExpression('z', bindings)).toThrow('Unbound variable: z')
  })

  it('compileExpression returns a reusable closure', () => {
    const expr: Expr = { op: '+', args: ['x', 'y'] }
    const fn = compileExpression(expr)
    expect(fn(bindings)).toBe(5)
    const otherBindings = new Map<string, number>([['x', 10], ['y', 20]])
    expect(fn(otherBindings)).toBe(30)
  })

  describe('arithmetic operations', () => {
    it('evaluates addition', () => {
      const expr: Expr = { op: '+', args: ['x', 'y', 5] }
      expect(evaluateExpression(expr, bindings)).toBe(10)
    })

    it('evaluates subtraction', () => {
      const expr: Expr = { op: '-', args: [10, 'x'] }
      expect(evaluateExpression(expr, bindings)).toBe(8)
    })

    it('evaluates unary minus', () => {
      const expr: Expr = { op: '-', args: ['x'] }
      expect(evaluateExpression(expr, bindings)).toBe(-2)
    })

    it('evaluates multiplication', () => {
      const expr: Expr = { op: '*', args: ['x', 'y'] }
      expect(evaluateExpression(expr, bindings)).toBe(6)
    })

    it('evaluates division', () => {
      const expr: Expr = { op: '/', args: [6, 'x'] }
      expect(evaluateExpression(expr, bindings)).toBe(3)
    })

    it('evaluates exponentiation', () => {
      const expr: Expr = { op: '^', args: ['x', 'y'] }
      expect(evaluateExpression(expr, bindings)).toBe(8)
    })
  })

  describe('mathematical functions', () => {
    it('evaluates exp', () => {
      expect(evaluateExpression({ op: 'exp', args: [0] }, bindings)).toBe(1)
    })

    it('evaluates log', () => {
      expect(evaluateExpression({ op: 'log', args: [Math.E] }, bindings)).toBeCloseTo(1)
    })

    it('evaluates sqrt', () => {
      expect(evaluateExpression({ op: 'sqrt', args: [4] }, bindings)).toBe(2)
    })

    it('evaluates trig functions', () => {
      expect(evaluateExpression({ op: 'sin', args: [0] }, bindings)).toBe(0)
      expect(evaluateExpression({ op: 'cos', args: [0] }, bindings)).toBe(1)
    })

    it('evaluates n-ary min/max', () => {
      expect(evaluateExpression({ op: 'min', args: ['x', 'y', 1] }, bindings)).toBe(1)
      expect(evaluateExpression({ op: 'max', args: ['x', 'y', 1] }, bindings)).toBe(3)
    })

    it('rejects min/max with fewer than 2 args (esm-spec §4.2)', () => {
      // esm-2is — n-ary arity ≥ 2
      expect(() => evaluateExpression({ op: 'min', args: ['x'] }, bindings))
        .toThrow('min requires at least 2 arguments')
      expect(() => evaluateExpression({ op: 'max', args: ['x'] }, bindings))
        .toThrow('max requires at least 2 arguments')
    })
  })

  describe('comparison and logical operations', () => {
    it('evaluates comparisons', () => {
      expect(evaluateExpression({ op: '>', args: ['y', 'x'] }, bindings)).toBe(1)
      expect(evaluateExpression({ op: '<', args: ['y', 'x'] }, bindings)).toBe(0)
      expect(evaluateExpression({ op: '==', args: ['x', 2] }, bindings)).toBe(1)
    })

    it('evaluates logical operations', () => {
      expect(evaluateExpression({ op: 'and', args: [1, 1] }, bindings)).toBe(1)
      expect(evaluateExpression({ op: 'and', args: [1, 0] }, bindings)).toBe(0)
      expect(evaluateExpression({ op: 'or', args: [0, 1] }, bindings)).toBe(1)
      expect(evaluateExpression({ op: 'not', args: [0] }, bindings)).toBe(1)
    })

    it('evaluates ifelse', () => {
      expect(evaluateExpression({ op: 'ifelse', args: [1, 'x', 'y'] }, bindings)).toBe(2)
      expect(evaluateExpression({ op: 'ifelse', args: [0, 'x', 'y'] }, bindings)).toBe(3)
    })
  })

  describe('error handling', () => {
    it('throws for division by zero', () => {
      expect(() => evaluateExpression({ op: '/', args: [1, 0] }, bindings))
        .toThrow('Division by zero')
    })

    it('throws for invalid log argument', () => {
      expect(() => evaluateExpression({ op: 'log', args: [-1] }, bindings))
        .toThrow('log argument must be positive')
    })

    it('throws for invalid sqrt argument', () => {
      expect(() => evaluateExpression({ op: 'sqrt', args: [-1] }, bindings))
        .toThrow('sqrt argument must be non-negative')
    })

    it('throws for unsupported operator', () => {
      const expr: any = { op: 'unsupported', args: [1] }
      expect(() => evaluateExpression(expr, bindings))
        .toThrow('Unsupported operator: unsupported')
    })

    it('rejects unlowered enum nodes', () => {
      const expr: any = { op: 'enum', value: 'foo' }
      expect(() => evaluateExpression(expr, bindings))
        .toThrow(/enum op encountered/)
    })

    it('rejects array-valued const nodes in scalar position', () => {
      const expr: any = { op: 'const', value: [1, 2, 3] }
      expect(() => evaluateExpression(expr, bindings))
        .toThrow(/array value cannot be evaluated as a scalar/)
    })
  })
})