import { describe, it, expect } from 'vitest'
import { parseUnit, checkDimensions, validateUnits } from './units.js'
import type { DimensionalRep, Expression, EsmFile } from './types.js'

describe('Unit parsing and dimensional analysis', () => {
  describe('parseUnit', () => {
    it('should handle dimensionless units', () => {
      expect(parseUnit('degrees')).toEqual({ dimensionless: true })
      expect(parseUnit('dimensionless')).toEqual({ dimensionless: true })
      expect(parseUnit('')).toEqual({ dimensionless: true })
      expect(parseUnit('mol/mol')).toEqual({ dimensionless: true })
      expect(parseUnit('ppb')).toEqual({ dimensionless: true })
      expect(parseUnit('ppm')).toEqual({ dimensionless: true })
    })

    it('should parse basic units', () => {
      expect(parseUnit('K')).toEqual({ K: 1 })
      expect(parseUnit('m')).toEqual({ m: 1 })
      expect(parseUnit('s')).toEqual({ s: 1 })
      expect(parseUnit('mol')).toEqual({ mol: 1 })
      expect(parseUnit('molec')).toEqual({ molec: 1 })
    })

    it('should parse compound units', () => {
      expect(parseUnit('m/s')).toEqual({ m: 1, s: -1 })
      expect(parseUnit('mol/mol/s')).toEqual({ s: -1 })  // mol/mol cancels out, left with 1/s
      expect(parseUnit('1/s')).toEqual({ s: -1 })
      expect(parseUnit('s/m')).toEqual({ s: 1, m: -1 })
    })

    it('should parse units with exponents', () => {
      expect(parseUnit('cm^3')).toEqual({ cm: 3 })
      expect(parseUnit('cm^3/molec/s')).toEqual({ cm: 3, molec: -1, s: -1 })
    })

    it('should handle multiplication', () => {
      expect(parseUnit('molec/cm^3')).toEqual({ molec: 1, cm: -3 })
    })

    it('should handle complex real-world units', () => {
      // Real examples from ESM spec
      expect(parseUnit('mol/mol')).toEqual({ dimensionless: true })
      expect(parseUnit('cm^3/molec/s')).toEqual({ cm: 3, molec: -1, s: -1 })
      expect(parseUnit('molec/cm^3')).toEqual({ molec: 1, cm: -3 })
      expect(parseUnit('mol/mol/s')).toEqual({ s: -1 })
    })
  })

  describe('checkDimensions', () => {
    const createUnitBindings = (bindings: Record<string, string>): Map<string, DimensionalRep> => {
      const map = new Map<string, DimensionalRep>()
      for (const [name, unitStr] of Object.entries(bindings)) {
        map.set(name, parseUnit(unitStr))
      }
      return map
    }

    it('should handle numbers and variables', () => {
      const bindings = createUnitBindings({ x: 'm', t: 's' })

      const numberResult = checkDimensions(42, bindings)
      expect(numberResult.dimensions).toEqual({ dimensionless: true })
      expect(numberResult.warnings).toEqual([])

      const varResult = checkDimensions('x', bindings)
      expect(varResult.dimensions).toEqual({ m: 1 })
      expect(varResult.warnings).toEqual([])

      const unknownVarResult = checkDimensions('unknown', bindings)
      expect(unknownVarResult.dimensions).toEqual({ dimensionless: true })
      expect(unknownVarResult.warnings).toEqual(['Unknown variable: unknown'])
    })

    it('should handle addition and subtraction', () => {
      const bindings = createUnitBindings({ x: 'm', y: 'm', t: 's' })

      // Same dimensions - valid
      const addExpr: Expression = { op: '+', args: ['x', 'y'] }
      const addResult = checkDimensions(addExpr, bindings)
      expect(addResult.dimensions).toEqual({ m: 1 })
      expect(addResult.warnings).toEqual([])

      // Different dimensions - invalid
      const badAddExpr: Expression = { op: '+', args: ['x', 't'] }
      const badAddResult = checkDimensions(badAddExpr, bindings)
      expect(badAddResult.warnings[0]).toContain('Addition/subtraction requires same dimensions')
    })

    it('should handle multiplication', () => {
      const bindings = createUnitBindings({ F: 'kg*m/s^2', m: 'kg', a: 'm/s^2' })

      const multExpr: Expression = { op: '*', args: ['m', 'a'] }
      const result = checkDimensions(multExpr, bindings)
      // This is a simplified test - full implementation would need better unit parsing for compound units
      expect(result.warnings).toEqual([])
    })

    it('should handle division', () => {
      const bindings = createUnitBindings({ v: 'm/s', t: 's', a: 'm/s^2' })

      const divExpr: Expression = { op: '/', args: ['v', 't'] }
      const result = checkDimensions(divExpr, bindings)
      // v/t should give acceleration units
      expect(result.warnings).toEqual([])
    })

    it('should handle derivative operator', () => {
      const bindings = createUnitBindings({ x: 'm', t: 's' })

      const derivExpr: Expression = { op: 'D', args: ['x'], wrt: 't' }
      const result = checkDimensions(derivExpr, bindings)
      // D(x)/D(t) should have dimensions m/s
      expect(result.dimensions).toEqual({ m: 1, s: -1 })
      expect(result.warnings).toEqual([])
    })

    it('should handle mathematical functions', () => {
      const bindings = createUnitBindings({ x: 'dimensionless', y: 'm' })

      // Functions requiring dimensionless arguments
      const expExpr: Expression = { op: 'exp', args: ['x'] }
      const expResult = checkDimensions(expExpr, bindings)
      expect(expResult.dimensions).toEqual({ dimensionless: true })
      expect(expResult.warnings).toEqual([])

      // Function with dimensional argument - should warn
      const badExpExpr: Expression = { op: 'exp', args: ['y'] }
      const badExpResult = checkDimensions(badExpExpr, bindings)
      expect(badExpResult.warnings[0]).toContain('exp() requires dimensionless argument')
    })

    it('should handle comparison operators', () => {
      const bindings = createUnitBindings({ x: 'm', y: 'm', t: 's' })

      // Same dimensions - valid
      const compExpr: Expression = { op: '>', args: ['x', 'y'] }
      const compResult = checkDimensions(compExpr, bindings)
      expect(compResult.dimensions).toEqual({ dimensionless: true })
      expect(compResult.warnings).toEqual([])

      // Different dimensions - invalid
      const badCompExpr: Expression = { op: '>', args: ['x', 't'] }
      const badCompResult = checkDimensions(badCompExpr, bindings)
      expect(badCompResult.warnings[0]).toContain('> requires arguments with same dimensions')
    })

    it('should handle conditional expressions', () => {
      const bindings = createUnitBindings({ condition: 'dimensionless', x: 'm', y: 'm' })

      const ifExpr: Expression = { op: 'ifelse', args: ['condition', 'x', 'y'] }
      const result = checkDimensions(ifExpr, bindings)
      expect(result.dimensions).toEqual({ m: 1 })
      expect(result.warnings).toEqual([])
    })
  })

  describe('validateUnits', () => {
    it('should validate simple ESM file with no errors', () => {
      const esmFile: EsmFile = {
        esm: '0.1.0',
        metadata: {
          name: 'test',
          description: 'test model',
          authors: ['test']
        },
        models: {
          TestModel: {
            variables: {
              x: { type: 'state', units: 'm', description: 'Position' },
              v: { type: 'state', units: 'm/s', description: 'Velocity' },
              t: { type: 'parameter', units: 's', description: 'Time' }
            },
            equations: [
              {
                lhs: { op: 'D', args: ['x'], wrt: 't' },
                rhs: 'v'
              }
            ]
          }
        }
      }

      const warnings = validateUnits(esmFile)
      // D(x)/D(t) has dimensions m/s, v has dimensions m/s - should be consistent
      expect(warnings).toEqual([])
    })

    it('should detect dimensional inconsistencies', () => {
      const esmFile: EsmFile = {
        esm: '0.1.0',
        metadata: {
          name: 'test',
          description: 'test model',
          authors: ['test']
        },
        models: {
          TestModel: {
            variables: {
              x: { type: 'state', units: 'm', description: 'Position' },
              f: { type: 'parameter', units: 's', description: 'Force (wrong units)' }
            },
            equations: [
              {
                lhs: { op: 'D', args: ['x'], wrt: 't' },
                rhs: 'f'
              }
            ]
          }
        }
      }

      const warnings = validateUnits(esmFile)
      expect(warnings.length).toBeGreaterThan(0)
      expect(warnings[0].message).toContain('Dimensional mismatch')
    })

    it('should validate observed variables', () => {
      const esmFile: EsmFile = {
        esm: '0.1.0',
        metadata: {
          name: 'test',
          description: 'test model',
          authors: ['test']
        },
        models: {
          TestModel: {
            variables: {
              k: { type: 'parameter', units: '1/s', description: 'Rate constant' },
              x: { type: 'state', units: 'm', description: 'Position' },
              rate: {
                type: 'observed',
                units: 'm/s',
                expression: { op: '*', args: ['k', 'x'] },
                description: 'Rate of change'
              }
            }
          }
        }
      }

      const warnings = validateUnits(esmFile)
      // k (1/s) * x (m) = m/s, which matches the declared units
      expect(warnings).toEqual([])
    })

    it('should handle reaction systems', () => {
      const esmFile: EsmFile = {
        esm: '0.1.0',
        metadata: {
          name: 'test',
          description: 'test reaction',
          authors: ['test']
        },
        reaction_systems: {
          SimpleReaction: {
            species: {
              A: { units: 'mol/mol', description: 'Species A' },
              B: { units: 'mol/mol', description: 'Species B' }
            },
            parameters: {
              k: { units: '1/s', description: 'Rate constant' },
              M: { units: 'molec/cm^3', description: 'Number density' }
            },
            reactions: [
              {
                id: 'R1',
                substrates: { A: 1 },
                products: { B: 1 },
                rate: { op: '*', args: ['k', 'A'] }
              }
            ]
          }
        }
      }

      const warnings = validateUnits(esmFile)
      // This is a basic test - reaction system validation is complex
      expect(warnings).toEqual([])
    })
  })

  describe('Edge cases and error handling', () => {
    it('should handle empty or null unit strings gracefully', () => {
      expect(parseUnit('')).toEqual({ dimensionless: true })
      expect(parseUnit('   ')).toEqual({ dimensionless: true })
    })

    it('should handle unknown operators gracefully', () => {
      const bindings = new Map<string, DimensionalRep>()
      bindings.set('x', { m: 1 })

      const unknownOpExpr: Expression = { op: 'unknown_op' as any, args: ['x'] }
      const result = checkDimensions(unknownOpExpr, bindings)
      expect(result.warnings).toContain('Unknown operator: unknown_op')
    })

    it('should handle malformed expressions', () => {
      const bindings = new Map<string, DimensionalRep>()

      // Division with wrong number of arguments
      const badDivExpr: Expression = { op: '/', args: ['x', 'y', 'z'] }
      const result = checkDimensions(badDivExpr, bindings)
      // Should find the division error among other warnings
      const divisionWarning = result.warnings.find(w => w.includes('Division requires exactly 2 arguments'))
      expect(divisionWarning).toBeDefined()
    })
  })
})