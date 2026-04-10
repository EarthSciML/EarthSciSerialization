/**
 * Code generation for the ESM format
 *
 * This module provides functions to generate self-contained scripts
 * from ESM files in multiple target languages:
 * - Julia: compatible with ModelingToolkit, Catalyst, EarthSciMLBase, and OrdinaryDiffEq
 * - Python: compatible with SymPy, earthsci_toolkit, and SciPy
 */

import type { EsmFile, Model, ReactionSystem, Expression, ExpressionNode, Equation, ModelVariable, Species, Reaction, ContinuousEvent, DiscreteEvent, CouplingEntry, Domain, DataLoader } from './types.js'
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

  // Generate coupling code
  if (file.coupling && file.coupling.length > 0) {
    lines.push('# Coupling')
    for (const coupling of file.coupling) {
      lines.push(...generateCouplingCode(coupling))
    }
    lines.push('')
  }

  // Generate domain code
  if (file.domain) {
    lines.push('# Domain')
    lines.push(...generateDomainCode(file.domain))
    lines.push('')
  }

  // Generate data loaders code
  if (file.data_loaders && Object.keys(file.data_loaders).length > 0) {
    lines.push('# Data Loaders')
    for (const [name, dataLoader] of Object.entries(file.data_loaders)) {
      lines.push(...generateDataLoaderCode(name, dataLoader))
    }
    lines.push('')
  }

  return lines.join('\n')
}

/**
 * Generate a self-contained Python script from an ESM file
 * @param file ESM file to generate Python code for
 * @returns Python script as a string
 */
export function toPythonCode(file: EsmFile): string {
  const lines: string[] = []

  // Header comment
  lines.push(`# Generated Python script from ESM file`)
  lines.push(`# ESM version: ${file.esm}`)
  if (file.metadata?.title) {
    lines.push(`# Title: ${file.metadata.title}`)
  }
  if (file.metadata?.description) {
    lines.push(`# Description: ${file.metadata.description}`)
  }
  lines.push('')

  // Import statements
  lines.push('# Package imports')
  lines.push('import sympy as sp')
  lines.push('import earthsci_toolkit as esm')
  lines.push('import scipy')
  lines.push('from sympy import Function')
  lines.push('')

  // Generate models
  if (file.models && Object.keys(file.models).length > 0) {
    lines.push('# Models')
    for (const [name, model] of Object.entries(file.models)) {
      lines.push(...generatePythonModelCode(name, model))
      lines.push('')
    }
  }

  // Generate reaction systems
  if (file.reaction_systems && Object.keys(file.reaction_systems).length > 0) {
    lines.push('# Reaction Systems')
    for (const [name, reactionSystem] of Object.entries(file.reaction_systems)) {
      lines.push(...generatePythonReactionSystemCode(name, reactionSystem))
      lines.push('')
    }
  }

  // Generate simulation setup with actual default values
  lines.push('# Simulation setup')
  lines.push('tspan = (0, 10)  # time span')

  // Collect default values from all models and reaction systems
  const parameters: { [key: string]: any } = {}
  const initialConditions: { [key: string]: any } = {}

  // Collect from models
  if (file.models) {
    for (const model of Object.values(file.models)) {
      if (model.variables) {
        for (const [varName, variable] of Object.entries(model.variables)) {
          if (variable.type === 'parameter' && variable.default !== undefined) {
            parameters[varName] = variable.default
          } else if (variable.type === 'state' && variable.default !== undefined) {
            initialConditions[varName] = variable.default
          }
        }
      }
    }
  }

  // Collect from reaction systems
  if (file.reaction_systems) {
    for (const reactionSystem of Object.values(file.reaction_systems)) {
      if (reactionSystem.species) {
        for (const [speciesName, species] of Object.entries(reactionSystem.species)) {
          // Handle both "default" and "initial_value" properties, with "default" taking precedence
          const initialValue = species.default !== undefined ? species.default : (species as any).initial_value
          if (initialValue !== undefined) {
            initialConditions[speciesName] = initialValue
          }
        }
      }
    }
  }

  // Generate parameters dictionary
  if (Object.keys(parameters).length > 0) {
    lines.push('parameters = {')
    for (const [name, value] of Object.entries(parameters)) {
      lines.push(`    "${name}": ${value},`)
    }
    lines.push('}')
  } else {
    lines.push('parameters = {}  # no parameter defaults specified')
  }

  // Generate initial conditions dictionary
  if (Object.keys(initialConditions).length > 0) {
    lines.push('initial_conditions = {')
    for (const [name, value] of Object.entries(initialConditions)) {
      lines.push(`    "${name}": ${value},`)
    }
    lines.push('}')
  } else {
    lines.push('initial_conditions = {}  # no initial condition defaults specified')
  }

  lines.push('')
  lines.push('# result = esm.simulate(tspan=tspan, parameters=parameters, initial_conditions=initial_conditions)')
  lines.push('')

  // Generate coupling, domain, and data loader code
  if (file.coupling && file.coupling.length > 0) {
    lines.push('# Coupling')
    for (const coupling of file.coupling) {
      lines.push(...generatePythonCouplingCode(coupling))
    }
    lines.push('')
  }

  if (file.domain) {
    lines.push('# Domain')
    lines.push(...generatePythonDomainCode(file.domain))
    lines.push('')
  }

  // Generate data loaders code
  if (file.data_loaders && Object.keys(file.data_loaders).length > 0) {
    lines.push('# Data Loaders')
    for (const [name, dataLoader] of Object.entries(file.data_loaders)) {
      lines.push(...generatePythonDataLoaderCode(name, dataLoader))
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
  const stateVars: (ModelVariable & { name: string })[] = []
  const parameters: (ModelVariable & { name: string })[] = []

  if (model.variables) {
    for (const [varName, variable] of Object.entries(model.variables)) {
      if (variable.type === 'state') {
        stateVars.push({ ...variable, name: varName })
      } else if (variable.type === 'parameter') {
        parameters.push({ ...variable, name: varName })
      }
    }
  }

  // Generate @variables declaration
  if (stateVars.length > 0) {
    const varDecls = stateVars.map(v => formatVariableDeclaration(v, v.name)).join(' ')
    lines.push(`@variables t ${varDecls}`)
  }

  // Generate @parameters declaration
  if (parameters.length > 0) {
    const paramDecls = parameters.map(v => formatVariableDeclaration(v, v.name)).join(' ')
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
    const speciesDecls = Object.entries(reactionSystem.species)
      .map(([name, s]) => formatSpeciesDeclaration(s, name)).join(' ')
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
 * Generate coupling code for Julia
 */
function generateCouplingCode(coupling: CouplingEntry): string[] {
  const lines: string[] = []

  // Generate comment first for clarity
  lines.push(`# Coupling ${coupling.type}: ${coupling.from} -> ${coupling.to}`)

  // Different coupling implementations based on type
  switch (coupling.type) {
    case 'explicit':
      lines.push(`${coupling.from}_to_${coupling.to}_coupling = ConnectorSystem([`)
      if (coupling.variables && coupling.variables.length > 0) {
        for (const variable of coupling.variables) {
          lines.push(`    ${coupling.from}_system.${variable} ~ ${coupling.to}_system.${variable},`)
        }
      }
      lines.push(`])`)
      break
    case 'operator_compose':
      lines.push(`${coupling.from}_${coupling.to}_composed = compose(${coupling.from}_system, ${coupling.to}_system)`)
      break
    case 'operator_apply':
      lines.push(`${coupling.from}_${coupling.to}_applied = apply(${coupling.from}_operator, ${coupling.to}_system)`)
      break
    default:
      lines.push(`# Coupling type '${coupling.type}' implementation`)
      lines.push(`${coupling.from}_${coupling.to}_coupling = couple(${coupling.from}_system, ${coupling.to}_system)`)
  }

  return lines
}

/**
 * Generate domain code for Julia
 */
function generateDomainCode(domain: Domain): string[] {
  const lines: string[] = []

  // Independent variable (time)
  const timeVar = domain.independent_variable || 't'
  lines.push(`# Time domain setup`)
  lines.push(`@variables ${timeVar}`)

  // Spatial coordinates
  if (domain.spatial_coordinates && domain.spatial_coordinates.length > 0) {
    lines.push(`# Spatial coordinates`)
    const spatialVars = domain.spatial_coordinates.join(' ')
    lines.push(`@variables ${spatialVars}`)
  }

  // Temporal domain
  if (domain.temporal) {
    lines.push(`# Temporal domain`)
    const start = domain.temporal.start || '0.0'
    const end = domain.temporal.end || '1.0'
    lines.push(`tspan = (${start}, ${end})`)
  }

  // Discretization for spatial domain
  if (domain.discretization) {
    lines.push(`# Domain discretization`)
    for (const [dim, disc] of Object.entries(domain.discretization)) {
      lines.push(`${dim}_discretization = Discretization(${JSON.stringify(disc)})`)
    }
  }

  return lines
}

/**
 * Generate data loader code for Julia
 */
function generateDataLoaderCode(name: string, dataLoader: DataLoader): string[] {
  const lines: string[] = []

  lines.push(`# Data loader: ${name}`)

  // Type-specific data loader implementations
  switch (dataLoader.type) {
    case 'gridded_data':
      lines.push(`${name}_loader = GriddedDataLoader("${dataLoader.loader_id}")`)
      if (dataLoader.source) {
        lines.push(`${name}_data = load_gridded_data("${dataLoader.source}")`)
      }
      break
    case 'emissions':
      lines.push(`${name}_loader = EmissionsLoader("${dataLoader.loader_id}")`)
      if (dataLoader.source) {
        lines.push(`${name}_emissions = load_emissions("${dataLoader.source}")`)
      }
      break
    case 'timeseries':
      lines.push(`${name}_loader = TimeSeriesLoader("${dataLoader.loader_id}")`)
      if (dataLoader.source) {
        lines.push(`${name}_timeseries = load_timeseries("${dataLoader.source}")`)
      }
      break
    case 'static':
      lines.push(`${name}_loader = StaticDataLoader("${dataLoader.loader_id}")`)
      if (dataLoader.source) {
        lines.push(`${name}_static = load_static_data("${dataLoader.source}")`)
      }
      break
    case 'callback':
      lines.push(`${name}_loader = CallbackDataLoader("${dataLoader.loader_id}")`)
      break
    default:
      lines.push(`${name}_loader = DataLoader("${dataLoader.loader_id}")`)
  }

  // Configuration
  if (dataLoader.config) {
    lines.push(`configure!(${name}_loader, ${JSON.stringify(dataLoader.config)})`)
  }

  // Variables provided
  if (dataLoader.provides) {
    lines.push(`# Variables provided by ${name}:`)
    for (const [variable, info] of Object.entries(dataLoader.provides)) {
      const units = info.units ? ` (${info.units})` : ''
      const desc = info.description ? ` - ${info.description}` : ''
      lines.push(`#   ${variable}${units}${desc}`)
    }
  }

  return lines
}

/**
 * Format a variable declaration with defaults and units
 */
function formatVariableDeclaration(variable: ModelVariable, name: string): string {
  let decl = name

  // Add default value and units if present (check both "units" and "unit" properties for compatibility)
  const units = variable.units || (variable as any).unit
  if (variable.default !== undefined || units) {
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

    if (units) {
      parts.push(`u"${units}"`)
    }

    decl += parts.join(', ')
    decl += ')'
  }

  return decl
}

/**
 * Format a species declaration
 */
function formatSpeciesDeclaration(species: Species, name: string): string {
  let decl = name

  // Add default value if present (check both "default" and "initial_value" properties for compatibility)
  const initialValue = species.default !== undefined ? species.default : (species as any).initial_value
  if (initialValue !== undefined) {
    // Ensure decimal point for floating point numbers
    if (typeof initialValue === 'number' && Number.isInteger(initialValue)) {
      decl += `(${initialValue}.0)`
    } else {
      decl += `(${initialValue})`
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

  // Format substrates (reactants) - handle both "substrates" and "reactants" properties for compatibility
  const substrates = reaction.substrates || (reaction as any).reactants
  const reactants = substrates ?
    substrates.map((r: any) => r.stoichiometry && r.stoichiometry !== 1 ?
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

/**
 * Generate Python code for a model
 */
function generatePythonModelCode(name: string, model: Model): string[] {
  const lines: string[] = []

  lines.push(`# Model: ${name}`)

  // Collect state variables and parameters
  const stateVars: (ModelVariable & { name: string })[] = []
  const parameters: (ModelVariable & { name: string })[] = []

  if (model.variables) {
    for (const [varName, variable] of Object.entries(model.variables)) {
      if (variable.type === 'state') {
        stateVars.push({ ...variable, name: varName })
      } else if (variable.type === 'parameter') {
        parameters.push({ ...variable, name: varName })
      }
    }
  }

  // Generate time symbol if needed
  const hasDerivatives = model.equations && model.equations.some(eq =>
    hasDerivativeInExpression(eq.lhs) || hasDerivativeInExpression(eq.rhs)
  )
  if (hasDerivatives) {
    lines.push('# Time variable')
    lines.push('t = sp.Symbol(\'t\')')
    lines.push('')
  }

  // Generate symbol/function definitions
  if (stateVars.length > 0) {
    lines.push('# State variables')
    for (const variable of stateVars) {
      // Check both "units" and "unit" properties for compatibility
      const units = variable.units || (variable as any).unit
      const comment = units ? `  # ${units}` : ''
      if (variable.name && variable.name.includes('(')) {
        // Function symbol (e.g., contains parentheses)
        lines.push(`${variable.name} = sp.Function('${variable.name.split('(')[0]}')${comment}`)
      } else {
        // Regular symbol - but make it a function if derivatives are present
        if (hasDerivatives) {
          lines.push(`${variable.name} = sp.Function('${variable.name}')${comment}`)
        } else {
          lines.push(`${variable.name} = sp.Symbol('${variable.name}')${comment}`)
        }
      }
    }
    lines.push('')
  }

  if (parameters.length > 0) {
    lines.push('# Parameters')
    for (const parameter of parameters) {
      // Check both "units" and "unit" properties for compatibility
      const units = parameter.units || (parameter as any).unit
      const comment = units ? `  # ${units}` : ''
      lines.push(`${parameter.name} = sp.Symbol('${parameter.name}')${comment}`)
    }
    lines.push('')
  }

  // Generate equations
  if (model.equations && model.equations.length > 0) {
    lines.push('# Equations')
    for (const [i, equation] of model.equations.entries()) {
      const lhs = formatPythonExpression(equation.lhs)
      const rhs = formatPythonExpression(equation.rhs)
      lines.push(`eq${i + 1} = sp.Eq(${lhs}, ${rhs})`)
    }
  }

  return lines
}

/**
 * Generate Python code for a reaction system
 */
function generatePythonReactionSystemCode(name: string, reactionSystem: ReactionSystem): string[] {
  const lines: string[] = []

  lines.push(`# Reaction System: ${name}`)

  // Generate species symbols
  if (reactionSystem.species && Object.keys(reactionSystem.species).length > 0) {
    lines.push('# Species')
    for (const [name, species] of Object.entries(reactionSystem.species)) {
      lines.push(`${name} = sp.Symbol('${name}')`)
    }
    lines.push('')
  }

  // Generate reaction rate expressions
  if (reactionSystem.reactions && Object.keys(reactionSystem.reactions).length > 0) {
    lines.push('# Rate expressions')
    for (const [reactionName, reaction] of Object.entries(reactionSystem.reactions)) {
      if (reaction.rate) {
        const rateExpr = formatPythonExpression(reaction.rate)
        lines.push(`${reactionName}_rate = ${rateExpr}`)
      }
    }
    lines.push('')

    lines.push('# Stoichiometry setup (TODO: Implement reaction network)')
    for (const [reactionName, reaction] of Object.entries(reactionSystem.reactions)) {
      lines.push(`# Reaction: ${reactionName}`)
      // Handle both "substrates" and "reactants" properties for compatibility
      const substrates = reaction.substrates || (reaction as any).reactants
      if (substrates) {
        const reactantStr = substrates
          .map((r: any) => r.stoichiometry && r.stoichiometry !== 1 ? `${r.stoichiometry}*${r.species}` : r.species)
          .join(' + ')
        lines.push(`#   Reactants: ${reactantStr}`)
      }
      if (reaction.products) {
        const productStr = reaction.products
          .map(p => p.stoichiometry && p.stoichiometry !== 1 ? `${p.stoichiometry}*${p.species}` : p.species)
          .join(' + ')
        lines.push(`#   Products: ${productStr}`)
      }
    }
  }

  return lines
}

/**
 * Generate coupling code for Python
 */
function generatePythonCouplingCode(coupling: CouplingEntry): string[] {
  const lines: string[] = []

  lines.push(`# Coupling ${coupling.type}: ${coupling.from} -> ${coupling.to}`)

  // Different coupling implementations based on type
  switch (coupling.type) {
    case 'explicit':
      lines.push(`${coupling.from}_to_${coupling.to}_coupling = esm.ExplicitCoupling(`)
      lines.push(`    from_model="${coupling.from}",`)
      lines.push(`    to_model="${coupling.to}",`)
      if (coupling.variables && coupling.variables.length > 0) {
        lines.push(`    variables=${JSON.stringify(coupling.variables)}`)
      }
      lines.push(`)`)
      break
    case 'operator_compose':
      lines.push(`${coupling.from}_${coupling.to}_composed = esm.compose_systems(${coupling.from}_system, ${coupling.to}_system)`)
      break
    case 'operator_apply':
      lines.push(`${coupling.from}_${coupling.to}_applied = esm.apply_operator(${coupling.from}_operator, ${coupling.to}_system)`)
      break
    default:
      lines.push(`# Coupling type '${coupling.type}' implementation`)
      lines.push(`${coupling.from}_${coupling.to}_coupling = esm.couple_systems(${coupling.from}_system, ${coupling.to}_system)`)
  }

  return lines
}

/**
 * Generate domain code for Python
 */
function generatePythonDomainCode(domain: Domain): string[] {
  const lines: string[] = []

  lines.push(`# Domain configuration`)

  // Independent variable (time)
  const timeVar = domain.independent_variable || 't'
  lines.push(`${timeVar} = sp.Symbol('${timeVar}')`)

  // Spatial coordinates
  if (domain.spatial_coordinates && domain.spatial_coordinates.length > 0) {
    lines.push(`# Spatial coordinates`)
    for (const coord of domain.spatial_coordinates) {
      lines.push(`${coord} = sp.Symbol('${coord}')`)
    }
  }

  // Temporal domain
  if (domain.temporal) {
    lines.push(`# Temporal domain`)
    const start = domain.temporal.start || '0.0'
    const end = domain.temporal.end || '1.0'
    lines.push(`tspan = (${start}, ${end})`)

    if (domain.temporal.reference_time) {
      lines.push(`reference_time = "${domain.temporal.reference_time}"`)
    }
  }

  // Domain setup
  lines.push(`domain = esm.Domain(`)
  lines.push(`    spatial_coordinates=[${domain.spatial_coordinates?.map(c => `"${c}"`).join(', ') || ''}],`)
  if (domain.temporal) {
    lines.push(`    temporal=esm.TemporalDomain(`)
    lines.push(`        start=${domain.temporal.start || '0.0'},`)
    lines.push(`        end=${domain.temporal.end || '1.0'}`)
    lines.push(`    )`)
  }
  lines.push(`)`)

  return lines
}

/**
 * Generate data loader code for Python
 */
function generatePythonDataLoaderCode(name: string, dataLoader: DataLoader): string[] {
  const lines: string[] = []

  lines.push(`# Data loader: ${name}`)

  // Type-specific data loader implementations
  switch (dataLoader.type) {
    case 'gridded_data':
      lines.push(`${name}_loader = esm.GriddedDataLoader("${dataLoader.loader_id}")`)
      if (dataLoader.source) {
        lines.push(`${name}_data = ${name}_loader.load("${dataLoader.source}")`)
      }
      break
    case 'emissions':
      lines.push(`${name}_loader = esm.EmissionsLoader("${dataLoader.loader_id}")`)
      if (dataLoader.source) {
        lines.push(`${name}_emissions = ${name}_loader.load("${dataLoader.source}")`)
      }
      break
    case 'timeseries':
      lines.push(`${name}_loader = esm.TimeSeriesLoader("${dataLoader.loader_id}")`)
      if (dataLoader.source) {
        lines.push(`${name}_timeseries = ${name}_loader.load("${dataLoader.source}")`)
      }
      break
    case 'static':
      lines.push(`${name}_loader = esm.StaticDataLoader("${dataLoader.loader_id}")`)
      if (dataLoader.source) {
        lines.push(`${name}_static = ${name}_loader.load("${dataLoader.source}")`)
      }
      break
    case 'callback':
      lines.push(`${name}_loader = esm.CallbackDataLoader("${dataLoader.loader_id}")`)
      break
    default:
      lines.push(`${name}_loader = esm.DataLoader("${dataLoader.loader_id}")`)
  }

  // Configuration
  if (dataLoader.config) {
    lines.push(`${name}_loader.configure(${JSON.stringify(dataLoader.config)})`)
  }

  // Variables provided
  if (dataLoader.provides) {
    lines.push(`# Variables provided by ${name}:`)
    for (const [variable, info] of Object.entries(dataLoader.provides)) {
      const units = info.units ? ` (${info.units})` : ''
      const desc = info.description ? ` - ${info.description}` : ''
      lines.push(`#   ${variable}${units}${desc}`)
    }
  }

  return lines
}

/**
 * Format an expression for Python code generation
 */
function formatPythonExpression(expr: Expression): string {
  if (typeof expr === 'number') {
    return expr.toString()
  }

  if (typeof expr === 'string') {
    return expr
  }

  if (typeof expr === 'object' && expr.op) {
    return formatPythonExpressionNode(expr)
  }

  throw new Error(`Unsupported expression type: ${typeof expr}`)
}

/**
 * Format an expression node for Python, applying operator mappings
 */
function formatPythonExpressionNode(node: ExpressionNode): string {
  const { op, args } = node

  // Apply expression mappings as specified in task description
  switch (op) {
    case '+':
      return args.map(formatPythonExpression).join(' + ')
    case '*':
      return args.map(formatPythonExpression).join(' * ')
    case 'D':
      // D(x,t) → Derivative(x(t), t)
      if (args.length >= 1) {
        const varName = formatPythonExpression(args[0])
        // Assume time variable t
        return `sp.Derivative(${varName}(t), t)`
      }
      return 'sp.Derivative()'
    case 'exp':
      return `sp.exp(${args.map(formatPythonExpression).join(', ')})`
    case 'ifelse':
      // ifelse(condition, true_val, false_val) → sp.Piecewise((true_val, condition), (false_val, True))
      if (args.length >= 3) {
        const condition = formatPythonExpression(args[0])
        const trueVal = formatPythonExpression(args[1])
        const falseVal = formatPythonExpression(args[2])
        return `sp.Piecewise((${trueVal}, ${condition}), (${falseVal}, True))`
      }
      return `sp.Piecewise((0, True))`
    case 'Pre':
      // Pre → Function('Pre')
      return `Function('Pre')(${args.map(formatPythonExpression).join(', ')})`
    case '^':
      // ^ → **
      return args.map(formatPythonExpression).join(' ** ')
    case 'grad':
      // grad(x,y) → sp.Derivative(x, y)
      if (args.length >= 2) {
        const func = formatPythonExpression(args[0])
        const var_ = formatPythonExpression(args[1])
        return `sp.Derivative(${func}, ${var_})`
      } else if (args.length === 1) {
        // Default to x if dimension not specified
        return `sp.Derivative(${formatPythonExpression(args[0])}, x)`
      }
      return 'sp.Derivative()'
    case '-':
      if (args.length === 1) {
        return `-${formatPythonExpression(args[0])}`
      } else {
        return args.map(formatPythonExpression).join(' - ')
      }
    case '/':
      return args.map(formatPythonExpression).join(' / ')
    case '<': case '>': case '<=': case '>=': case '==': case '!=':
      return args.map(formatPythonExpression).join(` ${op} `)
    case 'and':
      return args.map(formatPythonExpression).join(' & ')
    case 'or':
      return args.map(formatPythonExpression).join(' | ')
    case 'not':
      return `~(${formatPythonExpression(args[0])})`
    default:
      // For other operators, use function call syntax
      return `${op}(${args.map(formatPythonExpression).join(', ')})`
  }
}

/**
 * Check if an expression contains derivatives
 */
function hasDerivativeInExpression(expr: Expression): boolean {
  if (typeof expr === 'object' && expr.op) {
    if (expr.op === 'D') {
      return true
    }
    return expr.args.some(arg => hasDerivativeInExpression(arg))
  }
  return false
}