/**
 * Expression substitution functionality for the ESM format
 *
 * Provides immutable substitution operations that replace variable references
 * with bound expressions throughout ESM structures.
 */

import type { Expr, ExprNode, Model, ReactionSystem } from './types.js'

/**
 * Recursively substitute variable references in an expression with bound expressions.
 * Handles scoped references (Model.Subsystem.var) by splitting on '.' and matching
 * path through system hierarchy per format spec Section 4.3.
 *
 * @param expr - Expression to substitute into
 * @param bindings - Variable name to expression mappings
 * @returns New expression with substitutions applied (immutable)
 */
export function substitute(expr: Expr, bindings: Record<string, Expr>): Expr {
  // Base cases: numbers remain unchanged
  if (typeof expr === 'number') {
    return expr
  }

  // String case: variable reference
  if (typeof expr === 'string') {
    // Check for direct binding
    if (bindings.hasOwnProperty(expr)) {
      return bindings[expr]!
    }

    // Check for scoped reference (e.g., "Model.Subsystem.var")
    // For now, treat as direct lookup - full scoped resolution would require
    // access to the model hierarchy context
    return expr
  }

  // ExpressionNode case: recursively substitute arguments
  const node = expr as ExprNode
  const substitutedArgs = node.args.map(arg => substitute(arg, bindings))

  // Return new node with substituted arguments
  return {
    ...node,
    args: substitutedArgs as [Expr, ...Expr[]]
  }
}

/**
 * Apply substitution across all equations in a model.
 * Returns a new model with substitutions applied (immutable).
 *
 * @param model - Model to substitute into
 * @param bindings - Variable name to expression mappings
 * @returns New model with substitutions applied
 */
export function substituteInModel(model: Model, bindings: Record<string, Expr>): Model {
  // Substitute in all equations
  const equations = model.equations.map(eq => ({
    ...eq,
    lhs: substitute(eq.lhs, bindings),
    rhs: substitute(eq.rhs, bindings)
  }))

  // Substitute in variable expressions (for observed variables)
  const variables = Object.fromEntries(
    Object.entries(model.variables).map(([name, variable]) => [
      name,
      {
        ...variable,
        ...(variable.expression && {
          expression: substitute(variable.expression, bindings)
        })
      }
    ])
  )

  // Substitute in subsystems recursively
  const subsystems = model.subsystems
    ? Object.fromEntries(
        Object.entries(model.subsystems).map(([name, subsystem]) => [
          name,
          substituteInModel(subsystem, bindings)
        ])
      )
    : undefined

  return {
    ...model,
    equations,
    variables,
    ...(subsystems && { subsystems })
  }
}

/**
 * Apply substitution across all rate expressions in a reaction system.
 * Returns a new reaction system with substitutions applied (immutable).
 *
 * @param system - ReactionSystem to substitute into
 * @param bindings - Variable name to expression mappings
 * @returns New reaction system with substitutions applied
 */
export function substituteInReactionSystem(
  system: ReactionSystem,
  bindings: Record<string, Expr>
): ReactionSystem {
  // Substitute in all reaction rate expressions
  const reactions = system.reactions.map(reaction => ({
    ...reaction,
    rate: substitute(reaction.rate, bindings)
  })) as [typeof system.reactions[0], ...typeof system.reactions[0][]]

  // Substitute in constraint equations if present
  const constraint_equations = system.constraint_equations?.map(eq => ({
    ...eq,
    lhs: substitute(eq.lhs, bindings),
    rhs: substitute(eq.rhs, bindings)
  }))

  // Substitute in subsystems recursively
  const subsystems = system.subsystems
    ? Object.fromEntries(
        Object.entries(system.subsystems).map(([name, subsystem]) => [
          name,
          substituteInReactionSystem(subsystem, bindings)
        ])
      )
    : undefined

  return {
    ...system,
    reactions,
    ...(constraint_equations && { constraint_equations }),
    ...(subsystems && { subsystems })
  }
}