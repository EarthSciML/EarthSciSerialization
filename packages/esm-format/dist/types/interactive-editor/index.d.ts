/**
 * Interactive Editor - Core SolidJS Components
 *
 * This module provides the core interactive editing components for ESM expressions,
 * built with SolidJS for granular reactivity and optimal performance.
 *
 * The components render AST nodes directly as interactive DOM elements with
 * CSS-based mathematical layout, providing click-to-edit, hover highlighting,
 * and real-time validation capabilities.
 */
export { ExpressionNode as ExpressionNodeComponent, type ExpressionNodeProps } from './ExpressionNode.tsx';
export { ModelEditor, type ModelEditorProps } from './ModelEditor.tsx';
export { CouplingGraph, type CouplingGraphProps } from './CouplingGraph.tsx';
export { ValidationPanel, type ValidationPanelProps } from './ValidationPanel.tsx';
export { FileSummary, type FileSummaryProps } from './FileSummary.tsx';
export { SimulationControls, type SimulationControlsProps } from './SimulationControls.tsx';
export * from '../layout/index.js';
export interface EditorState {
    editMode: boolean;
    activeEdit: string | null;
    unsavedChanges: boolean;
    validationErrors: ValidationError[];
    dragState: DragState | null;
}
export interface ValidationError {
    id: string;
    type: 'syntax' | 'semantic' | 'type' | 'reference';
    message: string;
    path: (string | number)[];
    severity: 'error' | 'warning';
    suggestion?: string;
}
export interface DragState {
    isDragging: boolean;
    draggedPath: (string | number)[];
    dropTargets: (string | number)[][];
    ghostElement?: HTMLElement;
}
export interface UndoRedoState {
    undoStack: Command[];
    redoStack: Command[];
    maxStackSize: number;
    canUndo: boolean;
    canRedo: boolean;
}
export interface Command {
    id: string;
    type: string;
    execute(): CommandResult;
    undo(): CommandResult;
    redo(): CommandResult;
    canMerge: boolean;
    groupId?: string;
    timestamp: Date;
}
export interface CommandResult {
    success: boolean;
    error?: string;
    changes?: Change[];
}
export interface Change {
    path: (string | number)[];
    oldValue: any;
    newValue: any;
}
export interface HoverState {
    hoveredElement: string | null;
    highlightedElements: string[];
    tooltip: TooltipData | null;
    hoverTimeout: number;
}
export interface TooltipData {
    content: string;
    position: {
        x: number;
        y: number;
    };
    type: 'variable' | 'operator' | 'error' | 'validation';
}
export declare const PathUtils: {
    toString: (path: (string | number)[]) => string;
    fromString: (pathStr: string) => (string | number)[];
    isAncestor: (ancestor: (string | number)[], descendant: (string | number)[]) => boolean;
    commonPrefix: (path1: (string | number)[], path2: (string | number)[]) => (string | number)[];
};
export declare const EDITOR_CONFIG: {
    readonly HOVER_DEBOUNCE: 100;
    readonly VALIDATION_DEBOUNCE: 200;
    readonly EDIT_SAVE_TIMEOUT: 500;
    readonly MAX_UNDO_STACK_SIZE: 100;
    readonly COMMAND_MERGE_TIMEOUT: 1000;
    readonly MIN_TOUCH_TARGET: 44;
    readonly TOOLTIP_DELAY: 800;
    readonly ANIMATION_DURATION: 150;
    readonly MAX_EXPRESSION_DEPTH: 20;
    readonly MAX_VARIABLES_PER_EXPRESSION: 100;
};
export declare const CSS_CLASSES: {
    readonly NODE: "esm-expression-node";
    readonly VARIABLE: "esm-variable";
    readonly NUMBER: "esm-number";
    readonly OPERATOR: "esm-operator";
    readonly FRACTION: "esm-fraction";
    readonly EXPONENT: "esm-exponent";
    readonly DERIVATIVE: "esm-derivative";
    readonly FUNCTION: "esm-function";
    readonly SELECTED: "selected";
    readonly HIGHLIGHTED: "highlighted";
    readonly EDITING: "editing";
    readonly HOVERED: "hovered";
    readonly ERROR: "error";
    readonly WARNING: "warning";
};
//# sourceMappingURL=index.d.ts.map