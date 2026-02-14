import { describe, it, expect } from 'vitest'
import { validateSchema, load, SchemaValidationError } from './index.js'

describe('Schema Edge Cases', () => {
  describe('anyOf constraint: models OR reaction_systems required', () => {
    it('should fail when neither models nor reaction_systems are present', () => {
      const invalid = {
        esm: "0.1.0",
        metadata: { name: "test" }
        // Missing both models AND reaction_systems
      }

      const errors = validateSchema(invalid)
      expect(errors.length).toBeGreaterThan(0)

      // Should also throw when using load()
      expect(() => load(invalid)).toThrow(SchemaValidationError)
    })

    it('should pass with only models', () => {
      const withModels = {
        esm: "0.1.0",
        metadata: { name: "test" },
        models: {
          "test_model": {
            variables: {},
            equations: []
          }
        }
      }

      const errors = validateSchema(withModels)
      expect(errors).toEqual([])

      // Should not throw when using load()
      const result = load(withModels)
      expect(result.esm).toBe("0.1.0")
    })

    it('should pass with only reaction_systems', () => {
      const withReactionSystems = {
        esm: "0.1.0",
        metadata: { name: "test" },
        reaction_systems: {
          "test_rs": {
            species: {},
            parameters: {},
            reactions: [
              { id: "R1", substrates: null, products: null, rate: 1.0 }
            ]
          }
        }
      }

      const errors = validateSchema(withReactionSystems)
      expect(errors).toEqual([])

      // Should not throw when using load()
      const result = load(withReactionSystems)
      expect(result.esm).toBe("0.1.0")
    })

    it('should pass with both models and reaction_systems', () => {
      const withBoth = {
        esm: "0.1.0",
        metadata: { name: "test" },
        models: {
          "test_model": {
            variables: {},
            equations: []
          }
        },
        reaction_systems: {
          "test_rs": {
            species: {},
            parameters: {},
            reactions: [
              { id: "R1", substrates: null, products: null, rate: 1.0 }
            ]
          }
        }
      }

      const errors = validateSchema(withBoth)
      expect(errors).toEqual([])

      // Should not throw when using load()
      const result = load(withBoth)
      expect(result.esm).toBe("0.1.0")
    })
  })

  describe('conditional schema: observed variables require expression field', () => {
    it('should fail when observed variable lacks expression', () => {
      const invalid = {
        esm: "0.1.0",
        metadata: { name: "test" },
        models: {
          "test": {
            variables: {
              "bad_observed": {
                type: "observed"
                // Missing required expression field for observed type
              }
            },
            equations: []
          }
        }
      }

      const errors = validateSchema(invalid)
      expect(errors.length).toBeGreaterThan(0)

      // Check that the error mentions the missing expression
      const expressionError = errors.find(error =>
        error.path.includes('bad_observed') ||
        error.message.includes('expression') ||
        error.keyword === 'required'
      )
      expect(expressionError).toBeDefined()

      // Should throw when using load()
      expect(() => load(invalid)).toThrow(SchemaValidationError)
    })

    it('should pass when observed variable has expression (string)', () => {
      const valid = {
        esm: "0.1.0",
        metadata: { name: "test" },
        models: {
          "test": {
            variables: {
              "good_observed": {
                type: "observed",
                expression: "x + y"
              }
            },
            equations: []
          }
        }
      }

      const errors = validateSchema(valid)
      expect(errors).toEqual([])

      const result = load(valid)
      expect(result.esm).toBe("0.1.0")
    })

    it('should pass when observed variable has expression (number)', () => {
      const valid = {
        esm: "0.1.0",
        metadata: { name: "test" },
        models: {
          "test": {
            variables: {
              "good_observed": {
                type: "observed",
                expression: 42
              }
            },
            equations: []
          }
        }
      }

      const errors = validateSchema(valid)
      expect(errors).toEqual([])

      const result = load(valid)
      expect(result.esm).toBe("0.1.0")
    })

    it('should pass when observed variable has expression (object)', () => {
      const valid = {
        esm: "0.1.0",
        metadata: { name: "test" },
        models: {
          "test": {
            variables: {
              "good_observed": {
                type: "observed",
                expression: {
                  op: "+",
                  args: ["x", "y"]
                }
              }
            },
            equations: []
          }
        }
      }

      const errors = validateSchema(valid)
      expect(errors).toEqual([])

      const result = load(valid)
      expect(result.esm).toBe("0.1.0")
    })

    it('should allow other variable types without expression', () => {
      const valid = {
        esm: "0.1.0",
        metadata: { name: "test" },
        models: {
          "test": {
            variables: {
              "state_var": {
                type: "state",
                units: "kg/m3"
              },
              "param_var": {
                type: "parameter",
                default: 1.0
              }
            },
            equations: []
          }
        }
      }

      const errors = validateSchema(valid)
      expect(errors).toEqual([])

      const result = load(valid)
      expect(result.esm).toBe("0.1.0")
    })
  })
})