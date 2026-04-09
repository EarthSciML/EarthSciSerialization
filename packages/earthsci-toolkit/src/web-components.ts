/**
 * Web Components Export - Export SolidJS components as standard custom elements
 *
 * This module uses solid-element to convert SolidJS components into standard
 * web components that can be used in any framework or vanilla HTML.
 *
 * Components exported:
 * - <esm-expression-node> - Interactive expression rendering
 * - <esm-model-editor> - Full model editing interface
 * - <esm-coupling-graph> - Visual coupling graph
 */

import { customElement } from 'solid-element';
import { ExpressionNode, type ExpressionNodeProps } from './interactive-editor/ExpressionNode.js';
import { ModelEditor, type ModelEditorProps } from './interactive-editor/ModelEditor.js';
import { CouplingGraph, type CouplingGraphProps } from './interactive-editor/CouplingGraph.js';
import { ValidationPanel, type ValidationPanelProps } from './interactive-editor/ValidationPanel.js';
import { FileSummary, type FileSummaryProps } from './interactive-editor/FileSummary.js';
import { SimulationControls, type SimulationControlsProps } from './interactive-editor/SimulationControls.js';
import type { Expression, Model, EsmFile, ValidationError } from './types.js';
import { createSignal } from 'solid-js';

// Import CSS styles
import './web-components.css';

/**
 * Web component wrapper for ExpressionNode
 *
 * Usage:
 * <esm-expression-node
 *   expression='{"op": "+", "args": [1, 2]}'
 *   path='["root"]'
 *   allow-editing="true">
 * </esm-expression-node>
 */
export interface EsmExpressionNodeProps {
  /** JSON string of the expression to render */
  expression: string;

  /** JSON array string of the path for this node */
  path: string;

  /** Whether inline editing is enabled */
  'allow-editing'?: boolean;

  /** Whether this node is currently selected */
  'is-selected'?: boolean;
}

/**
 * Web component wrapper for ModelEditor
 *
 * Usage:
 * <esm-model-editor
 *   model='{"variables": {...}, "equations": [...]}'
 *   allow-editing="true">
 * </esm-model-editor>
 */
export interface EsmModelEditorProps {
  /** JSON string of the model to edit */
  model: string;

  /** Whether inline editing is enabled */
  'allow-editing'?: boolean;

  /** Whether to show validation errors inline */
  'show-validation'?: boolean;

  /** JSON array string of validation errors to display */
  'validation-errors'?: string;
}

/**
 * Web component wrapper for CouplingGraph
 *
 * Usage:
 * <esm-coupling-graph
 *   esm-file='{"components": [...], "coupling": [...]}'
 *   width="800"
 *   height="600"
 *   interactive="true">
 * </esm-coupling-graph>
 */
export interface EsmCouplingGraphProps {
  /** JSON string of the ESM file to visualize */
  'esm-file': string;

  /** Width of the visualization area */
  width?: number;

  /** Height of the visualization area */
  height?: number;

  /** Whether the visualization should be interactive */
  interactive?: boolean;
}

/**
 * Web component wrapper for ValidationPanel
 *
 * Usage:
 * <esm-validation-panel
 *   model='{"variables": {...}, "equations": [...]}'
 *   validation-errors='[{"message": "Error", "path": "..."}]'
 *   show-details="true">
 * </esm-validation-panel>
 */
export interface EsmValidationPanelProps {
  /** JSON string of the model being validated */
  model: string;

  /** JSON array string of validation errors */
  'validation-errors': string;

  /** JSON array string of validation warnings */
  'validation-warnings'?: string;

  /** Whether the panel should auto-update when model changes */
  'auto-validate'?: boolean;

  /** Whether to show detailed error information */
  'show-details'?: boolean;
}

/**
 * Web component wrapper for FileSummary
 *
 * Usage:
 * <esm-file-summary
 *   esm-file='{"components": [...], "coupling": [...]}'
 *   show-details="true"
 *   show-export-options="true">
 * </esm-file-summary>
 */
export interface EsmFileSummaryProps {
  /** JSON string of the ESM file to summarize */
  'esm-file': string;

  /** Whether to show detailed statistics */
  'show-details'?: boolean;

  /** Whether to show export options */
  'show-export-options'?: boolean;
}

/**
 * Web component wrapper for SimulationControls
 *
 * Usage:
 * <esm-simulation-controls
 *   esm-file='{"components": [...], "coupling": [...]}'
 *   is-running="false"
 *   progress="50"
 *   available-backends='["julia", "python"]'>
 * </esm-simulation-controls>
 */
export interface EsmSimulationControlsProps {
  /** JSON string of the ESM file to simulate */
  'esm-file': string;

  /** Whether simulation is currently running */
  'is-running'?: boolean;

  /** Current simulation progress (0-100) */
  progress?: number;

  /** Simulation status message */
  'status-message'?: string;

  /** JSON array string of available simulation backends */
  'available-backends'?: string;

  /** Current selected backend */
  'selected-backend'?: string;

  /** JSON string of simulation parameters */
  'simulation-params'?: string;
}

/**
 * Convert kebab-case attributes to camelCase props and handle type conversions
 */
function convertWebComponentProps<T>(
  attrs: Record<string, any>,
  conversions: Record<string, (value: string) => any> = {}
): T {
  const props: Record<string, any> = {};

  for (const [key, value] of Object.entries(attrs)) {
    // Convert kebab-case to camelCase
    const camelKey = key.replace(/-([a-z])/g, (_, char) => char.toUpperCase());

    // Apply custom conversions
    if (conversions[key]) {
      props[camelKey] = conversions[key](value);
    } else if (typeof value === 'string') {
      // Handle common string conversions
      if (value === 'true' || value === 'false') {
        props[camelKey] = value === 'true';
      } else if (/^\d+$/.test(value)) {
        props[camelKey] = parseInt(value, 10);
      } else if (/^\d*\.\d+$/.test(value)) {
        props[camelKey] = parseFloat(value);
      } else {
        props[camelKey] = value;
      }
    } else {
      props[camelKey] = value;
    }
  }

  return props as T;
}

// Web component definitions with proper event handling
export const EsmExpressionNodeComponent = (props: any) => {
  // Validate required props
  if (!props.expression) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-state';
    errorDiv.textContent = 'Missing required attribute: expression';
    return errorDiv;
  }

  try {
    // Parse JSON strings
    const expression: Expression = JSON.parse(props.expression);
    const path: (string | number)[] = JSON.parse(props.path || '[]');

    // Handle missing highlightedVars
    const [highlightedVars] = createSignal(new Set<string>());

    // Convert props
    const componentProps: ExpressionNodeProps = {
      expr: expression,
      path: path,
      highlightedVars: () => highlightedVars(),
      onHoverVar: (name: string | null) => {
        if (typeof window !== 'undefined' && props.element) {
          const event = new CustomEvent('variableHover', {
            detail: { variableName: name },
            bubbles: true
          });
          props.element.dispatchEvent(event);
        }
      },
      onSelect: (path: (string | number)[]) => {
        if (typeof window !== 'undefined' && props.element) {
          const event = new CustomEvent('expressionSelect', {
            detail: { path },
            bubbles: true
          });
          props.element.dispatchEvent(event);
        }
      },
      onReplace: (path: (string | number)[], newExpr: Expression) => {
        if (typeof window !== 'undefined' && props.element) {
          const event = new CustomEvent('expressionReplace', {
            detail: { path, expression: newExpr },
            bubbles: true
          });
          props.element.dispatchEvent(event);
        }
      },
      isSelected: props['is-selected'] === 'true' || props['is-selected'] === true,
      allowEditing: props['allow-editing'] !== 'false'
    };

    return ExpressionNode(componentProps);
  } catch (error) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-state';
    errorDiv.textContent = `Component error: ${error instanceof Error ? error.message : 'Unknown error'}`;
    return errorDiv;
  }
};

export const EsmModelEditorComponent = (props: any) => {
  // Validate required props
  if (!props.model) {
    return () => {
      const errorDiv = document.createElement('div');
      errorDiv.className = 'error-state';
      errorDiv.textContent = 'Missing required attribute: model';
      return errorDiv;
    };
  }

  try {
    // Parse JSON strings
    const model: Model = JSON.parse(props.model);
    const validationErrors: string[] = props['validation-errors']
      ? JSON.parse(props['validation-errors'])
      : [];

    // Convert props
    const componentProps: ModelEditorProps = {
      model: model,
      onChange: (updatedModel: Model) => {
        if (typeof window !== 'undefined' && props.element) {
          const event = new CustomEvent('modelChange', {
            detail: updatedModel,
            bubbles: true
          });
          props.element.dispatchEvent(event);
        }
      },
      allowEditing: props['allow-editing'] !== 'false',
      showValidation: props['show-validation'] !== 'false',
      validationErrors: validationErrors
    };

    return ModelEditor(componentProps);
  } catch (error) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-state';
    errorDiv.textContent = `Component error: ${error instanceof Error ? error.message : 'Unknown error'}`;
    return errorDiv;
  }
};

export const EsmCouplingGraphComponent = (props: any) => {
  // Validate required props
  const esmFileValue = props['esm-file'] || props.esmFile;
  if (!esmFileValue) {
    return () => {
      const errorDiv = document.createElement('div');
      errorDiv.className = 'error-state';
      errorDiv.textContent = 'Missing required attribute: esm-file';
      return errorDiv;
    };
  }

  try {
    // Parse JSON strings
    const esmFile: EsmFile = JSON.parse(esmFileValue);

    // Convert props
    const componentProps: CouplingGraphProps = {
      esmFile: esmFile,
      onEditCoupling: (coupling: any, edgeId: string) => {
        if (typeof window !== 'undefined' && props.element) {
          const event = new CustomEvent('couplingEdit', {
            detail: { coupling, edgeId },
            bubbles: true
          });
          props.element.dispatchEvent(event);
        }
      },
      onSelectComponent: (componentId: string) => {
        if (typeof window !== 'undefined' && props.element) {
          const event = new CustomEvent('componentSelect', {
            detail: { componentId },
            bubbles: true
          });
          props.element.dispatchEvent(event);
        }
      },
      width: props.width ? parseInt(props.width, 10) : undefined,
      height: props.height ? parseInt(props.height, 10) : undefined,
      interactive: props.interactive !== 'false'
    };

    return CouplingGraph(componentProps);
  } catch (error) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-state';
    errorDiv.textContent = `Component error: ${error instanceof Error ? error.message : 'Unknown error'}`;
    return errorDiv;
  }
};

export const EsmValidationPanelComponent = (props: any) => {
  // Validate required props
  if (!props.model) {
    return () => {
      const errorDiv = document.createElement('div');
      errorDiv.className = 'error-state';
      errorDiv.textContent = 'Missing required attribute: model';
      return errorDiv;
    };
  }

  if (!props['validation-errors']) {
    return () => {
      const errorDiv = document.createElement('div');
      errorDiv.className = 'error-state';
      errorDiv.textContent = 'Missing required attribute: validation-errors';
      return errorDiv;
    };
  }

  try {
    // Parse JSON strings
    const model: Model = JSON.parse(props.model);
    const validationErrors: ValidationError[] = JSON.parse(props['validation-errors']);
    const validationWarnings: ValidationError[] = props['validation-warnings']
      ? JSON.parse(props['validation-warnings'])
      : [];

    // Convert props
    const componentProps: ValidationPanelProps = {
      model: model,
      validationErrors: validationErrors,
      validationWarnings: validationWarnings,
      autoValidate: props['auto-validate'] !== 'false',
      showDetails: props['show-details'] !== 'false',
      onErrorClick: (error: ValidationError) => {
        if (typeof window !== 'undefined' && props.element) {
          const event = new CustomEvent('errorClick', {
            detail: error,
            bubbles: true
          });
          props.element.dispatchEvent(event);
        }
      }
    };

    return ValidationPanel(componentProps);
  } catch (error) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-state';
    errorDiv.textContent = `Component error: ${error instanceof Error ? error.message : 'Unknown error'}`;
    return errorDiv;
  }
};

export const EsmFileSummaryComponent = (props: any) => {
  // Validate required props
  const esmFileValue = props['esm-file'] || props.esmFile;
  if (!esmFileValue) {
    return () => {
      const errorDiv = document.createElement('div');
      errorDiv.className = 'error-state';
      errorDiv.textContent = 'Missing required attribute: esm-file';
      return errorDiv;
    };
  }

  try {
    // Parse JSON strings
    const esmFile: EsmFile = JSON.parse(esmFileValue);

    // Convert props
    const componentProps: FileSummaryProps = {
      esmFile: esmFile,
      showDetails: props['show-details'] !== 'false',
      showExportOptions: props['show-export-options'] !== 'false',
      onComponentTypeClick: (componentType: string) => {
        if (typeof window !== 'undefined' && props.element) {
          const event = new CustomEvent('componentTypeClick', {
            detail: { componentType },
            bubbles: true
          });
          props.element.dispatchEvent(event);
        }
      },
      onExport: (format: 'json' | 'yaml' | 'toml') => {
        if (typeof window !== 'undefined' && props.element) {
          const event = new CustomEvent('export', {
            detail: { format },
            bubbles: true
          });
          props.element.dispatchEvent(event);
        }
      }
    };

    return FileSummary(componentProps);
  } catch (error) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-state';
    errorDiv.textContent = `Component error: ${error instanceof Error ? error.message : 'Unknown error'}`;
    return errorDiv;
  }
};

export const EsmSimulationControlsComponent = (props: any) => {
  // Validate required props
  const esmFileValue = props['esm-file'] || props.esmFile;
  if (!esmFileValue) {
    return () => {
      const errorDiv = document.createElement('div');
      errorDiv.className = 'error-state';
      errorDiv.textContent = 'Missing required attribute: esm-file';
      return errorDiv;
    };
  }

  try {
    // Parse JSON strings
    const esmFile: EsmFile = JSON.parse(esmFileValue);
    const availableBackends: string[] = props['available-backends']
      ? JSON.parse(props['available-backends'])
      : [];
    const simulationParams = props['simulation-params']
      ? JSON.parse(props['simulation-params'])
      : undefined;

    // Convert props
    const componentProps: SimulationControlsProps = {
      esmFile: esmFile,
      isRunning: props['is-running'] === 'true' || props['is-running'] === true,
      progress: props.progress ? parseFloat(props.progress) : undefined,
      statusMessage: props['status-message'],
      availableBackends: availableBackends.length > 0 ? availableBackends : undefined,
      selectedBackend: props['selected-backend'],
      simulationParams: simulationParams,
      onStartSimulation: (params) => {
        if (typeof window !== 'undefined' && props.element) {
          const event = new CustomEvent('startSimulation', {
            detail: params,
            bubbles: true
          });
          props.element.dispatchEvent(event);
        }
      },
      onStopSimulation: () => {
        if (typeof window !== 'undefined' && props.element) {
          const event = new CustomEvent('stopSimulation', {
            bubbles: true
          });
          props.element.dispatchEvent(event);
        }
      },
      onPauseResume: (isPaused: boolean) => {
        if (typeof window !== 'undefined' && props.element) {
          const event = new CustomEvent('pauseResume', {
            detail: { isPaused },
            bubbles: true
          });
          props.element.dispatchEvent(event);
        }
      },
      onParametersChange: (params) => {
        if (typeof window !== 'undefined' && props.element) {
          const event = new CustomEvent('parametersChange', {
            detail: params,
            bubbles: true
          });
          props.element.dispatchEvent(event);
        }
      },
      onBackendChange: (backend: string) => {
        if (typeof window !== 'undefined' && props.element) {
          const event = new CustomEvent('backendChange', {
            detail: { backend },
            bubbles: true
          });
          props.element.dispatchEvent(event);
        }
      }
    };

    return SimulationControls(componentProps);
  } catch (error) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-state';
    errorDiv.textContent = `Component error: ${error instanceof Error ? error.message : 'Unknown error'}`;
    return errorDiv;
  }
};

// Register web components
export function registerWebComponents() {
  if (typeof window === 'undefined' || typeof customElements === 'undefined') {
    return; // Skip registration in non-browser environments
  }

  try {
    // Register components with proper shadow DOM and styling
    customElement('esm-expression-node', {
      expression: '',
      path: '[]',
      'allow-editing': true,
      'is-selected': false
    }, (props, { element }) => EsmExpressionNodeComponent({ ...props, element }));

    customElement('esm-model-editor', {
      model: '',
      'allow-editing': true,
      'show-validation': true,
      'validation-errors': '[]'
    }, (props, { element }) => EsmModelEditorComponent({ ...props, element }));

    customElement('esm-coupling-graph', {
      'esm-file': '',
      width: 800,
      height: 600,
      interactive: true
    }, (props, { element }) => EsmCouplingGraphComponent({ ...props, element }));

    customElement('esm-validation-panel', {
      model: '',
      'validation-errors': '[]',
      'validation-warnings': '[]',
      'auto-validate': true,
      'show-details': true
    }, (props, { element }) => EsmValidationPanelComponent({ ...props, element }));

    customElement('esm-file-summary', {
      'esm-file': '',
      'show-details': true,
      'show-export-options': true
    }, (props, { element }) => EsmFileSummaryComponent({ ...props, element }));

    customElement('esm-simulation-controls', {
      'esm-file': '',
      'is-running': false,
      progress: 0,
      'status-message': '',
      'available-backends': '[]',
      'selected-backend': '',
      'simulation-params': '{}'
    }, (props, { element }) => EsmSimulationControlsComponent({ ...props, element }));

  } catch (error) {
    console.warn('Failed to register ESM web components:', error);
  }
}

// Auto-register when module is imported
if (typeof window !== 'undefined') {
  registerWebComponents();
}

// Export component interfaces for TypeScript users
export type {
  EsmExpressionNodeProps,
  EsmModelEditorProps,
  EsmCouplingGraphProps,
  EsmValidationPanelProps,
  EsmFileSummaryProps,
  EsmSimulationControlsProps
};