/**
 * ESM Format TypeScript Package - Core Only
 *
 * Entry point for core esm-format functionality without interactive components.
 * This build excludes SolidJS components to provide a lighter bundle.
 *
 * @example
 * ```typescript
 * import { EsmFile, Model, Expr } from 'esm-format/core';
 * ```
 */
// Re-export all types from types.ts (which includes generated types and augmentations)
export * from './types.js';
// Export parsing and serialization functions
export { load, validateSchema, ParseError, SchemaValidationError } from './parse.js';
export { save } from './serialize.js';
export { validate } from './validate.js';
// Export graph utilities
export { component_graph, componentExists, getComponentType } from './graph.js';
// Export pretty-printing utilities
export { toUnicode, toLatex, toAscii } from './pretty-print.js';
// Export substitution utilities
export { substitute, substituteInModel, substituteInReactionSystem } from './substitute.js';
// Export expression structural operations
export { freeVariables, freeParameters, contains, evaluate, simplify } from './expression.js';
// Package metadata
export const VERSION = '0.1.0';
export const SCHEMA_VERSION = '0.1.0';
//# sourceMappingURL=core.js.map