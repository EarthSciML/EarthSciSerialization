/**
 * Unit parsing and dimensional analysis for ESM format
 *
 * This module implements unit string parsing and dimensional consistency checking
 * following the ESM specification Section 3.3.1.
 */

import type { Expression, ExpressionNode, EsmFile } from './types.js'

/**
 * Canonical dimensional representation
 * Maps base dimensions to their powers
 */
export interface DimensionalRep {
  // Base SI dimensions
  mol?: number    // amount of substance
  molec?: number  // molecular count (alternative to mol)
  m?: number      // length
  s?: number      // time
  K?: number      // temperature
  kg?: number     // mass
  A?: number      // electric current
  cd?: number     // luminous intensity

  // Derived dimensions commonly used in ESM
  cm?: number     // centimeter (length, alternative to m)
  J?: number      // joule (energy)
  Pa?: number     // pascal (pressure)

  // Dimensionless ratios
  dimensionless?: boolean  // true if completely dimensionless
}

/**
 * Result of dimensional analysis
 */
export interface UnitResult {
  dimensions: DimensionalRep
  warnings: string[]
}

/**
 * Unit validation warning
 */
export interface UnitWarning {
  message: string
  location?: string
  equation?: string
}

/**
 * Parse a unit string into canonical dimensional representation
 *
 * Handles common patterns:
 * - "mol/mol" → {dimensionless: true} (cancels out)
 * - "cm^3/molec/s" → {cm: 3, molec: -1, s: -1}
 * - "K" → {K: 1}
 * - "m/s" → {m: 1, s: -1}
 * - "1/s" → {s: -1}
 * - "degrees" → {dimensionless: true}
 *
 * @param unitStr Unit string to parse
 * @returns Dimensional representation
 */
export function parseUnit(unitStr: string): DimensionalRep {
  if (!unitStr || unitStr.trim() === '') {
    return { dimensionless: true }
  }

  // Handle special cases
  const normalized = unitStr.trim().toLowerCase()
  if (normalized === 'degrees' || normalized === 'dimensionless') {
    return { dimensionless: true }
  }

  // Initialize result
  const dimensions: DimensionalRep = {}

  // Split by division first
  const parts = unitStr.split('/')
  const numerator = parts[0] || '1'
  const denominatorParts = parts.slice(1)

  // Parse numerator
  parseUnitPart(numerator, dimensions, 1)

  // Parse denominator parts
  for (const part of denominatorParts) {
    parseUnitPart(part, dimensions, -1)
  }

  // Check if all dimensions cancel out
  const nonZeroDims = Object.entries(dimensions).filter(([key, value]) =>
    key !== 'dimensionless' && value !== 0
  )

  if (nonZeroDims.length === 0) {
    return { dimensionless: true }
  }

  // Remove zero dimensions from result
  const cleanDimensions: DimensionalRep = {}
  for (const [key, value] of Object.entries(dimensions)) {
    if (key !== 'dimensionless' && value !== 0) {
      cleanDimensions[key as keyof DimensionalRep] = value
    }
  }

  return cleanDimensions
}

/**
 * Parse a single unit part (numerator or denominator component)
 * @param part Unit part string
 * @param dimensions Dimensions object to modify
 * @param sign Sign (1 for numerator, -1 for denominator)
 */
function parseUnitPart(part: string, dimensions: DimensionalRep, sign: number): void {
  if (!part || part.trim() === '' || part.trim() === '1') {
    return
  }

  // Handle multiplication within the part
  const factors = part.split('*')

  for (let factor of factors) {
    factor = factor.trim()
    if (!factor || factor === '1') continue

    // Check for exponents using ^ notation
    const expMatch = factor.match(/^([a-zA-Z]+)(\^?)([\+\-]?\d*)$/)
    if (expMatch) {
      const [, base, caretOperator, exponentStr] = expMatch
      let exponent = 1

      if (caretOperator === '^' && exponentStr) {
        exponent = parseInt(exponentStr) || 1
      }

      const finalExponent = sign * exponent

      // Map to canonical dimension names
      const canonicalBase = mapToCanonicalDimension(base)
      if (canonicalBase) {
        dimensions[canonicalBase] = (dimensions[canonicalBase] || 0) + finalExponent
      }
    }
  }
}

/**
 * Map unit strings to canonical dimension names
 * @param unit Unit string
 * @returns Canonical dimension name or null if unrecognized
 */
function mapToCanonicalDimension(unit: string): keyof DimensionalRep | null {
  const lowerUnit = unit.toLowerCase()

  const mapping: Record<string, keyof DimensionalRep> = {
    'mol': 'mol',
    'molec': 'molec',
    'm': 'm',
    'meter': 'm',
    'metres': 'm',
    'meters': 'm',
    'cm': 'cm',
    'centimeter': 'cm',
    'centimeters': 'cm',
    's': 's',
    'sec': 's',
    'second': 's',
    'seconds': 's',
    'k': 'K',
    'kelvin': 'K',
    'kg': 'kg',
    'kilogram': 'kg',
    'kilograms': 'kg',
    'a': 'A',
    'ampere': 'A',
    'amperes': 'A',
    'cd': 'cd',
    'candela': 'cd',
    'j': 'J',
    'joule': 'J',
    'joules': 'J',
    'pa': 'Pa',
    'pascal': 'Pa',
    'pascals': 'Pa',
    'ppb': 'dimensionless',
    'ppm': 'dimensionless'
  }

  return mapping[lowerUnit] || null
}

/**
 * Check dimensional consistency of an expression
 *
 * Follows rules from ESM spec Section 3.3.1:
 * - Addition/subtraction: operands must have same dimensions
 * - Multiplication: dimensions add
 * - Division: dimensions subtract
 * - D(x,t): dimension of x divided by dimension of t
 * - Functions require dimensionless arguments; result is dimensionless
 *
 * @param expr Expression to check
 * @param unitBindings Map of variable names to their dimensional representations
 * @returns Unit result with dimensions and any warnings
 */
export function checkDimensions(expr: Expression, unitBindings: Map<string, DimensionalRep>): UnitResult {
  const warnings: string[] = []

  if (typeof expr === 'number') {
    return { dimensions: { dimensionless: true }, warnings }
  }

  if (typeof expr === 'string') {
    // Variable reference
    const dims = unitBindings.get(expr)
    if (!dims) {
      warnings.push(`Unknown variable: ${expr}`)
      return { dimensions: { dimensionless: true }, warnings }
    }
    return { dimensions: dims, warnings }
  }

  // ExpressionNode
  const node = expr as ExpressionNode
  const op = node.op
  const args = node.args

  // Recursively check arguments
  const argResults = args.map(arg => checkDimensions(arg, unitBindings))
  warnings.push(...argResults.flatMap(r => r.warnings))

  const argDims = argResults.map(r => r.dimensions)

  switch (op) {
    case '+':
    case '-':
      // All operands must have same dimensions
      const firstDim = argDims[0]
      for (let i = 1; i < argDims.length; i++) {
        if (!dimensionsEqual(firstDim, argDims[i])) {
          warnings.push(`Addition/subtraction requires same dimensions, got ${formatDimensions(firstDim)} and ${formatDimensions(argDims[i])}`)
        }
      }
      return { dimensions: firstDim, warnings }

    case '*':
      // Dimensions multiply (add exponents)
      return { dimensions: multiplyDimensions(argDims), warnings }

    case '/':
      // Dimensions divide (subtract exponents)
      if (argDims.length !== 2) {
        warnings.push(`Division requires exactly 2 arguments, got ${argDims.length}`)
        return { dimensions: { dimensionless: true }, warnings }
      }
      return { dimensions: divideDimensions(argDims[0], argDims[1]), warnings }

    case '^':
      // Power: base dimensions multiplied by exponent (exponent must be dimensionless)
      if (argDims.length !== 2) {
        warnings.push(`Exponentiation requires exactly 2 arguments, got ${argDims.length}`)
        return { dimensions: { dimensionless: true }, warnings }
      }

      if (!isDimensionless(argDims[1])) {
        warnings.push(`Exponent must be dimensionless, got ${formatDimensions(argDims[1])}`)
      }

      // For simplicity, assume integer exponents for now
      // In a full implementation, we'd need to extract the numeric value
      return { dimensions: argDims[0], warnings }

    case 'D':
      // Derivative: dimension of variable divided by dimension of time
      if (args.length !== 1) {
        warnings.push(`Derivative D() requires exactly 1 argument, got ${args.length}`)
        return { dimensions: { dimensionless: true }, warnings }
      }

      // Time dimension (from wrt field, default to 't')
      const timeVar = node.wrt || 't'
      const timeDims = unitBindings.get(timeVar) || { s: 1 }  // assume seconds if not found

      return { dimensions: divideDimensions(argDims[0], timeDims), warnings }

    case 'grad':
    case 'div':
    case 'laplacian':
      // Spatial operators - dimension divided by length
      const lengthDims = { m: 1 }  // assume meters
      return { dimensions: divideDimensions(argDims[0], lengthDims), warnings }

    // Functions that require dimensionless arguments and return dimensionless
    case 'exp':
    case 'log':
    case 'log10':
    case 'sin':
    case 'cos':
    case 'tan':
    case 'asin':
    case 'acos':
    case 'atan':
      for (let i = 0; i < argDims.length; i++) {
        if (!isDimensionless(argDims[i])) {
          warnings.push(`${op}() requires dimensionless argument, got ${formatDimensions(argDims[i])}`)
        }
      }
      return { dimensions: { dimensionless: true }, warnings }

    case 'atan2':
      // Both arguments must have same dimensions, result is dimensionless
      if (argDims.length !== 2) {
        warnings.push(`atan2() requires exactly 2 arguments, got ${argDims.length}`)
        return { dimensions: { dimensionless: true }, warnings }
      }
      if (!dimensionsEqual(argDims[0], argDims[1])) {
        warnings.push(`atan2() requires arguments with same dimensions, got ${formatDimensions(argDims[0])} and ${formatDimensions(argDims[1])}`)
      }
      return { dimensions: { dimensionless: true }, warnings }

    case 'sqrt':
    case 'abs':
    case 'sign':
    case 'floor':
    case 'ceil':
      // These preserve dimensions of their argument
      return { dimensions: argDims[0] || { dimensionless: true }, warnings }

    case 'min':
    case 'max':
      // All arguments must have same dimensions, result has those dimensions
      if (argDims.length < 2) {
        warnings.push(`${op}() requires at least 2 arguments, got ${argDims.length}`)
        return { dimensions: { dimensionless: true }, warnings }
      }

      const refDim = argDims[0]
      for (let i = 1; i < argDims.length; i++) {
        if (!dimensionsEqual(refDim, argDims[i])) {
          warnings.push(`${op}() requires all arguments to have same dimensions, got ${formatDimensions(refDim)} and ${formatDimensions(argDims[i])}`)
        }
      }
      return { dimensions: refDim, warnings }

    case 'ifelse':
      // Condition must be dimensionless, then/else branches must have same dimensions
      if (argDims.length !== 3) {
        warnings.push(`ifelse() requires exactly 3 arguments, got ${argDims.length}`)
        return { dimensions: { dimensionless: true }, warnings }
      }

      if (!isDimensionless(argDims[0])) {
        warnings.push(`ifelse() condition must be dimensionless, got ${formatDimensions(argDims[0])}`)
      }

      if (!dimensionsEqual(argDims[1], argDims[2])) {
        warnings.push(`ifelse() branches must have same dimensions, got ${formatDimensions(argDims[1])} and ${formatDimensions(argDims[2])}`)
      }

      return { dimensions: argDims[1], warnings }

    case '>':
    case '<':
    case '>=':
    case '<=':
    case '==':
    case '!=':
      // Comparison: both operands must have same dimensions, result is dimensionless
      if (argDims.length !== 2) {
        warnings.push(`${op} requires exactly 2 arguments, got ${argDims.length}`)
        return { dimensions: { dimensionless: true }, warnings }
      }
      if (!dimensionsEqual(argDims[0], argDims[1])) {
        warnings.push(`${op} requires arguments with same dimensions, got ${formatDimensions(argDims[0])} and ${formatDimensions(argDims[1])}`)
      }
      return { dimensions: { dimensionless: true }, warnings }

    case 'and':
    case 'or':
    case 'not':
      // Logical operators: all arguments must be dimensionless, result is dimensionless
      for (let i = 0; i < argDims.length; i++) {
        if (!isDimensionless(argDims[i])) {
          warnings.push(`${op} requires dimensionless arguments, got ${formatDimensions(argDims[i])}`)
        }
      }
      return { dimensions: { dimensionless: true }, warnings }

    case 'Pre':
      // Pre operator preserves dimensions of its argument
      return { dimensions: argDims[0] || { dimensionless: true }, warnings }

    default:
      warnings.push(`Unknown operator: ${op}`)
      return { dimensions: { dimensionless: true }, warnings }
  }
}

/**
 * Validate dimensional consistency of all equations in an ESM file
 * @param file ESM file to validate
 * @returns Array of unit warnings
 */
export function validateUnits(file: EsmFile): UnitWarning[] {
  const warnings: UnitWarning[] = []

  // Build unit bindings from models and reaction systems
  const unitBindings = new Map<string, DimensionalRep>()

  // Process models
  if (file.models) {
    for (const [modelName, model] of Object.entries(file.models)) {
      if (model.variables) {
        for (const [varName, variable] of Object.entries(model.variables)) {
          const fullVarName = `${modelName}.${varName}`
          if (variable.units) {
            unitBindings.set(fullVarName, parseUnit(variable.units))
          }
          // Also add unqualified name if it doesn't conflict
          if (!unitBindings.has(varName)) {
            if (variable.units) {
              unitBindings.set(varName, parseUnit(variable.units))
            }
          }
        }
      }
    }
  }

  // Process reaction systems
  if (file.reaction_systems) {
    for (const [systemName, system] of Object.entries(file.reaction_systems)) {
      // Species
      if (system.species) {
        for (const [speciesName, species] of Object.entries(system.species)) {
          const fullSpeciesName = `${systemName}.${speciesName}`
          if (species.units) {
            unitBindings.set(fullSpeciesName, parseUnit(species.units))
          }
          if (!unitBindings.has(speciesName) && species.units) {
            unitBindings.set(speciesName, parseUnit(species.units))
          }
        }
      }

      // Parameters
      if (system.parameters) {
        for (const [paramName, param] of Object.entries(system.parameters)) {
          const fullParamName = `${systemName}.${paramName}`
          if (param.units) {
            unitBindings.set(fullParamName, parseUnit(param.units))
          }
          if (!unitBindings.has(paramName) && param.units) {
            unitBindings.set(paramName, parseUnit(param.units))
          }
        }
      }
    }
  }

  // Validate model equations
  if (file.models) {
    for (const [modelName, model] of Object.entries(file.models)) {
      if (model.equations) {
        for (const equation of model.equations) {
          try {
            const lhsResult = checkDimensions(equation.lhs, unitBindings)
            const rhsResult = checkDimensions(equation.rhs, unitBindings)

            if (!dimensionsEqual(lhsResult.dimensions, rhsResult.dimensions)) {
              warnings.push({
                message: `Dimensional mismatch in equation: LHS has ${formatDimensions(lhsResult.dimensions)}, RHS has ${formatDimensions(rhsResult.dimensions)}`,
                location: `models.${modelName}`,
                equation: `${JSON.stringify(equation.lhs)} = ${JSON.stringify(equation.rhs)}`
              })
            }

            // Add any warnings from dimensional analysis
            for (const warning of [...lhsResult.warnings, ...rhsResult.warnings]) {
              warnings.push({
                message: warning,
                location: `models.${modelName}`
              })
            }
          } catch (error) {
            warnings.push({
              message: `Error checking equation dimensions: ${error instanceof Error ? error.message : String(error)}`,
              location: `models.${modelName}`
            })
          }
        }
      }

      // Validate observed variable expressions
      if (model.variables) {
        for (const [varName, variable] of Object.entries(model.variables)) {
          if (variable.type === 'observed' && variable.expression) {
            try {
              const exprResult = checkDimensions(variable.expression, unitBindings)
              const varDims = variable.units ? parseUnit(variable.units) : { dimensionless: true }

              if (!dimensionsEqual(exprResult.dimensions, varDims)) {
                warnings.push({
                  message: `Dimensional mismatch in observed variable ${varName}: declared as ${formatDimensions(varDims)}, expression evaluates to ${formatDimensions(exprResult.dimensions)}`,
                  location: `models.${modelName}.variables.${varName}`
                })
              }

              for (const warning of exprResult.warnings) {
                warnings.push({
                  message: warning,
                  location: `models.${modelName}.variables.${varName}`
                })
              }
            } catch (error) {
              warnings.push({
                message: `Error checking observed variable dimensions: ${error instanceof Error ? error.message : String(error)}`,
                location: `models.${modelName}.variables.${varName}`
              })
            }
          }
        }
      }
    }
  }

  return warnings
}

/**
 * Helper functions for dimensional arithmetic
 */

function dimensionsEqual(a: DimensionalRep, b: DimensionalRep): boolean {
  // Handle dimensionless special case
  const aDimensionless = isDimensionless(a)
  const bDimensionless = isDimensionless(b)

  if (aDimensionless && bDimensionless) return true
  if (aDimensionless || bDimensionless) return false

  // Compare all possible dimension keys
  const allKeys = new Set([...Object.keys(a), ...Object.keys(b)])

  for (const key of allKeys) {
    if (key === 'dimensionless') continue
    const aVal = (a as any)[key] || 0
    const bVal = (b as any)[key] || 0
    if (aVal !== bVal) return false
  }

  return true
}

function isDimensionless(dims: DimensionalRep): boolean {
  if (dims.dimensionless) return true

  // Check if all dimension powers are zero
  for (const [key, value] of Object.entries(dims)) {
    if (key !== 'dimensionless' && value !== 0) {
      return false
    }
  }

  return true
}

function multiplyDimensions(dimensions: DimensionalRep[]): DimensionalRep {
  const result: DimensionalRep = {}

  for (const dim of dimensions) {
    if (dim.dimensionless) continue

    for (const [key, value] of Object.entries(dim)) {
      if (key === 'dimensionless') continue
      result[key as keyof DimensionalRep] = ((result as any)[key] || 0) + (value || 0)
    }
  }

  // Check if result is dimensionless
  const nonZero = Object.entries(result).filter(([key, value]) => key !== 'dimensionless' && value !== 0)
  if (nonZero.length === 0) {
    return { dimensionless: true }
  }

  return result
}

function divideDimensions(numerator: DimensionalRep, denominator: DimensionalRep): DimensionalRep {
  const result: DimensionalRep = {}

  // Add numerator dimensions
  if (!numerator.dimensionless) {
    for (const [key, value] of Object.entries(numerator)) {
      if (key === 'dimensionless') continue
      result[key as keyof DimensionalRep] = value || 0
    }
  }

  // Subtract denominator dimensions
  if (!denominator.dimensionless) {
    for (const [key, value] of Object.entries(denominator)) {
      if (key === 'dimensionless') continue
      result[key as keyof DimensionalRep] = ((result as any)[key] || 0) - (value || 0)
    }
  }

  // Check if result is dimensionless
  const nonZero = Object.entries(result).filter(([key, value]) => key !== 'dimensionless' && value !== 0)
  if (nonZero.length === 0) {
    return { dimensionless: true }
  }

  return result
}

function formatDimensions(dims: DimensionalRep): string {
  if (dims.dimensionless) return 'dimensionless'

  const parts: string[] = []

  for (const [key, value] of Object.entries(dims)) {
    if (key === 'dimensionless' || value === 0) continue

    if (value === 1) {
      parts.push(key)
    } else if (value === -1) {
      parts.push(`/${key}`)
    } else if (value > 0) {
      parts.push(`${key}^${value}`)
    } else {
      parts.push(`/${key}^${-value}`)
    }
  }

  return parts.length > 0 ? parts.join('·') : 'dimensionless'
}