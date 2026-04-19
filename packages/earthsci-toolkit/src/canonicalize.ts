/**
 * Canonical AST form per discretization RFC §5.4.
 *
 * Implements `canonicalize(expr)` and `canonicalJson(expr)` for the TypeScript
 * binding.
 *
 * **Known limitation (gt-ca2u).** JavaScript numbers are IEEE-754 doubles
 * with no native integer/float distinction. Until gt-ca2u (TS rep refactor)
 * lands, every numeric literal is treated as a float and serialized per
 * §5.4.6 with a trailing `.0` for integer-valued magnitudes. The other
 * bindings (Julia/Rust/Python/Go) will emit `1` for an integer node and
 * `1.0` for a float node, so cross-binding byte-equality holds only for
 * fixtures that contain no integer literals — or that happen to use the
 * same wire token after canonicalization. Once gt-ca2u introduces a
 * tagged-literal representation in TS, this file should be updated to
 * preserve and emit the int/float distinction.
 *
 * See `docs/rfcs/discretization.md` §5.4.1–§5.4.7 for the normative rules.
 */

import type { Expression, ExpressionNode } from './generated.js'

export class CanonicalizeError extends Error {
  /** Stable RFC §5.4.6 / §5.4.7 error code. */
  readonly code: string
  constructor(code: string, message?: string) {
    super(message ?? code)
    this.code = code
    this.name = 'CanonicalizeError'
  }
}

/** `E_CANONICAL_NONFINITE` — NaN or ±Inf (§5.4.6). */
export const E_CANONICAL_NONFINITE = 'E_CANONICAL_NONFINITE'
/** `E_CANONICAL_DIVBY_ZERO` — `/(0, 0)` (§5.4.7). */
export const E_CANONICAL_DIVBY_ZERO = 'E_CANONICAL_DIVBY_ZERO'

type Expr = Expression
type Node = Expression & { op: string; args: Expression[] }

function isNode(e: Expr): e is Node {
  return typeof e === 'object' && e !== null && 'op' in e && 'args' in e
}

function isNumber(e: Expr): e is number {
  return typeof e === 'number'
}

function isString(e: Expr): e is string {
  return typeof e === 'string'
}

/** Canonicalize an expression tree per RFC §5.4. Input is not mutated. */
export function canonicalize(expr: Expr): Expr {
  if (isNumber(expr)) {
    if (!Number.isFinite(expr)) {
      throw new CanonicalizeError(E_CANONICAL_NONFINITE)
    }
    return expr
  }
  if (isString(expr)) {
    return expr
  }
  if (isNode(expr)) {
    return canonOp(expr)
  }
  throw new TypeError(`unknown expression type: ${typeof expr}`)
}

/** Emit canonical on-wire JSON per §5.4.6 (sorted keys, no whitespace). */
export function canonicalJson(expr: Expr): string {
  return emitJson(canonicalize(expr))
}

function canonOp(node: Node): Expr {
  const newArgs: Expr[] = node.args.map((a) => canonicalize(a))
  const work: Node = { ...node, args: newArgs } as Node
  switch (work.op) {
    case '+':
      return canonAdd(work)
    case '*':
      return canonMul(work)
    case '-':
      return canonSub(work)
    case '/':
      return canonDiv(work)
    case 'neg':
      return canonNeg(work)
    default:
      return work
  }
}

function canonAdd(node: Node): Expr {
  const flat = flattenSameOp(node.args, '+')
  // Without int/float distinction, treat zero-elim as straightforward drop.
  const others = flat.filter((a) => !isZeroAny(a))
  if (others.length === 0) return 0
  if (others.length === 1) return others[0]
  sortArgs(others)
  return { ...node, op: '+', args: others }
}

function canonMul(node: Node): Expr {
  const flat = flattenSameOp(node.args, '*')
  for (const a of flat) {
    if (isZeroAny(a)) {
      // Preserve signed zero (only meaningful for -0).
      if (typeof a === 'number' && Object.is(a, -0)) return -0
      return 0
    }
  }
  const others = flat.filter((a) => !isOneAny(a))
  if (others.length === 0) return 1
  if (others.length === 1) return others[0]
  sortArgs(others)
  return { ...node, op: '*', args: others }
}

function canonSub(node: Node): Expr {
  if (node.args.length === 1) return canonNegValue(node.args[0])
  if (node.args.length === 2) {
    const [a, b] = node.args
    if (isZeroAny(a)) return canonNegValue(b)
    if (isZeroAny(b)) return a
  }
  return node
}

function canonDiv(node: Node): Expr {
  if (node.args.length !== 2) return node
  const [a, b] = node.args
  if (isZeroAny(a) && isZeroAny(b)) {
    throw new CanonicalizeError(E_CANONICAL_DIVBY_ZERO)
  }
  if (isOneAny(b)) return a
  if (isZeroAny(a)) return 0
  return node
}

function canonNeg(node: Node): Expr {
  if (node.args.length !== 1) return node
  return canonNegValue(node.args[0])
}

function canonNegValue(arg: Expr): Expr {
  if (isNumber(arg)) return -arg
  if (isNode(arg) && arg.op === 'neg' && arg.args.length === 1) return arg.args[0]
  return { op: 'neg', args: [arg] } as Node
}

function flattenSameOp(args: Expr[], op: string): Expr[] {
  const out: Expr[] = []
  for (const a of args) {
    if (isNode(a) && a.op === op) {
      out.push(...a.args)
    } else {
      out.push(a)
    }
  }
  return out
}

function isZeroAny(e: Expr): boolean {
  return isNumber(e) && e === 0
}

function isOneAny(e: Expr): boolean {
  return isNumber(e) && e === 1
}

function argTier(e: Expr): number {
  if (isNumber(e)) return 0
  if (isString(e)) return 1
  if (isNode(e)) return 2
  return 3
}

function sortArgs(args: Expr[]): void {
  // Memoize canonical JSON for non-leaf nodes (§5.4.9).
  const cache = new Map<number, string>()
  const indices = args.map((_, i) => i)
  const getJson = (i: number, e: Expr): string => {
    let s = cache.get(i)
    if (s === undefined) {
      s = emitJson(e)
      cache.set(i, s)
    }
    return s
  }
  indices.sort((ia, ib) => compareExprs(args[ia], args[ib], ia, ib, getJson))
  const snap = indices.map((i) => args[i])
  for (let i = 0; i < args.length; i++) args[i] = snap[i]
}

function compareExprs(
  a: Expr,
  b: Expr,
  ia: number,
  ib: number,
  getJson: (i: number, e: Expr) => string,
): number {
  const ta = argTier(a)
  const tb = argTier(b)
  if (ta !== tb) return ta - tb
  if (ta === 0) {
    return (a as number) - (b as number)
  }
  if (ta === 1) {
    return (a as string) < (b as string) ? -1 : (a as string) > (b as string) ? 1 : 0
  }
  const aj = getJson(ia, a)
  const bj = getJson(ib, b)
  return aj < bj ? -1 : aj > bj ? 1 : 0
}

function emitJson(e: Expr): string {
  if (isNumber(e)) {
    if (!Number.isFinite(e)) throw new CanonicalizeError(E_CANONICAL_NONFINITE)
    return formatCanonicalFloat(e)
  }
  if (isString(e)) return JSON.stringify(e)
  if (isNode(e)) return emitNodeJson(e)
  if (e === null) return 'null'
  return JSON.stringify(e)
}

function emitNodeJson(n: Node): string {
  const entries: Array<[string, string]> = []
  entries.push(['op', JSON.stringify(n.op)])
  entries.push(['args', `[${n.args.map(emitJson).join(',')}]`])
  if ('wrt' in n && (n as Record<string, unknown>).wrt !== undefined) {
    entries.push(['wrt', JSON.stringify((n as Record<string, unknown>).wrt)])
  }
  if ('dim' in n && (n as Record<string, unknown>).dim !== undefined) {
    entries.push(['dim', JSON.stringify((n as Record<string, unknown>).dim)])
  }
  if ('handler_id' in n && (n as Record<string, unknown>).handler_id !== undefined) {
    entries.push(['handler_id', JSON.stringify((n as Record<string, unknown>).handler_id)])
  }
  entries.sort((x, y) => (x[0] < y[0] ? -1 : x[0] > y[0] ? 1 : 0))
  const body = entries.map(([k, v]) => `${JSON.stringify(k)}:${v}`).join(',')
  return `{${body}}`
}

/**
 * Format a finite `number` per RFC §5.4.6.
 *
 * Note: the trailing `.0` for integer-valued magnitudes applies because TS
 * has no int/float distinction (every numeric literal is a float). Once
 * gt-ca2u introduces typed integer nodes, integer values should serialize
 * without the suffix.
 */
export function formatCanonicalFloat(f: number): string {
  if (!Number.isFinite(f)) {
    throw new CanonicalizeError(E_CANONICAL_NONFINITE)
  }
  if (f === 0) {
    return Object.is(f, -0) ? '-0.0' : '0.0'
  }
  const abs = Math.abs(f)
  const useExp = abs < 1e-6 || abs >= 1e21
  if (useExp) {
    // Number.prototype.toString already gives shortest round-trip and uses
    // exponent form outside [1e-6, 1e21). Strip leading + on the exponent.
    let s = f.toString()
    return normalizeExponent(s)
  }
  let s = f.toString()
  if (s.includes('e') || s.includes('E')) {
    // Defensive: Number.toString shouldn't produce exp form here, but if it
    // does, expand manually.
    s = expandToPlain(f)
  }
  if (!s.includes('.')) s += '.0'
  return s
}

function normalizeExponent(s: string): string {
  const m = /^(-?[0-9]*\.?[0-9]*)[eE]([+-]?[0-9]+)$/.exec(s)
  if (!m) return s
  const mant = m[1]
  let exp = m[2]
  if (exp.startsWith('+')) exp = exp.slice(1)
  let sign = ''
  if (exp.startsWith('-')) {
    sign = '-'
    exp = exp.slice(1)
  }
  exp = exp.replace(/^0+/, '') || '0'
  return `${mant}e${sign}${exp}`
}

function expandToPlain(f: number): string {
  // Use toFixed with sufficient precision then trim.
  // For numbers in [1e-6, 1e21), toString already gives plain decimal —
  // this branch is defensive only.
  const s = f.toFixed(20)
  // Trim trailing zeros but keep at least one digit after dot.
  return s.replace(/(\.[0-9]*?)0+$/, '$1').replace(/\.$/, '')
}
