/**
 * Demo Pages for Interactive Testing
 *
 * Creates demo HTML pages that showcase the interactive ESM editor components
 * for use in Playwright testing and manual testing.
 */

export interface DemoPageConfig {
  title: string;
  path: string;
  html: string;
}

export const demoPages: DemoPageConfig[] = [
  {
    title: 'ExpressionNode Demo',
    path: '/demo/expression-node',
    html: `
      <!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ExpressionNode Demo</title>
        <style>
          body { font-family: Arial, sans-serif; padding: 20px; }
          .demo-section { margin: 20px 0; padding: 15px; border: 1px solid #ccc; }
          .esm-expression-node { margin: 5px; }
        </style>
      </head>
      <body>
        <h1>ExpressionNode Interactive Demo</h1>

        <div class="demo-section">
          <h2>Basic Expressions</h2>
          <esm-expression-node
            data-testid="expression-node-42"
            expression="42"
            path='["numbers", 0]'
            allow-editing="true">
          </esm-expression-node>

          <esm-expression-node
            data-testid="expression-node-temperature"
            expression='"temperature"'
            path='["variables", 0]'
            allow-editing="true">
          </esm-expression-node>

          <esm-expression-node
            data-testid="expression-node-pressure"
            expression='"pressure"'
            path='["variables", 1]'
            allow-editing="true">
          </esm-expression-node>
        </div>

        <div class="demo-section">
          <h2>Mathematical Operations</h2>
          <esm-expression-node
            data-testid="expression-node-add-op"
            expression='{"op": "+", "args": [1, 2]}'
            path='["operators", 0]'>
          </esm-expression-node>

          <esm-expression-node
            expression='{"op": "*", "args": ["x", "y"]}'
            path='["operators", 1]'>
          </esm-expression-node>

          <esm-expression-node
            expression='{"op": "/", "args": ["numerator", "denominator"]}'
            path='["operators", 2]'>
          </esm-expression-node>

          <esm-expression-node
            expression='{"op": "^", "args": ["x", 2]}'
            path='["operators", 3]'>
          </esm-expression-node>
        </div>

        <div class="demo-section">
          <h2>Functions</h2>
          <esm-expression-node
            expression='{"op": "sin", "args": ["x"]}'
            path='["functions", 0]'>
          </esm-expression-node>

          <esm-expression-node
            expression='{"op": "log", "args": [{"op": "+", "args": ["a", "b"]}]}'
            path='["functions", 1]'>
          </esm-expression-node>
        </div>

        <script type="module" src="./expression-node-demo.js"></script>
      </body>
      </html>
    `
  },

  {
    title: 'Expression Editor Demo',
    path: '/demo/expression-editor',
    html: `
      <!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Expression Editor Demo</title>
        <style>
          body { font-family: Arial, sans-serif; padding: 20px; }
          .editor-container { border: 1px solid #ccc; padding: 20px; margin: 10px 0; }
          .palette { position: fixed; right: 20px; top: 20px; width: 200px; border: 1px solid #ccc; padding: 10px; }
        </style>
      </head>
      <body>
        <h1>Expression Editor Demo</h1>

        <div class="editor-container" data-testid="expression-editor">
          <h2>Editable Expressions</h2>

          <p>Numbers (double-click to edit):</p>
          <esm-expression-node
            data-testid="editable-number-42"
            expression="42"
            path='["editor", "numbers", 0]'
            allow-editing="true">
          </esm-expression-node>

          <esm-expression-node
            data-testid="editable-number-1000000"
            expression="1000000"
            path='["editor", "numbers", 1]'
            allow-editing="true">
          </esm-expression-node>

          <esm-expression-node
            data-testid="editable-number-0"
            expression="0"
            path='["editor", "numbers", 2]'
            allow-editing="true">
          </esm-expression-node>

          <p>Variables (double-click to edit):</p>
          <esm-expression-node
            data-testid="editable-variable-temp"
            expression='"temp"'
            path='["editor", "variables", 0]'
            allow-editing="true">
          </esm-expression-node>

          <esm-expression-node
            data-testid="editable-variable-x"
            expression='"x"'
            path='["editor", "variables", 1]'
            allow-editing="true">
          </esm-expression-node>

          <div data-testid="insertion-point" style="min-height: 50px; border: 2px dashed #ccc; margin: 10px 0;">
            <p>Click here and press Ctrl+Space for expression palette</p>
          </div>

          <div data-testid="expression-result" style="font-size: 18px; margin: 10px 0;"></div>
        </div>

        <div class="palette" data-testid="expression-palette" style="display: none;">
          <h3>Expression Palette</h3>
          <div data-testid="palette-category-math">
            <h4>Math</h4>
            <button data-testid="palette-sin">sin()</button>
            <button data-testid="palette-cos">cos()</button>
            <button data-testid="palette-log">log()</button>
          </div>
          <div data-testid="palette-category-trig">
            <h4>Trigonometry</h4>
            <button data-testid="palette-sinh">sinh()</button>
            <button data-testid="palette-cosh">cosh()</button>
          </div>
          <div data-testid="palette-category-constants">
            <h4>Constants</h4>
            <button>π</button>
            <button>e</button>
          </div>
        </div>

        <script type="module" src="./expression-editor-demo.js"></script>
      </body>
      </html>
    `
  },

  {
    title: 'Model Editor Demo',
    path: '/demo/model-editor',
    html: `
      <!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Model Editor Demo</title>
        <style>
          body { font-family: Arial, sans-serif; padding: 20px; }
          .model-container { max-width: 800px; margin: 0 auto; }
          .panel { border: 1px solid #ccc; padding: 15px; margin: 10px 0; }
          table { width: 100%; border-collapse: collapse; }
          th, td { padding: 8px; border: 1px solid #ddd; text-align: left; }
          .dialog { position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
                   background: white; border: 2px solid #ccc; padding: 20px; z-index: 1000; }
          .overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                    background: rgba(0,0,0,0.5); z-index: 999; }
        </style>
      </head>
      <body>
        <div class="model-container">
          <h1>Model Editor Demo</h1>

          <div class="panel">
            <h2>Variables</h2>
            <button data-testid="add-variable-button">Add Variable</button>

            <table data-testid="variables-list">
              <thead>
                <tr><th>Name</th><th>Type</th><th>Units</th><th>Actions</th></tr>
              </thead>
              <tbody>
                <tr data-testid="variable-row-temperature">
                  <td>temperature</td>
                  <td><span data-testid="variable-type-temperature">state</span></td>
                  <td>K</td>
                  <td>
                    <button data-testid="edit-variable-button">Edit</button>
                    <button data-testid="delete-variable-button">Delete</button>
                  </td>
                </tr>
                <tr data-testid="variable-row-pressure">
                  <td>pressure</td>
                  <td>parameter</td>
                  <td>Pa</td>
                  <td>
                    <button>Edit</button>
                    <button>Delete</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="panel">
            <h2>Equations</h2>
            <button data-testid="add-equation-button">Add Equation</button>

            <div data-testid="equations-list">
              <div data-testid="equation-0">
                d(temperature)/dt = -k⋅temperature
              </div>
            </div>
          </div>

          <div class="panel" data-testid="model-validation-panel">
            <h2>Validation</h2>
            <div>Model is valid ✓</div>
          </div>
        </div>

        <!-- Variable Dialog -->
        <div class="overlay" data-testid="variable-dialog-overlay" style="display: none;"></div>
        <div class="dialog" data-testid="variable-dialog" style="display: none;">
          <h3>Variable Properties</h3>
          <form>
            <label for="variable-name">Name:</label>
            <input id="variable-name" data-testid="variable-name-input" />
            <div data-testid="variable-name-error" style="color: red; display: none;"></div>

            <label for="variable-type">Type:</label>
            <select id="variable-type" data-testid="variable-type-select">
              <option value="state">State</option>
              <option value="parameter">Parameter</option>
              <option value="observed">Observed</option>
            </select>

            <label for="variable-units">Units:</label>
            <input id="variable-units" data-testid="variable-units-input" />

            <label for="variable-description">Description:</label>
            <textarea id="variable-description" data-testid="variable-description-input"></textarea>

            <button type="button" data-testid="save-variable-button">Save</button>
            <button type="button" data-testid="cancel-variable-button">Cancel</button>
          </form>
        </div>

        <!-- Equation Dialog -->
        <div class="dialog" data-testid="equation-dialog" style="display: none;">
          <h3>Add Equation</h3>
          <form>
            <label for="equation-type">Type:</label>
            <select id="equation-type" data-testid="equation-type-select">
              <option value="differential">Differential</option>
              <option value="algebraic">Algebraic</option>
            </select>

            <label for="equation-lhs">Left Side:</label>
            <input id="equation-lhs" data-testid="equation-lhs-input" placeholder="e.g., d(temperature)/dt" />

            <label for="equation-rhs">Right Side:</label>
            <input id="equation-rhs" data-testid="equation-rhs-input" placeholder="e.g., -k * temperature" />

            <div data-testid="equation-syntax-error" style="color: red; display: none;"></div>
            <div data-testid="dimensional-error" style="color: orange; display: none;"></div>

            <button type="button" data-testid="save-equation-button">Save</button>
            <button type="button">Cancel</button>
          </form>
        </div>

        <!-- Confirmation Dialog -->
        <div class="dialog" data-testid="confirm-delete-dialog" style="display: none;">
          <h3>Confirm Deletion</h3>
          <p>Are you sure you want to delete this item?</p>
          <button data-testid="confirm-delete-button">Delete</button>
          <button>Cancel</button>
        </div>

        <script type="module" src="./model-editor-demo.js"></script>
      </body>
      </html>
    `
  }
];

export function createDemoServer() {
  // This would typically create an Express server serving the demo pages
  // For testing purposes, the HTML content is available statically
  console.log('Demo pages configured:', demoPages.map(p => p.path));
}