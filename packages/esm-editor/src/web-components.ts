/**
 * Web Components Export - Export ESM Editor SolidJS components as standard custom elements
 *
 * This module uses solid-element to convert SolidJS components into standard
 * web components that can be used in any framework (React, Vue, Svelte) or vanilla HTML.
 *
 * Components exported:
 * - <esm-expression-editor> - Interactive expression editing interface
 * - <esm-model-editor> - Full model editing interface
 * - <esm-file-editor> - Complete ESM file editor
 * - <esm-reaction-editor> - Reaction system editor
 * - <esm-coupling-graph> - Visual coupling graph editor
 */

import { customElement } from 'solid-element';
import { createSignal } from 'solid-js';
import type { Expression, EsmFile, Model, ReactionSystem } from 'esm-format';

// Import the editor components
import { EquationEditor, type EquationEditorProps } from './components/EquationEditor.js';
import { ModelEditor, type ModelEditorProps } from './components/ModelEditor.js';
import { ReactionEditor, type ReactionEditorProps } from './components/ReactionEditor.js';
import { CouplingGraph, type CouplingGraphProps } from './components/CouplingGraph.js';
import { ValidationPanel, type ValidationPanelProps } from './components/ValidationPanel.js';
import { FileSummary, type FileSummaryProps } from './components/FileSummary.js';

// Import styles
import './web-components.css';

/**
 * Web component wrapper for EquationEditor (expression editing)
 *
 * Usage:
 * <esm-expression-editor
 *   expression='{"op": "+", "args": [1, 2]}'
 *   allow-editing="true"
 *   show-palette="true">
 * </esm-expression-editor>
 */
export interface EsmExpressionEditorProps {
  /** JSON string of the expression to edit */
  expression: string;
  /** Whether editing is allowed */
  'allow-editing'?: boolean;
  /** Whether to show the expression palette */
  'show-palette'?: boolean;
  /** Whether to show validation errors */
  'show-validation'?: boolean;
}

/**
 * Web component wrapper for ModelEditor
 *
 * Usage:
 * <esm-model-editor
 *   model='{"variables": {...}, "equations": [...]}'
 *   allow-editing="true"
 *   show-validation="true">
 * </esm-model-editor>
 */
export interface EsmModelEditorProps {
  /** JSON string of the model to edit */
  model: string;
  /** Whether editing is allowed */
  'allow-editing'?: boolean;
  /** Whether to show validation errors inline */
  'show-validation'?: boolean;
  /** JSON array string of validation errors to display */
  'validation-errors'?: string;
}

/**
 * Web component wrapper for complete ESM file editing
 *
 * Usage:
 * <esm-file-editor
 *   esm-file='{"components": {...}, "coupling": [...]}'
 *   allow-editing="true"
 *   enable-undo="true">
 * </esm-file-editor>
 */
export interface EsmFileEditorProps {
  /** JSON string of the ESM file to edit */
  'esm-file': string;
  /** Whether editing is allowed */
  'allow-editing'?: boolean;
  /** Whether to enable undo/redo functionality */
  'enable-undo'?: boolean;
  /** Whether to show the file summary panel */
  'show-summary'?: boolean;
  /** Whether to show validation panel */
  'show-validation'?: boolean;
}

/**
 * Web component wrapper for ReactionEditor
 *
 * Usage:
 * <esm-reaction-editor
 *   reaction-system='{"species": {...}, "reactions": [...]}'
 *   allow-editing="true"
 *   show-validation="true">
 * </esm-reaction-editor>
 */
export interface EsmReactionEditorProps {
  /** JSON string of the reaction system to edit */
  'reaction-system': string;
  /** Whether editing is allowed */
  'allow-editing'?: boolean;
  /** Whether to show validation errors */
  'show-validation'?: boolean;
  /** JSON array string of validation errors */
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
 *   interactive="true"
 *   allow-editing="true">
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
  /** Whether coupling editing is allowed */
  'allow-editing'?: boolean;
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

export const EsmExpressionEditorComponent = (props: any) => {
  if (!props.expression) {
    return () => {
      const errorDiv = document.createElement('div');
      errorDiv.className = 'error-state';
      errorDiv.textContent = 'Missing required attribute: expression';
      return errorDiv;
    };
  }

  try {
    const expression: Expression = JSON.parse(props.expression);

    const componentProps: EquationEditorProps = {
      initialExpression: expression,
      onChange: (newExpr: Expression) => {
        if (typeof window !== 'undefined' && props.element) {
          const event = new CustomEvent('change', {
            detail: { expression: newExpr },
            bubbles: true
          });
          props.element.dispatchEvent(event);
        }
      },
      allowEditing: props['allow-editing'] !== 'false',
      showPalette: props['show-palette'] !== 'false',
      showValidation: props['show-validation'] !== 'false'
    };

    return () => EquationEditor(componentProps);
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
  if (!props.model) {
    return () => {
      const errorDiv = document.createElement('div');
      errorDiv.className = 'error-state';
      errorDiv.textContent = 'Missing required attribute: model';
      return errorDiv;
    };
  }

  try {
    const model: Model = JSON.parse(props.model);
    const validationErrors: string[] = props['validation-errors']
      ? JSON.parse(props['validation-errors'])
      : [];

    const componentProps: ModelEditorProps = {
      model: model,
      onChange: (updatedModel: Model) => {
        if (typeof window !== 'undefined' && props.element) {
          const event = new CustomEvent('change', {
            detail: { model: updatedModel },
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

export const EsmFileEditorComponent = (props: any) => {
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
    const esmFile: EsmFile = JSON.parse(esmFileValue);
    const [currentFile, setCurrentFile] = createSignal(esmFile);

    // This would be a comprehensive file editor combining all components
    // For now, we'll use FileSummary as a placeholder
    const componentProps: FileSummaryProps = {
      esmFile: currentFile(),
      showDetails: props['show-summary'] !== 'false',
      showExportOptions: true,
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
            detail: { format, file: currentFile() },
            bubbles: true
          });
          props.element.dispatchEvent(event);
        }
      }
    };

    return () => FileSummary(componentProps);
  } catch (error) {
    return () => {
      const errorDiv = document.createElement('div');
      errorDiv.className = 'error-state';
      errorDiv.textContent = `Component error: ${error instanceof Error ? error.message : 'Unknown error'}`;
      return errorDiv;
    };
  }
};

export const EsmReactionEditorComponent = (props: any) => {
  const reactionSystemValue = props['reaction-system'] || props.reactionSystem;
  if (!reactionSystemValue) {
    return () => {
      const errorDiv = document.createElement('div');
      errorDiv.className = 'error-state';
      errorDiv.textContent = 'Missing required attribute: reaction-system';
      return errorDiv;
    };
  }

  try {
    const reactionSystem: ReactionSystem = JSON.parse(reactionSystemValue);
    const validationErrors: string[] = props['validation-errors']
      ? JSON.parse(props['validation-errors'])
      : [];

    const componentProps: ReactionEditorProps = {
      reactionSystem: reactionSystem,
      onChange: (updatedSystem: ReactionSystem) => {
        if (typeof window !== 'undefined' && props.element) {
          const event = new CustomEvent('change', {
            detail: { reactionSystem: updatedSystem },
            bubbles: true
          });
          props.element.dispatchEvent(event);
        }
      },
      allowEditing: props['allow-editing'] !== 'false',
      showValidation: props['show-validation'] !== 'false',
      validationErrors: validationErrors
    };

    return () => ReactionEditor(componentProps);
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
    const esmFile: EsmFile = JSON.parse(esmFileValue);

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
      interactive: props.interactive !== 'false',
      allowEditing: props['allow-editing'] !== 'false'
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

/**
 * Register all ESM editor web components
 */
export function registerWebComponents() {
  if (typeof window === 'undefined' || typeof customElements === 'undefined') {
    return; // Skip registration in non-browser environments
  }

  try {
    // Register editor components with proper shadow DOM and styling
    customElement('esm-expression-editor', {
      ...EsmExpressionEditorComponent,
      element: null  // Will be set by solid-element
    }, ['expression', 'allow-editing', 'show-palette', 'show-validation']);

    customElement('esm-model-editor', {
      ...EsmModelEditorComponent,
      element: null  // Will be set by solid-element
    }, ['model', 'allow-editing', 'show-validation', 'validation-errors']);

    customElement('esm-file-editor', {
      ...EsmFileEditorComponent,
      element: null  // Will be set by solid-element
    }, ['esm-file', 'allow-editing', 'enable-undo', 'show-summary', 'show-validation']);

    customElement('esm-reaction-editor', {
      ...EsmReactionEditorComponent,
      element: null  // Will be set by solid-element
    }, ['reaction-system', 'allow-editing', 'show-validation', 'validation-errors']);

    customElement('esm-coupling-graph', {
      ...EsmCouplingGraphComponent,
      element: null  // Will be set by solid-element
    }, ['esm-file', 'width', 'height', 'interactive', 'allow-editing']);

    console.log('ESM Editor web components registered successfully');

  } catch (error) {
    console.warn('Failed to register ESM Editor web components:', error);
  }
}

// Auto-register when module is imported in browser environment
if (typeof window !== 'undefined') {
  // Delay registration to ensure solid-element is loaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', registerWebComponents);
  } else {
    // Document is already loaded
    setTimeout(registerWebComponents, 0);
  }
}

// Export component interfaces for TypeScript users
export type {
  EsmExpressionEditorProps,
  EsmModelEditorProps,
  EsmFileEditorProps,
  EsmReactionEditorProps,
  EsmCouplingGraphProps
};