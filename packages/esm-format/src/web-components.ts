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
import type { Expression, Model, EsmFile } from './types.js';
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
    return () => {
      const errorDiv = document.createElement('div');
      errorDiv.className = 'error-state';
      errorDiv.textContent = 'Missing required attribute: expression';
      return errorDiv;
    };
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

    return () => ExpressionNode(componentProps);
  } catch (error) {
    return () => {
      const errorDiv = document.createElement('div');
      errorDiv.className = 'error-state';
      errorDiv.textContent = `Component error: ${error instanceof Error ? error.message : 'Unknown error'}`;
      return errorDiv;
    };
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

    return () => ModelEditor(componentProps);
  } catch (error) {
    return () => {
      const errorDiv = document.createElement('div');
      errorDiv.className = 'error-state';
      errorDiv.textContent = `Component error: ${error instanceof Error ? error.message : 'Unknown error'}`;
      return errorDiv;
    };
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

    return () => CouplingGraph(componentProps);
  } catch (error) {
    return () => {
      const errorDiv = document.createElement('div');
      errorDiv.className = 'error-state';
      errorDiv.textContent = `Component error: ${error instanceof Error ? error.message : 'Unknown error'}`;
      return errorDiv;
    };
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
      ...EsmExpressionNodeComponent,
      element: null  // Will be set by solid-element
    }, ['expression', 'path', 'allow-editing', 'is-selected']);

    customElement('esm-model-editor', {
      ...EsmModelEditorComponent,
      element: null  // Will be set by solid-element
    }, ['model', 'allow-editing', 'show-validation', 'validation-errors']);

    customElement('esm-coupling-graph', {
      ...EsmCouplingGraphComponent,
      element: null  // Will be set by solid-element
    }, ['esm-file', 'width', 'height', 'interactive']);

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
  EsmCouplingGraphProps
};