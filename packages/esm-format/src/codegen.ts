/**
 * Julia code generation for the ESM format
 *
 * This module provides functions to generate self-contained Julia scripts
 * from ESM files, compatible with ModelingToolkit, Catalyst, EarthSciMLBase,
 * and OrdinaryDiffEq packages.
 */

import type { EsmFile, Model, ReactionSystem, Expression, ExpressionNode, Equation, ModelVariable, Species, Reaction, ContinuousEvent, DiscreteEvent, CouplingEntry, Domain, Solver, DataLoader } from './types.js'
import { toAscii } from './pretty-print.js'

/**
 * Generate a self-contained Julia script from an ESM file
 * @param file ESM file to generate Julia code for
 * @returns Julia script as a string
 */
export function toJuliaCode(file: EsmFile): string {
  const lines: string[] = []

  // Header comment
  lines.push(`# Generated Julia script from ESM file`)
  lines.push(`# ESM version: ${file.esm}`)
  if (file.metadata?.title) {
    lines.push(`# Title: ${file.metadata.title}`)
  }
  if (file.metadata?.description) {
    lines.push(`# Description: ${file.metadata.description}`)
  }
  lines.push('')

  // Using statements
  lines.push('# Package imports')
  lines.push('using ModelingToolkit')
  lines.push('using Catalyst')
  lines.push('using EarthSciMLBase')
  lines.push('using OrdinaryDiffEq')
  lines.push('using Unitful')
  lines.push('')

  // Generate models
  if (file.models && Object.keys(file.models).length > 0) {
    lines.push('# Models')
    for (const [name, model] of Object.entries(file.models)) {
      lines.push(...generateModelCode(name, model))
      lines.push('')
    }
  }

  // Generate reaction systems
  if (file.reaction_systems && Object.keys(file.reaction_systems).length > 0) {
    lines.push('# Reaction Systems')
    for (const [name, reactionSystem] of Object.entries(file.reaction_systems)) {
      lines.push(...generateReactionSystemCode(name, reactionSystem))
      lines.push('')
    }
  }

  // Generate events
  if (file.events && Object.keys(file.events).length > 0) {
    lines.push('# Events')
    for (const [name, event] of Object.entries(file.events)) {
      lines.push(...generateEventCode(name, event))
      lines.push('')
    }
  }

  // Generate coupling as TODO comments
  if (file.coupling && file.coupling.length > 0) {
    lines.push('# Coupling (TODO)')
    for (const coupling of file.coupling) {
      lines.push(...generateCouplingComment(coupling))
    }
    lines.push('')
  }

  // Generate domain as TODO comment
  if (file.domain) {
    lines.push('# Domain (TODO)')
    lines.push(...generateDomainComment(file.domain))
    lines.push('')
  }

  // Generate solver as TODO comment
  if (file.solver) {
    lines.push('# Solver (TODO)')
    lines.push(...generateSolverComment(file.solver))
    lines.push('')
  }

  // Generate data loaders as TODO comments
  if (file.data_loaders && Object.keys(file.data_loaders).length > 0) {
    lines.push('# Data Loaders (TODO)')
    for (const [name, dataLoader] of Object.entries(file.data_loaders)) {
      lines.push(...generateDataLoaderComment(name, dataLoader))
    }
    lines.push('')
  }

  return lines.join('\n')
}

/**
 * Generate Julia code for a model
 */
function generateModelCode(name: string, model: Model): string[] {
  const lines: string[] = []

  lines.push(`# Model: ${name}`)

  // Collect state variables and parameters
  const stateVars: ModelVariable[] = []
  const parameters: ModelVariable[] = []

  if (model.variables) {
    for (const variable of Object.values(model.variables)) {
      if (variable.type === 'state') {
        stateVars.push(variable)
      } else if (variable.type === 'parameter') {
        parameters.push(variable)
      }
    }
  }

  // Generate @variables declaration
  if (stateVars.length > 0) {
    const varDecls = stateVars.map(v => formatVariableDeclaration(v)).join(' ')
    lines.push(`@variables t ${varDecls}`)
  }

  // Generate @parameters declaration
  if (parameters.length > 0) {
    const paramDecls = parameters.map(v => formatVariableDeclaration(v)).join(' ')
    lines.push(`@parameters ${paramDecls}`)
  }

  // Generate equations
  if (model.equations && model.equations.length > 0) {
    lines.push('')
    lines.push('eqs = [')
    for (const equation of model.equations) {
      lines.push(`    ${formatEquation(equation)},`)
    }
    lines.push(']')
  }

  // Generate @named ODESystem
  lines.push('')
  lines.push(`@named ${name}_system = ODESystem(eqs)`)

  return lines
}

/**
 * Generate Julia code for a reaction system
 */
function generateReactionSystemCode(name: string, reactionSystem: ReactionSystem): string[] {
  const lines: string[] = []

  lines.push(`# Reaction System: ${name}`)

  // Generate @species declaration
  if (reactionSystem.species && Object.keys(reactionSystem.species).length > 0) {
    const speciesDecls = Object.values(reactionSystem.species)
      .map(s => formatSpeciesDeclaration(s)).join(' ')
    lines.push(`@species ${speciesDecls}`)
  }

  // Generate @parameters for reaction parameters
  const reactionParams = new Set<string>()
  if (reactionSystem.reactions) {
    for (const reaction of Object.values(reactionSystem.reactions)) {
      // Extract parameter names from rate expressions
      if (reaction.rate) {
        const paramNames = extractParameterNames(reaction.rate)
        paramNames.forEach(p => reactionParams.add(p))
      }
    }
  }

  if (reactionParams.size > 0) {
    lines.push(`@parameters ${Array.from(reactionParams).join(' ')}`)
  }

  // Generate reactions
  if (reactionSystem.reactions && Object.keys(reactionSystem.reactions).length > 0) {
    lines.push('')
    lines.push('rxs = [')
    for (const reaction of Object.values(reactionSystem.reactions)) {
      lines.push(`    ${formatReaction(reaction)},`)
    }
    lines.push(']')
  }

  // Generate @named ReactionSystem
  lines.push('')
  lines.push(`@named ${name}_system = ReactionSystem(rxs)`)

  return lines
}

/**
 * Generate Julia code for events
 */
function generateEventCode(name: string, event: ContinuousEvent | DiscreteEvent): string[] {
  const lines: string[] = []

  if ('condition' in event) {
    // Continuous event
    lines.push(`# Continuous Event: ${name}`)
    const condition = formatExpression(event.condition)
    const affect = formatAffect(event.affect)
    lines.push(`${name}_event = SymbolicContinuousCallback(${condition}, ${affect})`)
  } else {
    // Discrete event
    lines.push(`# Discrete Event: ${name}`)
    const trigger = formatDiscreteTrigger(event.trigger)
    const affect = formatAffect(event.affect)
    lines.push(`${name}_event = DiscreteCallback(${trigger}, ${affect})`)
  }

  return lines
}

/**
 * Generate coupling TODO comments
 */
function generateCouplingComment(coupling: CouplingEntry): string[] {
  const lines: string[] = []
  lines.push(`# TODO: Implement coupling ${coupling.type}`)
  lines.push(`#   From: ${coupling.from}`)
  lines.push(`#   To: ${coupling.to}`)
  if (coupling.variables && coupling.variables.length > 0) {
    lines.push(`#   Variables: ${coupling.variables.join(', ')}`)
  }
  return lines
}

/**
 * Generate domain TODO comments
 */
function generateDomainComment(domain: Domain): string[] {
  const lines: string[] = []
  lines.push(`# TODO: Implement domain`)
  if (domain.spatial_coordinates && domain.spatial_coordinates.length > 0) {
    lines.push(`#   Spatial coordinates: ${domain.spatial_coordinates.join(', ')}`)
  }
  if (domain.temporal_coordinates && domain.temporal_coordinates.length > 0) {
    lines.push(`#   Temporal coordinates: ${domain.temporal_coordinates.join(', ')}`)
  }
  return lines
}

/**
 * Generate solver TODO comments
 */
function generateSolverComment(solver: Solver): string[] {
  const lines: string[] = []
  lines.push(`# TODO: Implement solver`)
  if (solver.algorithm) {
    lines.push(`#   Algorithm: ${solver.algorithm}`)
  }
  if (solver.tolerances) {
    lines.push(`#   Tolerances: ${JSON.stringify(solver.tolerances)}`)
  }
  return lines
}

/**
 * Generate data loader TODO comments
 */
function generateDataLoaderComment(name: string, dataLoader: DataLoader): string[] {
  const lines: string[] = []
  lines.push(`# TODO: Implement data loader ${name}`)
  if (dataLoader.source) {
    lines.push(`#   Source: ${dataLoader.source}`)
  }
  if (dataLoader.format) {
    lines.push(`#   Format: ${dataLoader.format}`)
  }
  return lines
}

/**
 * Format a variable declaration with defaults and units
 */
function formatVariableDeclaration(variable: ModelVariable): string {
  let decl = variable.name || 'unnamed'

  // Add default value and units if present
  if (variable.default !== undefined || variable.unit) {
    decl += '('
    const parts: string[] = []

    if (variable.default !== undefined) {
      // Ensure decimal point for floating point numbers
      const defaultVal = variable.default
      if (typeof defaultVal === 'number' && Number.isInteger(defaultVal)) {
        parts.push(`${defaultVal}.0`)
      } else {
        parts.push(`${defaultVal}`)
      }
    }

    if (variable.unit) {
      parts.push(`u"${variable.unit}"`)
    }

    decl += parts.join(', ')
    decl += ')'
  }

  return decl
}

/**
 * Format a species declaration
 */
function formatSpeciesDeclaration(species: Species): string {
  let decl = species.name || 'unnamed'

  // Add default value if present
  if (species.initial_value !== undefined) {
    // Ensure decimal point for floating point numbers
    const initialVal = species.initial_value
    if (typeof initialVal === 'number' && Number.isInteger(initialVal)) {
      decl += `(${initialVal}.0)`
    } else {
      decl += `(${initialVal})`
    }
  }

  return decl
}

/**
 * Format an equation using ~ syntax
 */
function formatEquation(equation: Equation): string {
  const lhs = formatExpression(equation.lhs)
  const rhs = formatExpression(equation.rhs)
  return `${lhs} ~ ${rhs}`
}

/**
 * Format a reaction
 */
function formatReaction(reaction: Reaction): string {
  const rate = reaction.rate ? formatExpression(reaction.rate) : '1.0'

  // Format reactants
  const reactants = reaction.reactants ?
    reaction.reactants.map(r => r.stoichiometry && r.stoichiometry !== 1 ?
      `${r.stoichiometry}*${r.species}` : r.species).join(' + ') :
    '∅'

  // Format products
  const products = reaction.products ?
    reaction.products.map(p => p.stoichiometry && p.stoichiometry !== 1 ?
      `${p.stoichiometry}*${p.species}` : p.species).join(' + ') :
    '∅'

  return `Reaction(${rate}, [${reactants}], [${products}])`
}

/**
 * Format an expression for Julia code generation
 */
function formatExpression(expr: Expression): string {
  if (typeof expr === 'number') {
    return expr.toString()
  }

  if (typeof expr === 'string') {
    return expr
  }

  if (typeof expr === 'object' && expr.op) {
    return formatExpressionNode(expr)
  }

  throw new Error(`Unsupported expression type: ${typeof expr}`)
}

/**
 * Format an expression node for Julia, applying operator mappings
 */
function formatExpressionNode(node: ExpressionNode): string {
  const { op, args, wrt } = node

  // Apply expression mappings as specified in task description
  switch (op) {
    case '+':
      return args.map(formatExpression).join(' + ')
    case '*':
      return args.map(formatExpression).join(' * ')
    case 'D':
      // D(x,t) → D(x) (remove time parameter)
      if (args.length >= 1) {
        return `D(${formatExpression(args[0])})`
      }
      return 'D()'
    case 'exp':
      return `exp(${args.map(formatExpression).join(', ')})`
    case 'ifelse':
      return `ifelse(${args.map(formatExpression).join(', ')})`
    case 'Pre':
      return `Pre(${args.map(formatExpression).join(', ')})`
    case '^':
      return args.map(formatExpression).join(' ^ ')
    case 'grad':
      // grad(x,y) → Differential(y)(x)
      if (args.length >= 2) {
        return `Differential(${formatExpression(args[1])})(${formatExpression(args[0])})`
      } else if (args.length === 1) {
        // Default to x if dimension not specified
        return `Differential(x)(${formatExpression(args[0])})`
      }
      return 'Differential(x)()'
    case '-':
      if (args.length === 1) {
        return `-${formatExpression(args[0])}`
      } else {
        return args.map(formatExpression).join(' - ')
      }
    case '/':
      return args.map(formatExpression).join(' / ')
    case '<': case '>': case '<=': case '>=': case '==': case '!=':
      return args.map(formatExpression).join(` ${op} `)
    case 'and':
      return args.map(formatExpression).join(' && ')
    case 'or':
      return args.map(formatExpression).join(' || ')
    case 'not':
      return `!(${formatExpression(args[0])})`
    default:
      // For other operators, use function call syntax
      return `${op}(${args.map(formatExpression).join(', ')})`
  }
}

/**
 * Format affect clause for events
 */
function formatAffect(affect: any): string {
  if (Array.isArray(affect)) {
    return `[${affect.map(formatAffectEquation).join(', ')}]`
  } else if (affect && typeof affect === 'object' && (affect.lhs || affect.rhs)) {
    return formatAffectEquation(affect)
  } else {
    return 'nothing'
  }
}

/**
 * Format a single affect equation
 */
function formatAffectEquation(affect: any): string {
  if (affect.lhs && affect.rhs) {
    return `${formatExpression(affect.lhs)} ~ ${formatExpression(affect.rhs)}`
  }
  return 'nothing'
}

/**
 * Format discrete event trigger
 */
function formatDiscreteTrigger(trigger: any): string {
  if (trigger.condition) {
    return formatExpression(trigger.condition)
  }
  return 'true'
}

/**
 * Extract parameter names from an expression
 */
function extractParameterNames(expr: Expression): Set<string> {
  const params = new Set<string>()

  if (typeof expr === 'string') {
    // Simple heuristic: single letters or names starting with k/K are likely parameters
    if (expr.length === 1 || expr.startsWith('k') || expr.startsWith('K')) {
      params.add(expr)
    }
  } else if (typeof expr === 'object' && expr.op) {
    // Recursively extract from arguments
    for (const arg of expr.args) {
      const childParams = extractParameterNames(arg)
      childParams.forEach(p => params.add(p))
    }
  }

  return params
}