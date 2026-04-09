/**
 * ExpressionNode - Core SolidJS component for rendering interactive AST nodes
 *
 * This component renders a single AST node as interactive DOM with CSS math layout,
 * handles click/hover events, supports inline editing, and provides the foundation
 * for all expression editing capabilities.
 *
 * Features:
 * - Click-to-select nodes with visual feedback
 * - Hover highlighting with equivalence classes
 * - Double-click inline editing of numbers/variables
 * - CSS-based math rendering (fractions, superscripts, derivatives)
 * - Reactive updates via Solid store
 * - Full keyboard accessibility
 */
import { Component, Accessor } from 'solid-js';
import type { Expression } from '../types.js';
export interface ExpressionNodeProps {
    /** The expression to render (reactive) */
    expr: Expression;
    /** AST path for this node (for unique identification and updates) */
    path: (string | number)[];
    /** Currently highlighted variable equivalence class */
    highlightedVars: Accessor<Set<string>>;
    /** Callback when hovering over a variable */
    onHoverVar: (name: string | null) => void;
    /** Callback when selecting a node */
    onSelect: (path: (string | number)[]) => void;
    /** Callback when replacing a node with new expression */
    onReplace: (path: (string | number)[], newExpr: Expression) => void;
    /** Whether this node is currently selected */
    isSelected?: boolean;
    /** Whether inline editing is enabled */
    allowEditing?: boolean;
}
/**
 * Core ExpressionNode component that renders any Expression as interactive DOM
 */
export declare const ExpressionNode: Component<ExpressionNodeProps>;
export default ExpressionNode;
//# sourceMappingURL=ExpressionNode.d.ts.map