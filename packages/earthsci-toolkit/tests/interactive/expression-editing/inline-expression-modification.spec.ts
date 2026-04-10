/**
 * Inline Expression Modification Tests
 *
 * Tests for direct editing of expressions within the interface including
 * auto-completion, syntax error recovery, and mathematical notation rendering.
 */

import { test, expect } from '@playwright/test';

test.describe('Inline Expression Modification', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/demo/expression-editor');
  });

  test.describe('Inline Expression Editing', () => {
    test('should support basic number editing', async ({ page }) => {
      const numberNode = page.locator('[data-testid="editable-number-42"]');

      await numberNode.dblclick();
      const editInput = page.locator('.esm-expression-edit');
      await editInput.fill('3.14159');
      await page.keyboard.press('Enter');

      await expect(numberNode).toContainText('3.14159');
    });

    test('should support scientific notation input', async ({ page }) => {
      const numberNode = page.locator('[data-testid="editable-number-1000000"]');

      await numberNode.dblclick();
      const editInput = page.locator('.esm-expression-edit');
      await editInput.fill('1.5e6');
      await page.keyboard.press('Enter');

      await expect(numberNode).toContainText('1.500e+6');
    });

    test('should support variable renaming', async ({ page }) => {
      const variableNode = page.locator('[data-testid="editable-variable-temp"]');

      await variableNode.dblclick();
      const editInput = page.locator('.esm-expression-edit');
      await editInput.fill('temperature');
      await page.keyboard.press('Enter');

      await expect(variableNode).toContainText('temperature');
    });

    test('should validate variable names', async ({ page }) => {
      const variableNode = page.locator('[data-testid="editable-variable-x"]');

      await variableNode.dblclick();
      const editInput = page.locator('.esm-expression-edit');
      await editInput.fill('123invalid');
      await page.keyboard.press('Enter');

      const errorMessage = page.locator('.validation-error');
      await expect(errorMessage).toContainText('Invalid variable name');
    });
  });

  test.describe('Expression Palette Integration', () => {
    test('should open expression palette on keyboard shortcut', async ({ page }) => {
      const editorArea = page.locator('[data-testid="expression-editor"]');

      await editorArea.click();
      await page.keyboard.press('Control+Space');

      const palette = page.locator('[data-testid="expression-palette"]');
      await expect(palette).toBeVisible();
    });

    test('should insert functions from palette', async ({ page }) => {
      const insertionPoint = page.locator('[data-testid="insertion-point"]');

      await insertionPoint.click();
      await page.keyboard.press('Control+Space');

      const sinFunction = page.locator('[data-testid="palette-sin"]');
      await sinFunction.click();

      const newFunction = page.locator('.esm-function-name:has-text("sin")');
      await expect(newFunction).toBeVisible();
    });

    test('should show palette categories', async ({ page }) => {
      const editorArea = page.locator('[data-testid="expression-editor"]');

      await editorArea.click();
      await page.keyboard.press('Control+Space');

      await expect(page.locator('[data-testid="palette-category-math"]')).toBeVisible();
      await expect(page.locator('[data-testid="palette-category-trig"]')).toBeVisible();
      await expect(page.locator('[data-testid="palette-category-constants"]')).toBeVisible();
    });
  });

  test.describe('Auto-completion Behavior', () => {
    test('should show function suggestions while typing', async ({ page }) => {
      const numberNode = page.locator('[data-testid="editable-number-0"]');

      await numberNode.dblclick();
      const editInput = page.locator('.esm-expression-edit');
      await editInput.type('si');

      const suggestions = page.locator('[data-testid="autocomplete-suggestions"]');
      await expect(suggestions).toBeVisible();
      await expect(page.locator('[data-testid="suggestion-sin"]')).toBeVisible();
      await expect(page.locator('[data-testid="suggestion-sinh"]')).toBeVisible();
    });

    test('should complete function names with Tab', async ({ page }) => {
      const numberNode = page.locator('[data-testid="editable-number-0"]');

      await numberNode.dblclick();
      const editInput = page.locator('.esm-expression-edit');
      await editInput.type('si');
      await page.keyboard.press('Tab');

      await expect(editInput).toHaveValue('sin');
    });

    test('should show variable suggestions', async ({ page }) => {
      const numberNode = page.locator('[data-testid="editable-number-0"]');

      await numberNode.dblclick();
      const editInput = page.locator('.esm-expression-edit');
      await editInput.type('tem');

      const suggestions = page.locator('[data-testid="autocomplete-suggestions"]');
      await expect(page.locator('[data-testid="suggestion-temperature"]')).toBeVisible();
    });
  });

  test.describe('Syntax Error Recovery', () => {
    test('should highlight syntax errors in real-time', async ({ page }) => {
      const numberNode = page.locator('[data-testid="editable-number-42"]');

      await numberNode.dblclick();
      const editInput = page.locator('.esm-expression-edit');
      await editInput.type('sin(');

      await expect(editInput).toHaveClass(/syntax-error/);
      const errorIndicator = page.locator('.error-indicator');
      await expect(errorIndicator).toBeVisible();
    });

    test('should suggest corrections for common mistakes', async ({ page }) => {
      const numberNode = page.locator('[data-testid="editable-number-0"]');

      await numberNode.dblclick();
      const editInput = page.locator('.esm-expression-edit');
      await editInput.type('2x');

      const suggestion = page.locator('[data-testid="correction-suggestion"]');
      await expect(suggestion).toContainText('Did you mean: 2*x?');
    });

    test('should auto-correct simple mistakes on Enter', async ({ page }) => {
      const numberNode = page.locator('[data-testid="editable-number-0"]');

      await numberNode.dblclick();
      const editInput = page.locator('.esm-expression-edit');
      await editInput.type('2x');
      await page.keyboard.press('Enter');

      const correctedExpression = page.locator('[data-testid="expression-result"]');
      await expect(correctedExpression).toContainText('2⋅x');
    });
  });

  test.describe('Precedence-aware Parenthesis Insertion', () => {
    test('should auto-insert parentheses when needed', async ({ page }) => {
      const insertionPoint = page.locator('[data-testid="insertion-point"]');

      await insertionPoint.click();
      await page.keyboard.type('a + b * c');

      const expression = page.locator('[data-testid="expression-result"]');
      await expect(expression).toContainText('a + b⋅c'); // No extra parentheses needed

      await page.keyboard.press('Home');
      await page.keyboard.type('(');
      await page.keyboard.press('End');
      await page.keyboard.type(') / d');

      await expect(expression).toContainText('(a + b⋅c) / d'); // Parentheses preserve precedence
    });

    test('should suggest parentheses for clarity', async ({ page }) => {
      const insertionPoint = page.locator('[data-testid="insertion-point"]');

      await insertionPoint.click();
      await page.keyboard.type('a + b * c + d');

      const suggestion = page.locator('[data-testid="precedence-suggestion"]');
      await expect(suggestion).toContainText('Add parentheses for clarity?');
    });
  });

  test.describe('Mathematical Notation Rendering', () => {
    test('should render fractions properly', async ({ page }) => {
      const insertionPoint = page.locator('[data-testid="insertion-point"]');

      await insertionPoint.click();
      await page.keyboard.type('(a + b) / (c + d)');
      await page.keyboard.press('Enter');

      const fraction = page.locator('.esm-fraction');
      await expect(fraction).toBeVisible();

      const numerator = fraction.locator('.esm-fraction-numerator');
      const denominator = fraction.locator('.esm-fraction-denominator');

      await expect(numerator).toContainText('a + b');
      await expect(denominator).toContainText('c + d');
    });

    test('should render exponents as superscripts', async ({ page }) => {
      const insertionPoint = page.locator('[data-testid="insertion-point"]');

      await insertionPoint.click();
      await page.keyboard.type('x^2 + y^(n+1)');
      await page.keyboard.press('Enter');

      const simpleExponent = page.locator('.esm-exponent:has-text("2")');
      const complexExponent = page.locator('.esm-exponent:has-text("n+1")');

      await expect(simpleExponent).toBeVisible();
      await expect(complexExponent).toBeVisible();
    });

    test('should render derivatives properly', async ({ page }) => {
      const insertionPoint = page.locator('[data-testid="insertion-point"]');

      await insertionPoint.click();
      await page.keyboard.type('d(x^2)/dx');
      await page.keyboard.press('Enter');

      const derivative = page.locator('.esm-derivative');
      await expect(derivative).toBeVisible();

      const dOperators = derivative.locator('.esm-d-operator');
      await expect(dOperators).toHaveCount(2); // dx in numerator and denominator
    });
  });

  test.describe('MathML/LaTeX Output Verification', () => {
    test('should generate correct MathML for complex expressions', async ({ page }) => {
      const insertionPoint = page.locator('[data-testid="insertion-point"]');

      await insertionPoint.click();
      await page.keyboard.type('sqrt(x^2 + y^2)');
      await page.keyboard.press('Enter');

      const mathmlOutput = page.locator('[data-testid="mathml-output"]');
      const mathmlContent = await mathmlOutput.textContent();

      expect(mathmlContent).toContain('<msqrt>');
      expect(mathmlContent).toContain('<msup>');
    });

    test('should generate correct LaTeX for publication', async ({ page }) => {
      const insertionPoint = page.locator('[data-testid="insertion-point"]');

      await insertionPoint.click();
      await page.keyboard.type('integral(sin(x), x, 0, pi)');
      await page.keyboard.press('Enter');

      const latexOutput = page.locator('[data-testid="latex-output"]');
      const latexContent = await latexOutput.textContent();

      expect(latexContent).toContain('\\int_{0}^{\\pi}');
      expect(latexContent).toContain('\\sin(x)');
    });

    test('should export to clipboard in multiple formats', async ({ page }) => {
      const expression = page.locator('[data-testid="complex-expression"]');

      await expression.click({ button: 'right' });
      const contextMenu = page.locator('[data-testid="context-menu"]');

      await contextMenu.locator('text=Copy as LaTeX').click();

      // Verify clipboard content (requires additional setup in real tests)
      const notification = page.locator('[data-testid="copy-notification"]');
      await expect(notification).toContainText('LaTeX copied to clipboard');
    });
  });
});