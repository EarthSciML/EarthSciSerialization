/**
 * DAE binding contract for the typescript binding (discretization RFC §12).
 *
 * typescript's strategy is **trivial-factor + error otherwise**. Given an
 * ESM document whose models mix differential and algebraic equations,
 * `discretize()`:
 *
 *   1. Classifies every equation as `differential` (LHS is
 *      `D(x, wrt=<indep>)` where `<indep>` is the enclosing model's
 *      domain's `independent_variable`, default `"t"`) or `algebraic`
 *      (everything else — observed-equation LHS, authored constraints,
 *      `algebraic: true` / `produces: "algebraic"` markers).
 *   2. Factors out **trivial** algebraic equations: equations of the
 *      form `lhs ~ rhs` where `lhs` is a plain variable name that does
 *      not appear in `rhs`. Each trivial equation is substituted into
 *      every downstream equation (algebraic and differential) and then
 *      removed. This iterates until fixed point, so a chain of observed
 *      equations (`z ~ y+1; y ~ sin(x); D(x) ~ y`) collapses to
 *      `D(x) ~ sin(x)`.
 *   3. If any algebraic equations remain after factoring (non-trivial
 *      constraints, cyclic observed chains, implicit equations), throws
 *      `DAEError` with code `E_NONTRIVIAL_DAE` naming the first
 *      offending equation and pointing at the Julia binding + RFC §12
 *      for full-DAE support.
 *
 * Full DAE support (implicit constraints, index reduction) is Julia-only
 * at v0.2.0; typescript has no usable DAE ecosystem stack. See
 * `docs/rfcs/dae-binding-strategies.md`.
 *
 * The §11 discretize pipeline (load, rewrite, canonicalize, …) is not
 * yet implemented in typescript; this module implements §12 only and
 * operates on an already-canonicalized ESM document.
 */

import type { EsmFile, Equation, Expression, ExprNode, Model, Domain } from './types.js'
import { contains } from './expression.js'
import { substitute } from './substitute.js'
import { isNumericLiteral } from './numeric-literal.js'

export const E_NONTRIVIAL_DAE = 'E_NONTRIVIAL_DAE'

/**
 * Error thrown by `discretize()` when the DAE binding contract fails.
 * The `code` property carries a normative error code string.
 */
export class DAEError extends Error {
  readonly code: string
  /** Binding-idiomatic path (`models.<name>.equations[<i>]`) pointing at the first residual algebraic equation, when applicable. */
  readonly equationPath: string | undefined
  constructor(code: string, message: string, equationPath?: string) {
    super(message)
    this.name = 'DAEError'
    this.code = code
    this.equationPath = equationPath
  }
}

/** Per-binding DAE classification summary. */
export interface DAEInfo {
  algebraic_equation_count: number
  per_model: Record<string, number>
}

/**
 * Widened ESM type for the output of `discretize()`. Adds the RFC §12
 * DAE classification fields (`system_class`, `dae_info`) to
 * `metadata`. These fields live on the top-level metadata because
 * `Model` has `additionalProperties: false` in the schema.
 */
export type DiscretizeResult = EsmFile & {
  metadata: EsmFile['metadata'] & {
    system_class?: 'ode' | 'dae'
    dae_info?: DAEInfo
  }
}

/**
 * Run the typescript binding's trivial-DAE factoring pass and RFC §12
 * contract check on an ESM document.
 *
 * The input is deep-cloned; the input object is not mutated.
 *
 * @throws DAEError (`E_NONTRIVIAL_DAE`) if factoring leaves any
 *   algebraic equation behind.
 */
export function discretize(esm: EsmFile): DiscretizeResult {
  const out = deepClone(esm) as DiscretizeResult
  const indepByDomain = collectIndependentVariables(out)

  let totalAlgebraic = 0
  const perModel: Record<string, number> = {}

  const models = out.models ?? {}
  for (const [modelName, model] of Object.entries(models)) {
    const indep = modelIndependentVariable(model, indepByDomain)
    const residual = factorModel(model, modelName, indep)
    totalAlgebraic += residual
    perModel[modelName] = residual
  }

  const systemClass: 'ode' | 'dae' = totalAlgebraic > 0 ? 'dae' : 'ode'
  const metadata = out.metadata as DiscretizeResult['metadata']
  metadata.system_class = systemClass
  metadata.dae_info = { algebraic_equation_count: totalAlgebraic, per_model: perModel }

  if (totalAlgebraic > 0) {
    const firstOffender = findFirstAlgebraicPath(out, indepByDomain)
    throw new DAEError(
      E_NONTRIVIAL_DAE,
      `${E_NONTRIVIAL_DAE}: discretize() output contains ${totalAlgebraic} non-trivial algebraic equation(s) after factoring trivial observed-style equations. ` +
        `First offender: ${firstOffender ?? '(unknown)'}. ` +
        `The typescript binding supports only trivial DAEs (observed equations of the form \`y ~ expr\` where \`y\` does not appear in \`expr\`); ` +
        `implicit constraints and cyclic observed chains require a full DAE assembler. ` +
        `Use the Julia binding (EarthSciSerialization.jl) for full DAE support, or rewrite the constraint in an explicit form. ` +
        `See RFC §12 and docs/rfcs/dae-binding-strategies.md.`,
      firstOffender ?? undefined
    )
  }

  return out
}

/**
 * Factor trivial algebraic equations within one model. Mutates `model`
 * in place. Returns the count of residual (non-trivial) algebraic
 * equations.
 */
function factorModel(model: Model, _modelName: string, indep: string): number {
  if (!Array.isArray(model.equations) || model.equations.length === 0) {
    return 0
  }

  // Iterative trivial-equation elimination. On each pass, scan for a
  // currently-trivial algebraic equation (LHS is a plain variable name,
  // RHS does not reference that variable), substitute it into every
  // other equation, and remove it. Repeat until no progress is made.
  let equations = model.equations.slice()

  // Safety bound: an upper bound on the number of substitution passes is
  // the initial equation count (each pass removes ≥ 1 algebraic eqn).
  const maxPasses = equations.length + 1
  for (let pass = 0; pass < maxPasses; pass++) {
    let idx = -1
    let lhsName = ''
    for (let i = 0; i < equations.length; i++) {
      const eqn = equations[i]!
      if (!isAlgebraicEquation(eqn, indep)) continue
      const name = trivialLhsName(eqn)
      if (name == null) continue
      if (contains(eqn.rhs as Expression, name)) continue
      // Refuse to factor if the candidate variable is differentiated
      // anywhere (it's a true state, not an observed quantity, and
      // naive substitution would miss the chain rule). Leave it as a
      // residual algebraic equation → E_NONTRIVIAL_DAE.
      if (isDifferentiatedInAny(equations, name, i)) continue
      idx = i
      lhsName = name
      break
    }
    if (idx < 0) break
    const removed = equations[idx]!
    // Substitute everywhere else; drop the trivial equation.
    const bindings: Record<string, Expression> = { [lhsName]: removed.rhs as Expression }
    equations = equations
      .filter((_, i) => i !== idx)
      .map(eqn => ({
        ...eqn,
        lhs: substitute(eqn.lhs as Expression, bindings) as Expression,
        rhs: substitute(eqn.rhs as Expression, bindings) as Expression,
      }))
  }

  model.equations = equations

  // Count whatever algebraic equations are still here.
  let residual = 0
  for (const eqn of equations) {
    if (isAlgebraicEquation(eqn, indep)) residual++
  }
  return residual
}

/**
 * Return the LHS variable name if the equation's LHS is a plain
 * variable reference suitable for trivial factoring. `null` otherwise
 * (LHS is a number, an expression node, a scoped dotted reference, or
 * a numeric literal).
 */
function trivialLhsName(eqn: Equation): string | null {
  const lhs = eqn.lhs as Expression
  if (typeof lhs !== 'string') return null
  // Scoped references (`A.B.c`) are not safe to substitute by a single
  // name; treat as non-trivial. Numeric-literal leaves already fail the
  // `typeof === 'string'` check above.
  if (lhs.includes('.')) return null
  return lhs
}

/**
 * Classify an equation as algebraic (`true`) vs differential (`false`).
 * Differential iff LHS is an operator node `D(x, wrt=<indep>)` and
 * `wrt` is either absent (defaults to the model's independent variable)
 * or equal to `indep`.
 *
 * Authored `algebraic: true` or `produces: "algebraic"` markers on the
 * equation object force algebraic classification, matching Julia
 * behavior. Any unrecognized LHS shape is treated as algebraic so the
 * contract fails closed rather than silently dropping a constraint.
 */
function isAlgebraicEquation(eqn: Equation, indep: string): boolean {
  const marker = (eqn as Equation & { algebraic?: unknown; produces?: unknown })
  if (marker.algebraic === true) return true
  const produces = marker.produces
  if (produces === 'algebraic') return true
  if (produces && typeof produces === 'object' && (produces as { kind?: string }).kind === 'algebraic') {
    return true
  }

  const lhs = eqn.lhs as Expression
  if (lhs == null) return true
  if (typeof lhs === 'number' || isNumericLiteral(lhs)) return true
  if (typeof lhs === 'string') return true // observed-equation LHS
  const node = lhs as ExprNode
  if (!node || node.op !== 'D') return true
  const wrt = (node as ExprNode & { wrt?: unknown }).wrt
  if (wrt == null) return false
  if (typeof wrt === 'string' && wrt === indep) return false
  return true
}

/**
 * Walk every equation (skipping `skipIdx`) looking for `D(name, …)` or
 * `D(name)` nodes whose first argument is exactly `name`. Returns true
 * if any such node is found in either lhs or rhs — signals that
 * `name` carries a time derivative and therefore is not an observed
 * variable safe for naive substitution.
 */
function isDifferentiatedInAny(
  equations: Equation[],
  name: string,
  skipIdx: number
): boolean {
  for (let i = 0; i < equations.length; i++) {
    if (i === skipIdx) continue
    const eqn = equations[i]!
    if (hasDerivativeOf(eqn.lhs as Expression, name)) return true
    if (hasDerivativeOf(eqn.rhs as Expression, name)) return true
  }
  return false
}

function hasDerivativeOf(expr: Expression, name: string): boolean {
  if (typeof expr === 'string' || typeof expr === 'number' || isNumericLiteral(expr)) {
    return false
  }
  const node = expr as ExprNode
  if (!node || typeof node !== 'object') return false
  if (node.op === 'D' && Array.isArray(node.args) && node.args[0] === name) {
    return true
  }
  if (Array.isArray(node.args)) {
    for (const arg of node.args) {
      if (hasDerivativeOf(arg as Expression, name)) return true
    }
  }
  return false
}

function collectIndependentVariables(esm: EsmFile): Record<string, string> {
  const out: Record<string, string> = {}
  const domains = esm.domains ?? {}
  for (const [name, d] of Object.entries(domains)) {
    const iv = (d as Domain).independent_variable
    out[name] = typeof iv === 'string' ? iv : 't'
  }
  return out
}

function modelIndependentVariable(model: Model, indepByDomain: Record<string, string>): string {
  const dom = model.domain
  if (typeof dom !== 'string') return 't'
  return indepByDomain[dom] ?? 't'
}

function findFirstAlgebraicPath(
  esm: EsmFile,
  indepByDomain: Record<string, string>
): string | null {
  const models = esm.models ?? {}
  for (const [mname, model] of Object.entries(models)) {
    const indep = modelIndependentVariable(model, indepByDomain)
    const eqns = model.equations ?? []
    for (let i = 0; i < eqns.length; i++) {
      if (isAlgebraicEquation(eqns[i]!, indep)) {
        return `models.${mname}.equations[${i}]`
      }
    }
  }
  return null
}

function deepClone<T>(value: T): T {
  // Prefer native structuredClone when present (Node ≥ 17, jsdom in
  // vitest); fall back to a JSON round-trip for older envs. ESM
  // documents are pure JSON (no Dates, Maps, etc.), so JSON is safe
  // and predictable.
  const sc = (globalThis as { structuredClone?: <U>(v: U) => U }).structuredClone
  if (typeof sc === 'function') return sc(value)
  return JSON.parse(JSON.stringify(value))
}
