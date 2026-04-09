/**
 * Tests for expression substitution functionality
 */
import { describe, it, expect } from 'vitest';
import { substitute, substituteInModel, substituteInReactionSystem } from './substitute.js';
describe('substitute', () => {
    it('handles number literals unchanged', () => {
        const expr = 42;
        const bindings = { x: 10 };
        expect(substitute(expr, bindings)).toBe(42);
    });
    it('substitutes simple variable references', () => {
        const expr = 'x';
        const bindings = { x: 42 };
        expect(substitute(expr, bindings)).toBe(42);
    });
    it('leaves unbound variables unchanged', () => {
        const expr = 'y';
        const bindings = { x: 42 };
        expect(substitute(expr, bindings)).toBe('y');
    });
    it('substitutes variables with expressions', () => {
        const expr = 'x';
        const bindings = { x: { op: '+', args: [1, 2] } };
        expect(substitute(expr, bindings)).toEqual({ op: '+', args: [1, 2] });
    });
    it('handles nested function calls', () => {
        const expr = {
            op: 'exp',
            args: [{
                    op: '/',
                    args: [{
                            op: '*',
                            args: [-1370, 'T']
                        }, 'R']
                }]
        };
        const bindings = { T: 298.15, R: 8.314 };
        const expected = {
            op: 'exp',
            args: [{
                    op: '/',
                    args: [{
                            op: '*',
                            args: [-1370, 298.15]
                        }, 8.314]
                }]
        };
        expect(substitute(expr, bindings)).toEqual(expected);
    });
    it('handles multiple levels of nesting with repeated variables', () => {
        const expr = {
            op: '+',
            args: [
                { op: '*', args: ['A', { op: 'sin', args: [{ op: '*', args: ['omega', 't'] }] }] },
                { op: '*', args: ['A', { op: 'cos', args: [{ op: '*', args: ['omega', 't'] }] }] }
            ]
        };
        const bindings = { A: 2.5, omega: 1.5 };
        const expected = {
            op: '+',
            args: [
                { op: '*', args: [2.5, { op: 'sin', args: [{ op: '*', args: [1.5, 't'] }] }] },
                { op: '*', args: [2.5, { op: 'cos', args: [{ op: '*', args: [1.5, 't'] }] }] }
            ]
        };
        expect(substitute(expr, bindings)).toEqual(expected);
    });
    it('handles derivative expressions', () => {
        const expr = {
            op: 'D',
            args: [{ op: '*', args: ['k', 'concentration'] }],
            wrt: 't'
        };
        const bindings = { k: 0.1, concentration: 'C_species' };
        const expected = {
            op: 'D',
            args: [{ op: '*', args: [0.1, 'C_species'] }],
            wrt: 't'
        };
        expect(substitute(expr, bindings)).toEqual(expected);
    });
    it('handles conditional expressions', () => {
        const expr = {
            op: 'ifelse',
            args: [
                { op: '>', args: [{ op: '*', args: ['x', 'scale'] }, 'threshold'] },
                { op: '*', args: ['x', 'amplification'] },
                { op: '/', args: ['x', 'damping'] }
            ]
        };
        const bindings = { scale: 2.0, threshold: 10.0, amplification: 1.5, damping: 0.8 };
        const expected = {
            op: 'ifelse',
            args: [
                { op: '>', args: [{ op: '*', args: ['x', 2.0] }, 10.0] },
                { op: '*', args: ['x', 1.5] },
                { op: '/', args: ['x', 0.8] }
            ]
        };
        expect(substitute(expr, bindings)).toEqual(expected);
    });
});
describe('substituteInModel', () => {
    it('substitutes in model equations', () => {
        const model = {
            variables: {
                x: { type: 'state', units: 'm' },
                k: { type: 'parameter', default: 1.0 }
            },
            equations: [
                { lhs: { op: 'D', args: ['x'], wrt: 't' }, rhs: { op: '*', args: ['k', 'x'] } }
            ]
        };
        const bindings = { k: 2.5 };
        const result = substituteInModel(model, bindings);
        expect(result.equations[0].rhs).toEqual({ op: '*', args: [2.5, 'x'] });
        expect(result.variables).toEqual(model.variables); // Variables unchanged
    });
    it('substitutes in observed variable expressions', () => {
        const model = {
            variables: {
                x: { type: 'state' },
                y: { type: 'observed', expression: { op: '*', args: ['k', 'x'] } }
            },
            equations: []
        };
        const bindings = { k: 2.0 };
        const result = substituteInModel(model, bindings);
        expect(result.variables.y?.expression).toEqual({ op: '*', args: [2.0, 'x'] });
    });
});
describe('substituteInReactionSystem', () => {
    it('substitutes in reaction rate expressions', () => {
        const system = {
            species: {
                A: { units: 'mol/L' },
                B: { units: 'mol/L' }
            },
            parameters: {
                k: { default: 1.0, units: '1/s' }
            },
            reactions: [
                {
                    id: 'R1',
                    substrates: [{ species: 'A', stoichiometry: 1 }],
                    products: [{ species: 'B', stoichiometry: 1 }],
                    rate: { op: '*', args: ['k', 'A'] }
                }
            ]
        };
        const bindings = { k: 1.5 };
        const result = substituteInReactionSystem(system, bindings);
        expect(result.reactions[0].rate).toEqual({ op: '*', args: [1.5, 'A'] });
    });
    it('substitutes in constraint equations when present', () => {
        const system = {
            species: { A: { units: 'mol/L' } },
            parameters: { k: { default: 1.0 } },
            reactions: [
                { id: 'R1', substrates: null, products: null, rate: 1.0 }
            ],
            constraint_equations: [
                { lhs: 'total', rhs: { op: '*', args: ['k', 'A'] } }
            ]
        };
        const bindings = { k: 2.0 };
        const result = substituteInReactionSystem(system, bindings);
        expect(result.constraint_equations?.[0]?.rhs).toEqual({ op: '*', args: [2.0, 'A'] });
    });
});
//# sourceMappingURL=substitute.test.js.map