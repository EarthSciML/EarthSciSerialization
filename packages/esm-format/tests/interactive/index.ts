/**
 * Interactive Test Fixtures Index
 *
 * Central export for all interactive test fixtures and utilities.
 * This provides a convenient way to access test data and helper functions
 * from the interactive test suite.
 */

import expressionInteractionFixtures from './fixtures/expression-interaction-fixtures.json';
import undoRedoScenarios from './fixtures/undo-redo-scenarios.json';
import dragDropTestCases from './fixtures/drag-drop-test-cases.json';
import accessibilityInteractionFixtures from './fixtures/accessibility-interaction-fixtures.json';

// Test data fixtures
export const expressionTestCases = {
  simple: {
    number: 42,
    variable: 'temperature',
    scientific: 1.5e6
  },

  operators: {
    addition: { op: '+', args: [1, 2] },
    multiplication: { op: '*', args: ['x', 'y'] },
    division: { op: '/', args: ['numerator', 'denominator'] },
    power: { op: '^', args: ['base', 'exponent'] }
  },

  functions: {
    sine: { op: 'sin', args: ['x'] },
    logarithm: { op: 'log', args: ['value'] },
    squareRoot: { op: 'sqrt', args: [{ op: '+', args: ['x', 'y'] }] }
  },

  complex: {
    nested: {
      op: '+',
      args: [
        { op: '*', args: [{ op: 'sin', args: ['x'] }, { op: '/', args: ['a', 'b'] }] },
        { op: '^', args: [{ op: 'log', args: ['y'] }, 2] }
      ]
    },

    deeplyNested: (depth: number) => {
      let expr: any = 'x';
      for (let i = 0; i < depth; i++) {
        expr = { op: '+', args: [expr, i] };
      }
      return expr;
    }
  }
};

export const modelTestData = {
  simple: {
    variables: {
      temperature: { name: 'temperature', type: 'state', units: 'K' },
      pressure: { name: 'pressure', type: 'parameter', units: 'Pa' }
    },
    equations: [
      { lhs: 'temperature', rhs: 300 }
    ]
  },

  atmospheric: {
    variables: {
      O3: { name: 'O3', type: 'state', units: 'mol/L', description: 'Ozone concentration' },
      NO: { name: 'NO', type: 'state', units: 'mol/L', description: 'Nitric oxide concentration' },
      NO2: { name: 'NO2', type: 'state', units: 'mol/L', description: 'Nitrogen dioxide concentration' },
      temperature: { name: 'temperature', type: 'parameter', units: 'K', description: 'Air temperature' },
      pressure: { name: 'pressure', type: 'parameter', units: 'Pa', description: 'Air pressure' }
    },
    equations: [
      {
        lhs: { op: 'D', args: ['O3'], wrt: 't' },
        rhs: { op: '-', args: [{ op: '*', args: ['k1', 'O3'] }] }
      },
      {
        lhs: { op: 'D', args: ['NO'], wrt: 't' },
        rhs: { op: '+', args: [
          { op: '*', args: ['k2', 'NO2'] },
          { op: '*', args: ['-k3', 'NO', 'O3'] }
        ]}
      }
    ],
    reactions: [
      {
        reactants: [{ species: 'NO', coefficient: 1 }, { species: 'O3', coefficient: 1 }],
        products: [{ species: 'NO2', coefficient: 1 }, { species: 'O2', coefficient: 1 }],
        rate_constant: 'k3'
      }
    ]
  },

  large: (numVars: number, numEqs: number) => {
    const variables: Record<string, any> = {};
    const equations: any[] = [];

    // Generate variables
    for (let i = 0; i < numVars; i++) {
      variables[`var_${i}`] = {
        name: `var_${i}`,
        type: i % 3 === 0 ? 'state' : i % 3 === 1 ? 'parameter' : 'observed',
        units: 'mol/L',
        description: `Generated variable ${i}`
      };
    }

    // Generate equations
    for (let i = 0; i < numEqs && i < numVars - 1; i++) {
      equations.push({
        lhs: `var_${i}`,
        rhs: { op: '*', args: [`var_${i + 1}`, 'k'] }
      });
    }

    return { variables, equations };
  }
};

export const couplingTestData = {
  simple: {
    models: {
      Transport: {
        variables: { concentration: { name: 'concentration', type: 'state' } }
      },
      Chemistry: {
        variables: { chemical_amount: { name: 'chemical_amount', type: 'state' } }
      }
    },
    coupling: [
      {
        source: { model: 'Transport', variable: 'concentration' },
        target: { model: 'Chemistry', variable: 'chemical_amount' },
        type: 'direct'
      }
    ]
  },

  complex: (numModels: number, numCouplings: number) => {
    const models: Record<string, any> = {};
    const coupling: any[] = [];

    // Generate models
    for (let i = 0; i < numModels; i++) {
      models[`Model_${i}`] = {
        variables: {
          [`var_${i}`]: { name: `var_${i}`, type: 'state' }
        }
      };
    }

    // Generate couplings
    for (let i = 0; i < numCouplings; i++) {
      coupling.push({
        source: { model: `Model_${i % numModels}`, variable: `var_${i % numModels}` },
        target: { model: `Model_${(i + 1) % numModels}`, variable: `var_${(i + 1) % numModels}` },
        type: i % 2 === 0 ? 'direct' : 'interpolated'
      });
    }

    return { models, coupling };
  }
};

// Test helper functions
export const testHelpers = {
  /**
   * Generate a data-testid selector
   */
  testId: (id: string) => `[data-testid="${id}"]`,

  /**
   * Wait for element to be visible and stable
   */
  waitForStable: async (page: any, selector: string, timeout = 5000) => {
    await page.waitForSelector(selector, { state: 'visible', timeout });
    await page.waitForTimeout(100); // Allow for any animations
  },

  /**
   * Measure performance of an operation
   */
  measurePerformance: async (page: any, operation: () => Promise<void>) => {
    const start = await page.evaluate(() => performance.now());
    await operation();
    const end = await page.evaluate(() => performance.now());
    return end - start;
  },

  /**
   * Check accessibility of an element
   */
  checkAccessibility: async (page: any, selector: string) => {
    const element = page.locator(selector);

    // Check basic accessibility attributes
    const hasTabIndex = await element.evaluate(el => el.hasAttribute('tabindex'));
    const hasAriaLabel = await element.evaluate(el => el.hasAttribute('aria-label'));
    const hasRole = await element.evaluate(el => el.hasAttribute('role'));

    return {
      focusable: hasTabIndex || await element.evaluate(el =>
        ['button', 'input', 'select', 'textarea', 'a'].includes(el.tagName.toLowerCase())
      ),
      labeled: hasAriaLabel || await element.evaluate(el => {
        const label = document.querySelector(`label[for="${el.id}"]`);
        return !!label;
      }),
      hasRole
    };
  }
};

// Performance benchmarks
export const performanceTargets = {
  simpleExpressionRender: 16, // ms (60fps)
  complexExpressionRender: 50, // ms
  userInteractionResponse: 100, // ms
  largeModelLoad: 1000, // ms
  memoryLeakThreshold: 10 * 1024 * 1024, // bytes (10MB)

  // Stress test parameters
  stressTest: {
    rapidInteractions: 20,
    deepNestingLevels: 50,
    largeModelVariables: 200,
    largeModelEquations: 50,
    manyExpressionsCount: 100
  }
};

// Accessibility standards
export const accessibilityStandards = {
  wcag21AA: {
    contrastRatio: 4.5,
    focusIndicatorMinSize: 2, // px
    keyboardNavigation: true,
    screenReaderSupport: true
  },

  ariaRoles: {
    button: 'button',
    dialog: 'dialog',
    alertDialog: 'alertdialog',
    alert: 'alert',
    status: 'status',
    log: 'log'
  },

  ariaProperties: {
    label: 'aria-label',
    describedBy: 'aria-describedby',
    live: 'aria-live',
    atomic: 'aria-atomic',
    pressed: 'aria-pressed'
  }
};

// Interactive expression editing fixtures
export const interactiveExpressionFixtures = expressionInteractionFixtures;
export const undoRedoFixtures = undoRedoScenarios;
export const dragDropFixtures = dragDropTestCases;
export const accessibilityFixtures = accessibilityInteractionFixtures;

export default {
  expressionTestCases,
  modelTestData,
  couplingTestData,
  testHelpers,
  performanceTargets,
  accessibilityStandards,
  interactiveExpressionFixtures,
  undoRedoFixtures,
  dragDropFixtures,
  accessibilityFixtures
};