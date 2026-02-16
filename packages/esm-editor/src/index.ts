/**
 * ESM Editor - Interactive SolidJS editor for EarthSciML expressions
 *
 * This package provides interactive editing components for ESM format expressions,
 * built on SolidJS with proper reactive state management and accessibility support.
 */

// Core components
export { ExpressionNode, type ExpressionNodeProps } from './components/ExpressionNode';
export { ExpressionPalette, type ExpressionPaletteProps } from './components/ExpressionPalette';

// Editor components
export { EquationEditor, type EquationEditorProps } from './components/EquationEditor';
export { ModelEditor, type ModelEditorProps } from './components/ModelEditor';
export { ReactionEditor, type ReactionEditorProps } from './components/ReactionEditor';
export { CouplingGraph, type CouplingGraphProps } from './components/CouplingGraph';

// Variable highlighting primitives
export {
  buildVarEquivalences,
  normalizeScopedReference,
  HighlightProvider,
  useHighlightContext,
  createHighlightContext,
  isHighlighted,
  type HighlightContextValue,
  type ScopingMode,
  type HighlightProviderProps
} from './primitives/highlighted-var';

// Selection and inline editing primitives
export {
  SelectionProvider,
  useSelectionContext,
  createSelectionContext,
  getVariableSuggestions,
  pathsEqual,
  pathToString,
  stringToPath,
  type SelectionContextValue,
  type SelectionProviderProps,
  type NodeDetails
} from './primitives/selection';

// Structural editing primitives
export {
  StructuralEditingProvider,
  useStructuralEditingContext,
  StructuralEditingMenu,
  DraggableExpression,
  WRAP_OPERATORS,
  COMMUTATIVE_OPERATORS,
  type StructuralEditingContextValue,
  type StructuralEditingProviderProps,
  type StructuralEditingMenuProps,
  type DraggableExpressionProps,
  type DragState
} from './primitives/structural-editing';

// Re-export types from esm-format for convenience
export type {
  Expression,
  ExpressionNode as ExprNode,
  ComponentNode,
  CouplingEdge,
  Graph
} from 'esm-format';