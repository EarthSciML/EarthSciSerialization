/**
 * Expression substitution functionality for the ESM format
 *
 * Provides immutable substitution operations that replace variable references
 * with bound expressions throughout ESM structures.
 */
import type { Expr, Model, ReactionSystem } from './types.js';
/**
 * Recursively substitute variable references in an expression with bound expressions.
 * Handles scoped references (Model.Subsystem.var) by splitting on '.' and matching
 * path through system hierarchy per format spec Section 4.3.
 *
 * @param expr - Expression to substitute into
 * @param bindings - Variable name to expression mappings
 * @returns New expression with substitutions applied (immutable)
 */
export declare function substitute(expr: Expr, bindings: Record<string, Expr>): Expr;
/**
 * Apply substitution across all equations in a model.
 * Returns a new model with substitutions applied (immutable).
 *
 * @param model - Model to substitute into
 * @param bindings - Variable name to expression mappings
 * @returns New model with substitutions applied
 */
export declare function substituteInModel(model: Model, bindings: Record<string, Expr>): Model;
/**
 * Apply substitution across all rate expressions in a reaction system.
 * Returns a new reaction system with substitutions applied (immutable).
 *
 * @param system - ReactionSystem to substitute into
 * @param bindings - Variable name to expression mappings
 * @returns New reaction system with substitutions applied
 */
export declare function substituteInReactionSystem(system: ReactionSystem, bindings: Record<string, Expr>): ReactionSystem;
//# sourceMappingURL=substitute.d.ts.map