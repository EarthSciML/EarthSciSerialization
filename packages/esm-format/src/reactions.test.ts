import { describe, it, expect } from 'vitest'
import { deriveODEs } from './reactions.js'
import type { ReactionSystem, Model, Equation } from './types.js'

describe('Reaction system ODE derivation', () => {
  describe('deriveODEs', () => {
    it('should handle simple single reaction', () => {
      const system: ReactionSystem = {
        species: {
          A: { units: 'mol/L', default: 1.0 },
          B: { units: 'mol/L', default: 0.0 },
        },
        parameters: {
          k1: { default: 0.1, units: '1/s' },
        },
        reactions: [
          {
            id: 'R1',
            substrates: [{ species: 'A', stoichiometry: 1 }],
            products: [{ species: 'B', stoichiometry: 1 }],
            rate: 'k1',
          },
        ],
      }

      const model = deriveODEs(system)

      // Check variables
      expect(model.variables.A).toEqual({
        type: 'state',
        units: 'mol/L',
        default: 1.0,
      })
      expect(model.variables.B).toEqual({
        type: 'state',
        units: 'mol/L',
        default: 0.0,
      })
      expect(model.variables.k1).toEqual({
        type: 'parameter',
        default: 0.1,
        units: '1/s',
      })

      // Check equations
      expect(model.equations).toHaveLength(2)

      // d[A]/dt = -k1 * A
      const eqnA = model.equations.find(eq =>
        typeof eq.lhs === 'object' &&
        eq.lhs.op === 'D' &&
        eq.lhs.args[0] === 'A' &&
        eq.lhs.wrt === 't'
      )
      expect(eqnA).toBeDefined()
      expect(eqnA?.rhs).toEqual({
        op: '-',
        args: [{ op: '*', args: ['k1', 'A'] }]
      })

      // d[B]/dt = k1 * A
      const eqnB = model.equations.find(eq =>
        typeof eq.lhs === 'object' &&
        eq.lhs.op === 'D' &&
        eq.lhs.args[0] === 'B' &&
        eq.lhs.wrt === 't'
      )
      expect(eqnB).toBeDefined()
      expect(eqnB?.rhs).toEqual({
        op: '*',
        args: ['k1', 'A']
      })
    })

    it('should handle source reaction (null substrates)', () => {
      const system: ReactionSystem = {
        species: {
          A: { units: 'mol/L', default: 0.0 },
        },
        parameters: {
          k_source: { default: 0.5, units: 'mol/L/s' },
        },
        reactions: [
          {
            id: 'R_source',
            substrates: null, // Source reaction: ∅ → A
            products: [{ species: 'A', stoichiometry: 1 }],
            rate: 'k_source',
          },
        ],
      }

      const model = deriveODEs(system)

      // d[A]/dt = k_source (direct production)
      const eqnA = model.equations.find(eq =>
        typeof eq.lhs === 'object' &&
        eq.lhs.op === 'D' &&
        eq.lhs.args[0] === 'A' &&
        eq.lhs.wrt === 't'
      )
      expect(eqnA?.rhs).toBe('k_source')
    })

    it('should handle sink reaction (null products)', () => {
      const system: ReactionSystem = {
        species: {
          A: { units: 'mol/L', default: 1.0 },
        },
        parameters: {
          k_sink: { default: 0.1, units: '1/s' },
        },
        reactions: [
          {
            id: 'R_sink',
            substrates: [{ species: 'A', stoichiometry: 1 }],
            products: null, // Sink reaction: A → ∅
            rate: 'k_sink',
          },
        ],
      }

      const model = deriveODEs(system)

      // d[A]/dt = -k_sink * A (direct loss)
      const eqnA = model.equations.find(eq =>
        typeof eq.lhs === 'object' &&
        eq.lhs.op === 'D' &&
        eq.lhs.args[0] === 'A' &&
        eq.lhs.wrt === 't'
      )
      expect(eqnA?.rhs).toEqual({
        op: '-',
        args: [{ op: '*', args: ['k_sink', 'A'] }]
      })
    })

    it('should handle reactions with stoichiometry > 1', () => {
      const system: ReactionSystem = {
        species: {
          A: { units: 'mol/L', default: 1.0 },
          B: { units: 'mol/L', default: 0.0 },
        },
        parameters: {
          k1: { default: 0.1, units: 'L/mol/s' },
        },
        reactions: [
          {
            id: 'R1',
            substrates: [{ species: 'A', stoichiometry: 2 }], // 2A → B
            products: [{ species: 'B', stoichiometry: 1 }],
            rate: 'k1',
          },
        ],
      }

      const model = deriveODEs(system)

      // d[A]/dt = -2 * k1 * A^2
      const eqnA = model.equations.find(eq =>
        typeof eq.lhs === 'object' &&
        eq.lhs.op === 'D' &&
        eq.lhs.args[0] === 'A' &&
        eq.lhs.wrt === 't'
      )
      expect(eqnA?.rhs).toEqual({
        op: '*',
        args: [-2, { op: '*', args: ['k1', { op: '^', args: ['A', 2] }] }]
      })

      // d[B]/dt = k1 * A^2
      const eqnB = model.equations.find(eq =>
        typeof eq.lhs === 'object' &&
        eq.lhs.op === 'D' &&
        eq.lhs.args[0] === 'B' &&
        eq.lhs.wrt === 't'
      )
      expect(eqnB?.rhs).toEqual({
        op: '*',
        args: ['k1', { op: '^', args: ['A', 2] }]
      })
    })

    it('should handle multiple reactions affecting same species', () => {
      const system: ReactionSystem = {
        species: {
          A: { units: 'mol/L', default: 1.0 },
          B: { units: 'mol/L', default: 0.0 },
          C: { units: 'mol/L', default: 0.0 },
        },
        parameters: {
          k1: { default: 0.1, units: '1/s' },
          k2: { default: 0.05, units: '1/s' },
        },
        reactions: [
          {
            id: 'R1',
            substrates: [{ species: 'A', stoichiometry: 1 }],
            products: [{ species: 'B', stoichiometry: 1 }],
            rate: 'k1',
          },
          {
            id: 'R2',
            substrates: [{ species: 'A', stoichiometry: 1 }],
            products: [{ species: 'C', stoichiometry: 1 }],
            rate: 'k2',
          },
        ],
      }

      const model = deriveODEs(system)

      // d[A]/dt = -(k1 * A) - (k2 * A) = -(k1 + k2) * A (summed terms)
      const eqnA = model.equations.find(eq =>
        typeof eq.lhs === 'object' &&
        eq.lhs.op === 'D' &&
        eq.lhs.args[0] === 'A' &&
        eq.lhs.wrt === 't'
      )
      expect(eqnA?.rhs).toEqual({
        op: '+',
        args: [
          { op: '-', args: [{ op: '*', args: ['k1', 'A'] }] },
          { op: '-', args: [{ op: '*', args: ['k2', 'A'] }] }
        ]
      })

      // d[B]/dt = k1 * A
      const eqnB = model.equations.find(eq =>
        typeof eq.lhs === 'object' &&
        eq.lhs.op === 'D' &&
        eq.lhs.args[0] === 'B' &&
        eq.lhs.wrt === 't'
      )
      expect(eqnB?.rhs).toEqual({
        op: '*',
        args: ['k1', 'A']
      })

      // d[C]/dt = k2 * A
      const eqnC = model.equations.find(eq =>
        typeof eq.lhs === 'object' &&
        eq.lhs.op === 'D' &&
        eq.lhs.args[0] === 'C' &&
        eq.lhs.wrt === 't'
      )
      expect(eqnC?.rhs).toEqual({
        op: '*',
        args: ['k2', 'A']
      })
    })

    it('should handle species with no reactions', () => {
      const system: ReactionSystem = {
        species: {
          A: { units: 'mol/L', default: 1.0 },
          B: { units: 'mol/L', default: 0.0 }, // B is not in any reactions
        },
        parameters: {
          k1: { default: 0.1, units: '1/s' },
        },
        reactions: [
          // Only reaction: A → ∅ (sink)
          {
            id: 'R1',
            substrates: [{ species: 'A', stoichiometry: 1 }],
            products: null,
            rate: 'k1',
          },
        ],
      }

      const model = deriveODEs(system)

      // d[B]/dt = 0 (no reactions affect B)
      const eqnB = model.equations.find(eq =>
        typeof eq.lhs === 'object' &&
        eq.lhs.op === 'D' &&
        eq.lhs.args[0] === 'B' &&
        eq.lhs.wrt === 't'
      )
      expect(eqnB?.rhs).toBe(0)
    })

    it('should append constraint equations', () => {
      const system: ReactionSystem = {
        species: {
          A: { units: 'mol/L', default: 1.0 },
          B: { units: 'mol/L', default: 0.0 },
        },
        parameters: {
          k1: { default: 0.1, units: '1/s' },
          total: { default: 1.0, units: 'mol/L' },
        },
        reactions: [
          {
            id: 'R1',
            substrates: [{ species: 'A', stoichiometry: 1 }],
            products: [{ species: 'B', stoichiometry: 1 }],
            rate: 'k1',
          },
        ],
        constraint_equations: [
          {
            lhs: 'total',
            rhs: { op: '+', args: ['A', 'B'] }, // Conservation constraint
          },
        ],
      }

      const model = deriveODEs(system)

      // Should have 2 ODEs + 1 constraint = 3 equations total
      expect(model.equations).toHaveLength(3)

      // Check that constraint equation was appended
      const constraintEqn = model.equations.find(eq => eq.lhs === 'total')
      expect(constraintEqn).toBeDefined()
      expect(constraintEqn?.rhs).toEqual({
        op: '+',
        args: ['A', 'B']
      })
    })

    it('should preserve coupletype and reference', () => {
      const system: ReactionSystem = {
        coupletype: 'chemistry',
        reference: { doi: '10.1000/test', url: 'https://example.com' },
        species: {
          A: { units: 'mol/L', default: 1.0 },
        },
        parameters: {
          k1: { default: 0.1, units: '1/s' },
        },
        reactions: [
          {
            id: 'R1',
            substrates: [{ species: 'A', stoichiometry: 1 }],
            products: null,
            rate: 'k1',
          },
        ],
      }

      const model = deriveODEs(system)

      expect(model.coupletype).toBe('chemistry')
      expect(model.reference).toEqual({ doi: '10.1000/test', url: 'https://example.com' })
    })

    it('should handle complex rate expressions', () => {
      const system: ReactionSystem = {
        species: {
          A: { units: 'mol/L', default: 1.0 },
          B: { units: 'mol/L', default: 0.0 },
        },
        parameters: {
          k_base: { default: 0.1, units: '1/s' },
          T: { default: 298, units: 'K' },
        },
        reactions: [
          {
            id: 'R1',
            substrates: [{ species: 'A', stoichiometry: 1 }],
            products: [{ species: 'B', stoichiometry: 1 }],
            rate: {
              op: '*',
              args: [
                'k_base',
                { op: 'exp', args: [{ op: '/', args: [1000, 'T'] }] }
              ]
            }, // Arrhenius rate: k_base * exp(1000/T)
          },
        ],
      }

      const model = deriveODEs(system)

      // d[A]/dt = -(k_base * exp(1000/T)) * A
      const eqnA = model.equations.find(eq =>
        typeof eq.lhs === 'object' &&
        eq.lhs.op === 'D' &&
        eq.lhs.args[0] === 'A' &&
        eq.lhs.wrt === 't'
      )
      expect(eqnA?.rhs).toEqual({
        op: '-',
        args: [{
          op: '*',
          args: [
            {
              op: '*',
              args: [
                'k_base',
                { op: 'exp', args: [{ op: '/', args: [1000, 'T'] }] }
              ]
            },
            'A'
          ]
        }]
      })
    })
  })
})