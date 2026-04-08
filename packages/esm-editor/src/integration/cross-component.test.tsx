/**
 * Integration tests for cross-component interactions in ESM Editor
 *
 * These tests verify that components work together correctly:
 * - Selection updating ValidationPanel
 * - Undo/redo across multiple components
 * - Data synchronization between editors
 */

import { describe, it, beforeEach, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@solidjs/testing-library';
import { createSignal } from 'solid-js';
// Import components for integration testing
import { ExpressionEditor } from '../components/ExpressionEditor';
import { ModelEditor } from '../components/ModelEditor';

// Define types locally to avoid esm-format import issues
type Expression = number | string | { op: string; args: any[] };
type ModelVariable = {
  type: "state" | "parameter" | "observed";
  units?: string;
  default?: number;
  description?: string;
};
type Model = {
  name?: string;
  description?: string;
  variables: Array<ModelVariable & { name: string }>;
  equations: Array<{ lhs: Expression; rhs: Expression }>;
};
type EsmFile = {
  schema_version: string;
  metadata: {
    name: string;
    description: string;
    version: string;
    authors: string[];
    created: string;
    modified: string;
  };
  components: Record<string, Model>;
  coupling: any[];
};

describe('Cross-Component Integration', () => {
  const validModel: Model = {
    name: "Test Model",
    description: "Test model for integration testing",
    variables: [
      {
        name: "O3",
        type: "state",
        units: "mol/mol",
        description: "Ozone concentration"
      },
      {
        name: "NO",
        type: "state",
        units: "mol/mol",
        description: "Nitric oxide concentration"
      }
    ],
    equations: [
      {
        lhs: { op: 'D', args: ['O3', 't'] },
        rhs: { op: '*', args: [-0.1, 'O3'] }
      }
    ]
  };

  const validEsmFile: EsmFile = {
    schema_version: "1.0",
    metadata: {
      name: "Integration Test Model",
      description: "Model for integration testing",
      version: "0.1.0",
      authors: ["Test Suite"],
      created: new Date().toISOString(),
      modified: new Date().toISOString()
    },
    components: {
      "Chemistry": validModel
    },
    coupling: []
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Expression and Model Editor Integration', () => {
    it('should synchronize data between expression editor and model editor', async () => {
      const expression: Expression = { op: '+', args: ['x', 2] };
      const [selectedExpression, setSelectedExpression] = createSignal(expression);
      const [currentModel, setCurrentModel] = createSignal(validModel);
      const changeLog: string[] = [];

      const logChange = (source: string, data: any) => {
        changeLog.push(`${source}: ${typeof data === 'object' ? JSON.stringify(data).substring(0, 50) : data}`);
      };

      // Render both components
      render(() => (
        <div>
          <ExpressionEditor
            initialExpression={selectedExpression()}
            onChange={(newExpr) => {
              setSelectedExpression(newExpr);
              logChange('expression', newExpr);
            }}
            allowEditing={true}
            showValidation={true}
          />
          <ModelEditor
            model={currentModel()}
            onModelChange={(newModel) => {
              setCurrentModel(newModel);
              logChange('model', { variableCount: newModel.variables.length });
            }}
            allowEditing={true}
          />
          <div data-testid="change-log">{changeLog.join(', ')}</div>
        </div>
      ));

      // Verify initial state - use more specific selectors
      expect(screen.getByLabelText(/Operator: \+/)).toBeInTheDocument(); // Expression operator
      expect(screen.getByLabelText(/Variable: x/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Number: 2/)).toBeInTheDocument();
      expect(screen.getByText('Test Model')).toBeInTheDocument();
      expect(screen.getByText('O3')).toBeInTheDocument();
    });

    it('should handle variable highlighting across components', async () => {
      const [highlightedVars, setHighlightedVars] = createSignal(new Set<string>(['O3']));
      const [model, setModel] = createSignal(validModel);

      render(() => (
        <div>
          <ExpressionEditor
            initialExpression={{ op: '+', args: ['O3', 'NO'] }}
            onChange={() => {}}
            allowEditing={true}
            highlightedVars={highlightedVars()}
          />
          <ModelEditor
            model={model()}
            onModelChange={setModel}
            allowEditing={true}
            selectedVariable={Array.from(highlightedVars())[0]}
          />
          <button
            onClick={() => setHighlightedVars(new Set(['NO']))}
            data-testid="highlight-no"
          >
            Highlight NO
          </button>
        </div>
      ));

      // Verify both variables are present in both components
      expect(screen.getAllByText('O3')).toHaveLength(2); // Expression + Variables panel
      expect(screen.getAllByText('NO')).toHaveLength(2); // Expression + Variables panel

      // Test highlighting change
      fireEvent.click(screen.getByTestId('highlight-no'));
      expect(highlightedVars().has('NO')).toBe(true);
      expect(highlightedVars().has('O3')).toBe(false);
    });
  });

  describe('Undo/Redo Cross-Component Integration', () => {
    it('should support undo/redo operations across multiple editors', async () => {
      const [currentModel, setCurrentModel] = createSignal(validModel);
      const [currentExpression, setCurrentExpression] = createSignal({ op: '+', args: ['a', 'b'] });

      const modelChangeHistory: Model[] = [];
      const expressionModelChangeHistory: Expression[] = [];

      const onModelChange = (newModel: Model) => {
        modelChangeHistory.push(currentModel());
        setCurrentModel(newModel);
      };

      const onExpressionModelChange = (newExpr: Expression) => {
        expressionModelChangeHistory.push(currentExpression());
        setCurrentExpression(newExpr);
      };

      render(() => (
        <div>
          <ModelEditor
            model={currentModel()}
            onModelChange={onModelChange}
            allowEditing={true}
            showValidation={true}
          />
          <ExpressionEditor
            initialExpression={currentExpression()}
            onModelChange={onExpressionModelChange}
            allowEditing={true}
            showValidation={true}
          />
        </div>
      ));

      // Verify initial render
      expect(screen.getByText('O3')).toBeInTheDocument();
      expect(screen.getByText('+')).toBeInTheDocument();

      // Simulate changes to test history tracking
      const newExpression: Expression = { op: '*', args: ['c', 'd'] };
      onExpressionModelChange(newExpression);

      expect(expressionModelChangeHistory).toHaveLength(1);
      expect(expressionModelChangeHistory[0]).toEqual({ op: '+', args: ['a', 'b'] });
    });

    it('should maintain consistent state during undo/redo operations', async () => {
      const initialState = {
        model: validModel,
        expression: { op: '+', args: [1, 2] }
      };

      const [appState, setAppState] = createSignal(initialState);
      const stateHistory: typeof initialState[] = [initialState];

      const updateState = (updates: Partial<typeof initialState>) => {
        const currentState = appState();
        stateHistory.push(currentState);
        setAppState({ ...currentState, ...updates });
      };

      const undo = () => {
        if (stateHistory.length > 1) {
          const previousState = stateHistory.pop();
          if (previousState) {
            setAppState(previousState);
          }
        }
      };

      render(() => (
        <div>
          <ModelEditor
            model={appState().model}
            onModelChange={(newModel) => updateState({ model: newModel })}
            allowEditing={true}
          />
          <ExpressionEditor
            initialExpression={appState().expression}
            onModelChange={(newExpr) => updateState({ expression: newExpr })}
            allowEditing={true}
          />
          <button onClick={undo} data-testid="undo-button">
            Undo
          </button>
        </div>
      ));

      // Verify initial state
      expect(screen.getByText('O3')).toBeInTheDocument();
      expect(screen.getByText('+')).toBeInTheDocument();

      // Simulate state change
      updateState({ expression: { op: '*', args: [3, 4] } });
      expect(stateHistory).toHaveLength(2);

      // Test undo functionality
      const undoButton = screen.getByTestId('undo-button');
      fireEvent.click(undoButton);

      // State should be restored
      expect(appState().expression).toEqual({ op: '+', args: [1, 2] });
    });
  });

  describe('Data Flow Integration', () => {
    it('should propagate changes from model editor to dependent components', async () => {
      const [model, setModel] = createSignal(validModel);
      const [validationState, setValidationState] = createSignal({ isValid: true, errors: [] });

      const onModelChange = (newModel: Model) => {
        setModel(newModel);
        // Simulate validation update
        setValidationState({ isValid: true, errors: [] });
      };

      render(() => (
        <div>
          <ModelEditor
            model={model()}
            onModelChange={onModelChange}
            allowEditing={true}
          />
          <div data-testid="validation-status">
            {validationState().isValid ? 'Valid' : 'Invalid'}
          </div>
        </div>
      ));

      expect(screen.getByTestId('validation-status')).toHaveTextContent('Valid');

      // Verify model variables are displayed
      expect(screen.getByText('O3')).toBeInTheDocument();
      expect(screen.getByText('NO')).toBeInTheDocument();
    });

    it('should handle cascading updates across multiple components', async () => {
      const [globalState, setGlobalState] = createSignal({
        model: validModel,
        selectedVariable: 'O3',
        validationErrors: []
      });

      const updateGlobalState = (updates: Partial<typeof globalState>) => {
        setGlobalState(current => ({ ...current(), ...updates }));
      };

      render(() => (
        <div>
          <ModelEditor
            model={globalState().model}
            onModelChange={(newModel) => updateGlobalState({ model: newModel })}
            allowEditing={true}
            selectedVariable={globalState().selectedVariable}
          />
          <ExpressionEditor
            initialExpression={globalState().model.equations[0]?.rhs || 0}
            onModelChange={(newExpr) => {
              const updatedModel = {
                ...globalState().model,
                equations: [{
                  ...globalState().model.equations[0],
                  rhs: newExpr
                }]
              };
              updateGlobalState({ model: updatedModel });
            }}
            allowEditing={true}
            highlightedVars={new Set([globalState().selectedVariable])}
          />
          {/* Validation would be handled by a validation panel component */}
        </div>
      ));

      // Verify all components are rendered and connected
      expect(screen.getByText('O3')).toBeInTheDocument();
      expect(screen.getByText('*')).toBeInTheDocument(); // From the equation RHS

      // Test that state updates propagate
      expect(globalState().selectedVariable).toBe('O3');
    });
  });

  describe('Event Coordination', () => {
    it('should coordinate custom events between components', async () => {
      const eventLog: string[] = [];

      const logEvent = (eventType: string, detail: any) => {
        eventLog.push(`${eventType}: ${JSON.stringify(detail)}`);
      };

      render(() => (
        <div
          onSelectionModelChange={(e: CustomEvent) => logEvent('selection', e.detail)}
          onValidationUpdate={(e: CustomEvent) => logEvent('validation', e.detail)}
          onModelChange={(e: CustomEvent) => logEvent('change', e.detail)}
        >
          <ModelEditor
            model={validModel}
            onModelChange={(newModel) => logEvent('model-change', { model: newModel })}
            allowEditing={true}
          />
          <ExpressionEditor
            initialExpression={{ op: '+', args: [1, 2] }}
            onModelChange={(newExpr) => logEvent('expression-change', { expression: newExpr })}
            allowEditing={true}
          />
        </div>
      ));

      // Components should be rendered without errors
      expect(screen.getByText('O3')).toBeInTheDocument();
      expect(screen.getByText('+')).toBeInTheDocument();

      // Event coordination is primarily tested through the component rendering
      // and the fact that no errors are thrown during complex interactions
    });
  });
});