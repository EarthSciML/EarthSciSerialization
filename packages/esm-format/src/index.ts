/**
 * ESM Format TypeScript Package
 *
 * Entry point for the esm-format package, providing complete TypeScript
 * type definitions for the EarthSciML Serialization Format.
 *
 * @example
 * ```typescript
 * import { EsmFile, Model, Expr } from 'esm-format';
 *
 * const myModel: Model = {
 *   name: "atmospheric_chemistry",
 *   variables: [],
 *   equations: []
 * };
 * ```
 */

// Re-export all types from types.ts (which includes generated types and augmentations)
export * from './types.js'

// Export parsing and serialization functions
export { load, validateSchema, ParseError, SchemaValidationError } from './parse.js'
export type { SchemaError } from './parse.js'
export { save } from './serialize.js'
export { validate } from './validate.js'
export type { ValidationError, ValidationResult } from './validate.js'

// Export graph utilities
export { component_graph, componentGraph, expressionGraph, componentExists, getComponentType } from './graph.js'
export type { ComponentGraph, ComponentNode, CouplingEdge, Graph, VariableNode, DependencyEdge } from './graph.js'

// Export pretty-printing utilities
export { toUnicode, toLatex, toAscii } from './pretty-print.js'

// Export substitution utilities
export { substitute, substituteInModel, substituteInReactionSystem } from './substitute.js'

// Export immutable editing operations
export * from './edit.js'

// Export expression structural operations
export { freeVariables, freeParameters, contains, evaluate, simplify } from './expression.js'

// Export reaction system ODE derivation and stoichiometric matrix computation
export { deriveODEs, stoichiometricMatrix, substrateMatrix, productMatrix } from './reactions.js'

// Export unit parsing and dimensional analysis
export { parseUnit, checkDimensions, validateUnits } from './units.js'
export type { DimensionalRep, UnitResult, UnitWarning } from './units.js'

// Interactive editor components (SolidJS)
export * from './interactive-editor/index.js'

// Web Components (framework-agnostic usage)
export * from './web-components.js'

// Error handling and diagnostics
export * from './error-handling.js'

// Package metadata
export const VERSION = '0.1.0'
export const SCHEMA_VERSION = '0.1.0'