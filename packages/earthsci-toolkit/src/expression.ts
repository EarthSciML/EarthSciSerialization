/**
 * Expression structural operations for the ESM format
 *
 * This module provides utilities for analyzing and manipulating mathematical
 * expressions in the ESM format AST.
 */

import type { Expression, ExpressionNode, Model } from './types.js'
import { isNumericLiteral, type NumericLiteral } from './numeric-literal.js'
import { dispatchClosedFunction } from './registered_functions.js'

/**
 * Type alias for better readability. Widened to accept `NumericLiteral`
 * leaves (per discretization RFC §5.4.1) alongside plain JS numbers.
 */
export type Expr = Expression | NumericLiteral

/**
 * Extract all variable references from an expression
 * @param expr Expression to analyze
 * @returns Set of variable names referenced in the expression
 */
export function freeVariables(expr: Expr): Set<string> {
  const variables = new Set<string>()

  if (typeof expr === 'string') {
    variables.add(expr)
  } else if (typeof expr === 'number' || isNumericLiteral(expr)) {
    // Numeric literals contain no variables
    return variables
  } else if (typeof expr === 'object' && (expr as ExpressionNode).op) {
    // ExpressionNode - recursively analyze arguments
    for (const arg of (expr as ExpressionNode).args) {
      const childVars = freeVariables(arg as Expr)
      childVars.forEach(v => variables.add(v))
    }
  }

  return variables
}

/**
 * Extract free parameters from an expression within a model context
 * @param expr Expression to analyze
 * @param model Model context to determine parameter vs state variables
 * @returns Set of parameter names referenced in the expression
 */
export function freeParameters(expr: Expr, model: Model): Set<string> {
  const allVars = freeVariables(expr)
  const parameters = new Set<string>()

  for (const varName of allVars) {
    const variable = model.variables[varName]
    if (variable && variable.type === 'parameter') {
      parameters.add(varName)
    }
  }

  return parameters
}

/**
 * Check if an expression contains a specific variable
 * @param expr Expression to search
 * @param varName Variable name to look for
 * @returns True if the variable appears in the expression
 */
export function contains(expr: Expr, varName: string): boolean {
  if (typeof expr === 'string') {
    return expr === varName
  } else if (typeof expr === 'number' || isNumericLiteral(expr)) {
    return false
  } else if (typeof expr === 'object' && (expr as ExpressionNode).op) {
    // ExpressionNode - recursively check arguments
    return (expr as ExpressionNode).args.some(arg => contains(arg as Expr, varName))
  }

  return false
}

/**
 * Evaluate an expression numerically with variable bindings
 * @param expr Expression to evaluate
 * @param bindings Map of variable names to their numeric values
 * @returns Numeric result
 * @throws Error if variables are unbound or evaluation fails
 */
export function evaluate(expr: Expr, bindings: Map<string, number>): number {
  if (typeof expr === 'number') {
    return expr
  } else if (isNumericLiteral(expr)) {
    return expr.value
  } else if (typeof expr === 'string') {
    if (bindings.has(expr)) {
      return bindings.get(expr)!
    } else {
      throw new Error(`Unbound variable: ${expr}`)
    }
  } else if (typeof expr === 'object' && (expr as ExpressionNode).op) {
    // ExpressionNode - evaluate based on operator
    const node = expr as any

    // const: inline literal — only meaningful as a scalar when its value
    // is a number; array-valued const nodes are extracted by callers
    // that consume them (e.g. interp.searchsorted's xs argument).
    if (node.op === 'const') {
      const v = node.value
      if (typeof v === 'number') return v
      if (Array.isArray(v)) {
        throw new Error('const node with array value cannot be evaluated as a scalar; arrays are consumed by container ops (e.g. interp.searchsorted, index)')
      }
      throw new Error(`const node with non-numeric value: ${typeof v}`)
    }

    // enum nodes should have been lowered to const at load time. If we
    // see one here, the file was evaluated before the lowering pass ran.
    if (node.op === 'enum') {
      throw new Error("enum op encountered during evaluate(); enum nodes must be lowered to 'const' integer nodes via lowerEnums() at load time")
    }

    // fn: closed function registry dispatch (esm-spec §9.2). Most args
    // evaluate to scalars; interp.searchsorted's second arg is a const
    // array that we extract WITHOUT evaluating it through the scalar path.
    if (node.op === 'fn') {
      const fnName = node.name
      if (typeof fnName !== 'string') {
        throw new Error('fn op missing required string `name` field')
      }
      const fnArgs = node.args.map((arg: any) => {
        if (arg && typeof arg === 'object' && (arg as ExpressionNode).op === 'const' && Array.isArray((arg as any).value)) {
          // Array-valued const argument — pass the raw array through.
          return (arg as any).value
        }
        return evaluate(arg, bindings)
      })
      return dispatchClosedFunction(fnName, fnArgs)
    }

    const args: any = node.args.map((arg: any) => evaluate(arg, bindings))

    switch (node.op) {
      case '+':
        return args.reduce((sum, val) => sum + val, 0)
      case '-':
        if (args.length === 1) return -args[0]
        return args.reduce((diff, val, idx) => idx === 0 ? val : diff - val)
      case '*':
        return args.reduce((prod, val) => prod * val, 1)
      case '/':
        if (args.length !== 2) throw new Error('Division requires exactly 2 arguments')
        if (args[1] === 0) throw new Error('Division by zero')
        return args[0] / args[1]
      case '^':
        if (args.length !== 2) throw new Error('Exponentiation requires exactly 2 arguments')
        return Math.pow(args[0], args[1])
      case 'exp':
        if (args.length !== 1) throw new Error('exp requires exactly 1 argument')
        return Math.exp(args[0])
      case 'log':
        if (args.length !== 1) throw new Error('log requires exactly 1 argument')
        if (args[0] <= 0) throw new Error('log argument must be positive')
        return Math.log(args[0])
      case 'log10':
        if (args.length !== 1) throw new Error('log10 requires exactly 1 argument')
        if (args[0] <= 0) throw new Error('log10 argument must be positive')
        return Math.log10(args[0])
      case 'sqrt':
        if (args.length !== 1) throw new Error('sqrt requires exactly 1 argument')
        if (args[0] < 0) throw new Error('sqrt argument must be non-negative')
        return Math.sqrt(args[0])
      case 'abs':
        if (args.length !== 1) throw new Error('abs requires exactly 1 argument')
        return Math.abs(args[0])
      case 'sin':
        if (args.length !== 1) throw new Error('sin requires exactly 1 argument')
        return Math.sin(args[0])
      case 'cos':
        if (args.length !== 1) throw new Error('cos requires exactly 1 argument')
        return Math.cos(args[0])
      case 'tan':
        if (args.length !== 1) throw new Error('tan requires exactly 1 argument')
        return Math.tan(args[0])
      case 'asin':
        if (args.length !== 1) throw new Error('asin requires exactly 1 argument')
        if (args[0] < -1 || args[0] > 1) throw new Error('asin argument must be in [-1, 1]')
        return Math.asin(args[0])
      case 'acos':
        if (args.length !== 1) throw new Error('acos requires exactly 1 argument')
        if (args[0] < -1 || args[0] > 1) throw new Error('acos argument must be in [-1, 1]')
        return Math.acos(args[0])
      case 'atan':
        if (args.length !== 1) throw new Error('atan requires exactly 1 argument')
        return Math.atan(args[0])
      case 'atan2':
        if (args.length !== 2) throw new Error('atan2 requires exactly 2 arguments')
        return Math.atan2(args[0], args[1])
      case 'min':
        // n-ary min (esm-spec §4.2 — arity ≥ 2)
        if (args.length < 2) throw new Error('min requires at least 2 arguments')
        return Math.min(...args)
      case 'max':
        // n-ary max (esm-spec §4.2 — arity ≥ 2)
        if (args.length < 2) throw new Error('max requires at least 2 arguments')
        return Math.max(...args)
      case 'floor':
        if (args.length !== 1) throw new Error('floor requires exactly 1 argument')
        return Math.floor(args[0])
      case 'ceil':
        if (args.length !== 1) throw new Error('ceil requires exactly 1 argument')
        return Math.ceil(args[0])
      case 'sign':
        if (args.length !== 1) throw new Error('sign requires exactly 1 argument')
        return Math.sign(args[0])
      case '>':
        if (args.length !== 2) throw new Error('> requires exactly 2 arguments')
        return args[0] > args[1] ? 1 : 0
      case '<':
        if (args.length !== 2) throw new Error('< requires exactly 2 arguments')
        return args[0] < args[1] ? 1 : 0
      case '>=':
        if (args.length !== 2) throw new Error('>= requires exactly 2 arguments')
        return args[0] >= args[1] ? 1 : 0
      case '<=':
        if (args.length !== 2) throw new Error('<= requires exactly 2 arguments')
        return args[0] <= args[1] ? 1 : 0
      case '==':
        if (args.length !== 2) throw new Error('== requires exactly 2 arguments')
        return args[0] === args[1] ? 1 : 0
      case '!=':
        if (args.length !== 2) throw new Error('!= requires exactly 2 arguments')
        return args[0] !== args[1] ? 1 : 0
      case 'and':
        return args.every(x => x !== 0) ? 1 : 0
      case 'or':
        return args.some(x => x !== 0) ? 1 : 0
      case 'not':
        if (args.length !== 1) throw new Error('not requires exactly 1 argument')
        return args[0] === 0 ? 1 : 0
      case 'ifelse':
        if (args.length !== 3) throw new Error('ifelse requires exactly 3 arguments')
        return args[0] !== 0 ? args[1] : args[2]
      default:
        throw new Error(`Unsupported operator: ${node.op}`)
    }
  }

  throw new Error('Invalid expression type')
}

/**
 * Simplify an expression using basic algebraic rules
 * @param expr Expression to simplify
 * @returns Simplified expression
 */
export function simplify(expr: Expr): Expr {
  if (typeof expr === 'number' || typeof expr === 'string') {
    return expr
  }

  if (isNumericLiteral(expr)) {
    // NumericLiteral leaves carry a kind tag that simplify is not
    // responsible for folding. Canonical int/float folding lives in
    // canonicalize() per RFC §5.4. Return unchanged.
    return expr
  }

  if (typeof expr === 'object' && (expr as ExpressionNode).op) {
    // First simplify all arguments recursively
    const simplifiedArgs = expr.args.map(arg => simplify(arg))

    // Apply simplification rules based on operator
    switch (expr.op) {
      case '+':
        // Remove zeros: x + 0 -> x
        const nonZeroTerms = simplifiedArgs.filter(arg => arg !== 0)
        if (nonZeroTerms.length === 0) return 0
        if (nonZeroTerms.length === 1) return nonZeroTerms[0]

        // Separate constants and variables for partial constant folding
        const constants = nonZeroTerms.filter(arg => typeof arg === 'number') as number[]
        const variables = nonZeroTerms.filter(arg => typeof arg !== 'number')

        // If all terms are constants, return the sum
        if (variables.length === 0) {
          return constants.reduce((sum, val) => sum + val, 0)
        }

        // If there are constants to fold, combine them
        if (constants.length > 1) {
          const constantSum = constants.reduce((sum, val) => sum + val, 0)
          if (constantSum === 0) {
            // If constant sum is zero, just return variables
            return variables.length === 1 ? variables[0] : { ...expr, args: variables as [Expression, ...Expression[]] }
          } else {
            // Include the folded constant with variables
            const finalTerms = [...variables, constantSum]
            return { ...expr, args: finalTerms as [Expression, ...Expression[]] }
          }
        }

        return { ...expr, args: nonZeroTerms as [Expression, ...Expression[]] }

      case '*':
        // Zero multiplication: x * 0 -> 0
        if (simplifiedArgs.some(arg => arg === 0)) return 0

        // Remove ones: x * 1 -> x
        const nonOneFactors = simplifiedArgs.filter(arg => arg !== 1)
        if (nonOneFactors.length === 0) return 1
        if (nonOneFactors.length === 1) return nonOneFactors[0]

        // Separate constants and variables for partial constant folding
        const constantFactors = nonOneFactors.filter(arg => typeof arg === 'number') as number[]
        const variableFactors = nonOneFactors.filter(arg => typeof arg !== 'number')

        // If all factors are constants, return the product
        if (variableFactors.length === 0) {
          return constantFactors.reduce((prod, val) => prod * val, 1)
        }

        // If there are constants to fold, combine them
        if (constantFactors.length > 1) {
          const constantProd = constantFactors.reduce((prod, val) => prod * val, 1)
          if (constantProd === 0) {
            return 0
          } else if (constantProd === 1) {
            // If constant product is one, just return variables
            return variableFactors.length === 1 ? variableFactors[0] : { ...expr, args: variableFactors as [Expression, ...Expression[]] }
          } else {
            // Include the folded constant with variables
            const finalFactors = [...variableFactors, constantProd]
            return { ...expr, args: finalFactors as [Expression, ...Expression[]] }
          }
        }

        return { ...expr, args: nonOneFactors as [Expression, ...Expression[]] }

      case '-':
        if (simplifiedArgs.length === 1) {
          // Unary minus: -(-x) -> x would need deeper analysis
          if (typeof simplifiedArgs[0] === 'number') {
            return -simplifiedArgs[0]
          }
        } else if (simplifiedArgs.length === 2) {
          // Binary subtraction: x - 0 -> x
          if (simplifiedArgs[1] === 0) return simplifiedArgs[0]

          // Constant folding
          if (typeof simplifiedArgs[0] === 'number' && typeof simplifiedArgs[1] === 'number') {
            return simplifiedArgs[0] - simplifiedArgs[1]
          }
        }

        return { ...expr, args: simplifiedArgs as [Expression, ...Expression[]] }

      case '/':
        if (simplifiedArgs.length === 2) {
          // x / 1 -> x
          if (simplifiedArgs[1] === 1) return simplifiedArgs[0]

          // 0 / x -> 0 (assuming x != 0)
          if (simplifiedArgs[0] === 0) return 0

          // Constant folding
          if (typeof simplifiedArgs[0] === 'number' && typeof simplifiedArgs[1] === 'number') {
            if (simplifiedArgs[1] === 0) throw new Error('Division by zero')
            return simplifiedArgs[0] / simplifiedArgs[1]
          }
        }

        return { ...expr, args: simplifiedArgs as [Expression, ...Expression[]] }

      case '^':
        if (simplifiedArgs.length === 2) {
          // x^0 -> 1
          if (simplifiedArgs[1] === 0) return 1

          // x^1 -> x
          if (simplifiedArgs[1] === 1) return simplifiedArgs[0]

          // 0^x -> 0 (assuming x > 0)
          if (simplifiedArgs[0] === 0) return 0

          // 1^x -> 1
          if (simplifiedArgs[0] === 1) return 1

          // Constant folding
          if (typeof simplifiedArgs[0] === 'number' && typeof simplifiedArgs[1] === 'number') {
            return Math.pow(simplifiedArgs[0], simplifiedArgs[1])
          }
        }

        return { ...expr, args: simplifiedArgs as [Expression, ...Expression[]] }

      default:
        // For other operators, just apply constant folding if all args are numeric
        if (simplifiedArgs.every(arg => typeof arg === 'number')) {
          try {
            // Create a temporary bindings map for evaluation
            const tempBindings = new Map<string, number>()
            return evaluate({ ...expr, args: simplifiedArgs as [Expression, ...Expression[]] }, tempBindings)
          } catch {
            // If evaluation fails, return the expression with simplified args
            return { ...expr, args: simplifiedArgs as [Expression, ...Expression[]] }
          }
        }

        return { ...expr, args: simplifiedArgs as [Expression, ...Expression[]] }
    }
  }

  return expr
}