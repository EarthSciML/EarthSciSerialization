/**
 * Tests for structural validation
 */
import { describe, it, expect } from 'vitest';
import { validate } from './validate.js';
describe('Structural validation', () => {
    it('should detect equation count mismatch', () => {
        const data = {
            esm: "0.1.0",
            metadata: { name: "test" },
            models: {
                TestModel: {
                    variables: {
                        x: { type: "state", default: 1.0 },
                        y: { type: "state", default: 2.0 }
                    },
                    equations: [
                        { lhs: { op: "D", args: ["x"], wrt: "t" }, rhs: "y" }
                    ]
                }
            }
        };
        const result = validate(data);
        expect(result.is_valid).toBe(false);
        expect(result.structural_errors).toHaveLength(1);
        expect(result.structural_errors[0].code).toBe('equation_count_mismatch');
        expect(result.structural_errors[0].path).toBe('/models/TestModel');
        expect(result.structural_errors[0].details.missing_equations_for).toEqual(['y']);
    });
    it('should detect undefined variable in equation', () => {
        const data = {
            esm: "0.1.0",
            metadata: { name: "test" },
            models: {
                TestModel: {
                    variables: {
                        x: { type: "state", default: 1.0 }
                    },
                    equations: [
                        { lhs: { op: "D", args: ["x"], wrt: "t" }, rhs: "undefined_var" }
                    ]
                }
            }
        };
        const result = validate(data);
        expect(result.is_valid).toBe(false);
        expect(result.structural_errors.some(err => err.code === 'undefined_variable')).toBe(true);
    });
    it('should detect undefined system in coupling', () => {
        const data = {
            esm: "0.1.0",
            metadata: { name: "test" },
            models: {
                TestModel: {
                    variables: {
                        x: { type: "state", default: 1.0 }
                    },
                    equations: [
                        { lhs: { op: "D", args: ["x"], wrt: "t" }, rhs: 1.0 }
                    ]
                }
            },
            coupling: [
                {
                    type: "operator_compose",
                    systems: ["TestModel", "NonExistentModel"]
                }
            ]
        };
        const result = validate(data);
        expect(result.is_valid).toBe(false);
        expect(result.structural_errors.some(err => err.code === 'undefined_system')).toBe(true);
    });
    it('should detect null reaction', () => {
        const data = {
            esm: "0.1.0",
            metadata: { name: "test" },
            reaction_systems: {
                TestSystem: {
                    species: {
                        A: { default: 1.0 }
                    },
                    parameters: {
                        k: { default: 0.1 }
                    },
                    reactions: [
                        {
                            id: "R1",
                            substrates: null,
                            products: null,
                            rate: "k"
                        }
                    ]
                }
            }
        };
        const result = validate(data);
        expect(result.is_valid).toBe(false);
        expect(result.structural_errors.some(err => err.code === 'null_reaction')).toBe(true);
    });
    it('should detect undefined species in reaction', () => {
        const data = {
            esm: "0.1.0",
            metadata: { name: "test" },
            reaction_systems: {
                TestSystem: {
                    species: {
                        A: { default: 1.0 }
                    },
                    parameters: {
                        k: { default: 0.1 }
                    },
                    reactions: [
                        {
                            id: "R1",
                            substrates: [{ species: "B", stoichiometry: 1 }], // B not declared
                            products: [{ species: "A", stoichiometry: 1 }],
                            rate: "k"
                        }
                    ]
                }
            }
        };
        const result = validate(data);
        expect(result.is_valid).toBe(false);
        expect(result.structural_errors.some(err => err.code === 'undefined_species')).toBe(true);
    });
    it('should pass validation for valid data', () => {
        const data = {
            esm: "0.1.0",
            metadata: { name: "test" },
            models: {
                TestModel: {
                    variables: {
                        x: { type: "state", default: 1.0 },
                        y: { type: "parameter", default: 2.0 }
                    },
                    equations: [
                        { lhs: { op: "D", args: ["x"], wrt: "t" }, rhs: "y" }
                    ]
                }
            }
        };
        const result = validate(data);
        expect(result.is_valid).toBe(true);
        expect(result.structural_errors).toHaveLength(0);
    });
});
//# sourceMappingURL=validate.test.js.map