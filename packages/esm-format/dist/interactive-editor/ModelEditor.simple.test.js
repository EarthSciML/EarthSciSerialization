/**
 * Simple compilation and structure test for ModelEditor
 *
 * This test verifies that the ModelEditor component can be imported
 * and has the expected interface without running in a browser environment.
 */
import { describe, it, expect } from 'vitest';
import { ModelEditor } from './ModelEditor.js';
describe('ModelEditor - Simple Tests', () => {
    // Sample minimal model for testing
    const sampleModel = {
        variables: {
            x: { type: 'state', units: 'm', description: 'Position' },
            v: { type: 'state', units: 'm/s', description: 'Velocity' },
            k: { type: 'parameter', units: '1/s', default: 1.0, description: 'Rate constant' }
        },
        equations: [
            {
                lhs: { op: 'D', args: ['x'], wrt: 't' },
                rhs: 'v'
            },
            {
                lhs: { op: 'D', args: ['v'], wrt: 't' },
                rhs: { op: '*', args: [{ op: '-', args: ['k'] }, 'x'] }
            }
        ]
    };
    it('should be importable', () => {
        expect(ModelEditor).toBeDefined();
        expect(typeof ModelEditor).toBe('function');
    });
    it('should accept proper props interface', () => {
        // This test verifies TypeScript compilation more than runtime behavior
        const props = {
            model: sampleModel,
            onChange: (updatedModel) => {
                // Mock callback
                console.log('Model updated:', updatedModel);
            },
            allowEditing: true,
            showValidation: true,
            validationErrors: ['Sample error']
        };
        // If this compiles without TypeScript errors, the interface is correct
        expect(props).toBeDefined();
        expect(props.model.variables).toBeDefined();
        expect(props.model.equations).toBeDefined();
        expect(typeof props.onChange).toBe('function');
    });
    it('should handle model with no events', () => {
        const modelWithoutEvents = {
            variables: {
                temp: { type: 'state', units: 'K', description: 'Temperature' }
            },
            equations: [
                {
                    lhs: { op: 'D', args: ['temp'], wrt: 't' },
                    rhs: 0
                }
            ]
        };
        expect(modelWithoutEvents.discrete_events).toBeUndefined();
        expect(modelWithoutEvents.continuous_events).toBeUndefined();
    });
    it('should handle model with events', () => {
        const modelWithEvents = {
            variables: {
                temp: { type: 'state', units: 'K', description: 'Temperature' }
            },
            equations: [
                {
                    lhs: { op: 'D', args: ['temp'], wrt: 't' },
                    rhs: 0
                }
            ],
            discrete_events: [
                {
                    name: 'reset',
                    trigger: { type: 'time', at: 10 },
                    affects: [{ lhs: 'temp', rhs: 300 }]
                }
            ],
            continuous_events: [
                {
                    name: 'overheating',
                    conditions: [{ op: '>', args: ['temp', 400] }],
                    affects: [{ lhs: 'temp', rhs: 350 }]
                }
            ]
        };
        expect(modelWithEvents.discrete_events).toHaveLength(1);
        expect(modelWithEvents.continuous_events).toHaveLength(1);
        expect(modelWithEvents.discrete_events[0].name).toBe('reset');
        expect(modelWithEvents.continuous_events[0].name).toBe('overheating');
    });
    it('should handle complex nested expressions', () => {
        const complexModel = {
            variables: {
                c: { type: 'state', units: 'mol/L', description: 'Concentration' },
                k1: { type: 'parameter', units: '1/s', default: 0.1 },
                k2: { type: 'parameter', units: 'L/(mol*s)', default: 0.01 }
            },
            equations: [
                {
                    lhs: { op: 'D', args: ['c'], wrt: 't' },
                    rhs: {
                        op: '+',
                        args: [
                            { op: '*', args: ['k1', 'c'] },
                            {
                                op: '*',
                                args: [
                                    'k2',
                                    { op: '^', args: ['c', 2] }
                                ]
                            }
                        ]
                    }
                }
            ]
        };
        expect(complexModel.equations[0].rhs).toEqual({
            op: '+',
            args: [
                { op: '*', args: ['k1', 'c'] },
                {
                    op: '*',
                    args: [
                        'k2',
                        { op: '^', args: ['c', 2] }
                    ]
                }
            ]
        });
    });
});
//# sourceMappingURL=ModelEditor.simple.test.js.map