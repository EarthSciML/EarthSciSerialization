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
export { ExpressionNode as ExpressionNodeComponent, type ExpressionNodeProps } from './ExpressionNode.tsx';
export { ModelEditor, type ModelEditorProps } from './ModelEditor.tsx';
export { CouplingGraph, type CouplingGraphProps } from './CouplingGraph.tsx';
export { ValidationPanel, type ValidationPanelProps } from './ValidationPanel.tsx';
export { FileSummary, type FileSummaryProps } from './FileSummary.tsx';
export { SimulationControls, type SimulationControlsProps } from './SimulationControls.tsx';

// Layout components for mathematical typography
export * from '../layout/index.js';

// Type definitions for interactive editing
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
  position: { x: number; y: number };
  type: 'variable' | 'operator' | 'error' | 'validation';
}

// Utility functions for path manipulation
export const PathUtils = {
  toString: (path: (string | number)[]): string => path.join('.'),

  fromString: (pathStr: string): (string | number)[] =>
    pathStr.split('.').map(segment =>
      /^\d+$/.test(segment) ? parseInt(segment, 10) : segment
    ),

  isAncestor: (ancestor: (string | number)[], descendant: (string | number)[]): boolean =>
    ancestor.length < descendant.length &&
    ancestor.every((segment, i) => segment === descendant[i]),

  commonPrefix: (path1: (string | number)[], path2: (string | number)[]): (string | number)[] => {
    const result = [];
    const minLength = Math.min(path1.length, path2.length);
    for (let i = 0; i < minLength; i++) {
      if (path1[i] === path2[i]) {
        result.push(path1[i]);
      } else {
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
  TOOLTIP_DELAY: 800,   // milliseconds
  ANIMATION_DURATION: 150, // milliseconds

  // Validation
  MAX_EXPRESSION_DEPTH: 20,
  MAX_VARIABLES_PER_EXPRESSION: 100
} as const;

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
} as const;