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

import type { Expr, Equation, Model, EsmFile, ReactionSystem, ExprNode } from './types.js'

// Element lookup table for chemical subscript detection (118 elements)
const ELEMENTS = new Set([
  // Period 1
  'H', 'He',
  // Period 2
  'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne',
  // Period 3
  'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar',
  // Period 4
  'K', 'Ca', 'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr',
  // Period 5
  'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn', 'Sb', 'Te', 'I', 'Xe',
  // Period 6
  'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu',
  'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg', 'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn',
  // Period 7
  'Fr', 'Ra', 'Ac', 'Th', 'Pa', 'U', 'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf', 'Es', 'Fm', 'Md', 'No', 'Lr',
  'Rf', 'Db', 'Sg', 'Bh', 'Hs', 'Mt', 'Ds', 'Rg', 'Cn', 'Nh', 'Fl', 'Mc', 'Lv', 'Ts', 'Og'
])

// Unicode subscripts for digits 0-9
const SUBSCRIPT_DIGITS = '₀₁₂₃₄₅₆₇₈₉'
function toSubscript(n: number): string {
  return n.toString().split('').map(d => SUBSCRIPT_DIGITS[parseInt(d)]).join('')
}

// Unicode superscripts for digits 0-9 and signs
const SUPERSCRIPT_MAP: Record<string, string> = {
  '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
  '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
  '+': '⁺', '-': '⁻'
}
function toSuperscript(text: string): string {
  return text.split('').map(c => SUPERSCRIPT_MAP[c] || c).join('')
}

// Greek letter mapping for LaTeX
const GREEK_LETTERS: Record<string, string> = {
  'alpha': '\\alpha', 'beta': '\\beta', 'gamma': '\\gamma', 'delta': '\\delta',
  'epsilon': '\\epsilon', 'zeta': '\\zeta', 'eta': '\\eta', 'theta': '\\theta',
  'iota': '\\iota', 'kappa': '\\kappa', 'lambda': '\\lambda', 'mu': '\\mu',
  'nu': '\\nu', 'xi': '\\xi', 'omicron': '\\omicron', 'pi': '\\pi',
  'rho': '\\rho', 'sigma': '\\sigma', 'tau': '\\tau', 'upsilon': '\\upsilon',
  'phi': '\\phi', 'chi': '\\chi', 'psi': '\\psi', 'omega': '\\omega',
  'Gamma': '\\Gamma', 'Delta': '\\Delta', 'Theta': '\\Theta', 'Lambda': '\\Lambda',
  'Xi': '\\Xi', 'Pi': '\\Pi', 'Sigma': '\\Sigma', 'Upsilon': '\\Upsilon',
  'Phi': '\\Phi', 'Psi': '\\Psi', 'Omega': '\\Omega',
  // Direct Unicode to LaTeX mappings
  'α': '\\alpha', 'β': '\\beta', 'γ': '\\gamma', 'δ': '\\delta',
  'ε': '\\epsilon', 'ζ': '\\zeta', 'η': '\\eta', 'θ': '\\theta',
  'ι': '\\iota', 'κ': '\\kappa', 'λ': '\\lambda', 'μ': '\\mu',
  'ν': '\\nu', 'ξ': '\\xi', 'ο': '\\omicron', 'π': '\\pi',
  'ρ': '\\rho', 'σ': '\\sigma', 'τ': '\\tau', 'υ': '\\upsilon',
  'φ': '\\phi', 'χ': '\\chi', 'ψ': '\\psi', 'ω': '\\omega'
}

function convertGreekLetters(text: string, format: 'unicode' | 'latex' | 'ascii'): string {
  if (format === 'latex') {
    // Replace Greek letters with LaTeX commands
    return text.replace(/[α-ωΑ-Ω]|(?:alpha|beta|gamma|delta|epsilon|zeta|eta|theta|iota|kappa|lambda|mu|nu|xi|omicron|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega)/g,
      (match) => GREEK_LETTERS[match] || match)
  } else if (format === 'unicode') {
    // Convert named Greek letters to Unicode symbols
    const unicodeGreek: Record<string, string> = {
      'phi': 'φ', 'theta': 'θ', 'gamma': 'γ', 'alpha': 'α', 'beta': 'β',
      'delta': 'δ', 'epsilon': 'ε', 'zeta': 'ζ', 'eta': 'η', 'iota': 'ι',
      'kappa': 'κ', 'lambda': 'λ', 'mu': 'μ', 'nu': 'ν', 'xi': 'ξ',
      'omicron': 'ο', 'pi': 'π', 'rho': 'ρ', 'sigma': 'σ', 'tau': 'τ',
      'upsilon': 'υ', 'chi': 'χ', 'psi': 'ψ', 'omega': 'ω'
    }
    return text.replace(/(?:alpha|beta|gamma|delta|epsilon|zeta|eta|theta|iota|kappa|lambda|mu|nu|xi|omicron|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega)/g,
      (match) => unicodeGreek[match] || match)
  } else if (format === 'ascii') {
    // Convert Unicode Greek letters to ASCII names
    const asciiGreek: Record<string, string> = {
      'φ': 'phi', 'θ': 'theta', 'γ': 'gamma', 'α': 'alpha', 'β': 'beta',
      'δ': 'delta', 'ε': 'epsilon', 'ζ': 'zeta', 'η': 'eta', 'ι': 'iota',
      'κ': 'kappa', 'λ': 'lambda', 'μ': 'mu', 'ν': 'nu', 'ξ': 'xi',
      'ο': 'omicron', 'π': 'pi', 'ρ': 'rho', 'σ': 'sigma', 'τ': 'tau',
      'υ': 'upsilon', 'χ': 'chi', 'ψ': 'psi', 'ω': 'omega'
    }
    return text.replace(/[α-ωΑ-Ω]/g, (match) => asciiGreek[match] || match)
  }

  return text
}

/**
 * Apply element-aware chemical subscript formatting to a variable name.
 * Uses greedy 2-char-before-1-char matching for element detection.
 */
function formatChemicalSubscripts(variable: string, format: 'unicode' | 'latex'): string {
  // Check if variable looks like a chemical formula (starts with element and has digits)
  const hasElements = hasElementPattern(variable)

  if (format === 'latex') {
    // First check if it's a mixed variable (non-element prefix + chemical suffix)
    const chemicalInfo = getChemicalSuffix(variable)
    if (chemicalInfo) {
      // Split into prefix and chemical part
      const { prefix, suffix } = chemicalInfo
      const chemicalPart = formatChemicalSubscripts(suffix, 'latex')
      // Remove outer \mathrm{} wrapper but keep the content formatted
      const innerContent = chemicalPart.replace(/^\\mathrm\{|\}$/g, '')
      return `${prefix}_{\\mathrm{${innerContent}}}`
    }

    if (hasElements) {
      // Pure chemical formula: wrap in \mathrm{} and convert digits to subscripts
      let result = variable
      result = result.replace(/(\d+)/g, (match, digits) => {
        // Single digits don't need braces in LaTeX subscripts
        return digits.length === 1 ? `_${digits}` : `_{${digits}}`
      })
      return `\\mathrm{${result}}`
    } else {
      // Regular variable: check if it should be in \mathrm{} (like var2)
      if (/\d/.test(variable)) {
        return `\\mathrm{${variable}}`
      }
      return variable
    }
  }

  if (!hasElements) {
    // Check if it's a mixed variable (non-element prefix + chemical suffix)
    const chemicalInfo = getChemicalSuffix(variable)
    if (chemicalInfo) {
      // Split into prefix and chemical part
      const { prefix, suffix } = chemicalInfo
      const chemicalPart = formatChemicalSubscripts(suffix, 'unicode')
      // For variables without underscores (like jNO2), don't add underscores
      if (!variable.includes('_')) {
        return `${prefix}${chemicalPart}`
      }
      // For variables with underscores (like k_NO_O3), preserve them
      return `${prefix}_${chemicalPart}`
    }
    // No element pattern found, return as-is
    return variable
  }

  // For unicode: element-aware subscript detection
  let result = ''
  let i = 0

  while (i < variable.length) {
    let matched = false

    // Try 2-character element first
    if (i + 1 < variable.length) {
      const twoChar = variable.slice(i, i + 2)
      if (ELEMENTS.has(twoChar)) {
        result += twoChar
        i += 2
        // Convert following digits to subscripts
        while (i < variable.length && /\d/.test(variable[i])) {
          result += SUBSCRIPT_DIGITS[parseInt(variable[i])]
          i++
        }
        matched = true
      }
    }

    // Try 1-character element if 2-char didn't match
    if (!matched && i < variable.length) {
      const oneChar = variable[i]
      if (ELEMENTS.has(oneChar)) {
        result += oneChar
        i++
        // Convert following digits to subscripts
        while (i < variable.length && /\d/.test(variable[i])) {
          result += SUBSCRIPT_DIGITS[parseInt(variable[i])]
          i++
        }
        matched = true
      }
    }

    // If not an element, copy character as-is
    if (!matched) {
      result += variable[i]
      i++
    }
  }

  return result
}

/**
 * Extract chemical formula suffix from a variable name
 */
function getChemicalSuffix(variable: string): { prefix: string; suffix: string } | null {
  // Handle patterns like k_NO_O3 (with underscore)
  if (variable.includes('_')) {
    const parts = variable.split('_')
    if (parts.length === 2) {
      const [prefix, suffix] = parts
      if (hasElementPattern(suffix) && !hasElementPattern(prefix)) {
        return { prefix, suffix }
      }
    }
    // For patterns like k_NO_O3, try treating NO_O3 as the chemical part
    if (parts.length === 3) {
      const prefix = parts[0]
      const suffix = parts.slice(1).join('_')  // Keep underscore within chemical formula
      if (hasElementPattern(suffix) && !hasElementPattern(prefix)) {
        return { prefix, suffix }
      }
    }
  }

  // Handle patterns like jNO2 (without underscore)
  // Try each position to split into non-element prefix and element suffix
  for (let i = 1; i < variable.length; i++) {
    const prefix = variable.substring(0, i)
    const suffix = variable.substring(i)

    if (hasElementPattern(suffix) && !hasElementPattern(prefix)) {
      return { prefix, suffix }
    }
  }

  return null
}

/**
 * Check if a variable has element patterns (for chemical formula detection)
 * Must be PURELY a chemical formula (no non-element characters)
 */
function hasElementPattern(variable: string): boolean {
  // Remove underscores for pure chemical formula check
  const cleanVariable = variable.replace(/_/g, '')

  let i = 0
  let hasElement = false

  while (i < cleanVariable.length) {
    // Skip non-alphabetic characters at the start
    while (i < cleanVariable.length && !/[A-Za-z]/.test(cleanVariable[i])) {
      i++
    }

    if (i >= cleanVariable.length) break

    let foundElement = false

    // Try 2-character element first
    if (i + 1 < cleanVariable.length) {
      const twoChar = cleanVariable.slice(i, i + 2)
      if (ELEMENTS.has(twoChar)) {
        hasElement = true
        foundElement = true
        i += 2
        // Skip digits
        while (i < cleanVariable.length && /\d/.test(cleanVariable[i])) {
          i++
        }
        continue
      }
    }

    // Try 1-character element
    if (!foundElement) {
      const oneChar = cleanVariable[i]
      if (ELEMENTS.has(oneChar)) {
        hasElement = true
        foundElement = true
        i++
        // Skip digits
        while (i < cleanVariable.length && /\d/.test(cleanVariable[i])) {
          i++
        }
        continue
      }
    }

    // If we encounter a non-element character, this is not a pure chemical formula
    if (!foundElement) {
      return false
    }
  }

  return hasElement
}

/**
 * Format a number in scientific notation with appropriate formatting
 */
function formatNumber(num: number, format: 'unicode' | 'latex' | 'ascii'): string {
  if (Number.isInteger(num) && Math.abs(num) < 1e6) {
    return num.toString()
  }

  const str = num.toExponential()
  const [mantissa, exponent] = str.split('e')
  const exp = parseInt(exponent)

  if (format === 'unicode') {
    return `${mantissa}×10${toSuperscript(exp.toString())}`
  } else if (format === 'latex') {
    return `${mantissa} \\times 10^{${exp}}`
  } else {
    return str // Plain scientific notation for ASCII
  }
}

/**
 * Get operator precedence for proper parenthesization
 */
function getOperatorPrecedence(op: string): number {
  switch (op) {
    case 'or': return 1
    case 'and': return 2
    case '==': case '!=': case '<': case '>': case '<=': case '>=': return 3
    case '+': case '-': return 4
    case '*': case '/': return 5
    case 'not': return 6  // Unary
    case '^': return 7
    default: return 8  // Functions get highest precedence
  }
}

/**
 * Check if parentheses are needed around a subexpression
 */
function needsParentheses(parent: ExprNode, child: Expr, isRightOperand = false): boolean {
  if (typeof child === 'number' || typeof child === 'string') {
    return false
  }

  const parentPrec = getOperatorPrecedence(parent.op)
  const childPrec = getOperatorPrecedence(child.op)

  if (childPrec < parentPrec) return true
  if (childPrec > parentPrec) return false

  // Same precedence: need parens if child is right operand and operator is not associative
  if (isRightOperand && (parent.op === '-' || parent.op === '/' || parent.op === '^')) {
    return true
  }

  // Special cases for function arguments - avoid parentheses for simple expressions
  if (['sin', 'cos', 'tan', 'exp', 'log', 'sqrt', 'abs', 'asin', 'acos', 'atan', 'floor', 'ceil', 'sign', 'log10'].includes(parent.op)) {
    // For function arguments, be much more permissive - only parenthesize logical operations
    return childPrec <= 1
  }

  // Special case for ifelse function - don't add unnecessary parens to arguments
  if (parent.op === 'ifelse') {
    // For function arguments, be much more permissive - only parenthesize logical operations
    return childPrec <= 1
  }

  // For unary minus, be less aggressive
  if (parent.op === '-' && parent.args.length === 1) {
    return childPrec <= 1
  }

  return false
}

/**
 * Format an expression as Unicode mathematical notation
 */
export function toUnicode(expr: Expr | Equation | Model | ReactionSystem | EsmFile): string {
  if (typeof expr === 'number') {
    return formatNumber(expr, 'unicode')
  }

  if (typeof expr === 'string') {
    return convertGreekLetters(formatChemicalSubscripts(expr, 'unicode'), 'unicode')
  }

  if ('op' in expr && 'args' in expr) {
    return formatExpressionNode(expr as ExprNode, 'unicode')
  }

  if ('lhs' in expr && 'rhs' in expr) {
    // Equation
    const equation = expr as Equation
    return `${toUnicode(equation.lhs)} = ${toUnicode(equation.rhs)}`
  }

  if ('models' in expr || 'metadata' in expr) {
    // EsmFile - model summary display (spec Section 6.3)
    return formatEsmFileSummary(expr as EsmFile, 'unicode')
  }

  if ('variables' in expr && 'equations' in expr) {
    // Model summary
    return formatModelSummary(expr as Model, 'unicode')
  }

  if ('species' in expr && 'reactions' in expr) {
    // ReactionSystem summary
    return formatReactionSystemSummary(expr as ReactionSystem, 'unicode')
  }

  throw new Error(`Unsupported expression type: ${typeof expr}`)
}

/**
 * Format an expression as LaTeX mathematical notation
 */
export function toLatex(expr: Expr | Equation | Model | ReactionSystem | EsmFile): string {
  if (typeof expr === 'number') {
    return formatNumber(expr, 'latex')
  }

  if (typeof expr === 'string') {
    const chemicalFormatted = formatChemicalSubscripts(expr, 'latex')
    return convertGreekLetters(chemicalFormatted, 'latex')
  }

  if ('op' in expr && 'args' in expr) {
    return formatExpressionNode(expr as ExprNode, 'latex')
  }

  if ('lhs' in expr && 'rhs' in expr) {
    // Equation
    const equation = expr as Equation
    return `${toLatex(equation.lhs)} = ${toLatex(equation.rhs)}`
  }

  if ('models' in expr || 'metadata' in expr) {
    // EsmFile - not typically formatted as LaTeX, return plain text
    return formatEsmFileSummary(expr as EsmFile, 'ascii')
  }

  if ('variables' in expr && 'equations' in expr) {
    // Model - not typically formatted as LaTeX, return plain text
    return formatModelSummary(expr as Model, 'ascii')
  }

  if ('species' in expr && 'reactions' in expr) {
    // ReactionSystem - not typically formatted as LaTeX, return plain text
    return formatReactionSystemSummary(expr as ReactionSystem, 'ascii')
  }

  throw new Error(`Unsupported expression type: ${typeof expr}`)
}

/**
 * Format an expression as plain ASCII text
 */
export function toAscii(expr: Expr | Equation | Model | ReactionSystem | EsmFile): string {
  if (typeof expr === 'number') {
    return formatNumber(expr, 'ascii')
  }

  if (typeof expr === 'string') {
    return convertGreekLetters(expr, 'ascii')
  }

  if ('op' in expr && 'args' in expr) {
    return formatExpressionNode(expr as ExprNode, 'ascii')
  }

  if ('lhs' in expr && 'rhs' in expr) {
    // Equation
    const equation = expr as Equation
    return `${toAscii(equation.lhs)} = ${toAscii(equation.rhs)}`
  }

  if ('models' in expr || 'metadata' in expr) {
    // EsmFile
    return formatEsmFileSummary(expr as EsmFile, 'ascii')
  }

  if ('variables' in expr && 'equations' in expr) {
    // Model
    return formatModelSummary(expr as Model, 'ascii')
  }

  if ('species' in expr && 'reactions' in expr) {
    // ReactionSystem
    return formatReactionSystemSummary(expr as ReactionSystem, 'ascii')
  }

  throw new Error(`Unsupported expression type: ${typeof expr}`)
}

/**
 * Format an ExpressionNode (operator with arguments)
 */
function formatExpressionNode(node: ExprNode, format: 'unicode' | 'latex' | 'ascii'): string {
  const { op, args, wrt } = node

  // Helper to format arguments with proper parenthesization
  const formatArg = (arg: Expr, isRightOperand = false): string => {
    let result: string
    if (format === 'unicode') result = toUnicode(arg)
    else if (format === 'latex') result = toLatex(arg)
    else result = toAscii(arg)

    if (needsParentheses(node, arg, isRightOperand)) {
      if (format === 'latex') return `\\left(${result}\\right)`
      else return `(${result})`
    }
    return result
  }

  // Binary operators
  if (args.length === 2) {
    const [left, right] = args

    switch (op) {
      case '+':
        return `${formatArg(left)} + ${formatArg(right, true)}`

      case '-':
        if (format === 'unicode') {
          return `${formatArg(left)} − ${formatArg(right, true)}`
        }
        return `${formatArg(left)} - ${formatArg(right, true)}`

      case '*':
        if (format === 'unicode') {
          return `${formatArg(left)}·${formatArg(right, true)}`
        } else if (format === 'latex') {
          return `${formatArg(left)} \\cdot ${formatArg(right, true)}`
        }
        return `${formatArg(left)} * ${formatArg(right, true)}`

      case '/':
        if (format === 'latex') {
          return `\\frac{${toLatex(left)}}{${toLatex(right)}}`
        } else if (format === 'unicode') {
          return `${formatArg(left)}/${formatArg(right, true)}`
        }
        return `${formatArg(left)} / ${formatArg(right, true)}`

      case '^':
        if (format === 'latex') {
          return `${formatArg(left)}^{${toLatex(right)}}`
        }
        // For unicode, try to use superscript digits
        if (format === 'unicode' && typeof right === 'number' && Number.isInteger(right)) {
          return `${formatArg(left)}${toSuperscript(right.toString())}`
        }
        return `${formatArg(left)}^${formatArg(right, true)}`


      case '>': case '<':
        return `${formatArg(left)} ${op} ${formatArg(right, true)}`

      case '>=':
        if (format === 'unicode') {
          return `${formatArg(left)} ≥ ${formatArg(right, true)}`
        } else if (format === 'latex') {
          return `${formatArg(left)} \\geq ${formatArg(right, true)}`
        }
        return `${formatArg(left)} ${op} ${formatArg(right, true)}`

      case '<=':
        if (format === 'unicode') {
          return `${formatArg(left)} ≤ ${formatArg(right, true)}`
        } else if (format === 'latex') {
          return `${formatArg(left)} \\leq ${formatArg(right, true)}`
        }
        return `${formatArg(left)} ${op} ${formatArg(right, true)}`

      case '==':
        if (format === 'unicode') {
          return `${formatArg(left)} = ${formatArg(right, true)}`
        } else if (format === 'latex') {
          return `${formatArg(left)} = ${formatArg(right, true)}`
        }
        return `${formatArg(left)} ${op} ${formatArg(right, true)}`

      case '!=':
        if (format === 'unicode') {
          return `${formatArg(left)} ≠ ${formatArg(right, true)}`
        } else if (format === 'latex') {
          return `${formatArg(left)} \\neq ${formatArg(right, true)}`
        }
        return `${formatArg(left)} ${op} ${formatArg(right, true)}`

      case 'and':
        if (format === 'unicode') {
          return `${formatArg(left)} ∧ ${formatArg(right, true)}`
        } else if (format === 'latex') {
          return `${formatArg(left)} \\land ${formatArg(right, true)}`
        }
        return `${formatArg(left)} and ${formatArg(right, true)}`

      case 'or':
        if (format === 'unicode') {
          return `${formatArg(left)} ∨ ${formatArg(right, true)}`
        } else if (format === 'latex') {
          return `${formatArg(left)} \\lor ${formatArg(right, true)}`
        }
        return `${formatArg(left)} or ${formatArg(right, true)}`

      case 'atan2':
        if (format === 'latex') {
          return `\\mathrm{atan2}(${toLatex(left)}, ${toLatex(right)})`
        }
        return `atan2(${formatArg(left)}, ${formatArg(right)})`

      case 'min': case 'max':
        if (format === 'latex') {
          return `\\${op}(${toLatex(left)}, ${toLatex(right)})`
        }
        return `${op}(${formatArg(left)}, ${formatArg(right)})`
    }
  }

  // Unary operators
  if (args.length === 1) {
    const [arg] = args

    switch (op) {
      case '-':
        // Unary minus
        if (format === 'unicode') {
          return `−${formatArg(arg)}`
        }
        return `-${formatArg(arg)}`

      case 'not':
        if (format === 'unicode') {
          return `¬${formatArg(arg)}`
        } else if (format === 'latex') {
          return `\\neg ${formatArg(arg)}`
        }
        return `not ${formatArg(arg)}`

      case 'exp': case 'sin': case 'cos': case 'tan':
        if (format === 'latex') {
          return `\\${op}(${toLatex(arg)})`
        }
        return `${op}(${formatArg(arg)})`

      case 'log':
        if (format === 'unicode') {
          return `ln(${formatArg(arg)})`
        } else if (format === 'latex') {
          return `\\ln(${toLatex(arg)})`
        }
        return `${op}(${formatArg(arg)})`

      case 'log10':
        if (format === 'unicode') {
          return `log₁₀(${formatArg(arg)})`
        } else if (format === 'latex') {
          return `\\log_{10}(${toLatex(arg)})`
        }
        return `${op}(${formatArg(arg)})`

      case 'sqrt':
        if (format === 'unicode') {
          return `√${formatArg(arg)}`
        } else if (format === 'latex') {
          return `\\sqrt{${toLatex(arg)}}`
        }
        return `${op}(${formatArg(arg)})`

      case 'abs':
        if (format === 'unicode') {
          return `|${formatArg(arg)}|`
        } else if (format === 'latex') {
          return `|${toLatex(arg)}|`
        }
        return `${op}(${formatArg(arg)})`

      case 'floor':
        if (format === 'unicode') {
          return `⌊${formatArg(arg)}⌋`
        } else if (format === 'latex') {
          return `\\lfloor ${toLatex(arg)} \\rfloor`
        }
        return `${op}(${formatArg(arg)})`

      case 'ceil':
        if (format === 'unicode') {
          return `⌈${formatArg(arg)}⌉`
        } else if (format === 'latex') {
          return `\\lceil ${toLatex(arg)} \\rceil`
        }
        return `${op}(${formatArg(arg)})`

      case 'sign':
        if (format === 'unicode') {
          return `sgn(${formatArg(arg)})`
        } else if (format === 'latex') {
          return `\\mathrm{sgn}(${toLatex(arg)})`
        }
        return `${op}(${formatArg(arg)})`

      case 'asin': case 'acos': case 'atan':
        const arcName = op.replace('a', 'arc')
        if (format === 'unicode') {
          return `${arcName}(${formatArg(arg)})`
        } else if (format === 'latex') {
          return `\\${arcName}(${toLatex(arg)})`
        }
        return `${op}(${formatArg(arg)})`

      case 'grad':
        const dim = (node as any).dim || 'x'  // dim is not in ExprNode type yet
        if (format === 'unicode') {
          const variable2 = formatArg(arg)
          return `∂${variable2}/∂${dim}`
        } else if (format === 'latex') {
          return `\\frac{\\partial ${toLatex(arg)}}{\\partial ${dim}}`
        }
        return `d(${toAscii(arg)})/d${dim}`

      case 'div':
        if (format === 'unicode') {
          return `∇·${formatArg(arg)}`
        } else if (format === 'latex') {
          return `\\nabla \\cdot \\mathbf{${toLatex(arg)}}`
        }
        return `${op}(${formatArg(arg)})`

      case 'laplacian':
        if (format === 'unicode') {
          return `∇²${formatArg(arg)}`
        } else if (format === 'latex') {
          return `\\nabla^2 ${toLatex(arg)}`
        }
        return `${op}(${formatArg(arg)})`

      case 'Pre':
        if (format === 'latex') {
          return `\\mathrm{Pre}(\\mathrm{${toLatex(arg)}})`
        }
        return `Pre(${formatArg(arg)})`

      case 'D':
        // Derivative operator
        const wrtVar = wrt || 't'
        if (format === 'unicode') {
          const variable = toUnicode(arg)
          return `∂${variable}/∂${wrtVar}`
        } else if (format === 'latex') {
          return `\\frac{\\partial ${toLatex(arg)}}{\\partial ${wrtVar}}`
        }
        return `D(${toAscii(arg)})/D${wrtVar}`
    }
  }

  // Ternary and n-ary operators
  if (args.length >= 3) {
    switch (op) {
      case 'ifelse':
        if (args.length === 3) {
          const [cond, thenExpr, elseExpr] = args
          return `ifelse(${formatArg(cond)}, ${formatArg(thenExpr)}, ${formatArg(elseExpr)})`
        }
        break

      case '+':
        // N-ary addition
        return args.map(arg => formatArg(arg)).join(' + ')

      case '*':
        // N-ary multiplication
        const sep = format === 'unicode' ? '·' : format === 'latex' ? ' \\cdot ' : ' * '
        return args.map(arg => formatArg(arg)).join(sep)

      case 'or':
        // N-ary or
        if (format === 'unicode') {
          return args.map(arg => formatArg(arg)).join(' ∨ ')
        } else if (format === 'latex') {
          return args.map(arg => formatArg(arg)).join(' \\lor ')
        }
        return args.map(arg => formatArg(arg)).join(' or ')

      case 'max':
        // N-ary max
        const maxArgList = args.map(arg => {
          if (format === 'unicode') return toUnicode(arg)
          else if (format === 'latex') return toLatex(arg)
          else return toAscii(arg)
        }).join(', ')

        if (format === 'latex') {
          return `\\max(${maxArgList})`
        }
        return `max(${maxArgList})`
    }
  }

  // Fallback: function call notation
  const argList = args.map(arg => {
    if (format === 'unicode') return toUnicode(arg)
    else if (format === 'latex') return toLatex(arg)
    else return toAscii(arg)
  }).join(', ')

  if (format === 'latex') {
    return `\\text{${op}}\\left(${argList}\\right)`
  }
  return `${op}(${argList})`
}

/**
 * Format model summary (implementation placeholder)
 */
function formatModelSummary(model: Model, format: 'unicode' | 'ascii'): string {
  // This is a placeholder - full implementation would need to format
  // the model according to spec Section 6.3
  const name = (model as any).name || 'unnamed'  // name might not be in Model type yet
  return `Model: ${name} (${model.variables?.length || 0} variables, ${model.equations?.length || 0} equations)`
}

/**
 * Format reaction system summary (implementation placeholder)
 */
function formatReactionSystemSummary(reactionSystem: ReactionSystem, format: 'unicode' | 'ascii'): string {
  const name = (reactionSystem as any).name || 'unnamed'  // name might not be in ReactionSystem type yet
  return `ReactionSystem: ${name} (${reactionSystem.species?.length || 0} species, ${reactionSystem.reactions?.length || 0} reactions)`
}

/**
 * Format ESM file summary (implementation placeholder)
 */
function formatEsmFileSummary(esmFile: EsmFile, format: 'unicode' | 'ascii'): string {
  const models = Object.keys(esmFile.models || {}).length
  const reactionSystems = Object.keys(esmFile.reaction_systems || {}).length
  const dataLoaders = Object.keys(esmFile.data_loaders || {}).length
  const title = (esmFile.metadata as any)?.title || 'Untitled'  // title might not be in Metadata type yet

  return `ESM v${esmFile.esm}: ${title} (${models} models, ${reactionSystems} reaction systems, ${dataLoaders} data loaders)`
}