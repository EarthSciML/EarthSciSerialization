/**
 * ESM Editor - Interactive SolidJS editor for EarthSciML expressions
 *
 * This package provides interactive editing components for ESM format expressions,
 * built on SolidJS with proper reactive state management and accessibility support.
 */

// Core components
export { ExpressionNode, type ExpressionNodeProps } from './components/ExpressionNode';

// Re-export types from esm-format for convenience
export type { Expression, ExpressionNode as ExprNode } from 'esm-format';