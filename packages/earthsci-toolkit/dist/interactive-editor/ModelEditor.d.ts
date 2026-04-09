/**
 * ModelEditor - SolidJS component for comprehensive model editing
 *
 * This component displays all equations in a model with editable variables panel,
 * equation list, and event editor. Provides full model editing capabilities with
 * live validation feedback and integration with ExpressionNode.
 *
 * Features:
 * - Variables panel with type badges (state/parameter/observed) and units
 * - Equation list with inline editing via ExpressionNode
 * - Event editor for discrete and continuous events
 * - Add/remove equations via UI
 * - Live validation feedback
 * - Accessible design with full keyboard navigation
 */
import { Component, Accessor } from 'solid-js';
import type { Model } from '../types.js';
export interface ModelEditorProps {
    /** The model to edit (reactive) */
    model: Model;
    /** Callback when the model is updated */
    onChange: (updatedModel: Model) => void;
    /** Currently highlighted variable equivalence class */
    highlightedVars?: Accessor<Set<string>>;
    /** Whether inline editing is enabled (default: true) */
    allowEditing?: boolean;
    /** Whether to show validation errors inline (default: true) */
    showValidation?: boolean;
    /** Optional validation errors to display */
    validationErrors?: string[];
}
/**
 * Main ModelEditor component that provides comprehensive model editing interface
 */
export declare const ModelEditor: Component<ModelEditorProps>;
export default ModelEditor;
//# sourceMappingURL=ModelEditor.d.ts.map