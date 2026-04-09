/**
 * Editor Responsiveness Performance Benchmarks
 *
 * Performance tests for interactive editor components to ensure responsive
 * user experience under various load conditions and complex expressions.
 */

import { test, expect } from '@playwright/test';

test.describe('Editor Responsiveness Benchmarks', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/demo/performance-test');
  });

  test.describe('Expression Rendering Performance', () => {
    test('should render simple expressions under 16ms (60fps)', async ({ page }) => {
      const simpleExpressions = [
        42,
        'temperature',
        { op: '+', args: [1, 2] },
        { op: '*', args: ['x', 'y'] },
        { op: '/', args: [1, 2] }
      ];

      for (const expr of simpleExpressions) {
        const renderTime = await page.evaluate((expression) => {
          const start = performance.now();

          const container = document.getElementById('render-test-container');
          container.innerHTML = `
            <esm-expression-node
              expression='${JSON.stringify(expression)}'
              path='["test"]'>
            </esm-expression-node>
          `;

          // Wait for component to fully render
          return new Promise(resolve => {
            requestAnimationFrame(() => {
              resolve(performance.now() - start);
            });
          });
        }, expr);

        expect(renderTime).toBeLessThan(16); // 60fps target
      }
    });

    test('should render complex nested expressions under 50ms', async ({ page }) => {
      const complexExpression = {
        op: '+',
        args: [
          {
            op: '*',
            args: [
              { op: 'sin', args: [{ op: '/', args: ['x', 'y'] }] },
              { op: '^', args: ['z', 2] }
            ]
          },
          {
            op: 'log',
            args: [
              { op: '+', args: ['a', 'b', 'c'] }
            ]
          },
          {
            op: '/',
            args: [
              { op: '*', args: [3.14159, 'r', 'r'] },
              { op: '+', args: [1, { op: 'exp', args: [{ op: '-', args: ['t'] }] }] }
            ]
          }
        ]
      };

      const renderTime = await page.evaluate((expression) => {
        const start = performance.now();

        const container = document.getElementById('render-test-container');
        container.innerHTML = `
          <esm-expression-node
            expression='${JSON.stringify(expression)}'
            path='["test"]'>
          </esm-expression-node>
        `;

        return new Promise(resolve => {
          requestAnimationFrame(() => {
            resolve(performance.now() - start);
          });
        });
      }, complexExpression);

      expect(renderTime).toBeLessThan(50);
    });

    test('should maintain performance with many expressions on screen', async ({ page }) => {
      const numExpressions = 100;
      const expressions = Array.from({ length: numExpressions }, (_, i) => ({
        op: '+',
        args: [i, { op: '*', args: ['x', i + 1] }]
      }));

      const totalRenderTime = await page.evaluate((expressions) => {
        const start = performance.now();

        const container = document.getElementById('render-test-container');
        const html = expressions.map((expr, i) => `
          <esm-expression-node
            expression='${JSON.stringify(expr)}'
            path='["test", ${i}]'>
          </esm-expression-node>
        `).join('');

        container.innerHTML = html;

        return new Promise(resolve => {
          // Wait for all components to render
          setTimeout(() => {
            resolve(performance.now() - start);
          }, 100);
        });
      }, expressions);

      // Should render 100 expressions in under 500ms
      expect(totalRenderTime).toBeLessThan(500);
    });
  });

  test.describe('Interaction Response Time', () => {
    test('should respond to clicks under 100ms', async ({ page }) => {
      await page.setContent(`
        <esm-expression-node
          id="click-test"
          expression='42'
          path='["test"]'>
        </esm-expression-node>
      `);

      const responseTime = await page.evaluate(async () => {
        const start = performance.now();
        const component = document.getElementById('click-test');

        component.click();

        // Wait for selection state to update
        await new Promise(resolve => requestAnimationFrame(resolve));

        return performance.now() - start;
      });

      expect(responseTime).toBeLessThan(100);
    });

    test('should start editing mode quickly on double-click', async ({ page }) => {
      await page.setContent(`
        <esm-expression-node
          id="edit-test"
          expression='42'
          path='["test"]'
          allow-editing="true">
        </esm-expression-node>
      `);

      const webComponent = page.locator('#edit-test');

      const startTime = Date.now();
      await webComponent.dblclick();

      const editInput = page.locator('.esm-expression-edit');
      await expect(editInput).toBeVisible();

      const responseTime = Date.now() - startTime;
      expect(responseTime).toBeLessThan(200);
    });

    test('should handle rapid hover events without lag', async ({ page }) => {
      const expressions = Array.from({ length: 10 }, (_, i) => `var_${i}`);

      const html = expressions.map((expr, i) => `
        <esm-expression-node
          id="hover-test-${i}"
          expression='"${expr}"'
          path='["test", ${i}]'>
        </esm-expression-node>
      `).join('');

      await page.setContent(html);

      const hoverTime = await page.evaluate(async () => {
        const start = performance.now();
        const nodes = document.querySelectorAll('[id^="hover-test-"]');

        for (const node of nodes) {
          node.dispatchEvent(new MouseEvent('mouseenter'));
          await new Promise(resolve => requestAnimationFrame(resolve));
          node.dispatchEvent(new MouseEvent('mouseleave'));
        }

        return performance.now() - start;
      });

      // Should handle 10 rapid hover events in under 100ms
      expect(hoverTime).toBeLessThan(100);
    });
  });

  test.describe('Model Editor Performance', () => {
    test('should load large models efficiently', async ({ page }) => {
      const largeModel = {
        variables: {},
        equations: [],
        reaction_systems: {}
      };

      // Create 200 variables
      for (let i = 0; i < 200; i++) {
        largeModel.variables[`var_${i}`] = {
          name: `var_${i}`,
          type: i % 3 === 0 ? 'state' : i % 3 === 1 ? 'parameter' : 'observed',
          units: 'mol/L',
          description: `Variable ${i}`
        };
      }

      // Create 50 equations
      for (let i = 0; i < 50; i++) {
        largeModel.equations.push({
          lhs: `var_${i}`,
          rhs: { op: '*', args: [`var_${i + 50}`, `var_${i + 100}`] }
        });
      }

      const loadTime = await page.evaluate((model) => {
        const start = performance.now();

        const container = document.getElementById('render-test-container');
        container.innerHTML = `
          <esm-model-editor
            model='${JSON.stringify(model)}'
            allow-editing="true">
          </esm-model-editor>
        `;

        return new Promise(resolve => {
          // Wait for model to fully load
          setTimeout(() => {
            resolve(performance.now() - start);
          }, 1000);
        });
      }, largeModel);

      // Should load large model in under 1 second
      expect(loadTime).toBeLessThan(1000);
    });

    test('should handle model updates without blocking UI', async ({ page }) => {
      const baseModel = {
        variables: { temp: { name: 'temp', type: 'state' } },
        equations: []
      };

      await page.setContent(`
        <esm-model-editor
          id="update-test"
          model='${JSON.stringify(baseModel)}'
          allow-editing="true">
        </esm-model-editor>
      `);

      // Measure time for 20 model updates
      const updateTime = await page.evaluate(async () => {
        const start = performance.now();
        const component = document.getElementById('update-test');

        for (let i = 0; i < 20; i++) {
          const model = {
            variables: {},
            equations: []
          };

          // Add increasing number of variables
          for (let j = 0; j < i + 1; j++) {
            model.variables[`var_${j}`] = {
              name: `var_${j}`,
              type: 'state'
            };
          }

          component.setAttribute('model', JSON.stringify(model));
          await new Promise(resolve => requestAnimationFrame(resolve));
        }

        return performance.now() - start;
      });

      // Should handle 20 updates in under 500ms
      expect(updateTime).toBeLessThan(500);
    });
  });

  test.describe('Coupling Graph Performance', () => {
    test('should render large coupling graphs efficiently', async ({ page }) => {
      const largeCouplingGraph = {
        models: {},
        reaction_systems: {},
        coupling: []
      };

      // Create 50 models
      for (let i = 0; i < 50; i++) {
        largeCouplingGraph.models[`Model_${i}`] = {
          variables: { [`var_${i}`]: { name: `var_${i}`, type: 'state' } },
          equations: []
        };
      }

      // Create 100 coupling entries
      for (let i = 0; i < 100; i++) {
        largeCouplingGraph.coupling.push({
          source: { model: `Model_${i % 50}`, variable: `var_${i % 50}` },
          target: { model: `Model_${(i + 1) % 50}`, variable: `var_${(i + 1) % 50}` },
          type: 'direct'
        });
      }

      const renderTime = await page.evaluate((graph) => {
        const start = performance.now();

        const container = document.getElementById('render-test-container');
        container.innerHTML = `
          <esm-coupling-graph
            esm-file='${JSON.stringify(graph)}'
            width="800"
            height="600">
          </esm-coupling-graph>
        `;

        return new Promise(resolve => {
          // Wait for D3 layout to complete
          setTimeout(() => {
            resolve(performance.now() - start);
          }, 2000);
        });
      }, largeCouplingGraph);

      // Should render large graph in under 2 seconds
      expect(renderTime).toBeLessThan(2000);
    });

    test('should maintain interactivity during force simulation', async ({ page }) => {
      const mediumGraph = {
        models: {},
        coupling: []
      };

      // Create 20 models with coupling
      for (let i = 0; i < 20; i++) {
        mediumGraph.models[`Model_${i}`] = {
          variables: { [`var_${i}`]: { name: `var_${i}`, type: 'state' } },
          equations: []
        };
      }

      for (let i = 0; i < 30; i++) {
        mediumGraph.coupling.push({
          source: { model: `Model_${i % 20}`, variable: `var_${i % 20}` },
          target: { model: `Model_${(i + 5) % 20}`, variable: `var_${(i + 5) % 20}` },
          type: 'direct'
        });
      }

      await page.setContent(`
        <esm-coupling-graph
          id="interactive-graph"
          esm-file='${JSON.stringify(mediumGraph)}'
          width="600"
          height="400"
          interactive="true">
        </esm-coupling-graph>
      `);

      // Wait for initial render
      await page.waitForTimeout(1000);

      // Test node interaction during simulation
      const graphSvg = page.locator('#interactive-graph svg');
      const firstNode = graphSvg.locator('circle').first();

      const interactionTime = await page.evaluate(async () => {
        const start = performance.now();

        // Simulate node click during force simulation
        const node = document.querySelector('#interactive-graph svg circle');
        node.click();

        await new Promise(resolve => requestAnimationFrame(resolve));

        return performance.now() - start;
      });

      // Should respond to interaction quickly even during simulation
      expect(interactionTime).toBeLessThan(50);
    });
  });

  test.describe('Memory Usage Benchmarks', () => {
    test('should not leak memory during expression updates', async ({ page }) => {
      const initialMemory = await page.evaluate(() => {
        // Force garbage collection if available
        if (window.gc) window.gc();
        return performance.memory ? performance.memory.usedJSHeapSize : 0;
      });

      // Create and destroy many expression nodes
      for (let i = 0; i < 50; i++) {
        await page.evaluate((iteration) => {
          const container = document.getElementById('render-test-container');

          // Create 20 expression nodes
          const html = Array.from({ length: 20 }, (_, j) => `
            <esm-expression-node
              expression='${JSON.stringify({ op: '+', args: [iteration, j] })}'
              path='["test", ${iteration}, ${j}]'>
            </esm-expression-node>
          `).join('');

          container.innerHTML = html;
        }, i);

        // Clear container
        await page.evaluate(() => {
          document.getElementById('render-test-container').innerHTML = '';
        });

        if (i % 10 === 0) {
          await page.waitForTimeout(10); // Allow cleanup
        }
      }

      const finalMemory = await page.evaluate(() => {
        // Force garbage collection if available
        if (window.gc) window.gc();
        return performance.memory ? performance.memory.usedJSHeapSize : 0;
      });

      // Memory usage should not grow significantly (allow 10MB increase)
      const memoryIncrease = finalMemory - initialMemory;
      expect(memoryIncrease).toBeLessThan(10 * 1024 * 1024); // 10MB
    });
  });

  test.describe('Stress Testing', () => {
    test('should handle rapid user interactions without crashes', async ({ page }) => {
      await page.setContent(`
        <esm-expression-node
          id="stress-test"
          expression='42'
          path='["test"]'
          allow-editing="true">
        </esm-expression-node>
      `);

      const webComponent = page.locator('#stress-test');

      // Perform many rapid interactions
      for (let i = 0; i < 20; i++) {
        await webComponent.click();
        await webComponent.hover();
        if (i % 5 === 0) {
          await webComponent.dblclick();
          await page.keyboard.press('Escape');
        }
      }

      // Component should still be functional
      await expect(webComponent).toBeVisible();
      await expect(webComponent).toContainText('42');
    });

    test('should handle deeply nested expressions without stack overflow', async ({ page }) => {
      // Create deeply nested expression (50 levels)
      let deepExpression = 'x';
      for (let i = 0; i < 50; i++) {
        deepExpression = { op: '+', args: [deepExpression, 1] };
      }

      const renderTime = await page.evaluate((expression) => {
        const start = performance.now();

        const container = document.getElementById('render-test-container');
        container.innerHTML = `
          <esm-expression-node
            expression='${JSON.stringify(expression)}'
            path='["test"]'>
          </esm-expression-node>
        `;

        return new Promise(resolve => {
          setTimeout(() => {
            resolve(performance.now() - start);
          }, 100);
        });
      }, deepExpression);

      // Should handle deep nesting without crashing
      expect(renderTime).toBeLessThan(200);
    });
  });
});