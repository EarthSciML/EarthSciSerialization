/**
 * Pretty-printing formatters for ESM format expressions, equations, models, and files.
 *
 * Implements three output formats:
 * - toUnicode(): Unicode mathematical notation with chemical subscripts
 * - toLatex(): LaTeX mathematical notation
 * - toAscii(): Plain text representation
 *
 * Based on ESM Format Specification Section 6.1
 */
import type { Expr, Equation, Model, EsmFile, ReactionSystem } from './types.js';
/**
 * Format an expression as Unicode mathematical notation
 */
export declare function toUnicode(expr: Expr | Equation | Model | ReactionSystem | EsmFile): string;
/**
 * Format an expression as LaTeX mathematical notation
 */
export declare function toLatex(expr: Expr | Equation | Model | ReactionSystem | EsmFile): string;
/**
 * Format an expression as plain ASCII text
 */
export declare function toAscii(expr: Expr | Equation | Model | ReactionSystem | EsmFile): string;
//# sourceMappingURL=pretty-print.d.ts.map