/**
 * Discretization pipeline per discretization RFC §11 (gt-gbs2) and
 * DAE support / binding contract per RFC §12 (gt-q7sh).
 *
 * The public entry point is `discretize(esm)`, which walks a parsed ESM
 * document and emits a discretized ESM:
 *
 *   1. Canonicalize all expressions (§5.4).
 *   2. Resolve model-level boundary conditions into a synthetic `bc` op
 *      so they flow through the same rule engine as interior equations.
 *   3. Apply the rule engine (§5.2) to every equation RHS and every BC
 *      value with a max-pass budget.
 *   4. Re-canonicalize the rewritten ASTs.
 *   5. Check for unrewritten PDE ops (§11 Step 7) — error or
 *      passthrough-annotate depending on `strictUnrewritten`.
 *   6. RFC §12: classify equations as differential vs algebraic, count
 *      algebraic equations, stamp `metadata.system_class` and
 *      `metadata.dae_info`, and either accept the DAE or abort with
 *      `E_NO_DAE_SUPPORT` per the `daeSupport` knob.
 *   7. Record `metadata.discretized_from` provenance.
 *
 * Scheme-expansion of `use:<scheme>` rules (§7.2.1) is deferred to Step 1b.
 *
 * Mirrors `packages/EarthSciSerialization.jl/src/discretize.jl` so both
 * bindings emit byte-identical canonical output on the Step 1 fixtures.
 */

import { canonicalize } from './canonicalize.js'
import type { Expr } from './expression.js'
import {
  DEFAULT_MAX_PASSES,
  RuleEngineError,
  emptyContext,
  parseExpr,
  parseRules,
  rewrite,
  type GridMeta,
  type Rule,
  type RuleContext,
  type VariableMeta,
} from './rule-engine.js'

export const E_UNREWRITTEN_PDE_OP = 'E_UNREWRITTEN_PDE_OP'
export const E_NO_DAE_SUPPORT = 'E_NO_DAE_SUPPORT'

export interface DiscretizeOptions {
  /** Per-expression rule-engine budget (§5.2.5). Default 32. */
  maxPasses?: number
  /**
   * When `true` (default), an unrewritten PDE op (`grad`, `div`,
   * `laplacian`, `D`, `bc`) on the RHS of any equation or BC after
   * rule-engine rewrite raises `RuleEngineError(E_UNREWRITTEN_PDE_OP)`.
   * When `false`, the offending equation/BC is annotated
   * `passthrough: true` and retained verbatim.
   */
  strictUnrewritten?: boolean
  /**
   * When `true` (default — or the `ESM_DAE_SUPPORT` env var is truthy),
   * the pipeline accepts ESMs whose classification is `dae`. When
   * `false`, any algebraic equation aborts the pipeline with
   * `RuleEngineError(E_NO_DAE_SUPPORT)`. See RFC §12.
   */
  daeSupport?: boolean
}

type Json = unknown
type JsonObject = Record<string, Json>

function isObject(x: Json): x is JsonObject {
  return typeof x === 'object' && x !== null && !Array.isArray(x)
}

function isOpNode(e: Expr): e is { op: string; args: Expr[]; wrt?: string; dim?: string } & Record<string, unknown> {
  return (
    typeof e === 'object' &&
    e !== null &&
    typeof (e as { op?: unknown }).op === 'string' &&
    Array.isArray((e as { args?: unknown }).args)
  )
}

/**
 * Run the RFC §11 discretization pipeline and the RFC §12 DAE binding
 * contract on an ESM document. Returns a new object; the input is not
 * mutated.
 */
export function discretize(esm: JsonObject, options: DiscretizeOptions = {}): JsonObject {
  const maxPasses = options.maxPasses ?? DEFAULT_MAX_PASSES
  const strictUnrewritten = options.strictUnrewritten ?? true
  const daeSupport = options.daeSupport ?? defaultDaeSupport()

  if (!isObject(esm)) {
    throw new TypeError('discretize: input must be a JSON object / Record')
  }

  const out = deepClone(esm) as JsonObject

  const topRules = loadRules(out.rules)
  const ctx = buildRuleContext(out)

  const models = out.models
  if (isObject(models)) {
    for (const mname of Object.keys(models)) {
      const mraw = models[mname]
      if (!isObject(mraw)) continue
      discretizeModel(mname, mraw, topRules, ctx, maxPasses, strictUnrewritten)
    }
  }

  applyDaeContract(out, daeSupport)
  recordDiscretizedFrom(out)
  return out
}

function defaultDaeSupport(): boolean {
  const raw = typeof process !== 'undefined' ? process.env?.ESM_DAE_SUPPORT : undefined
  if (raw === undefined || raw === null) return true
  const v = String(raw).trim().toLowerCase()
  return !(v === '0' || v === 'false' || v === 'off' || v === 'no')
}

// ---------------------------------------------------------------------------
// Rule context assembly (grids + variables)
// ---------------------------------------------------------------------------

function buildRuleContext(esm: JsonObject): RuleContext {
  const ctx: RuleContext = emptyContext()
  const gridsRaw = esm.grids
  if (isObject(gridsRaw)) {
    for (const [gname, graw] of Object.entries(gridsRaw)) {
      if (!isObject(graw)) continue
      ctx.grids[gname] = extractGridMeta(graw)
    }
  }
  const models = esm.models
  if (isObject(models)) {
    for (const mraw of Object.values(models)) {
      if (!isObject(mraw)) continue
      const mgrid = typeof mraw.grid === 'string' ? mraw.grid : undefined
      const vars = mraw.variables
      if (!isObject(vars)) continue
      for (const [vname, vraw] of Object.entries(vars)) {
        if (!isObject(vraw)) continue
        const meta: VariableMeta = {}
        if (mgrid !== undefined) meta.grid = mgrid
        if (Array.isArray(vraw.shape)) {
          meta.shape = (vraw.shape as unknown[]).filter(
            (s): s is string => typeof s === 'string',
          )
        }
        if (typeof vraw.location === 'string') meta.location = vraw.location
        ctx.variables[vname] = meta
      }
    }
  }
  return ctx
}

function extractGridMeta(graw: JsonObject): GridMeta {
  const meta: GridMeta = {}
  const dims = graw.dimensions
  if (!Array.isArray(dims)) return meta
  const spatial: string[] = []
  const periodic: string[] = []
  const nonuniform: string[] = []
  for (const d of dims) {
    if (!isObject(d)) continue
    const name = d.name
    if (typeof name !== 'string') continue
    spatial.push(name)
    if (d.periodic === true) periodic.push(name)
    const spacing = d.spacing
    if (spacing === 'nonuniform' || spacing === 'stretched') nonuniform.push(name)
  }
  meta.spatial_dims = spatial
  meta.periodic_dims = periodic
  meta.nonuniform_dims = nonuniform
  return meta
}

// ---------------------------------------------------------------------------
// Model-level pipeline
// ---------------------------------------------------------------------------

function discretizeModel(
  mname: string,
  model: JsonObject,
  topRules: Rule[],
  ctx: RuleContext,
  maxPasses: number,
  strictUnrewritten: boolean,
): void {
  const localRules = loadRules(model.rules)
  const rules = localRules.length === 0 ? topRules : [...topRules, ...localRules]
  const mp = lookupMaxPasses(model, maxPasses)

  const eqns = model.equations
  if (Array.isArray(eqns)) {
    for (let i = 0; i < eqns.length; i++) {
      const eqn = eqns[i]
      if (!isObject(eqn)) continue
      discretizeEquation(
        `models.${mname}.equations[${i}]`,
        eqn,
        rules,
        ctx,
        mp,
        strictUnrewritten,
      )
    }
  }

  const bcs = model.boundary_conditions
  if (isObject(bcs)) {
    for (const [bcName, bcRaw] of Object.entries(bcs)) {
      if (!isObject(bcRaw)) continue
      discretizeBc(
        `models.${mname}.boundary_conditions.${bcName}`,
        bcRaw,
        rules,
        ctx,
        mp,
        strictUnrewritten,
      )
    }
  }
}

function lookupMaxPasses(model: JsonObject, fallback: number): number {
  const cfg = model.rules_config
  if (isObject(cfg) && typeof cfg.max_passes === 'number' && Number.isInteger(cfg.max_passes)) {
    return cfg.max_passes
  }
  return fallback
}

// ---------------------------------------------------------------------------
// Per-equation / per-BC rewrite
// ---------------------------------------------------------------------------

function discretizeEquation(
  path: string,
  eqn: JsonObject,
  rules: Rule[],
  ctx: RuleContext,
  maxPasses: number,
  strictUnrewritten: boolean,
): void {
  const passthrough = asBool(eqn.passthrough)
  if ('rhs' in eqn) {
    eqn.rhs = rewriteOrPassthrough(
      `${path}.rhs`,
      eqn.rhs as Json,
      rules,
      ctx,
      maxPasses,
      strictUnrewritten,
      passthrough,
      (v) => {
        eqn.passthrough = v
      },
    )
  }
  if ('lhs' in eqn) {
    eqn.lhs = canonicalizeValue(eqn.lhs as Json)
  }
}

function discretizeBc(
  path: string,
  bc: JsonObject,
  rules: Rule[],
  ctx: RuleContext,
  maxPasses: number,
  strictUnrewritten: boolean,
): void {
  const passthrough = asBool(bc.passthrough)
  const variable = typeof bc.variable === 'string' ? bc.variable : undefined
  const kind = typeof bc.kind === 'string' ? bc.kind : undefined
  const side = typeof bc.side === 'string' ? bc.side : undefined
  const valueRaw = 'value' in bc ? (bc.value as Json) : undefined

  let rewrittenViaBcRule = false
  if (variable !== undefined && kind !== undefined && rules.length > 0) {
    const wrapper: JsonObject = {
      op: 'bc',
      args: [variable, ...(valueRaw !== undefined ? [valueRaw] : [])],
      kind,
    }
    if (side !== undefined) wrapper.side = side
    const bcExpr = parseExpr(wrapper)
    const rewritten = rewrite(canonicalize(bcExpr), rules, ctx, maxPasses)
    if (!(isOpNode(rewritten) && rewritten.op === 'bc')) {
      const final = canonicalize(rewritten)
      if (hasPdeOp(final) && !passthrough) {
        if (strictUnrewritten) {
          const op = firstPdeOp(final) ?? '?'
          throw new RuleEngineError(
            E_UNREWRITTEN_PDE_OP,
            `${path}.value still contains PDE op '${op}' after rewrite; annotate the BC with 'passthrough: true' to opt out`,
          )
        }
        bc.passthrough = true
      }
      bc.value = final as Json
      rewrittenViaBcRule = true
    }
  }

  if (!rewrittenViaBcRule && valueRaw !== undefined) {
    bc.value = rewriteOrPassthrough(
      `${path}.value`,
      valueRaw,
      rules,
      ctx,
      maxPasses,
      strictUnrewritten,
      passthrough,
      (v) => {
        bc.passthrough = v
      },
    )
  }
}

function rewriteOrPassthrough(
  path: string,
  valueRaw: Json,
  rules: Rule[],
  ctx: RuleContext,
  maxPasses: number,
  strictUnrewritten: boolean,
  passthrough: boolean,
  setPassthrough: (v: boolean) => void,
): Json {
  const expr = parseExpr(valueRaw)
  const canon0 = canonicalize(expr)
  const rewritten = rules.length === 0 ? canon0 : rewrite(canon0, rules, ctx, maxPasses)
  const canon1 = canonicalize(rewritten)
  if (passthrough) return canon1 as Json
  if (hasPdeOp(canon1)) {
    if (strictUnrewritten) {
      const op = firstPdeOp(canon1) ?? '?'
      throw new RuleEngineError(
        E_UNREWRITTEN_PDE_OP,
        `${path} still contains PDE op '${op}' after rewrite; annotate the equation/BC with 'passthrough: true' to opt out`,
      )
    }
    setPassthrough(true)
  }
  return canon1 as Json
}

function canonicalizeValue(raw: Json): Json {
  return canonicalize(parseExpr(raw)) as Json
}

// ---------------------------------------------------------------------------
// Leftover-PDE-op scan (§11 Step 7)
// ---------------------------------------------------------------------------

const PDE_OPS = new Set(['grad', 'div', 'laplacian', 'D', 'bc'])

function hasPdeOp(e: Expr): boolean {
  return firstPdeOp(e) !== null
}

function firstPdeOp(e: Expr): string | null {
  if (!isOpNode(e)) return null
  if (PDE_OPS.has(e.op)) return e.op
  for (const a of e.args) {
    const r = firstPdeOp(a)
    if (r !== null) return r
  }
  return null
}

// ---------------------------------------------------------------------------
// DAE classification and binding contract (RFC §12)
// ---------------------------------------------------------------------------

function applyDaeContract(esm: JsonObject, daeSupport: boolean): void {
  let totalAlgebraic = 0
  const perModel: Record<string, number> = {}
  let firstAlgebraicPath: string | null = null

  const models = esm.models
  if (isObject(models)) {
    const indepByDomain = indepVarByDomain(esm)
    for (const [mname, mraw] of Object.entries(models)) {
      if (!isObject(mraw)) continue
      const indep = modelIndependentVariable(mraw, indepByDomain)
      let count = 0
      const eqns = mraw.equations
      if (Array.isArray(eqns)) {
        for (let i = 0; i < eqns.length; i++) {
          const eqn = eqns[i]
          if (!isObject(eqn)) continue
          if (!isAlgebraicEquation(eqn, indep)) continue
          count += 1
          if (firstAlgebraicPath === null) {
            firstAlgebraicPath = `models.${mname}.equations[${i}]`
          }
        }
      }
      totalAlgebraic += count
      perModel[mname] = count
    }
  }

  const outMeta = ensureObject(esm, 'metadata')
  outMeta.system_class = totalAlgebraic > 0 ? 'dae' : 'ode'
  outMeta.dae_info = {
    algebraic_equation_count: totalAlgebraic,
    per_model: perModel,
  }

  if (totalAlgebraic > 0 && !daeSupport) {
    const where = firstAlgebraicPath ?? '(unknown)'
    throw new RuleEngineError(
      E_NO_DAE_SUPPORT,
      `discretize() output contains ${totalAlgebraic} algebraic equation(s) (first at ${where}); DAE support is disabled (daeSupport=false / ESM_DAE_SUPPORT=0). Enable DAE support or remove the algebraic constraint(s). See RFC §12.`,
    )
  }
}

function indepVarByDomain(esm: JsonObject): Record<string, string> {
  const out: Record<string, string> = {}
  const domains = esm.domains
  if (!isObject(domains)) return out
  for (const [dname, draw] of Object.entries(domains)) {
    if (!isObject(draw)) continue
    const iv = draw.independent_variable
    out[dname] = typeof iv === 'string' ? iv : 't'
  }
  return out
}

function modelIndependentVariable(
  model: JsonObject,
  indepByDomain: Record<string, string>,
): string {
  const dname = model.domain
  if (typeof dname !== 'string') return 't'
  return indepByDomain[dname] ?? 't'
}

function isAlgebraicEquation(eqn: JsonObject, indep: string): boolean {
  if ('produces' in eqn) {
    const p = eqn.produces
    if (p === 'algebraic') return true
    if (isObject(p) && p.kind === 'algebraic') return true
  }
  if (asBool(eqn.algebraic)) return true
  const lhsRaw = 'lhs' in eqn ? (eqn.lhs as Json) : undefined
  if (lhsRaw === undefined) return true
  let lhs: Expr
  try {
    lhs = parseExpr(lhsRaw)
  } catch {
    return true
  }
  if (isOpNode(lhs) && lhs.op === 'D') {
    const wrt = lhs.wrt
    if (wrt === undefined || wrt === indep) return false
  }
  return true
}

function ensureObject(container: JsonObject, key: string): JsonObject {
  const raw = container[key]
  if (isObject(raw)) return raw
  const d: JsonObject = {}
  container[key] = d
  return d
}

// ---------------------------------------------------------------------------
// Metadata: discretized_from provenance
// ---------------------------------------------------------------------------

function recordDiscretizedFrom(esm: JsonObject): void {
  const meta = ensureObject(esm, 'metadata')
  const provenance: JsonObject = {}
  const srcName = meta.name
  if (typeof srcName === 'string') provenance.name = srcName
  meta.discretized_from = provenance
  const tags = meta.tags
  if (Array.isArray(tags)) {
    if (!tags.some((t) => t === 'discretized')) tags.push('discretized')
  } else {
    meta.tags = ['discretized']
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function loadRules(raw: Json): Rule[] {
  if (raw === undefined || raw === null) return []
  if (Array.isArray(raw)) {
    if (raw.length === 0) return []
    return parseRules(raw)
  }
  if (isObject(raw)) {
    if (Object.keys(raw).length === 0) return []
    return parseRules(raw)
  }
  return []
}

function asBool(x: Json): boolean {
  if (typeof x === 'boolean') return x
  if (typeof x === 'string') return x.toLowerCase() === 'true'
  return false
}

function deepClone<T>(x: T): T {
  if (Array.isArray(x)) return x.map((v) => deepClone(v)) as unknown as T
  if (isObject(x as Json)) {
    const out: JsonObject = {}
    for (const [k, v] of Object.entries(x as JsonObject)) {
      out[k] = deepClone(v)
    }
    return out as unknown as T
  }
  return x
}
