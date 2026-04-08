/**
 * EarthSciML Serialization Format TypeScript Type Definitions
 *
 * This module provides the complete type definitions for the ESM format,
 * including auto-generated types from the JSON schema and manual augmentations
 * for discriminated unions and improved type safety.
 */

// Re-export all generated types
export * from './generated.js'

// Manual type augmentations for better TypeScript experience

/**
 * Expression type alias - more concise name for mathematical expressions
 * Alias for the generated Expression type
 */
import type { Expression as GeneratedExpression, ExpressionNode } from './generated.js'
export type Expr = GeneratedExpression // number | string | ExpressionNode

/**
 * Main ESM file structure
 * Alias for the generated ESMFormat type
 */
import type { ESMFormat } from './generated.js'
export type EsmFile = ESMFormat

/**
 * Enhanced CouplingEntry with proper discriminated union
 * Based on the 'type' field for better type narrowing
 */
import type { CouplingEntry as GeneratedCouplingEntry } from './generated.js'

// The base CouplingEntry already has discriminated union structure
// Re-export with a more descriptive name
export type { CouplingEntry } from './generated.js'

/**
 * Enhanced DiscreteEventTrigger with proper discriminated union
 * The generated type already has proper discriminated union structure
 */
import type { DiscreteEventTrigger as GeneratedDiscreteEventTrigger } from './generated.js'
export type { DiscreteEventTrigger } from './generated.js'

// Re-export key types with explicit names for better documentation
export type {
  // Core file structure
  ESMFormat as EsmFormat,
  Metadata,

  // Model components
  Model,
  ReactionSystem,
  ModelVariable,
  Species,
  Reaction,

  // Events
  ContinuousEvent,
  DiscreteEvent,

  // Expressions and equations
  Expression,
  ExpressionNode as ExprNode,
  Equation,
  AffectEquation,
  FunctionalAffect,

  // Data handling
  DataLoader,
  Operator,

  // System configuration
  Domain,
  Solver,
  Reference,
} from './generated.js'