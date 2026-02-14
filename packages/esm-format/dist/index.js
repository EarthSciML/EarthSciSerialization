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
export * from './types.js';
// Package metadata
export const VERSION = '0.1.0';
export const SCHEMA_VERSION = '0.1.0';
//# sourceMappingURL=index.js.map