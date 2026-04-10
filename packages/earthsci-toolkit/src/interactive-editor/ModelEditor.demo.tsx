/**
 * ModelEditor Demo - Interactive demonstration of the ModelEditor component
 *
 * This demo shows the ModelEditor with a sample atmospheric chemistry model
 * and demonstrates all the key features including variable management,
 * equation editing, and event handling.
 */

import { Component, createSignal, createMemo } from 'solid-js';
import { render } from 'solid-js/web';
import { ModelEditor } from './ModelEditor.js';
import type { Model } from '../types.js';

// Import styles
import './ModelEditor.css';
import './ExpressionNode.css';

// Sample atmospheric chemistry model for demonstration
const initialModel: Model = {
  reference: {
    citation: "Sample atmospheric chemistry model for demonstration",
    notes: "Simplified NOx-O3 chemistry"
  },
  variables: {
    // State variables (species concentrations)
    NO: {
      type: 'state',
      units: 'mol/mol',
      description: 'Nitric oxide concentration',
      default: 0.1e-9
    },
    NO2: {
      type: 'state',
      units: 'mol/mol',
      description: 'Nitrogen dioxide concentration',
      default: 1.0e-9
    },
    O3: {
      type: 'state',
      units: 'mol/mol',
      description: 'Ozone concentration',
      default: 40e-9
    },

    // Parameters
    T: {
      type: 'parameter',
      units: 'K',
      default: 298.15,
      description: 'Temperature'
    },
    P: {
      type: 'parameter',
      units: 'Pa',
      default: 101325.0,
      description: 'Pressure'
    },
    jNO2: {
      type: 'parameter',
      units: '1/s',
      default: 0.005,
      description: 'NO2 photolysis rate'
    },
    k1: {
      type: 'parameter',
      units: 'cm^3/(molec*s)',
      default: 1.8e-12,
      description: 'NO + O3 reaction rate constant at 298K'
    },

    // Observed variables
    NOx: {
      type: 'observed',
      units: 'mol/mol',
      description: 'Total reactive nitrogen'
    }
  },
  equations: [
    // NO evolution: d[NO]/dt = jNO2*[NO2] - k1*[NO]*[O3]
    {
      lhs: { op: 'D', args: ['NO'], wrt: 't' },
      rhs: {
        op: '-',
        args: [
          { op: '*', args: ['jNO2', 'NO2'] },
          {
            op: '*',
            args: [
              'k1',
              { op: '*', args: ['NO', 'O3'] }
            ]
          }
        ]
      }
    },
    // NO2 evolution: d[NO2]/dt = k1*[NO]*[O3] - jNO2*[NO2]
    {
      lhs: { op: 'D', args: ['NO2'], wrt: 't' },
      rhs: {
        op: '-',
        args: [
          {
            op: '*',
            args: [
              'k1',
              { op: '*', args: ['NO', 'O3'] }
            ]
          },
          { op: '*', args: ['jNO2', 'NO2'] }
        ]
      }
    },
    // O3 evolution: d[O3]/dt = -k1*[NO]*[O3]
    {
      lhs: { op: 'D', args: ['O3'], wrt: 't' },
      rhs: {
        op: '*',
        args: [
          { op: '-', args: ['k1'] },
          { op: '*', args: ['NO', 'O3'] }
        ]
      }
    },
    // NOx is observed: NOx = NO + NO2
    {
      lhs: 'NOx',
      rhs: { op: '+', args: ['NO', 'NO2'] }
    }
  ],
  discrete_events: [
    {
      name: 'morning_emission_pulse',
      trigger: { type: 'time', at: 3600 }, // 1 hour in seconds
      affects: [
        { lhs: 'NO', rhs: { op: '+', args: ['NO', 5e-9] } }
      ]
    }
  ],
  continuous_events: [
    {
      name: 'high_ozone_alert',
      conditions: [{ op: '>', args: ['O3', 120e-9] }],
      affects: [
        { lhs: 'jNO2', rhs: { op: '*', args: ['jNO2', 1.5] } }
      ]
    }
  ]
};

/**
 * Demo component that showcases the ModelEditor
 */
const ModelEditorDemo: Component = () => {
  const [model, setModel] = createSignal<Model>(initialModel);
  const [validationErrors, setValidationErrors] = createSignal<string[]>([]);
  const [showJSON, setShowJSON] = createSignal(false);

  // Simple validation - check for undefined variables in expressions
  const validateModel = createMemo(() => {
    const errors: string[] = [];
    const varNames = new Set(Object.keys(model().variables));

    // Check equations for undefined variables
    model().equations.forEach((eq, i) => {
      const varsInEq = extractVariables(eq.lhs).concat(extractVariables(eq.rhs));
      varsInEq.forEach(varName => {
        if (!varNames.has(varName)) {
          errors.push(`Equation ${i + 1}: Undefined variable "${varName}"`);
        }
      });
    });

    setValidationErrors(errors);
    return errors;
  });

  // Update validation when model changes
  createMemo(() => validateModel());

  const handleModelChange = (updatedModel: Model) => {
    setModel(updatedModel);
    console.log('Model updated:', updatedModel);
  };

  return (
    <div style={{
      "font-family": "system-ui, sans-serif",
      "max-width": "1200px",
      "margin": "0 auto",
      "padding": "20px"
    }}>
      <h1>ModelEditor Demo</h1>
      <p>
        This demonstrates the ModelEditor component with a sample atmospheric chemistry model.
        Try editing variables, equations, and observe the live validation feedback.
      </p>

      <div style={{
        "display": "grid",
        "grid-template-columns": showJSON() ? "1fr 1fr" : "1fr",
        "gap": "20px",
        "margin-top": "20px"
      }}>
        {/* ModelEditor */}
        <div style={{
          "border": "1px solid #ddd",
          "border-radius": "8px",
          "overflow": "hidden"
        }}>
          <ModelEditor
            model={model()}
            onChange={handleModelChange}
            allowEditing={true}
            showValidation={true}
            validationErrors={validationErrors()}
          />
        </div>

        {/* JSON View (optional) */}
        {showJSON() && (
          <div style={{
            "border": "1px solid #ddd",
            "border-radius": "8px",
            "padding": "16px",
            "background": "#f8f9fa"
          }}>
            <h3 style={{ "margin-top": "0" }}>Model JSON</h3>
            <pre style={{
              "font-size": "12px",
              "overflow": "auto",
              "max-height": "600px",
              "background": "white",
              "padding": "12px",
              "border-radius": "4px",
              "border": "1px solid #e9ecef"
            }}>
              {JSON.stringify(model(), null, 2)}
            </pre>
          </div>
        )}
      </div>

      {/* Controls */}
      <div style={{
        "margin-top": "20px",
        "padding": "16px",
        "background": "#f8f9fa",
        "border-radius": "8px"
      }}>
        <h3 style={{ "margin-top": "0" }}>Demo Controls</h3>
        <label style={{ "display": "flex", "align-items": "center", "gap": "8px" }}>
          <input
            type="checkbox"
            checked={showJSON()}
            onChange={(e) => setShowJSON(e.currentTarget.checked)}
          />
          Show JSON representation
        </label>

        <div style={{ "margin-top": "12px" }}>
          <button
            onClick={() => setModel(initialModel)}
            style={{
              "padding": "8px 16px",
              "background": "#007bff",
              "color": "white",
              "border": "none",
              "border-radius": "4px",
              "cursor": "pointer",
              "margin-right": "8px"
            }}
          >
            Reset Model
          </button>

          <button
            onClick={() => console.log('Current model:', model())}
            style={{
              "padding": "8px 16px",
              "background": "#28a745",
              "color": "white",
              "border": "none",
              "border-radius": "4px",
              "cursor": "pointer"
            }}
          >
            Log Model to Console
          </button>
        </div>
      </div>

      {/* Instructions */}
      <div style={{
        "margin-top": "20px",
        "padding": "16px",
        "background": "#e3f2fd",
        "border-radius": "8px"
      }}>
        <h3 style={{ "margin-top": "0" }}>Try These Features:</h3>
        <ul style={{ "line-height": "1.6" }}>
          <li><strong>Variables Tab:</strong> Click on variables to edit their properties, add new ones, or remove existing ones</li>
          <li><strong>Equations Tab:</strong> Double-click on numbers and variables in equations to edit them inline</li>
          <li><strong>Variable Highlighting:</strong> Hover over variables to see them highlighted throughout equations</li>
          <li><strong>Type Badges:</strong> Notice the color-coded badges showing variable types (state, parameter, observed)</li>
          <li><strong>Events Tab:</strong> View discrete and continuous events that affect the model</li>
          <li><strong>Live Validation:</strong> Try referencing an undefined variable to see validation errors</li>
          <li><strong>Add/Remove:</strong> Use the "+" buttons to add new variables or equations</li>
        </ul>
      </div>
    </div>
  );
};

// Helper function to extract variable names from expressions (simplified)
function extractVariables(expr: any): string[] {
  if (typeof expr === 'string') {
    // Simple check - if it's a string and not a number, treat as variable
    return isNaN(Number(expr)) ? [expr] : [];
  }
  if (typeof expr === 'object' && expr && 'args' in expr) {
    const vars: string[] = [];
    expr.args.forEach((arg: any) => {
      vars.push(...extractVariables(arg));
    });
    return vars;
  }
  return [];
}

// Mount the demo (for use in HTML file)
if (typeof window !== 'undefined') {
  const container = document.getElementById('model-editor-demo');
  if (container) {
    render(() => <ModelEditorDemo />, container);
  }
}

export { ModelEditorDemo, ModelEditor };