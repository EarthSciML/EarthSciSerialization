/**
 * Symbolic differentiation capabilities
 *
 * This module provides functions to compute symbolic derivatives
 * of expressions with respect to variables, supporting the chain rule
 * and various mathematical functions.
 */

import type { Expr } from '../types.js';
import type { DerivativeResult } from './types.js';
import { simplify } from '../expression.js';

/**
 * Compute the symbolic derivative of an expression with respect to a variable
 * @param expr Expression to differentiate
 * @param variable Variable with respect to which to differentiate
 * @returns Derivative result with simplified form
 */
export function differentiate(expr: Expr, variable: string): DerivativeResult {
  const derivative = computeDerivative(expr, variable);
  const simplified = simplify(derivative);

  return {
    derivative,
    variable,
    simplified: isEqual(derivative, simplified) ? undefined : simplified
  };
}

/**
 * Compute partial derivatives with respect to multiple variables
 * @param expr Expression to differentiate
 * @param variables Array of variables to differentiate with respect to
 * @returns Map of variable names to their derivative results
 */
export function partialDerivatives(expr: Expr, variables: string[]): Map<string, DerivativeResult> {
  const results = new Map<string, DerivativeResult>();

  for (const variable of variables) {
    results.set(variable, differentiate(expr, variable));
  }

  return results;
}

/**
 * Compute the gradient (all first partial derivatives)
 * @param expr Expression to differentiate
 * @param variables Array of variables (if not provided, will extract from expression)
 * @returns Gradient as array of derivatives
 */
export function gradient(expr: Expr, variables?: string[]): DerivativeResult[] {
  if (!variables) {
    // Extract variables from the expression
    variables = Array.from(extractVariables(expr));
  }

  return variables.map(variable => differentiate(expr, variable));
}

/**
 * Core differentiation logic using symbolic rules
 */
function computeDerivative(expr: Expr, variable: string): Expr {
  // Base cases
  if (typeof expr === 'number') {
    // d/dx (constant) = 0
    return 0;
  }

  if (typeof expr === 'string') {
    // d/dx (x) = 1, d/dx (y) = 0 where y ≠ x
    return expr === variable ? 1 : 0;
  }

  if (typeof expr === 'object' && expr.op) {
    const args = expr.args;

    switch (expr.op) {
      // Basic arithmetic
      case '+':
        // d/dx (u + v) = du/dx + dv/dx
        return {
          op: '+',
          args: args.map(arg => computeDerivative(arg, variable))
        };

      case '-':
        if (args.length === 1) {
          // d/dx (-u) = -du/dx
          return {
            op: '-',
            args: [computeDerivative(args[0], variable)]
          };
        } else {
          // d/dx (u - v) = du/dx - dv/dx
          return {
            op: '-',
            args: args.map(arg => computeDerivative(arg, variable))
          };
        }

      case '*':
        // Product rule: d/dx (uv) = u'v + uv'
        // For multiple factors: d/dx (uvw) = u'vw + uv'w + uvw'
        if (args.length === 2) {
          const [u, v] = args;
          const du = computeDerivative(u, variable);
          const dv = computeDerivative(v, variable);

          return {
            op: '+',
            args: [
              { op: '*', args: [du, v] },
              { op: '*', args: [u, dv] }
            ]
          };
        } else if (args.length > 2) {
          // Use product rule recursively
          const first = args[0];
          const rest = { op: '*', args: args.slice(1) } as Expr;
          return computeDerivative({ op: '*', args: [first, rest] }, variable);
        }
        break;

      case '/':
        // Quotient rule: d/dx (u/v) = (u'v - uv')/v²
        if (args.length === 2) {
          const [u, v] = args;
          const du = computeDerivative(u, variable);
          const dv = computeDerivative(v, variable);

          return {
            op: '/',
            args: [
              {
                op: '-',
                args: [
                  { op: '*', args: [du, v] },
                  { op: '*', args: [u, dv] }
                ]
              },
              { op: '^', args: [v, 2] }
            ]
          };
        }
        break;

      case '^':
        // Power rule: d/dx (u^n) = n * u^(n-1) * u'
        if (args.length === 2) {
          const [base, exponent] = args;

          // Special case: constant exponent
          if (typeof exponent === 'number') {
            if (exponent === 0) return 0;
            if (exponent === 1) return computeDerivative(base, variable);

            const du = computeDerivative(base, variable);
            return {
              op: '*',
              args: [
                exponent,
                { op: '^', args: [base, exponent - 1] },
                du
              ]
            };
          }

          // General case: d/dx (u^v) = u^v * (v' * ln(u) + v * u'/u)
          const du = computeDerivative(base, variable);
          const dv = computeDerivative(exponent, variable);

          return {
            op: '*',
            args: [
              expr, // u^v
              {
                op: '+',
                args: [
                  { op: '*', args: [dv, { op: 'log', args: [base] }] },
                  { op: '*', args: [exponent, { op: '/', args: [du, base] }] }
                ]
              }
            ]
          };
        }
        break;

      // Elementary functions
      case 'exp':
        // d/dx (e^u) = e^u * u'
        if (args.length === 1) {
          const u = args[0];
          const du = computeDerivative(u, variable);
          return {
            op: '*',
            args: [expr, du] // e^u * u'
          };
        }
        break;

      case 'log':
        // d/dx (ln(u)) = u'/u
        if (args.length === 1) {
          const u = args[0];
          const du = computeDerivative(u, variable);
          return {
            op: '/',
            args: [du, u]
          };
        }
        break;

      case 'log10':
        // d/dx (log₁₀(u)) = u'/(u * ln(10))
        if (args.length === 1) {
          const u = args[0];
          const du = computeDerivative(u, variable);
          return {
            op: '/',
            args: [
              du,
              {
                op: '*',
                args: [u, Math.LN10] // ln(10)
              }
            ]
          };
        }
        break;

      case 'sin':
        // d/dx (sin(u)) = cos(u) * u'
        if (args.length === 1) {
          const u = args[0];
          const du = computeDerivative(u, variable);
          return {
            op: '*',
            args: [
              { op: 'cos', args: [u] },
              du
            ]
          };
        }
        break;

      case 'cos':
        // d/dx (cos(u)) = -sin(u) * u'
        if (args.length === 1) {
          const u = args[0];
          const du = computeDerivative(u, variable);
          return {
            op: '*',
            args: [
              { op: '-', args: [{ op: 'sin', args: [u] }] },
              du
            ]
          };
        }
        break;

      case 'tan':
        // d/dx (tan(u)) = sec²(u) * u' = (1/cos²(u)) * u'
        if (args.length === 1) {
          const u = args[0];
          const du = computeDerivative(u, variable);
          return {
            op: '*',
            args: [
              {
                op: '/',
                args: [1, { op: '^', args: [{ op: 'cos', args: [u] }, 2] }]
              },
              du
            ]
          };
        }
        break;

      case 'asin':
        // d/dx (arcsin(u)) = u'/√(1-u²)
        if (args.length === 1) {
          const u = args[0];
          const du = computeDerivative(u, variable);
          return {
            op: '/',
            args: [
              du,
              {
                op: 'sqrt',
                args: [
                  {
                    op: '-',
                    args: [1, { op: '^', args: [u, 2] }]
                  }
                ]
              }
            ]
          };
        }
        break;

      case 'acos':
        // d/dx (arccos(u)) = -u'/√(1-u²)
        if (args.length === 1) {
          const u = args[0];
          const du = computeDerivative(u, variable);
          return {
            op: '/',
            args: [
              { op: '-', args: [du] },
              {
                op: 'sqrt',
                args: [
                  {
                    op: '-',
                    args: [1, { op: '^', args: [u, 2] }]
                  }
                ]
              }
            ]
          };
        }
        break;

      case 'atan':
        // d/dx (arctan(u)) = u'/(1+u²)
        if (args.length === 1) {
          const u = args[0];
          const du = computeDerivative(u, variable);
          return {
            op: '/',
            args: [
              du,
              {
                op: '+',
                args: [1, { op: '^', args: [u, 2] }]
              }
            ]
          };
        }
        break;

      case 'sqrt':
        // d/dx (√u) = u'/(2√u)
        if (args.length === 1) {
          const u = args[0];
          const du = computeDerivative(u, variable);
          return {
            op: '/',
            args: [
              du,
              {
                op: '*',
                args: [2, { op: 'sqrt', args: [u] }]
              }
            ]
          };
        }
        break;

      case 'abs':
        // d/dx (|u|) = u' * sign(u)
        if (args.length === 1) {
          const u = args[0];
          const du = computeDerivative(u, variable);
          return {
            op: '*',
            args: [
              du,
              { op: 'sign', args: [u] }
            ]
          };
        }
        break;

      // Comparison and logical operators (derivatives are 0 or undefined)
      case '>':
      case '<':
      case '>=':
      case '<=':
      case '==':
      case '!=':
      case 'and':
      case 'or':
      case 'not':
        // These don't have well-defined derivatives in the usual sense
        return 0;

      case 'ifelse':
        // d/dx (ifelse(cond, a, b)) = ifelse(cond, da/dx, db/dx)
        // Note: This assumes the condition doesn't depend on x
        if (args.length === 3) {
          const [condition, trueBranch, falseBranch] = args;
          return {
            op: 'ifelse',
            args: [
              condition,
              computeDerivative(trueBranch, variable),
              computeDerivative(falseBranch, variable)
            ]
          };
        }
        break;

      case 'min':
      case 'max':
        // These functions are not differentiable at the boundary, but we can provide
        // a reasonable approximation using the ifelse construct
        if (args.length === 2) {
          const [u, v] = args;
          const du = computeDerivative(u, variable);
          const dv = computeDerivative(v, variable);

          const condition = expr.op === 'min'
            ? { op: '<', args: [u, v] }
            : { op: '>', args: [u, v] };

          return {
            op: 'ifelse',
            args: [condition, du, dv]
          };
        }
        break;

      default:
        // For unknown functions, assume they are not differentiable
        // or return a placeholder derivative notation
        return {
          op: 'derivative',
          args: [expr, variable]
        } as any; // This would need to be added to the Expr type
    }
  }

  // Fallback: return 0 for anything we can't differentiate
  return 0;
}

/**
 * Extract all variables from an expression
 */
function extractVariables(expr: Expr): Set<string> {
  const variables = new Set<string>();

  if (typeof expr === 'string') {
    variables.add(expr);
  } else if (typeof expr === 'object' && expr.op) {
    for (const arg of expr.args) {
      const argVars = extractVariables(arg);
      argVars.forEach(v => variables.add(v));
    }
  }

  return variables;
}

/**
 * Check if two expressions are structurally equal
 */
function isEqual(expr1: Expr, expr2: Expr): boolean {
  if (typeof expr1 !== typeof expr2) return false;

  if (typeof expr1 === 'number') {
    return expr1 === expr2;
  }

  if (typeof expr1 === 'string') {
    return expr1 === expr2;
  }

  if (typeof expr1 === 'object' && typeof expr2 === 'object' && expr1.op && expr2.op) {
    if (expr1.op !== expr2.op) return false;
    if (expr1.args.length !== expr2.args.length) return false;

    for (let i = 0; i < expr1.args.length; i++) {
      if (!isEqual(expr1.args[i], expr2.args[i])) return false;
    }

    return true;
  }

  return false;
}

/**
 * Compute higher-order derivatives
 * @param expr Expression to differentiate
 * @param variable Variable with respect to which to differentiate
 * @param order Order of derivative (default: 1)
 * @returns Higher-order derivative result
 */
export function higherOrderDerivative(expr: Expr, variable: string, order: number = 1): DerivativeResult {
  if (order <= 0) {
    throw new Error('Derivative order must be positive');
  }

  let current = expr;
  const chainComponents: Array<{ expression: Expr; derivative: Expr }> = [];

  for (let i = 0; i < order; i++) {
    const derivative = computeDerivative(current, variable);
    chainComponents.push({
      expression: current,
      derivative
    });
    current = derivative;
  }

  const simplified = simplify(current);

  return {
    derivative: current,
    variable,
    simplified: isEqual(current, simplified) ? undefined : simplified,
    chainComponents
  };
}

/**
 * Check if an expression is differentiable with respect to a variable
 * @param expr Expression to check
 * @param variable Variable to check differentiability with respect to
 * @returns True if differentiable, false otherwise
 */
export function isDifferentiable(expr: Expr, variable: string): boolean {
  try {
    const derivative = computeDerivative(expr, variable);
    // If we get a result without throwing, it's differentiable
    return true;
  } catch {
    return false;
  }
}

/**
 * Find critical points (where derivative equals zero)
 * This is a symbolic analysis - actual solving would require numerical methods
 * @param expr Expression to analyze
 * @param variable Variable to find critical points for
 * @returns Information about potential critical points
 */
export function findCriticalPoints(expr: Expr, variable: string): {
  derivative: Expr;
  simplified?: Expr;
  hasConstantDerivative: boolean;
  isConstantZero: boolean;
} {
  const derivative = computeDerivative(expr, variable);
  const simplified = simplify(derivative);

  return {
    derivative,
    simplified: isEqual(derivative, simplified) ? undefined : simplified,
    hasConstantDerivative: typeof derivative === 'number',
    isConstantZero: derivative === 0
  };
}