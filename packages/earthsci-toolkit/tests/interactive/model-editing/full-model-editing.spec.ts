/**
 * Full Model Editing Tests
 *
 * Tests for comprehensive model editing including adding/removing variables,
 * creating equations, reaction editing, and cross-reference management.
 */

import { test, expect } from '@playwright/test';

test.describe('Full Model Editing', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/demo/model-editor');
  });

  test.describe('Adding and Removing Variables', () => {
    test('should add new state variable through UI', async ({ page }) => {
      const addVariableButton = page.locator('[data-testid="add-variable-button"]');

      await addVariableButton.click();

      const variableDialog = page.locator('[data-testid="variable-dialog"]');
      await expect(variableDialog).toBeVisible();

      await page.fill('[data-testid="variable-name-input"]', 'new_concentration');
      await page.selectOption('[data-testid="variable-type-select"]', 'state');
      await page.fill('[data-testid="variable-units-input"]', 'mg/L');
      await page.fill('[data-testid="variable-description-input"]', 'New chemical concentration');

      await page.click('[data-testid="save-variable-button"]');

      const variablesList = page.locator('[data-testid="variables-list"]');
      await expect(variablesList).toContainText('new_concentration');

      const variableType = page.locator('[data-testid="variable-type-new_concentration"]');
      await expect(variableType).toContainText('state');
    });

    test('should validate variable names', async ({ page }) => {
      const addVariableButton = page.locator('[data-testid="add-variable-button"]');
      await addVariableButton.click();

      await page.fill('[data-testid="variable-name-input"]', '123invalid');
      await page.click('[data-testid="save-variable-button"]');

      const errorMessage = page.locator('[data-testid="variable-name-error"]');
      await expect(errorMessage).toContainText('Variable name must start with a letter');
    });

    test('should prevent duplicate variable names', async ({ page }) => {
      const addVariableButton = page.locator('[data-testid="add-variable-button"]');
      await addVariableButton.click();

      await page.fill('[data-testid="variable-name-input"]', 'temperature'); // Existing variable
      await page.click('[data-testid="save-variable-button"]');

      const errorMessage = page.locator('[data-testid="variable-name-error"]');
      await expect(errorMessage).toContainText('Variable name already exists');
    });

    test('should remove variable with confirmation', async ({ page }) => {
      const variableRow = page.locator('[data-testid="variable-row-temperature"]');
      const deleteButton = variableRow.locator('[data-testid="delete-variable-button"]');

      await deleteButton.click();

      const confirmDialog = page.locator('[data-testid="confirm-delete-dialog"]');
      await expect(confirmDialog).toContainText('Delete variable temperature?');

      await page.click('[data-testid="confirm-delete-button"]');

      const variablesList = page.locator('[data-testid="variables-list"]');
      await expect(variablesList).not.toContainText('temperature');
    });
  });

  test.describe('Creating New Equations via UI', () => {
    test('should create differential equation', async ({ page }) => {
      const addEquationButton = page.locator('[data-testid="add-equation-button"]');

      await addEquationButton.click();
      await page.selectOption('[data-testid="equation-type-select"]', 'differential');

      const lhsInput = page.locator('[data-testid="equation-lhs-input"]');
      const rhsInput = page.locator('[data-testid="equation-rhs-input"]');

      await lhsInput.fill('d(concentration)/dt');
      await rhsInput.fill('-k * concentration');

      await page.click('[data-testid="save-equation-button"]');

      const equationsList = page.locator('[data-testid="equations-list"]');
      await expect(equationsList).toContainText('d(concentration)/dt = -k⋅concentration');
    });

    test('should create algebraic equation', async ({ page }) => {
      const addEquationButton = page.locator('[data-testid="add-equation-button"]');

      await addEquationButton.click();
      await page.selectOption('[data-testid="equation-type-select"]', 'algebraic');

      const lhsInput = page.locator('[data-testid="equation-lhs-input"]');
      const rhsInput = page.locator('[data-testid="equation-rhs-input"]');

      await lhsInput.fill('total_mass');
      await rhsInput.fill('concentration * volume');

      await page.click('[data-testid="save-equation-button"]');

      const equationsList = page.locator('[data-testid="equations-list"]');
      await expect(equationsList).toContainText('total_mass = concentration⋅volume');
    });

    test('should validate equation syntax', async ({ page }) => {
      const addEquationButton = page.locator('[data-testid="add-equation-button"]');

      await addEquationButton.click();

      const rhsInput = page.locator('[data-testid="equation-rhs-input"]');
      await rhsInput.fill('invalid_syntax((');

      const errorMessage = page.locator('[data-testid="equation-syntax-error"]');
      await expect(errorMessage).toContainText('Syntax error: Unmatched parentheses');
    });
  });

  test.describe('Reaction Editor Drag-and-Drop', () => {
    test('should create reaction by dragging species', async ({ page }) => {
      await page.goto('/demo/reaction-editor');

      const speciesA = page.locator('[data-testid="species-A"]');
      const speciesB = page.locator('[data-testid="species-B"]');
      const productC = page.locator('[data-testid="species-C"]');

      const reactionArea = page.locator('[data-testid="reaction-construction-area"]');

      // Drag reactants
      await speciesA.dragTo(reactionArea);
      await page.locator('[data-testid="add-plus-operator"]').click();
      await speciesB.dragTo(reactionArea);

      // Add reaction arrow
      await page.locator('[data-testid="add-reaction-arrow"]').click();

      // Drag products
      await productC.dragTo(reactionArea);

      const reactionEquation = page.locator('[data-testid="reaction-equation"]');
      await expect(reactionEquation).toContainText('A + B → C');

      await page.click('[data-testid="save-reaction-button"]');

      const reactionsList = page.locator('[data-testid="reactions-list"]');
      await expect(reactionsList).toContainText('A + B → C');
    });

    test('should support reversible reactions', async ({ page }) => {
      await page.goto('/demo/reaction-editor');

      const speciesA = page.locator('[data-testid="species-A"]');
      const speciesB = page.locator('[data-testid="species-B"]');

      const reactionArea = page.locator('[data-testid="reaction-construction-area"]');

      await speciesA.dragTo(reactionArea);
      await page.locator('[data-testid="add-reversible-arrow"]').click();
      await speciesB.dragTo(reactionArea);

      const reactionEquation = page.locator('[data-testid="reaction-equation"]');
      await expect(reactionEquation).toContainText('A ⇌ B');
    });

    test('should validate reaction stoichiometry', async ({ page }) => {
      await page.goto('/demo/reaction-editor');

      const speciesA = page.locator('[data-testid="species-A"]');

      const reactionArea = page.locator('[data-testid="reaction-construction-area"]');

      await speciesA.dragTo(reactionArea);
      await page.locator('[data-testid="add-reaction-arrow"]').click();
      // No products added

      await page.click('[data-testid="save-reaction-button"]');

      const errorMessage = page.locator('[data-testid="reaction-validation-error"]');
      await expect(errorMessage).toContainText('Reaction must have at least one product');
    });
  });

  test.describe('Species Property Modification', () => {
    test('should edit species properties', async ({ page }) => {
      const speciesRow = page.locator('[data-testid="species-row-O3"]');
      const editButton = speciesRow.locator('[data-testid="edit-species-button"]');

      await editButton.click();

      const propertiesDialog = page.locator('[data-testid="species-properties-dialog"]');
      await expect(propertiesDialog).toBeVisible();

      await page.fill('[data-testid="molecular-weight-input"]', '47.998');
      await page.fill('[data-testid="phase-input"]', 'gas');

      await page.click('[data-testid="save-properties-button"]');

      await expect(speciesRow).toContainText('47.998 g/mol');
    });

    test('should validate molecular weight', async ({ page }) => {
      const speciesRow = page.locator('[data-testid="species-row-O3"]');
      const editButton = speciesRow.locator('[data-testid="edit-species-button"]');

      await editButton.click();

      await page.fill('[data-testid="molecular-weight-input"]', '-10');
      await page.click('[data-testid="save-properties-button"]');

      const errorMessage = page.locator('[data-testid="molecular-weight-error"]');
      await expect(errorMessage).toContainText('Molecular weight must be positive');
    });
  });

  test.describe('Coupling Graph Manipulation', () => {
    test('should add coupling connection via graph', async ({ page }) => {
      await page.goto('/demo/coupling-editor');

      const model1Node = page.locator('[data-testid="model-node-Transport"]');
      const model2Node = page.locator('[data-testid="model-node-Chemistry"]');

      // Select first model
      await model1Node.click();
      await expect(model1Node).toHaveClass(/selected/);

      // Hold Ctrl and click second model to create connection
      await page.keyboard.down('Control');
      await model2Node.click();
      await page.keyboard.up('Control');

      const connectionDialog = page.locator('[data-testid="coupling-connection-dialog"]');
      await expect(connectionDialog).toBeVisible();

      await page.selectOption('[data-testid="source-variable-select"]', 'concentration');
      await page.selectOption('[data-testid="target-variable-select"]', 'chemical_amount');
      await page.selectOption('[data-testid="coupling-type-select"]', 'direct');

      await page.click('[data-testid="save-coupling-button"]');

      const couplingEdge = page.locator('[data-testid="coupling-edge-Transport-Chemistry"]');
      await expect(couplingEdge).toBeVisible();
    });

    test('should edit existing coupling by clicking edge', async ({ page }) => {
      await page.goto('/demo/coupling-editor');

      const existingEdge = page.locator('[data-testid="coupling-edge-Transport-Chemistry"]');
      await existingEdge.click();

      const editDialog = page.locator('[data-testid="edit-coupling-dialog"]');
      await expect(editDialog).toBeVisible();

      await page.selectOption('[data-testid="coupling-type-select"]', 'interpolated');
      await page.click('[data-testid="save-coupling-button"]');

      // Verify edge appearance changed
      await expect(existingEdge).toHaveClass(/interpolated/);
    });
  });

  test.describe('Cross-reference Updates', () => {
    test('should update all references when variable is renamed', async ({ page }) => {
      // Start with an equation that references 'temperature'
      const equationElement = page.locator('[data-testid="equation-0"]');
      await expect(equationElement).toContainText('temperature');

      // Rename the variable
      const variableRow = page.locator('[data-testid="variable-row-temperature"]');
      const editButton = variableRow.locator('[data-testid="edit-variable-button"]');

      await editButton.click();
      await page.fill('[data-testid="variable-name-input"]', 'temp');
      await page.click('[data-testid="save-variable-button"]');

      // Verify all references are updated
      await expect(equationElement).toContainText('temp');
      await expect(equationElement).not.toContainText('temperature');

      // Check that coupling references are also updated
      const couplingList = page.locator('[data-testid="coupling-list"]');
      await expect(couplingList).toContainText('temp');
    });

    test('should show impact analysis before renaming', async ({ page }) => {
      const variableRow = page.locator('[data-testid="variable-row-temperature"]');
      const editButton = variableRow.locator('[data-testid="edit-variable-button"]');

      await editButton.click();
      await page.fill('[data-testid="variable-name-input"]', 'temp');

      // Should show impact before saving
      const impactWarning = page.locator('[data-testid="rename-impact-warning"]');
      await expect(impactWarning).toContainText('This will update 3 equations and 2 coupling entries');
    });

    test('should prevent renaming if it creates conflicts', async ({ page }) => {
      const variableRow = page.locator('[data-testid="variable-row-temperature"]');
      const editButton = variableRow.locator('[data-testid="edit-variable-button"]');

      await editButton.click();
      await page.fill('[data-testid="variable-name-input"]', 'pressure'); // Existing variable

      const errorMessage = page.locator('[data-testid="variable-name-error"]');
      await expect(errorMessage).toContainText('Variable name already exists');

      const saveButton = page.locator('[data-testid="save-variable-button"]');
      await expect(saveButton).toBeDisabled();
    });
  });

  test.describe('Model Validation and Consistency', () => {
    test('should show validation errors for incomplete model', async ({ page }) => {
      // Create a variable without any equations
      const addVariableButton = page.locator('[data-testid="add-variable-button"]');
      await addVariableButton.click();

      await page.fill('[data-testid="variable-name-input"]', 'unused_var');
      await page.selectOption('[data-testid="variable-type-select"]', 'state');
      await page.click('[data-testid="save-variable-button"]');

      const validationPanel = page.locator('[data-testid="model-validation-panel"]');
      await expect(validationPanel).toContainText('Warning: unused_var is not used in any equation');
    });

    test('should validate dimensional consistency', async ({ page }) => {
      const addEquationButton = page.locator('[data-testid="add-equation-button"]');
      await addEquationButton.click();

      // Create dimensionally inconsistent equation
      const lhsInput = page.locator('[data-testid="equation-lhs-input"]');
      const rhsInput = page.locator('[data-testid="equation-rhs-input"]');

      await lhsInput.fill('temperature'); // Units: K
      await rhsInput.fill('pressure'); // Units: Pa

      const dimensionalError = page.locator('[data-testid="dimensional-error"]');
      await expect(dimensionalError).toContainText('Dimensional inconsistency: K ≠ Pa');
    });

    test('should validate mass balance for reactions', async ({ page }) => {
      await page.goto('/demo/reaction-editor');

      // Create unbalanced reaction
      const reactionInput = page.locator('[data-testid="reaction-input"]');
      await reactionInput.fill('H2 + O2 → H2O');

      const balanceError = page.locator('[data-testid="mass-balance-error"]');
      await expect(balanceError).toContainText('Reaction is not balanced: Missing O atom');
    });
  });
});