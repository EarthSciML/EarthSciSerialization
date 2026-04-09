/**
 * EarthSciML Serialization Format TypeScript Type Definitions
 *
 * This module provides the complete type definitions for the ESM format,
 * including auto-generated types from the JSON schema and manual augmentations
 * for discriminated unions and improved type safety.
 */
export * from './generated.js';
/**
 * Expression type alias - more concise name for mathematical expressions
 * Alias for the generated Expression type
 */
import type { Expression as GeneratedExpression } from './generated.js';
export type Expr = GeneratedExpression;
/**
 * Main ESM file structure
 * Alias for the generated ESMFormat type
 */
import type { ESMFormat } from './generated.js';
export type EsmFile = ESMFormat;
export type { CouplingEntry } from './generated.js';
export type { DiscreteEventTrigger } from './generated.js';
export type { ESMFormat as EsmFormat, Metadata, Model, ReactionSystem, ModelVariable, Species, Reaction, ContinuousEvent, DiscreteEvent, Expression, ExpressionNode as ExprNode, Equation, AffectEquation, FunctionalAffect, DataLoader, Operator, Domain, Solver, Reference, } from './generated.js';
