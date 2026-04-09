/**
 * Expression structural operations for the ESM format
 *
 * This module provides utilities for analyzing and manipulating mathematical
 * expressions in the ESM format AST.
 */
import type { Expression, Model } from './types.js';
/**
 * Type alias for better readability
 */
export type Expr = Expression;
/**
 * Extract all variable references from an expression
 * @param expr Expression to analyze
 * @returns Set of variable names referenced in the expression
 */
export declare function freeVariables(expr: Expr): Set<string>;
/**
 * Extract free parameters from an expression within a model context
 * @param expr Expression to analyze
 * @param model Model context to determine parameter vs state variables
 * @returns Set of parameter names referenced in the expression
 */
export declare function freeParameters(expr: Expr, model: Model): Set<string>;
/**
 * Check if an expression contains a specific variable
 * @param expr Expression to search
 * @param varName Variable name to look for
 * @returns True if the variable appears in the expression
 */
export declare function contains(expr: Expr, varName: string): boolean;
/**
 * Evaluate an expression numerically with variable bindings
 * @param expr Expression to evaluate
 * @param bindings Map of variable names to their numeric values
 * @returns Numeric result
 * @throws Error if variables are unbound or evaluation fails
 */
export declare function evaluate(expr: Expr, bindings: Map<string, number>): number;
/**
 * Simplify an expression using basic algebraic rules
 * @param expr Expression to simplify
 * @returns Simplified expression
 */
export declare function simplify(expr: Expr): Expr;
//# sourceMappingURL=expression.d.ts.map