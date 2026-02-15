/**
 * Tests for pretty-printing formatters using display test fixtures
 */

import { describe, it, expect } from 'vitest'
import { toUnicode, toLatex, toAscii } from './pretty-print.js'
import { readFileSync } from 'fs'
import { join } from 'path'

// Load test fixtures
const chemicalSubscriptsFixtures = JSON.parse(
  readFileSync(join(process.cwd(), '../../tests/display/chemical_subscripts.json'), 'utf8')
)

const comprehensiveOperatorsFixtures = JSON.parse(
  readFileSync(join(process.cwd(), '../../tests/display/comprehensive_operators.json'), 'utf8')
)

describe('Chemical Subscripts', () => {
  chemicalSubscriptsFixtures.forEach((fixture: any, index: number) => {
    it(`should format ${fixture.input} correctly (${fixture.reasoning})`, () => {
      // Test string inputs (chemical species)
      expect(toUnicode(fixture.input)).toBe(fixture.unicode)
      expect(toLatex(fixture.input)).toBe(fixture.latex)

      // ASCII doesn't have special formatting for chemical subscripts
      expect(toAscii(fixture.input)).toBe(fixture.input)
    })
  })
})

describe('Expression Operators', () => {
  comprehensiveOperatorsFixtures.forEach((group: any) => {
    describe(group.name, () => {
      group.tests.forEach((test: any, index: number) => {
        it(`should format ${JSON.stringify(test.input)} correctly`, () => {
          const input = test.input

          if (test.unicode) {
            expect(toUnicode(input)).toBe(test.unicode)
          }

          if (test.latex) {
            expect(toLatex(input)).toBe(test.latex)
          }

          if (test.ascii) {
            expect(toAscii(input)).toBe(test.ascii)
          }
        })
      })
    })
  })
})

describe('Basic expressions', () => {
  it('should format numbers correctly', () => {
    expect(toUnicode(42)).toBe('42')
    expect(toLatex(42)).toBe('42')
    expect(toAscii(42)).toBe('42')

    // Scientific notation
    expect(toUnicode(1.8e-12)).toBe('1.8×10⁻¹²')
    expect(toLatex(1.8e-12)).toBe('1.8 \\times 10^{-12}')
    expect(toAscii(1.8e-12)).toBe('1.8e-12')
  })

  it('should format simple variables correctly', () => {
    expect(toUnicode('x')).toBe('x')
    expect(toLatex('x')).toBe('x')
    expect(toAscii('x')).toBe('x')
  })

  it('should format simple expressions correctly', () => {
    const expr = { op: '+', args: ['a', 'b'] }
    expect(toUnicode(expr)).toBe('a + b')
    expect(toLatex(expr)).toBe('a + b')
    expect(toAscii(expr)).toBe('a + b')
  })

  it('should format multiplication correctly', () => {
    const expr = { op: '*', args: ['a', 'b'] }
    expect(toUnicode(expr)).toBe('a·b')
    expect(toLatex(expr)).toBe('a \\cdot b')
    expect(toAscii(expr)).toBe('a * b')
  })

  it('should format division correctly', () => {
    const expr = { op: '/', args: ['a', 'b'] }
    expect(toUnicode(expr)).toBe('a/b')
    expect(toLatex(expr)).toBe('\\frac{a}{b}')
    expect(toAscii(expr)).toBe('a / b')
  })

  it('should format power correctly', () => {
    const expr = { op: '^', args: ['x', 3] }
    expect(toUnicode(expr)).toBe('x³')
    expect(toLatex(expr)).toBe('x^{3}')
    expect(toAscii(expr)).toBe('x^3')
  })

  it('should format derivatives correctly', () => {
    const expr = { op: 'D', args: ['x'], wrt: 't' }
    expect(toUnicode(expr)).toBe('∂x/∂t')
    expect(toLatex(expr)).toBe('\\frac{\\partial x}{\\partial t}')
    expect(toAscii(expr)).toBe('D(x)/Dt')
  })
})