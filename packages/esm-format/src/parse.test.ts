import { describe, it, expect } from 'vitest'
import { load, save, ParseError, SchemaValidationError, validateSchema } from './index.js'

describe('Parse and Serialize', () => {
  const validMinimalEsm = {
    esm: "0.1.0",
    metadata: {
      name: "test-model"
    },
    models: {
      "test_model": {
        variables: {},
        equations: []
      }
    }
  }

  const validMinimalEsmJson = JSON.stringify(validMinimalEsm, null, 2)

  describe('load()', () => {
    it('should parse valid JSON string', () => {
      const result = load(validMinimalEsmJson)
      expect(result.esm).toBe('0.1.0')
      expect(result.metadata.name).toBe('test-model')
    })

    it('should accept pre-parsed object', () => {
      const result = load(validMinimalEsm)
      expect(result.esm).toBe('0.1.0')
      expect(result.metadata.name).toBe('test-model')
    })

    it('should throw ParseError on invalid JSON', () => {
      expect(() => {
        load('{ invalid json')
      }).toThrow(ParseError)
    })

    it('should throw SchemaValidationError on missing required fields', () => {
      const invalid = { esm: "0.1.0" } // missing metadata and models/reaction_systems
      expect(() => {
        load(invalid)
      }).toThrow(SchemaValidationError)
    })

    it('should throw SchemaValidationError on wrong version', () => {
      const invalid = {
        ...validMinimalEsm,
        esm: "0.2.0"
      }
      expect(() => {
        load(invalid)
      }).toThrow(SchemaValidationError)
    })

    it('should handle Expression union types', () => {
      const esmWithExpression = {
        esm: "0.1.0",
        metadata: { name: "expr-test" },
        models: {
          "test": {
            variables: {
              "x": {
                type: "state",
                units: "kg/m3",
                description: "concentration"
              },
              "temperature": {
                type: "parameter",
                units: "K",
                default: 298.15
              },
              "result": {
                type: "observed",
                expression: {
                  op: "+",
                  args: [42, "temperature", { op: "*", args: [2, "x"] }]
                }
              }
            },
            equations: [
              {
                lhs: "D(x, t)",
                rhs: {
                  op: "+",
                  args: [42, "temperature", { op: "*", args: [2, "x"] }]
                }
              }
            ]
          }
        }
      }

      const result = load(esmWithExpression)
      const testModel = result.models?.["test"]
      expect(testModel).toBeDefined()
      const observedVar = testModel?.variables["result"]
      expect(observedVar).toBeDefined()
      expect(observedVar?.type).toBe('observed')
      expect(typeof observedVar?.expression).toBe('object')
      if (observedVar && typeof observedVar.expression === 'object' && observedVar.expression && 'op' in observedVar.expression) {
        expect(observedVar.expression.op).toBe('+')
        expect(Array.isArray(observedVar.expression.args)).toBe(true)
        expect(observedVar.expression.args[0]).toBe(42) // number
        expect(observedVar.expression.args[1]).toBe('temperature') // string
        expect(typeof observedVar.expression.args[2]).toBe('object') // ExpressionNode
      }
    })

    it('should handle CouplingEntry discriminated unions', () => {
      const esmWithCoupling = {
        esm: "0.1.0",
        metadata: { name: "coupling-test" },
        models: {
          "model1": { variables: {}, equations: [] },
          "model2": { variables: {}, equations: [] }
        },
        coupling: [
          {
            type: "operator_compose",
            systems: ["model1", "model2"]
          }
        ]
      }

      const result = load(esmWithCoupling)
      expect(result.coupling).toBeDefined()
      expect(result.coupling?.[0]?.type).toBe('operator_compose')
    })

    it('should handle optional vs required fields correctly', () => {
      const esmWithOptionalFields = {
        esm: "0.1.0",
        metadata: {
          name: "optional-test",
          description: "A test model",
          // authors field is absent (optional)
        },
        models: {
          "test": {
            variables: {},
            equations: []
          }
        }
      }

      const result = load(esmWithOptionalFields)
      expect(result.metadata.description).toBe("A test model")
      expect(result.metadata.authors).toBeUndefined()
    })
  })

  describe('save()', () => {
    it('should serialize EsmFile to formatted JSON string', () => {
      const result = save(validMinimalEsm as any)
      expect(typeof result).toBe('string')

      // Should be valid JSON
      const parsed = JSON.parse(result)
      expect(parsed.esm).toBe('0.1.0')
      expect(parsed.metadata.name).toBe('test-model')
    })

    it('should produce formatted output with proper indentation', () => {
      const result = save(validMinimalEsm as any)
      expect(result).toContain('{\n  "esm"')
      expect(result).toContain('  "metadata": {')
    })
  })

  describe('round-trip property', () => {
    it('should satisfy load(save(load(json))) === load(json)', () => {
      const original = load(validMinimalEsmJson)
      const serialized = save(original)
      const reloaded = load(serialized)

      // Objects should be deeply equal
      expect(reloaded).toEqual(original)
    })

    it('should handle complex structures in round-trip', () => {
      const complexEsm = {
        esm: "0.1.0",
        metadata: {
          name: "complex-model",
          description: "A complex test model",
          authors: ["Test Author"],
          license: "MIT"
        },
        models: {
          "atmospheric": {
            variables: {
              "O3": { type: "state", units: "ppb", description: "Ozone concentration" },
              "NO2": { type: "parameter", units: "ppb", description: "Nitrogen dioxide", default: 10.0 },
              "k1": { type: "parameter", default: 0.5 }
            },
            equations: [
              {
                lhs: "D(O3, t)",
                rhs: { op: "*", args: [{ op: "+", args: ["k1", 0.1] }, "NO2"] }
              }
            ]
          },
          "surface": {
            variables: {},
            equations: []
          }
        },
        coupling: [
          {
            type: "operator_compose",
            systems: ["atmospheric", "surface"]
          }
        ]
      }

      const first = load(complexEsm)
      const serialized = save(first)
      const second = load(serialized)

      expect(second).toEqual(first)
    })
  })

  describe('validateSchema()', () => {
    it('should return empty array for valid data', () => {
      const errors = validateSchema(validMinimalEsm)
      expect(errors).toEqual([])
    })

    it('should return error details for invalid data', () => {
      const invalid = { esm: "invalid", metadata: {} }
      const errors = validateSchema(invalid)

      expect(errors.length).toBeGreaterThan(0)
      expect(errors[0]).toHaveProperty('path')
      expect(errors[0]).toHaveProperty('message')
      expect(errors[0]).toHaveProperty('keyword')
    })
  })

  describe('error handling', () => {
    it('should preserve original error in ParseError', () => {
      try {
        load('{ invalid json }')
      } catch (error) {
        if (error instanceof ParseError) {
          expect(error.originalError).toBeDefined()
          expect(error.message).toContain('Invalid JSON')
        }
      }
    })

    it('should include validation errors in SchemaValidationError', () => {
      try {
        load({ invalid: "data" })
      } catch (error) {
        if (error instanceof SchemaValidationError) {
          expect(error.errors).toBeDefined()
          expect(Array.isArray(error.errors)).toBe(true)
          expect(error.errors.length).toBeGreaterThan(0)
        }
      }
    })
  })
})