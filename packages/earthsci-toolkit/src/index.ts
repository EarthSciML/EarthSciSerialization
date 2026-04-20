/**
 * ESM Format TypeScript Package
 *
 * Entry point for the earthsci-toolkit package, providing complete TypeScript
 * type definitions for the EarthSciML Serialization Format.
 *
 * @example
 * ```typescript
 * import { EsmFile, Model, Expr } from 'earthsci-toolkit';
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
export { load, validateSchema, ParseError, SchemaValidationError, GridValidationError } from './parse.js'
export type { SchemaError, LoadOptions } from './parse.js'
export { save } from './serialize.js'
export { validate } from './validate.js'
export type { ValidationError, ValidationResult } from './validate.js'

// Export graph utilities
export { component_graph, componentGraph, expressionGraph, componentExists, getComponentType, toDot, toMermaid, toJsonGraph } from './graph.js'
export type { ComponentGraph, ComponentNode, CouplingEdge, Graph, VariableNode, DependencyEdge } from './graph.js'

// Export advanced expression analysis and manipulation
export * from './analysis/index.js'

// Export pretty-printing utilities
export { toUnicode, toLatex, toAscii, toMathML } from './pretty-print.js'

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
export type { UnitResult, UnitWarning } from './units.js'

// Export runtime unit conversion
export { convertUnits, parseUnitForConversion, unitsCompatible, UnitConversionError } from './unit-conversion.js'
export type { CanonicalDims, ParsedUnit } from './unit-conversion.js'

// Export code generation utilities
export { toJuliaCode, toPythonCode } from './codegen.js'

// Export migration functionality
export { migrate, canMigrate, getSupportedMigrationTargets, MigrationError } from './migration.js'

// Interactive editor components (SolidJS) - moved to esm-editor package
// export * from './interactive-editor/index.js'

// Web Components (framework-agnostic usage)
export * from './web-components.js'

// Error handling and diagnostics
export * from './error-handling.js'

// Coupled system flattening
export { flatten } from './flatten.js'
export type { FlattenedEquation, FlattenMetadata, FlattenedSystem } from './flatten.js'

// Subsystem reference loading
export { resolveSubsystemRefs, CircularReferenceError, RefLoadError } from './ref-loading.js'

// Canonical AST form (RFC §5.4). TS lacks native int/float distinction;
// see canonicalize.ts for the gt-ca2u limitation note.
export {
  canonicalize,
  canonicalJson,
  formatCanonicalFloat,
  CanonicalizeError,
  E_CANONICAL_NONFINITE,
  E_CANONICAL_DIVBY_ZERO,
} from './canonicalize.js'

// Rule engine (RFC §5.2). Pattern-match rewriting, guards, and fixed-point
// loop. Produces byte-identical canonical output with Julia and Rust on
// the Step 1 conformance fixtures.
export {
  rewrite,
  matchPattern,
  applyBindings,
  checkGuards,
  checkGuard,
  parseRules,
  parseExpr,
  checkUnrewrittenPdeOps,
  emptyContext,
  RuleEngineError,
  DEFAULT_MAX_PASSES,
  E_RULES_NOT_CONVERGED,
  E_UNREWRITTEN_PDE_OP,
  E_PATTERN_VAR_UNBOUND,
  E_PATTERN_VAR_TYPE,
  E_UNKNOWN_GUARD,
  E_RULE_PARSE,
  E_RULE_REPLACEMENT_MISSING,
} from './rule-engine.js'
export type { Rule, Guard, RuleContext, GridMeta, VariableMeta } from './rule-engine.js'

// Package metadata
export const VERSION = '0.1.0'
export const SCHEMA_VERSION = '0.1.0'