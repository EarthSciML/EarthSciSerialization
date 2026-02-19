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
// Core component exports
export { ExpressionNode as ExpressionNodeComponent } from './ExpressionNode.tsx';
export { ModelEditor } from './ModelEditor.tsx';
export { CouplingGraph } from './CouplingGraph.tsx';
export { ValidationPanel } from './ValidationPanel.tsx';
export { FileSummary } from './FileSummary.tsx';
export { SimulationControls } from './SimulationControls.tsx';
// Layout components for mathematical typography
export * from '../layout/index.js';
// Utility functions for path manipulation
export const PathUtils = {
    toString: (path) => path.join('.'),
    fromString: (pathStr) => pathStr.split('.').map(segment => /^\d+$/.test(segment) ? parseInt(segment, 10) : segment),
    isAncestor: (ancestor, descendant) => ancestor.length < descendant.length &&
        ancestor.every((segment, i) => segment === descendant[i]),
    commonPrefix: (path1, path2) => {
        const result = [];
        const minLength = Math.min(path1.length, path2.length);
        for (let i = 0; i < minLength; i++) {
            if (path1[i] === path2[i]) {
                result.push(path1[i]);
            }
            else {
                break;
            }
        }
        return result;
    }
};
// Constants for configuration
export const EDITOR_CONFIG = {
    // Performance thresholds (in milliseconds)
    HOVER_DEBOUNCE: 100,
    VALIDATION_DEBOUNCE: 200,
    EDIT_SAVE_TIMEOUT: 500,
    // Undo/redo limits
    MAX_UNDO_STACK_SIZE: 100,
    COMMAND_MERGE_TIMEOUT: 1000,
    // UI constants
    MIN_TOUCH_TARGET: 44, // pixels
    TOOLTIP_DELAY: 800, // milliseconds
    ANIMATION_DURATION: 150, // milliseconds
    // Validation
    MAX_EXPRESSION_DEPTH: 20,
    MAX_VARIABLES_PER_EXPRESSION: 100
};
// CSS class constants
export const CSS_CLASSES = {
    NODE: 'esm-expression-node',
    VARIABLE: 'esm-variable',
    NUMBER: 'esm-number',
    OPERATOR: 'esm-operator',
    FRACTION: 'esm-fraction',
    EXPONENT: 'esm-exponent',
    DERIVATIVE: 'esm-derivative',
    FUNCTION: 'esm-function',
    SELECTED: 'selected',
    HIGHLIGHTED: 'highlighted',
    EDITING: 'editing',
    HOVERED: 'hovered',
    ERROR: 'error',
    WARNING: 'warning'
};
//# sourceMappingURL=index.js.map