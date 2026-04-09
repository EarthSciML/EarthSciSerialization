import { describe, it, expect } from 'vitest'
import { freeVariables, freeParameters, contains, evaluate, simplify } from './expression.js'
import type { Model, Expr } from './types.js'

describe('Expression structural operations', () => {
  describe('freeVariables', () => {
    it('should return empty set for numbers', () => {
      expect(freeVariables(42)).toEqual(new Set())
    })

    it('should return single variable for string', () => {
      expect(freeVariables('x')).toEqual(new Set(['x']))
    })

    it('should collect variables from simple expression', () => {
      const expr: Expr = {
        op: '+',
        args: ['x', 'y']
      }
      expect(freeVariables(expr)).toEqual(new Set(['x', 'y']))
    })

    it('should collect variables from nested expression', () => {
      const expr: Expr = {
        op: '*',
        args: [
          { op: '+', args: ['x', 2] },
          { op: 'sin', args: ['y'] }
        ]
      }
      expect(freeVariables(expr)).toEqual(new Set(['x', 'y']))
    })

    it('should handle duplicate variables', () => {
      const expr: Expr = {
        op: '+',
        args: ['x', { op: '*', args: ['x', 2] }]
      }
      expect(freeVariables(expr)).toEqual(new Set(['x']))
    })
  })

  describe('freeParameters', () => {
    const testModel: Model = {
      variables: {
        'x': { type: 'state' },
        'k': { type: 'parameter' },
        'T': { type: 'parameter' },
        'C': { type: 'observed', expression: { op: '*', args: ['k', 'T'] } }
      },
      equations: []
    }

    it('should return empty set for expression with no parameters', () => {
      const expr: Expr = { op: '+', args: ['x', 2] }
      expect(freeParameters(expr, testModel)).toEqual(new Set())
    })

    it('should identify parameters in simple expression', () => {
      const expr: Expr = { op: '*', args: ['k', 'x'] }
      expect(freeParameters(expr, testModel)).toEqual(new Set(['k']))
    })

    it('should identify multiple parameters', () => {
      const expr: Expr = { op: '+', args: ['k', 'T'] }
      expect(freeParameters(expr, testModel)).toEqual(new Set(['k', 'T']))
    })

    it('should handle variables not in model', () => {
      const expr: Expr = { op: '+', args: ['k', 'unknown'] }
      expect(freeParameters(expr, testModel)).toEqual(new Set(['k']))
    })
  })

  describe('contains', () => {
    it('should return true for matching string', () => {
      expect(contains('x', 'x')).toBe(true)
    })

    it('should return false for non-matching string', () => {
      expect(contains('x', 'y')).toBe(false)
    })

    it('should return false for numbers', () => {
      expect(contains(42, 'x')).toBe(false)
    })

    it('should find variable in expression args', () => {
      const expr: Expr = { op: '+', args: ['x', 'y'] }
      expect(contains(expr, 'x')).toBe(true)
      expect(contains(expr, 'y')).toBe(true)
      expect(contains(expr, 'z')).toBe(false)
    })

    it('should find variable in nested expression', () => {
      const expr: Expr = {
        op: '*',
        args: [
          { op: '+', args: ['x', 2] },
          { op: 'sin', args: ['y'] }
        ]
      }
      expect(contains(expr, 'x')).toBe(true)
      expect(contains(expr, 'y')).toBe(true)
      expect(contains(expr, 'z')).toBe(false)
    })
  })

  describe('evaluate', () => {
    const bindings = new Map([
      ['x', 2],
      ['y', 3],
      ['pi', Math.PI]
    ])

    it('should return numbers as-is', () => {
      expect(evaluate(42, bindings)).toBe(42)
    })

    it('should resolve bound variables', () => {
      expect(evaluate('x', bindings)).toBe(2)
      expect(evaluate('y', bindings)).toBe(3)
    })

    it('should throw for unbound variables', () => {
      expect(() => evaluate('z', bindings)).toThrow('Unbound variable: z')
    })

    describe('arithmetic operations', () => {
      it('should evaluate addition', () => {
        const expr: Expr = { op: '+', args: ['x', 'y', 5] }
        expect(evaluate(expr, bindings)).toBe(10) // 2 + 3 + 5
      })

      it('should evaluate subtraction', () => {
        const expr: Expr = { op: '-', args: [10, 'x'] }
        expect(evaluate(expr, bindings)).toBe(8) // 10 - 2
      })

      it('should evaluate unary minus', () => {
        const expr: Expr = { op: '-', args: ['x'] }
        expect(evaluate(expr, bindings)).toBe(-2)
      })

      it('should evaluate multiplication', () => {
        const expr: Expr = { op: '*', args: ['x', 'y'] }
        expect(evaluate(expr, bindings)).toBe(6) // 2 * 3
      })

      it('should evaluate division', () => {
        const expr: Expr = { op: '/', args: [6, 'x'] }
        expect(evaluate(expr, bindings)).toBe(3) // 6 / 2
      })

      it('should evaluate exponentiation', () => {
        const expr: Expr = { op: '^', args: ['x', 'y'] }
        expect(evaluate(expr, bindings)).toBe(8) // 2^3
      })
    })

    describe('mathematical functions', () => {
      it('should evaluate exp', () => {
        const expr: Expr = { op: 'exp', args: [0] }
        expect(evaluate(expr, bindings)).toBe(1)
      })

      it('should evaluate log', () => {
        const expr: Expr = { op: 'log', args: [Math.E] }
        expect(evaluate(expr, bindings)).toBeCloseTo(1)
      })

      it('should evaluate sqrt', () => {
        const expr: Expr = { op: 'sqrt', args: [4] }
        expect(evaluate(expr, bindings)).toBe(2)
      })

      it('should evaluate trigonometric functions', () => {
        const expr1: Expr = { op: 'sin', args: [0] }
        expect(evaluate(expr1, bindings)).toBe(0)

        const expr2: Expr = { op: 'cos', args: [0] }
        expect(evaluate(expr2, bindings)).toBe(1)
      })

      it('should evaluate min and max', () => {
        const expr1: Expr = { op: 'min', args: ['x', 'y', 1] }
        expect(evaluate(expr1, bindings)).toBe(1) // min(2, 3, 1)

        const expr2: Expr = { op: 'max', args: ['x', 'y', 1] }
        expect(evaluate(expr2, bindings)).toBe(3) // max(2, 3, 1)
      })
    })

    describe('comparison operations', () => {
      it('should evaluate comparisons', () => {
        const expr1: Expr = { op: '>', args: ['y', 'x'] }
        expect(evaluate(expr1, bindings)).toBe(1) // 3 > 2

        const expr2: Expr = { op: '<', args: ['y', 'x'] }
        expect(evaluate(expr2, bindings)).toBe(0) // 3 < 2

        const expr3: Expr = { op: '==', args: ['x', 2] }
        expect(evaluate(expr3, bindings)).toBe(1) // 2 == 2
      })
    })

    describe('logical operations', () => {
      it('should evaluate logical operations', () => {
        const expr1: Expr = { op: 'and', args: [1, 1] }
        expect(evaluate(expr1, bindings)).toBe(1)

        const expr2: Expr = { op: 'and', args: [1, 0] }
        expect(evaluate(expr2, bindings)).toBe(0)

        const expr3: Expr = { op: 'or', args: [0, 1] }
        expect(evaluate(expr3, bindings)).toBe(1)

        const expr4: Expr = { op: 'not', args: [0] }
        expect(evaluate(expr4, bindings)).toBe(1)
      })

      it('should evaluate ifelse', () => {
        const expr: Expr = { op: 'ifelse', args: [1, 'x', 'y'] }
        expect(evaluate(expr, bindings)).toBe(2)

        const expr2: Expr = { op: 'ifelse', args: [0, 'x', 'y'] }
        expect(evaluate(expr2, bindings)).toBe(3)
      })
    })

    describe('error handling', () => {
      it('should throw for division by zero', () => {
        const expr: Expr = { op: '/', args: [1, 0] }
        expect(() => evaluate(expr, bindings)).toThrow('Division by zero')
      })

      it('should throw for invalid log argument', () => {
        const expr: Expr = { op: 'log', args: [-1] }
        expect(() => evaluate(expr, bindings)).toThrow('log argument must be positive')
      })

      it('should throw for invalid sqrt argument', () => {
        const expr: Expr = { op: 'sqrt', args: [-1] }
        expect(() => evaluate(expr, bindings)).toThrow('sqrt argument must be non-negative')
      })

      it('should throw for unsupported operator', () => {
        const expr: any = { op: 'unsupported', args: [1] }
        expect(() => evaluate(expr, bindings)).toThrow('Unsupported operator: unsupported')
      })
    })
  })

  describe('simplify', () => {
    it('should return numbers and variables as-is', () => {
      expect(simplify(42)).toBe(42)
      expect(simplify('x')).toBe('x')
    })

    describe('addition simplification', () => {
      it('should remove zeros', () => {
        const expr: Expr = { op: '+', args: ['x', 0, 'y'] }
        expect(simplify(expr)).toEqual({ op: '+', args: ['x', 'y'] })
      })

      it('should collapse to single term when only one non-zero', () => {
        const expr: Expr = { op: '+', args: ['x', 0, 0] }
        expect(simplify(expr)).toBe('x')
      })

      it('should return zero when all terms are zero', () => {
        const expr: Expr = { op: '+', args: [0, 0] }
        expect(simplify(expr)).toBe(0)
      })

      it('should fold constants', () => {
        const expr: Expr = { op: '+', args: [2, 3, 5] }
        expect(simplify(expr)).toBe(10)
      })

      it('should combine constant folding with zero removal', () => {
        const expr: Expr = { op: '+', args: ['x', 2, 0, 3] }
        expect(simplify(expr)).toEqual({ op: '+', args: ['x', 5] })
      })
    })

    describe('multiplication simplification', () => {
      it('should return zero for zero multiplication', () => {
        const expr: Expr = { op: '*', args: ['x', 0, 'y'] }
        expect(simplify(expr)).toBe(0)
      })

      it('should remove ones', () => {
        const expr: Expr = { op: '*', args: ['x', 1, 'y'] }
        expect(simplify(expr)).toEqual({ op: '*', args: ['x', 'y'] })
      })

      it('should collapse to single factor when only one non-one', () => {
        const expr: Expr = { op: '*', args: ['x', 1, 1] }
        expect(simplify(expr)).toBe('x')
      })

      it('should return one when all factors are one', () => {
        const expr: Expr = { op: '*', args: [1, 1] }
        expect(simplify(expr)).toBe(1)
      })

      it('should fold constants', () => {
        const expr: Expr = { op: '*', args: [2, 3, 5] }
        expect(simplify(expr)).toBe(30)
      })
    })

    describe('subtraction simplification', () => {
      it('should simplify x - 0 to x', () => {
        const expr: Expr = { op: '-', args: ['x', 0] }
        expect(simplify(expr)).toBe('x')
      })

      it('should fold constants', () => {
        const expr: Expr = { op: '-', args: [10, 3] }
        expect(simplify(expr)).toBe(7)
      })

      it('should handle unary minus', () => {
        const expr: Expr = { op: '-', args: [5] }
        expect(simplify(expr)).toBe(-5)
      })
    })

    describe('division simplification', () => {
      it('should simplify x / 1 to x', () => {
        const expr: Expr = { op: '/', args: ['x', 1] }
        expect(simplify(expr)).toBe('x')
      })

      it('should simplify 0 / x to 0', () => {
        const expr: Expr = { op: '/', args: [0, 'x'] }
        expect(simplify(expr)).toBe(0)
      })

      it('should fold constants', () => {
        const expr: Expr = { op: '/', args: [6, 2] }
        expect(simplify(expr)).toBe(3)
      })
    })

    describe('exponentiation simplification', () => {
      it('should simplify x^0 to 1', () => {
        const expr: Expr = { op: '^', args: ['x', 0] }
        expect(simplify(expr)).toBe(1)
      })

      it('should simplify x^1 to x', () => {
        const expr: Expr = { op: '^', args: ['x', 1] }
        expect(simplify(expr)).toBe('x')
      })

      it('should simplify 0^x to 0', () => {
        const expr: Expr = { op: '^', args: [0, 'x'] }
        expect(simplify(expr)).toBe(0)
      })

      it('should simplify 1^x to 1', () => {
        const expr: Expr = { op: '^', args: [1, 'x'] }
        expect(simplify(expr)).toBe(1)
      })

      it('should fold constants', () => {
        const expr: Expr = { op: '^', args: [2, 3] }
        expect(simplify(expr)).toBe(8)
      })
    })

    describe('recursive simplification', () => {
      it('should simplify nested expressions', () => {
        const expr: Expr = {
          op: '+',
          args: [
            { op: '*', args: ['x', 1] },
            { op: '+', args: [2, 3] }
          ]
        }
        expect(simplify(expr)).toEqual({ op: '+', args: ['x', 5] })
      })

      it('should handle complex nested case', () => {
        const expr: Expr = {
          op: '*',
          args: [
            { op: '+', args: ['x', 0] },
            { op: '^', args: ['y', 1] }
          ]
        }
        expect(simplify(expr)).toEqual({ op: '*', args: ['x', 'y'] })
      })
    })
  })
})