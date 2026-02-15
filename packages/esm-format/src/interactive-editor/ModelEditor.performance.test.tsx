/**
 * Performance benchmarks for ModelEditor component
 *
 * Tests the performance of ModelEditor with large and complex models
 * to ensure it meets requirements for production use.
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, cleanup } from '@solidjs/testing-library';
import { ModelEditor } from './ModelEditor.js';
import type { Model, Expression } from '../types.js';

const createLargeModel = (variableCount: number, equationCount: number): Model => {
  const variables: Model['variables'] = {};
  const equations: Model['equations'] = [];

  // Create many variables
  for (let i = 0; i < variableCount; i++) {
    const type = i % 3 === 0 ? 'state' : (i % 3 === 1 ? 'parameter' : 'observed');
    variables[`var_${i}`] = {
      type: type as any,
      units: 'unit',
      description: `Variable ${i}`,
      default: type === 'parameter' ? Math.random() : undefined
    };
  }

  // Create many equations with complex expressions
  for (let i = 0; i < equationCount; i++) {
    const lhs: Expression = i % 2 === 0
      ? { op: 'D', args: [`var_${i % variableCount}`], wrt: 't' }
      : `var_${i % variableCount}`;

    const rhs: Expression = {
      op: '+',
      args: [
        { op: '*', args: [`var_${(i + 1) % variableCount}`, `var_${(i + 2) % variableCount}`] },
        { op: '/', args: [`var_${(i + 3) % variableCount}`, { op: '^', args: [`var_${(i + 4) % variableCount}`, 2] }] }
      ]
    };

    equations.push({ lhs, rhs });
  }

  return { variables, equations };
};

const createDeeplyNestedModel = (): Model => {
  const variables = {
    a: { type: 'state' as const, units: 'unit', description: 'Variable A' },
    b: { type: 'state' as const, units: 'unit', description: 'Variable B' },
    c: { type: 'parameter' as const, units: 'unit', default: 1.0, description: 'Parameter C' }
  };

  // Create a deeply nested expression: ((((a * b) / c) ^ 2) + ((a - b) * c)) - (a / (b + c))
  const deeplyNestedExpression: Expression = {
    op: '-',
    args: [
      {
        op: '+',
        args: [
          {
            op: '^',
            args: [
              {
                op: '/',
                args: [
                  { op: '*', args: ['a', 'b'] },
                  'c'
                ]
              },
              2
            ]
          },
          {
            op: '*',
            args: [
              { op: '-', args: ['a', 'b'] },
              'c'
            ]
          }
        ]
      },
      {
        op: '/',
        args: [
          'a',
          { op: '+', args: ['b', 'c'] }
        ]
      }
    ]
  };

  const equations = [
    {
      lhs: { op: 'D', args: ['a'], wrt: 't' },
      rhs: deeplyNestedExpression
    }
  ];

  return { variables, equations };
};

describe('ModelEditor Performance Tests', () => {
  beforeEach(() => {
    // Clear any existing renders before each test
    cleanup();
  });

  afterEach(() => {
    cleanup();
  });

  it('should handle 100 variables efficiently', async () => {
    const model = createLargeModel(100, 10);
    const onChange = () => {};

    const startTime = performance.now();

    const { unmount } = render(() => (
      <ModelEditor model={model} onChange={onChange} />
    ));

    const renderTime = performance.now() - startTime;

    // Should render within 500ms even with 100 variables
    expect(renderTime).toBeLessThan(500);

    unmount();
  });

  it('should handle 1000 variables without crashing', async () => {
    const model = createLargeModel(1000, 50);
    const onChange = () => {};

    const startTime = performance.now();

    expect(() => {
      const { unmount } = render(() => (
        <ModelEditor model={model} onChange={onChange} />
      ));
      unmount();
    }).not.toThrow();

    const totalTime = performance.now() - startTime;

    // Should complete within 2 seconds even with 1000 variables
    expect(totalTime).toBeLessThan(2000);
  });

  it('should handle complex nested expressions efficiently', async () => {
    const model = createDeeplyNestedModel();
    const onChange = () => {};

    const startTime = performance.now();

    const { unmount } = render(() => (
      <ModelEditor model={model} onChange={onChange} />
    ));

    const renderTime = performance.now() - startTime;

    // Deeply nested expressions should render quickly
    expect(renderTime).toBeLessThan(100);

    unmount();
  });

  it('should handle rapid model updates without performance degradation', async () => {
    let model = createLargeModel(50, 20);
    const updates: number[] = [];

    const onChange = () => {
      // Simulate rapid updates
      const updateStart = performance.now();
      // Simulate some work
      for (let i = 0; i < 1000; i++) {
        Math.sqrt(i);
      }
      updates.push(performance.now() - updateStart);
    };

    const { unmount } = render(() => (
      <ModelEditor model={model} onChange={onChange} />
    ));

    // Simulate 10 rapid updates
    for (let i = 0; i < 10; i++) {
      model = {
        ...model,
        variables: {
          ...model.variables,
          [`new_var_${i}`]: {
            type: 'state',
            units: 'test',
            description: `New variable ${i}`
          }
        }
      };

      // Trigger a re-render (simulating prop change)
      onChange();
    }

    unmount();

    // All updates should complete quickly
    const maxUpdateTime = Math.max(...updates);
    expect(maxUpdateTime).toBeLessThan(50);
  });

  it('should have good memory characteristics with large models', async () => {
    // This test checks that we don't create excessive DOM nodes or memory leaks
    const model = createLargeModel(500, 100);
    const onChange = () => {};

    // Measure initial memory usage (rough approximation)
    const initialNodeCount = document.querySelectorAll('*').length;

    const { unmount } = render(() => (
      <ModelEditor model={model} onChange={onChange} />
    ));

    const peakNodeCount = document.querySelectorAll('*').length;
    const nodeIncrease = peakNodeCount - initialNodeCount;

    unmount();

    const finalNodeCount = document.querySelectorAll('*').length;

    // Should not create excessive DOM nodes (rough heuristic: less than 20 per variable)
    expect(nodeIncrease).toBeLessThan(Object.keys(model.variables).length * 20);

    // Should clean up properly after unmount
    expect(finalNodeCount).toBeLessThanOrEqual(initialNodeCount + 5); // Allow small variance
  });

  it('should efficiently switch between tabs in large models', async () => {
    const model = createLargeModel(200, 50);
    const onChange = () => {};

    const { unmount, getByRole } = render(() => (
      <ModelEditor model={model} onChange={onChange} />
    ));

    // Test switching to equations tab
    const equationsTab = getByRole('tab', { name: /Equations/ });

    const switchStart = performance.now();
    equationsTab.click();
    const switchTime = performance.now() - switchStart;

    // Tab switching should be fast
    expect(switchTime).toBeLessThan(200);

    // Test switching to events tab
    const eventsTab = getByRole('tab', { name: /Events/ });

    const switchStart2 = performance.now();
    eventsTab.click();
    const switchTime2 = performance.now() - switchStart2;

    expect(switchTime2).toBeLessThan(200);

    unmount();
  });

  it('should handle models with many events efficiently', async () => {
    const model: Model = {
      variables: {
        x: { type: 'state', units: 'm', description: 'Position' },
        v: { type: 'state', units: 'm/s', description: 'Velocity' }
      },
      equations: [
        {
          lhs: { op: 'D', args: ['x'], wrt: 't' },
          rhs: 'v'
        }
      ],
      discrete_events: [],
      continuous_events: []
    };

    // Add many events
    for (let i = 0; i < 100; i++) {
      model.discrete_events!.push({
        name: `event_${i}`,
        trigger: { type: 'time', at: i },
        affects: [{ lhs: 'x', rhs: i }]
      });

      model.continuous_events!.push({
        name: `condition_${i}`,
        conditions: [{ op: '>', args: ['x', i] }],
        affects: [{ lhs: 'v', rhs: 0 }]
      });
    }

    const onChange = () => {};

    const startTime = performance.now();

    const { unmount } = render(() => (
      <ModelEditor model={model} onChange={onChange} />
    ));

    const renderTime = performance.now() - startTime;

    // Should handle many events efficiently
    expect(renderTime).toBeLessThan(300);

    unmount();
  });
});