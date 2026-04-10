/**
 * SolidJS Web Component Export Tests
 *
 * Tests the export of SolidJS components as standard web components,
 * including event handling, props validation, and cross-boundary interactions.
 */

import { test, expect } from '@playwright/test';

test.describe('SolidJS Web Component Export', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/demo/web-components');
  });

  test.describe('Component Export and Registration', () => {
    test('should register ExpressionNode as web component', async ({ page }) => {
      // Check that the web component is registered
      const isRegistered = await page.evaluate(() => {
        return customElements.get('esm-expression-node') !== undefined;
      });

      expect(isRegistered).toBe(true);
    });

    test('should register ModelEditor as web component', async ({ page }) => {
      const isRegistered = await page.evaluate(() => {
        return customElements.get('esm-model-editor') !== undefined;
      });

      expect(isRegistered).toBe(true);
    });

    test('should register CouplingGraph as web component', async ({ page }) => {
      const isRegistered = await page.evaluate(() => {
        return customElements.get('esm-coupling-graph') !== undefined;
      });

      expect(isRegistered).toBe(true);
    });
  });

  test.describe('Props and Attributes Validation', () => {
    test('should accept expression prop as attribute', async ({ page }) => {
      await page.setContent(`
        <esm-expression-node
          expression='{"op": "+", "args": [1, 2]}'
          path='["test"]'
          allow-editing="true">
        </esm-expression-node>
      `);

      const webComponent = page.locator('esm-expression-node');
      await expect(webComponent).toBeVisible();

      // Check that the expression is rendered
      const operatorElement = webComponent.locator('.esm-operator');
      await expect(operatorElement).toContainText('+');
    });

    test('should validate required attributes', async ({ page }) => {
      await page.setContent(`
        <esm-expression-node></esm-expression-node>
      `);

      const webComponent = page.locator('esm-expression-node');

      // Should show error state for missing required props
      const errorState = webComponent.locator('.error-state');
      await expect(errorState).toContainText('Missing required attribute: expression');
    });

    test('should handle complex model data as JSON attribute', async ({ page }) => {
      const modelData = {
        variables: {
          temperature: { name: 'temperature', type: 'state', units: 'K' }
        },
        equations: [
          { lhs: 'temperature', rhs: 300 }
        ]
      };

      await page.setContent(`
        <esm-model-editor
          model='${JSON.stringify(modelData)}'
          allow-editing="true">
        </esm-model-editor>
      `);

      const webComponent = page.locator('esm-model-editor');
      const variablesList = webComponent.locator('[data-testid="variables-list"]');

      await expect(variablesList).toContainText('temperature');
    });

    test('should convert boolean attributes correctly', async ({ page }) => {
      await page.setContent(`
        <esm-expression-node
          expression='42'
          path='["test"]'
          allow-editing="true"
          is-selected="false">
        </esm-expression-node>
      `);

      const webComponent = page.locator('esm-expression-node');

      // Should not have selected class since is-selected="false"
      await expect(webComponent).not.toHaveClass(/selected/);
    });
  });

  test.describe('Event Handling Across Component Boundaries', () => {
    test('should emit custom events for user interactions', async ({ page }) => {
      await page.setContent(`
        <esm-expression-node
          expression='42'
          path='["test"]'
          allow-editing="true">
        </esm-expression-node>
      `);

      const webComponent = page.locator('esm-expression-node');

      // Set up event listener
      await page.evaluate(() => {
        window.capturedEvents = [];
        document.querySelector('esm-expression-node').addEventListener('expressionSelect', (e) => {
          window.capturedEvents.push({ type: 'select', detail: e.detail });
        });
      });

      await webComponent.click();

      const capturedEvents = await page.evaluate(() => window.capturedEvents);
      expect(capturedEvents).toHaveLength(1);
      expect(capturedEvents[0].type).toBe('select');
      expect(capturedEvents[0].detail.path).toEqual(['test']);
    });

    test('should emit hover events for variable highlighting', async ({ page }) => {
      await page.setContent(`
        <esm-expression-node
          expression='"temperature"'
          path='["test"]'>
        </esm-expression-node>
      `);

      const webComponent = page.locator('esm-expression-node');

      await page.evaluate(() => {
        window.hoverEvents = [];
        document.querySelector('esm-expression-node').addEventListener('variableHover', (e) => {
          window.hoverEvents.push(e.detail);
        });
      });

      await webComponent.hover();

      const hoverEvents = await page.evaluate(() => window.hoverEvents);
      expect(hoverEvents).toHaveLength(1);
      expect(hoverEvents[0].variableName).toBe('temperature');
    });

    test('should handle model change events', async ({ page }) => {
      const modelData = {
        variables: { temp: { name: 'temp', type: 'state' } },
        equations: []
      };

      await page.setContent(`
        <esm-model-editor
          model='${JSON.stringify(modelData)}'
          allow-editing="true">
        </esm-model-editor>
      `);

      const webComponent = page.locator('esm-model-editor');

      await page.evaluate(() => {
        window.modelChanges = [];
        document.querySelector('esm-model-editor').addEventListener('modelChange', (e) => {
          window.modelChanges.push(e.detail);
        });
      });

      // Trigger a change in the model
      const addButton = webComponent.locator('[data-testid="add-variable-button"]');
      await addButton.click();
      await page.fill('[data-testid="variable-name-input"]', 'pressure');
      await page.click('[data-testid="save-variable-button"]');

      const modelChanges = await page.evaluate(() => window.modelChanges);
      expect(modelChanges.length).toBeGreaterThan(0);
      expect(modelChanges[0].variables).toHaveProperty('pressure');
    });
  });

  test.describe('CSS Styling Isolation', () => {
    test('should isolate component styles using shadow DOM', async ({ page }) => {
      await page.setContent(`
        <style>
          .esm-expression-node { color: red !important; }
        </style>
        <esm-expression-node
          expression='42'
          path='["test"]'>
        </esm-expression-node>
      `);

      const webComponent = page.locator('esm-expression-node');

      // Check that external styles don't affect the component
      const shadowContent = await page.evaluate(() => {
        const component = document.querySelector('esm-expression-node');
        return component.shadowRoot.innerHTML;
      });

      expect(shadowContent).toContain('<style>'); // Component has its own styles

      // External red color should not apply
      const computedColor = await webComponent.evaluate(el =>
        getComputedStyle(el.shadowRoot.querySelector('.esm-expression-node')).color
      );
      expect(computedColor).not.toBe('rgb(255, 0, 0)'); // Not red
    });

    test('should allow CSS custom properties for theming', async ({ page }) => {
      await page.setContent(`
        <style>
          esm-expression-node {
            --esm-primary-color: blue;
            --esm-font-size: 18px;
          }
        </style>
        <esm-expression-node
          expression='42'
          path='["test"]'>
        </esm-expression-node>
      `);

      const webComponent = page.locator('esm-expression-node');

      // CSS custom properties should penetrate shadow DOM
      const fontSize = await webComponent.evaluate(el => {
        const numberElement = el.shadowRoot.querySelector('.esm-number');
        return getComputedStyle(numberElement).fontSize;
      });

      expect(fontSize).toBe('18px');
    });

    test('should not leak internal styles to document', async ({ page }) => {
      await page.setContent(`
        <esm-expression-node
          expression='42'
          path='["test"]'>
        </esm-expression-node>
        <div class="esm-number">External element</div>
      `);

      const externalElement = page.locator('div.esm-number');

      // External element should not get component styles
      const computedStyles = await externalElement.evaluate(el => {
        const styles = getComputedStyle(el);
        return {
          backgroundColor: styles.backgroundColor,
          padding: styles.padding
        };
      });

      // Should have default styles, not component styles
      expect(computedStyles.backgroundColor).toBe('rgba(0, 0, 0, 0)'); // transparent
    });
  });

  test.describe('Performance Under Rapid State Changes', () => {
    test('should handle rapid expression updates without lag', async ({ page }) => {
      await page.setContent(`
        <esm-expression-node
          id="perf-test"
          expression='0'
          path='["test"]'
          allow-editing="true">
        </esm-expression-node>
      `);

      const webComponent = page.locator('#perf-test');

      // Measure time for 100 rapid updates
      const startTime = await page.evaluate(async () => {
        const start = performance.now();
        const component = document.getElementById('perf-test');

        for (let i = 0; i < 100; i++) {
          component.setAttribute('expression', i.toString());
          // Small delay to simulate real updates
          await new Promise(resolve => requestAnimationFrame(resolve));
        }

        return performance.now() - start;
      });

      // Should complete in reasonable time (less than 1 second)
      expect(startTime).toBeLessThan(1000);

      // Final value should be correct
      await expect(webComponent).toContainText('99');
    });

    test('should batch model updates efficiently', async ({ page }) => {
      const modelData = {
        variables: {},
        equations: []
      };

      await page.setContent(`
        <esm-model-editor
          id="model-perf-test"
          model='${JSON.stringify(modelData)}'
          allow-editing="true">
        </esm-model-editor>
      `);

      // Add many variables rapidly
      const updateTime = await page.evaluate(async () => {
        const start = performance.now();
        const component = document.getElementById('model-perf-test');

        for (let i = 0; i < 50; i++) {
          const newModel = {
            variables: {},
            equations: []
          };

          // Add variables
          for (let j = 0; j <= i; j++) {
            newModel.variables[`var_${j}`] = {
              name: `var_${j}`,
              type: 'state'
            };
          }

          component.setAttribute('model', JSON.stringify(newModel));
          await new Promise(resolve => requestAnimationFrame(resolve));
        }

        return performance.now() - start;
      });

      // Should handle batched updates efficiently
      expect(updateTime).toBeLessThan(2000);
    });

    test('should maintain responsiveness during complex rendering', async ({ page }) => {
      // Create a complex expression tree
      const complexExpression = {
        op: '+',
        args: [
          {
            op: '*',
            args: [
              { op: 'sin', args: ['x'] },
              { op: '/', args: ['a', 'b'] }
            ]
          },
          {
            op: '^',
            args: [
              { op: 'log', args: ['y'] },
              2
            ]
          }
        ]
      };

      await page.setContent(`
        <esm-expression-node
          expression='${JSON.stringify(complexExpression)}'
          path='["test"]'
          allow-editing="true">
        </esm-expression-node>
      `);

      const webComponent = page.locator('esm-expression-node');

      // Should render complex expression quickly
      await expect(webComponent.locator('.esm-function-name')).toHaveCount(2); // sin and log
      await expect(webComponent.locator('.esm-fraction')).toHaveCount(1); // a/b
      await expect(webComponent.locator('.esm-exponent')).toHaveCount(1); // ^2

      // Should remain interactive
      const sinFunction = webComponent.locator('.esm-function-name:has-text("sin")');
      await sinFunction.click();

      // Should respond to click quickly
      await expect(webComponent).toHaveClass(/selected/);
    });
  });

  test.describe('Cross-browser Compatibility', () => {
    test('should work in different browsers', async ({ page }) => {
      await page.setContent(`
        <esm-expression-node
          expression='42'
          path='["test"]'>
        </esm-expression-node>
      `);

      const webComponent = page.locator('esm-expression-node');
      await expect(webComponent).toBeVisible();
      await expect(webComponent).toContainText('42');
    });

    test('should handle browser-specific event differences', async ({ page }) => {
      await page.setContent(`
        <esm-expression-node
          expression='42'
          path='["test"]'
          allow-editing="true">
        </esm-expression-node>
      `);

      const webComponent = page.locator('esm-expression-node');

      // Test both double-click and keyboard interaction
      await webComponent.dblclick();
      const editInput = page.locator('.esm-expression-edit');
      await expect(editInput).toBeVisible();

      await page.keyboard.press('Escape');
      await expect(editInput).not.toBeVisible();
    });
  });
});