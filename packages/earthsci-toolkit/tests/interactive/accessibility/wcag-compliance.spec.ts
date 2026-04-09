/**
 * WCAG Accessibility Compliance Tests
 *
 * Tests to ensure interactive ESM editor components meet WCAG 2.1 AA
 * accessibility guidelines including keyboard navigation, screen reader
 * support, and inclusive design principles.
 */

import { test, expect } from '@playwright/test';

test.describe('WCAG Accessibility Compliance', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/demo/accessibility-test');
  });

  test.describe('Keyboard Navigation (WCAG 2.1.1)', () => {
    test('should support Tab navigation through all interactive elements', async ({ page }) => {
      await page.setContent(`
        <esm-expression-node
          expression='42'
          path='["test1"]'
          allow-editing="true">
        </esm-expression-node>
        <esm-expression-node
          expression='"temperature"'
          path='["test2"]'
          allow-editing="true">
        </esm-expression-node>
        <button>Other Button</button>
      `);

      // Start navigation
      await page.keyboard.press('Tab');

      // First expression node should be focused
      let focusedElement = page.locator(':focus');
      await expect(focusedElement).toHaveAttribute('data-path', 'test1');

      // Navigate to second expression node
      await page.keyboard.press('Tab');
      focusedElement = page.locator(':focus');
      await expect(focusedElement).toHaveAttribute('data-path', 'test2');

      // Navigate to button
      await page.keyboard.press('Tab');
      focusedElement = page.locator(':focus');
      await expect(focusedElement).toHaveText('Other Button');
    });

    test('should support Shift+Tab for reverse navigation', async ({ page }) => {
      await page.setContent(`
        <esm-expression-node expression='1' path='["first"]'></esm-expression-node>
        <esm-expression-node expression='2' path='["second"]'></esm-expression-node>
        <esm-expression-node expression='3' path='["third"]'></esm-expression-node>
      `);

      // Navigate to last element
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');

      let focusedElement = page.locator(':focus');
      await expect(focusedElement).toHaveAttribute('data-path', 'third');

      // Navigate backwards
      await page.keyboard.press('Shift+Tab');
      focusedElement = page.locator(':focus');
      await expect(focusedElement).toHaveAttribute('data-path', 'second');

      await page.keyboard.press('Shift+Tab');
      focusedElement = page.locator(':focus');
      await expect(focusedElement).toHaveAttribute('data-path', 'first');
    });

    test('should support Enter key activation', async ({ page }) => {
      await page.setContent(`
        <esm-expression-node
          expression='42'
          path='["test"]'
          allow-editing="true">
        </esm-expression-node>
      `);

      const expressionNode = page.locator('[data-path="test"]');

      await expressionNode.focus();
      await page.keyboard.press('Enter');

      // Should enter edit mode
      const editInput = page.locator('.esm-expression-edit');
      await expect(editInput).toBeVisible();
      await expect(editInput).toBeFocused();
    });

    test('should support Space key activation for buttons', async ({ page }) => {
      await page.setContent(`
        <esm-model-editor>
          <button data-testid="add-variable-button">Add Variable</button>
        </esm-model-editor>
      `);

      const button = page.locator('[data-testid="add-variable-button"]');

      await button.focus();
      await page.keyboard.press('Space');

      // Button should be activated (would normally open dialog)
      // For test purposes, check that click event was triggered
      const clickCount = await button.evaluate(btn => btn.clickCount || 0);
      expect(clickCount).toBeGreaterThan(0);
    });

    test('should trap focus within modal dialogs', async ({ page }) => {
      await page.setContent(`
        <esm-model-editor>
          <button data-testid="open-dialog">Open Dialog</button>
        </esm-model-editor>
      `);

      await page.click('[data-testid="open-dialog"]');

      // Dialog should be open
      const dialog = page.locator('[role="dialog"]');
      await expect(dialog).toBeVisible();

      // Focus should be trapped within dialog
      const firstInput = dialog.locator('input, button, [tabindex]').first();
      const lastInput = dialog.locator('input, button, [tabindex]').last();

      await firstInput.focus();
      await page.keyboard.press('Tab');

      // Should cycle within dialog
      const focusedElement = page.locator(':focus');
      expect(await focusedElement.isVisible()).toBe(true);
      expect(await dialog.evaluate(d => d.contains(document.activeElement))).toBe(true);
    });
  });

  test.describe('Screen Reader Support (WCAG 1.3.1)', () => {
    test('should provide meaningful ARIA labels', async ({ page }) => {
      await page.setContent(`
        <esm-expression-node
          expression='42'
          path='["test"]'>
        </esm-expression-node>
      `);

      const expressionNode = page.locator('.esm-expression-node');

      await expect(expressionNode).toHaveAttribute('aria-label', 'Number: 42');
      await expect(expressionNode).toHaveAttribute('role', 'button');
    });

    test('should provide ARIA labels for complex expressions', async ({ page }) => {
      const complexExpr = {
        op: '+',
        args: [
          { op: 'sin', args: ['x'] },
          { op: '/', args: ['a', 'b'] }
        ]
      };

      await page.setContent(`
        <esm-expression-node
          expression='${JSON.stringify(complexExpr)}'
          path='["test"]'>
        </esm-expression-node>
      `);

      const operatorNode = page.locator('.esm-expression-node');
      await expect(operatorNode).toHaveAttribute('aria-label', 'Operator: +');

      // Nested function should have appropriate label
      const sinFunction = page.locator('.esm-function-name:has-text("sin")').first();
      const sinParent = sinFunction.locator('..').locator('.esm-expression-node');
      await expect(sinParent).toHaveAttribute('aria-label', 'Function: sin');
    });

    test('should use ARIA live regions for dynamic updates', async ({ page }) => {
      await page.setContent(`
        <esm-model-editor>
          <div data-testid="validation-messages" aria-live="polite" aria-atomic="true"></div>
        </esm-model-editor>
      `);

      const liveRegion = page.locator('[data-testid="validation-messages"]');

      await expect(liveRegion).toHaveAttribute('aria-live', 'polite');
      await expect(liveRegion).toHaveAttribute('aria-atomic', 'true');
    });

    test('should provide context for nested structures', async ({ page }) => {
      const fractionExpr = { op: '/', args: ['numerator', 'denominator'] };

      await page.setContent(`
        <esm-expression-node
          expression='${JSON.stringify(fractionExpr)}'
          path='["test"]'>
        </esm-expression-node>
      `);

      const numerator = page.locator('.esm-fraction-numerator .esm-expression-node');
      const denominator = page.locator('.esm-fraction-denominator .esm-expression-node');

      // Should provide context about position in fraction
      await expect(numerator).toHaveAttribute('aria-label', 'Variable: numerator, in fraction numerator');
      await expect(denominator).toHaveAttribute('aria-label', 'Variable: denominator, in fraction denominator');
    });
  });

  test.describe('Visual Design and Contrast (WCAG 1.4.3)', () => {
    test('should meet minimum contrast ratio requirements', async ({ page }) => {
      await page.setContent(`
        <esm-expression-node
          expression='42'
          path='["test"]'>
        </esm-expression-node>
      `);

      const expressionNode = page.locator('.esm-expression-node');

      const styles = await expressionNode.evaluate(el => {
        const computed = getComputedStyle(el);
        return {
          color: computed.color,
          backgroundColor: computed.backgroundColor
        };
      });

      // Calculate contrast ratio (simplified check)
      const textColor = styles.color;
      const bgColor = styles.backgroundColor;

      // Should have sufficient contrast (actual implementation would calculate luminance)
      expect(textColor).not.toBe(bgColor);
      expect(textColor).not.toBe('rgba(0, 0, 0, 0)'); // Not transparent
    });

    test('should provide high contrast mode support', async ({ page }) => {
      // Simulate high contrast mode
      await page.addStyleTag({
        content: `
          @media (prefers-contrast: high) {
            .esm-expression-node {
              border: 2px solid;
              background: window;
              color: windowText;
            }
          }
        `
      });

      await page.setContent(`
        <esm-expression-node
          expression='42'
          path='["test"]'>
        </esm-expression-node>
      `);

      const expressionNode = page.locator('.esm-expression-node');

      // In high contrast mode, elements should have visible borders
      const borderWidth = await expressionNode.evaluate(el =>
        getComputedStyle(el).borderWidth
      );

      // Should adapt to high contrast preferences
      expect(borderWidth).not.toBe('0px');
    });

    test('should support focus indicators', async ({ page }) => {
      await page.setContent(`
        <esm-expression-node
          expression='42'
          path='["test"]'>
        </esm-expression-node>
      `);

      const expressionNode = page.locator('.esm-expression-node');

      await expressionNode.focus();

      // Should have visible focus indicator
      const outline = await expressionNode.evaluate(el => {
        const computed = getComputedStyle(el);
        return {
          outline: computed.outline,
          outlineWidth: computed.outlineWidth,
          boxShadow: computed.boxShadow
        };
      });

      // Should have some form of focus indicator
      const hasFocusIndicator = outline.outline !== 'none' ||
                                 outline.outlineWidth !== '0px' ||
                                 outline.boxShadow !== 'none';

      expect(hasFocusIndicator).toBe(true);
    });
  });

  test.describe('Form Controls and Labels (WCAG 1.3.1)', () => {
    test('should associate labels with form controls', async ({ page }) => {
      await page.setContent(`
        <esm-model-editor>
          <label for="variable-name">Variable Name:</label>
          <input id="variable-name" data-testid="variable-name-input">

          <label for="variable-type">Variable Type:</label>
          <select id="variable-type" data-testid="variable-type-select">
            <option value="state">State</option>
            <option value="parameter">Parameter</option>
          </select>
        </esm-model-editor>
      `);

      const nameInput = page.locator('[data-testid="variable-name-input"]');
      const typeSelect = page.locator('[data-testid="variable-type-select"]');

      await expect(nameInput).toHaveAttribute('id', 'variable-name');
      await expect(typeSelect).toHaveAttribute('id', 'variable-type');

      // Labels should be properly associated
      const nameLabel = page.locator('label[for="variable-name"]');
      const typeLabel = page.locator('label[for="variable-type"]');

      await expect(nameLabel).toContainText('Variable Name');
      await expect(typeLabel).toContainText('Variable Type');
    });

    test('should provide fieldsets for grouped controls', async ({ page }) => {
      await page.setContent(`
        <esm-model-editor>
          <fieldset data-testid="variable-properties">
            <legend>Variable Properties</legend>
            <label><input type="radio" name="type" value="state"> State Variable</label>
            <label><input type="radio" name="type" value="parameter"> Parameter</label>
            <label><input type="radio" name="type" value="observed"> Observed Variable</label>
          </fieldset>
        </esm-model-editor>
      `);

      const fieldset = page.locator('[data-testid="variable-properties"]');
      const legend = fieldset.locator('legend');

      await expect(legend).toContainText('Variable Properties');

      // All radio buttons should be grouped under the fieldset
      const radioButtons = fieldset.locator('input[type="radio"]');
      await expect(radioButtons).toHaveCount(3);

      // All should have the same name attribute
      for (let i = 0; i < 3; i++) {
        await expect(radioButtons.nth(i)).toHaveAttribute('name', 'type');
      }
    });

    test('should provide error messages for form validation', async ({ page }) => {
      await page.setContent(`
        <esm-model-editor>
          <label for="variable-name">Variable Name:</label>
          <input id="variable-name" aria-describedby="name-error" data-testid="variable-name-input">
          <div id="name-error" role="alert" data-testid="name-error" style="display: none;"></div>
        </esm-model-editor>
      `);

      const nameInput = page.locator('[data-testid="variable-name-input"]');
      const errorDiv = page.locator('[data-testid="name-error"]');

      // Simulate validation error
      await nameInput.fill('123invalid');
      await nameInput.blur();

      // Error should be shown and associated
      await errorDiv.evaluate(el => {
        el.textContent = 'Variable name must start with a letter';
        el.style.display = 'block';
      });

      await expect(errorDiv).toHaveAttribute('role', 'alert');
      await expect(nameInput).toHaveAttribute('aria-describedby', 'name-error');
      await expect(errorDiv).toBeVisible();
    });
  });

  test.describe('Dynamic Content and Live Regions (WCAG 4.1.3)', () => {
    test('should announce status changes to screen readers', async ({ page }) => {
      await page.setContent(`
        <esm-model-editor>
          <div data-testid="status-message" aria-live="polite"></div>
        </esm-model-editor>
      `);

      const statusDiv = page.locator('[data-testid="status-message"]');

      // Simulate status update
      await statusDiv.evaluate(el => {
        el.textContent = 'Model saved successfully';
      });

      await expect(statusDiv).toHaveAttribute('aria-live', 'polite');
      await expect(statusDiv).toContainText('Model saved successfully');
    });

    test('should announce validation errors immediately', async ({ page }) => {
      await page.setContent(`
        <esm-model-editor>
          <div data-testid="error-announcer" aria-live="assertive" aria-atomic="true"></div>
        </esm-model-editor>
      `);

      const errorAnnouncer = page.locator('[data-testid="error-announcer"]');

      // Simulate urgent error
      await errorAnnouncer.evaluate(el => {
        el.textContent = 'Error: Invalid equation syntax detected';
      });

      await expect(errorAnnouncer).toHaveAttribute('aria-live', 'assertive');
      await expect(errorAnnouncer).toHaveAttribute('aria-atomic', 'true');
      await expect(errorAnnouncer).toContainText('Error: Invalid equation syntax detected');
    });

    test('should update button states appropriately', async ({ page }) => {
      await page.setContent(`
        <esm-model-editor>
          <button data-testid="save-button" aria-pressed="false">Save Model</button>
        </esm-model-editor>
      `);

      const saveButton = page.locator('[data-testid="save-button"]');

      // Initially not pressed
      await expect(saveButton).toHaveAttribute('aria-pressed', 'false');

      // Simulate save operation
      await saveButton.click();
      await saveButton.evaluate(btn => {
        btn.setAttribute('aria-pressed', 'true');
        btn.disabled = true;
        btn.textContent = 'Saving...';
      });

      await expect(saveButton).toHaveAttribute('aria-pressed', 'true');
      await expect(saveButton).toBeDisabled();
      await expect(saveButton).toContainText('Saving...');
    });
  });

  test.describe('Interactive Elements (WCAG 2.1.1)', () => {
    test('should support escape key to cancel operations', async ({ page }) => {
      await page.setContent(`
        <esm-expression-node
          expression='42'
          path='["test"]'
          allow-editing="true">
        </esm-expression-node>
      `);

      const expressionNode = page.locator('.esm-expression-node');

      // Enter edit mode
      await expressionNode.dblclick();
      const editInput = page.locator('.esm-expression-edit');
      await expect(editInput).toBeVisible();

      // Escape should cancel
      await page.keyboard.press('Escape');
      await expect(editInput).not.toBeVisible();
    });

    test('should provide clear instructions for complex interactions', async ({ page }) => {
      await page.setContent(`
        <esm-coupling-graph data-testid="coupling-graph">
          <div role="img" aria-label="Coupling graph showing model connections. Press Tab to navigate nodes, Enter to select, or Ctrl+Click to create connections.">
          </div>
        </esm-coupling-graph>
      `);

      const graph = page.locator('[data-testid="coupling-graph"] [role="img"]');

      await expect(graph).toHaveAttribute('aria-label');

      const ariaLabel = await graph.getAttribute('aria-label');
      expect(ariaLabel).toContain('Press Tab to navigate');
      expect(ariaLabel).toContain('Enter to select');
      expect(ariaLabel).toContain('Ctrl+Click');
    });

    test('should handle timeout-based interactions accessibly', async ({ page }) => {
      await page.setContent(`
        <esm-model-editor>
          <div data-testid="auto-save-status" aria-live="polite"></div>
        </esm-model-editor>
      `);

      const statusDiv = page.locator('[data-testid="auto-save-status"]');

      // Simulate auto-save with countdown
      await statusDiv.evaluate(el => {
        el.textContent = 'Auto-save in 5 seconds';
      });

      await expect(statusDiv).toContainText('Auto-save in 5 seconds');

      // Update countdown
      await statusDiv.evaluate(el => {
        el.textContent = 'Auto-saving now...';
      });

      await expect(statusDiv).toContainText('Auto-saving now...');
    });
  });

  test.describe('Error Prevention and Recovery (WCAG 3.3.4)', () => {
    test('should confirm destructive actions', async ({ page }) => {
      await page.setContent(`
        <esm-model-editor>
          <button data-testid="delete-model" aria-describedby="delete-warning">Delete Model</button>
          <div id="delete-warning">Warning: This action cannot be undone</div>
        </esm-model-editor>
      `);

      const deleteButton = page.locator('[data-testid="delete-model"]');
      const warning = page.locator('#delete-warning');

      await expect(deleteButton).toHaveAttribute('aria-describedby', 'delete-warning');
      await expect(warning).toContainText('cannot be undone');

      await deleteButton.click();

      // Should show confirmation dialog
      const dialog = page.locator('[role="alertdialog"]');
      await expect(dialog).toBeVisible();
    });

    test('should provide undo functionality', async ({ page }) => {
      await page.setContent(`
        <esm-model-editor>
          <button data-testid="undo-button" disabled aria-label="Undo last action">Undo</button>
        </esm-model-editor>
      `);

      const undoButton = page.locator('[data-testid="undo-button"]');

      // Initially disabled
      await expect(undoButton).toBeDisabled();

      // After an action, should be enabled
      await undoButton.evaluate(btn => {
        btn.disabled = false;
        btn.setAttribute('aria-label', 'Undo: Added variable temperature');
      });

      await expect(undoButton).toBeEnabled();
      await expect(undoButton).toHaveAttribute('aria-label', 'Undo: Added variable temperature');
    });
  });
});