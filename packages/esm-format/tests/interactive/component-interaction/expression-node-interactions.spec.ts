/**
 * ExpressionNode Component Interaction Tests
 *
 * Tests the core interactive behaviors of ExpressionNode components including
 * click-to-select, hover highlighting, drag-and-drop, and keyboard navigation.
 */

import { test, expect } from '@playwright/test';

test.describe('ExpressionNode Interactions', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/demo/expression-node');
  });

  test.describe('Click-to-Edit Behavior', () => {
    test('should select expression node on single click', async ({ page }) => {
      const expressionNode = page.locator('[data-testid="expression-node-42"]');

      await expressionNode.click();

      await expect(expressionNode).toHaveClass(/selected/);
    });

    test('should enter edit mode on double-click for numbers', async ({ page }) => {
      const numberNode = page.locator('[data-testid="expression-node-42"]');

      await numberNode.dblclick();

      const editInput = page.locator('.esm-expression-edit');
      await expect(editInput).toBeVisible();
      await expect(editInput).toHaveValue('42');
      await expect(editInput).toBeFocused();
    });

    test('should enter edit mode on double-click for variables', async ({ page }) => {
      const variableNode = page.locator('[data-testid="expression-node-temperature"]');

      await variableNode.dblclick();

      const editInput = page.locator('.esm-expression-edit');
      await expect(editInput).toBeVisible();
      await expect(editInput).toHaveValue('temperature');
    });

    test('should not allow editing of operator nodes', async ({ page }) => {
      const operatorNode = page.locator('[data-testid="expression-node-add-op"]');

      await operatorNode.dblclick();

      const editInput = page.locator('.esm-expression-edit');
      await expect(editInput).not.toBeVisible();
    });
  });

  test.describe('Variable Hover Highlighting', () => {
    test('should highlight equivalent variables on hover', async ({ page }) => {
      const variableNode = page.locator('[data-testid="expression-node-temperature"]');

      await variableNode.hover();

      // All nodes with the same variable name should be highlighted
      const highlightedNodes = page.locator('.esm-expression-node.highlighted');
      await expect(highlightedNodes).toHaveCount(3); // Assuming 3 instances of 'temperature'
    });

    test('should show tooltip with variable information on hover', async ({ page }) => {
      const variableNode = page.locator('[data-testid="expression-node-pressure"]');

      await variableNode.hover();

      const tooltip = page.locator('[role="tooltip"]');
      await expect(tooltip).toContainText('Variable: pressure');
    });

    test('should clear highlighting when mouse leaves', async ({ page }) => {
      const variableNode = page.locator('[data-testid="expression-node-temperature"]');
      const otherArea = page.locator('body');

      await variableNode.hover();
      await otherArea.hover();

      const highlightedNodes = page.locator('.esm-expression-node.highlighted');
      await expect(highlightedNodes).toHaveCount(0);
    });
  });

  test.describe('Keyboard Navigation', () => {
    test('should be focusable with Tab key', async ({ page }) => {
      const firstNode = page.locator('.esm-expression-node').first();

      await page.keyboard.press('Tab');

      await expect(firstNode).toBeFocused();
    });

    test('should navigate between nodes with arrow keys', async ({ page }) => {
      const nodes = page.locator('.esm-expression-node');
      const firstNode = nodes.first();
      const secondNode = nodes.nth(1);

      await firstNode.focus();
      await page.keyboard.press('ArrowRight');

      await expect(secondNode).toBeFocused();
    });

    test('should support Enter key to start editing', async ({ page }) => {
      const numberNode = page.locator('[data-testid="expression-node-42"]');

      await numberNode.focus();
      await page.keyboard.press('Enter');

      const editInput = page.locator('.esm-expression-edit');
      await expect(editInput).toBeVisible();
    });

    test('should support Escape to cancel editing', async ({ page }) => {
      const numberNode = page.locator('[data-testid="expression-node-42"]');

      await numberNode.dblclick();
      const editInput = page.locator('.esm-expression-edit');
      await editInput.fill('123');
      await page.keyboard.press('Escape');

      await expect(editInput).not.toBeVisible();
      await expect(numberNode).toContainText('42'); // Original value preserved
    });

    test('should save changes with Enter key', async ({ page }) => {
      const numberNode = page.locator('[data-testid="expression-node-42"]');

      await numberNode.dblclick();
      const editInput = page.locator('.esm-expression-edit');
      await editInput.fill('123');
      await page.keyboard.press('Enter');

      await expect(editInput).not.toBeVisible();
      await expect(numberNode).toContainText('123'); // Value updated
    });
  });

  test.describe('Selection State Management', () => {
    test('should maintain selection state across interactions', async ({ page }) => {
      const node1 = page.locator('[data-testid="expression-node-42"]');
      const node2 = page.locator('[data-testid="expression-node-temperature"]');

      await node1.click();
      await expect(node1).toHaveClass(/selected/);

      await node2.click();
      await expect(node1).not.toHaveClass(/selected/);
      await expect(node2).toHaveClass(/selected/);
    });

    test('should preserve selection during hover interactions', async ({ page }) => {
      const selectedNode = page.locator('[data-testid="expression-node-42"]');
      const hoveredNode = page.locator('[data-testid="expression-node-temperature"]');

      await selectedNode.click();
      await hoveredNode.hover();

      await expect(selectedNode).toHaveClass(/selected/);
    });
  });

  test.describe('Real-time Validation Feedback', () => {
    test('should show validation errors for invalid expressions', async ({ page }) => {
      const numberNode = page.locator('[data-testid="expression-node-42"]');

      await numberNode.dblclick();
      const editInput = page.locator('.esm-expression-edit');
      await editInput.fill('invalid_number_format');
      await page.keyboard.press('Enter');

      const errorMessage = page.locator('.validation-error');
      await expect(errorMessage).toBeVisible();
      await expect(errorMessage).toContainText('Invalid number format');
    });

    test('should provide live validation feedback while typing', async ({ page }) => {
      const variableNode = page.locator('[data-testid="expression-node-temperature"]');

      await variableNode.dblclick();
      const editInput = page.locator('.esm-expression-edit');
      await editInput.fill('123invalid');

      const validationHint = page.locator('.validation-hint');
      await expect(validationHint).toBeVisible();
    });
  });

  test.describe('Drag and Drop for Structural Editing', () => {
    test('should support drag and drop to reorder expression components', async ({ page }) => {
      const sourceNode = page.locator('[data-testid="expression-node-term-1"]');
      const targetNode = page.locator('[data-testid="expression-node-term-2"]');

      await sourceNode.dragTo(targetNode);

      // Verify the expression structure has been updated
      const updatedExpression = page.locator('[data-testid="expression-result"]');
      await expect(updatedExpression).toContainText('term2 + term1'); // Order changed
    });

    test('should show drop zones when dragging', async ({ page }) => {
      const sourceNode = page.locator('[data-testid="expression-node-term-1"]');

      await sourceNode.hover();
      await page.mouse.down();
      await page.mouse.move(100, 0);

      const dropZones = page.locator('.drop-zone');
      await expect(dropZones.first()).toBeVisible();

      await page.mouse.up();
    });

    test('should prevent invalid drag operations', async ({ page }) => {
      const operatorNode = page.locator('[data-testid="expression-node-add-op"]');
      const numberNode = page.locator('[data-testid="expression-node-42"]');

      await operatorNode.dragTo(numberNode);

      const errorMessage = page.locator('.drag-error');
      await expect(errorMessage).toContainText('Cannot replace number with operator');
    });
  });
});