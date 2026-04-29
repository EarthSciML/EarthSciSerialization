/**
 * Walker ghost-fill kernel — TypeScript binding parity for esm-37k.
 *
 * Provides {@link applyStencilGhosted1d}, the 1D Cartesian stencil
 * evaluator the rule walker needs to honor a rule's `boundary_policy`
 * and `ghost_width` per RFC §5.2.8. Mirrors the Julia reference in
 * `packages/EarthSciSerialization.jl/src/mms_evaluator.jl`
 * (`apply_stencil_ghosted_1d`); on `boundary_policy="periodic"` the
 * output is bit-equal to the Julia periodic kernel on identical
 * inputs.
 *
 * Closed set of boundary-policy kinds (RFC §5.2.8):
 *
 * - `periodic` — wrap-around fill.
 * - `reflecting` (alias `neumann_zero`) — mirror across the boundary
 *   face.
 * - `one_sided_extrapolation` (alias `extrapolate`) — polynomial
 *   extrapolation, degree 0..3 (default 1).
 * - `prescribed` (alias `ghosted`) — caller-supplied ghost values via
 *   a `prescribe(side, k)` callback.
 * - `panel_dispatch` — recognised but not implemented for the 1D
 *   walker (cubed-sphere only); throws
 *   {@link E_GHOST_FILL_UNSUPPORTED}.
 */

import { evaluate, type Expr } from './expression.js'
import type {
  BoundaryPolicy,
  BoundaryPolicySpec,
} from './rule-engine.js'

// ---------------------------------------------------------------------------
// Error type + stable codes
// ---------------------------------------------------------------------------

export class StencilEvaluatorError extends Error {
  readonly code: string
  constructor(code: string, message?: string) {
    super(message ?? code)
    this.code = code
    this.name = 'StencilEvaluatorError'
  }
}

export const E_GHOST_FILL_UNSUPPORTED = 'E_GHOST_FILL_UNSUPPORTED'
export const E_GHOST_WIDTH_TOO_SMALL = 'E_GHOST_WIDTH_TOO_SMALL'
export const E_STENCIL_BAD_INPUT = 'E_STENCIL_BAD_INPUT'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * Subset of the schema's `StencilEntry` consumed by the 1D walker:
 * a Cartesian-axis selector with an integer offset, plus an arbitrary
 * coefficient expression evaluated against the supplied bindings.
 */
export interface StencilEntryLike {
  selector: { kind?: string; axis?: string; offset: number; [k: string]: unknown }
  coeff: Expr
}

export type PrescribeFn = (side: 'left' | 'right', k: number) => number

export interface GhostedOptions {
  /** Ghost-cell padding to apply on each side. Must be ≥ max(|offset|). */
  ghostWidth: number
  /**
   * Either the closed-set string form or a single-axis policy spec
   * object. Multi-axis (`{by_axis: …}`) policies must be projected
   * onto the relevant axis by the caller before invocation.
   */
  boundaryPolicy: BoundaryPolicy | BoundaryPolicySpec | string
  /**
   * Required when `boundaryPolicy` resolves to `prescribed`. Receives
   * `(side, k)` with side ∈ {`'left'`, `'right'`} and `k` ∈ `1..ghostWidth`
   * (1 = closest to the boundary), returning the ghost-cell value.
   */
  prescribe?: PrescribeFn
  /**
   * Default `one_sided_extrapolation` degree if the policy form does
   * not carry one (string-form, or object form omitting `degree`).
   * Defaults to `1` (linear).
   */
  degree?: number
}

// ---------------------------------------------------------------------------
// Boundary-policy alias resolution
// ---------------------------------------------------------------------------

const KNOWN_KINDS = new Set([
  'periodic',
  'reflecting',
  'one_sided_extrapolation',
  'prescribed',
  'ghosted',
  'neumann_zero',
  'extrapolate',
  'panel_dispatch',
])

function canonicalKind(k: string): string {
  if (k === 'ghosted') return 'prescribed'
  if (k === 'neumann_zero') return 'reflecting'
  if (k === 'extrapolate') return 'one_sided_extrapolation'
  return k
}

function extractPolicyKind(bp: GhostedOptions['boundaryPolicy']): string {
  if (typeof bp === 'string') return bp
  if (bp && typeof bp === 'object' && 'kind' in bp && typeof (bp as BoundaryPolicySpec).kind === 'string') {
    return (bp as BoundaryPolicySpec).kind
  }
  throw new StencilEvaluatorError(
    E_STENCIL_BAD_INPUT,
    `boundary_policy spec object must carry a string \`kind\` field; got ${JSON.stringify(bp)}`,
  )
}

function extractPolicyDegree(bp: GhostedOptions['boundaryPolicy'], dflt: number): number {
  if (typeof bp !== 'object' || bp === null) return dflt
  const d = (bp as BoundaryPolicySpec).degree
  if (d === undefined) return dflt
  if (!Number.isInteger(d)) {
    throw new StencilEvaluatorError(
      E_STENCIL_BAD_INPUT,
      `one_sided_extrapolation degree must be an integer, got ${d}`,
    )
  }
  return d
}

// ---------------------------------------------------------------------------
// apply_stencil_ghosted_1d
// ---------------------------------------------------------------------------

/**
 * Apply a 1D Cartesian stencil on the interior sample vector `u` after
 * extending it on each side by `ghostWidth` cells using the rule's
 * declared `boundaryPolicy` (RFC §5.2.8). Returns the interior outputs
 * (length `u.length`) with ghost cells sliced off.
 *
 * Mirrors `apply_stencil_ghosted_1d` in `mms_evaluator.jl`. On
 * `boundary_policy="periodic"` the output is bit-equal to the Julia
 * periodic kernel on identical inputs.
 *
 * @throws {@link StencilEvaluatorError} with code
 *   {@link E_GHOST_WIDTH_TOO_SMALL} when the stencil reaches farther
 *   than `ghostWidth`,
 *   {@link E_GHOST_FILL_UNSUPPORTED} when `boundary_policy=panel_dispatch`,
 *   or {@link E_STENCIL_BAD_INPUT} for malformed inputs / unknown kind /
 *   missing prescribe callback.
 */
export function applyStencilGhosted1d(
  stencil: readonly StencilEntryLike[],
  u: readonly number[],
  bindings: Map<string, number>,
  opts: GhostedOptions,
): number[] {
  const Ng = opts.ghostWidth
  if (!Number.isInteger(Ng) || Ng < 0) {
    throw new StencilEvaluatorError(
      E_STENCIL_BAD_INPUT,
      `ghost_width must be a non-negative integer, got ${Ng}`,
    )
  }
  if (!Array.isArray(stencil) || stencil.length === 0) {
    throw new StencilEvaluatorError(
      E_STENCIL_BAD_INPUT,
      'stencil must be a non-empty list of {selector, coeff} entries',
    )
  }

  const coeffPairs: Array<[number, number]> = new Array(stencil.length)
  let maxOff = 0
  for (let i = 0; i < stencil.length; i++) {
    const s = stencil[i]
    const off = s.selector.offset
    if (!Number.isInteger(off)) {
      throw new StencilEvaluatorError(
        E_STENCIL_BAD_INPUT,
        `stencil entry ${i}: selector.offset must be an integer, got ${off}`,
      )
    }
    const c = evaluate(s.coeff as Expr, bindings)
    coeffPairs[i] = [off, c]
    const ao = Math.abs(off)
    if (ao > maxOff) maxOff = ao
  }

  if (Ng < maxOff) {
    throw new StencilEvaluatorError(
      E_GHOST_WIDTH_TOO_SMALL,
      `stencil offset ${maxOff} exceeds ghost_width ${Ng}; ` +
        'rule must declare `ghost_width` ≥ max(|offset|)',
    )
  }

  const n = u.length
  if (n < 2) {
    throw new StencilEvaluatorError(
      E_STENCIL_BAD_INPUT,
      `ghosted stencil application requires at least 2 interior cells; got ${n}`,
    )
  }

  const uExt = new Array<number>(n + 2 * Ng).fill(0)
  for (let i = 0; i < n; i++) uExt[Ng + i] = u[i]!

  const rawKind = extractPolicyKind(opts.boundaryPolicy)
  if (!KNOWN_KINDS.has(rawKind)) {
    throw new StencilEvaluatorError(
      E_STENCIL_BAD_INPUT,
      `unknown boundary_policy kind ${JSON.stringify(rawKind)}; expected one of: ${Array.from(KNOWN_KINDS).join(', ')}`,
    )
  }
  const kind = canonicalKind(rawKind)
  const degree = extractPolicyDegree(opts.boundaryPolicy, opts.degree ?? 1)

  switch (kind) {
    case 'periodic':
      fillGhostsPeriodic(uExt, u, Ng)
      break
    case 'reflecting':
      fillGhostsReflecting(uExt, u, Ng)
      break
    case 'one_sided_extrapolation':
      fillGhostsOneSided(uExt, u, Ng, degree)
      break
    case 'prescribed': {
      const fn = opts.prescribe
      if (!fn) {
        throw new StencilEvaluatorError(
          E_STENCIL_BAD_INPUT,
          'boundary_policy=`prescribed` requires a `prescribe` callback; ' +
            'callable receives (side, k) with side ∈ {"left","right"} and 1 ≤ k ≤ ghost_width',
        )
      }
      fillGhostsPrescribed(uExt, Ng, fn)
      break
    }
    case 'panel_dispatch':
      throw new StencilEvaluatorError(
        E_GHOST_FILL_UNSUPPORTED,
        'boundary_policy=`panel_dispatch` not implemented for the 1D walker ' +
          '(cubed-sphere only); see esm-37k follow-ups for the 2D adapter',
      )
    default:
      // Unreachable — KNOWN_KINDS gate + canonicalKind cover the closed set.
      throw new StencilEvaluatorError(
        E_STENCIL_BAD_INPUT,
        `unhandled boundary_policy kind ${JSON.stringify(kind)} after canonicalization`,
      )
  }

  const out = new Array<number>(n).fill(0)
  for (let i = 0; i < n; i++) {
    let acc = 0
    for (const [off, c] of coeffPairs) acc += c * uExt[Ng + i + off]!
    out[i] = acc
  }
  return out
}

// ---------------------------------------------------------------------------
// Ghost-fill kernels
// ---------------------------------------------------------------------------

function fillGhostsPeriodic(uExt: number[], u: readonly number[], Ng: number): void {
  const n = u.length
  for (let k = 1; k <= Ng; k++) {
    uExt[Ng - k] = u[n - k]!            // left ghost k mirrors interior cell n-k+1 (0-based n-k)
    uExt[Ng + n + k - 1] = u[k - 1]!    // right ghost k mirrors interior cell k (0-based k-1)
  }
}

function fillGhostsReflecting(uExt: number[], u: readonly number[], Ng: number): void {
  const n = u.length
  for (let k = 1; k <= Ng; k++) {
    // Mirror across the boundary face between cell 0 (ghost) and cell 1
    // (interior, 1-based): ghost cell k (1 = closest to the boundary) reads
    // interior cell k.
    uExt[Ng - k] = u[k - 1]!
    uExt[Ng + n + k - 1] = u[n - k]!
  }
}

function fillGhostsOneSided(
  uExt: number[],
  u: readonly number[],
  Ng: number,
  degree: number,
): void {
  if (!Number.isInteger(degree) || degree < 0 || degree > 3) {
    throw new StencilEvaluatorError(
      E_STENCIL_BAD_INPUT,
      `one_sided_extrapolation degree must be in 0..3, got ${degree}`,
    )
  }
  const n = u.length
  if (n <= degree) {
    throw new StencilEvaluatorError(
      E_STENCIL_BAD_INPUT,
      `one_sided_extrapolation degree ${degree} requires at least ${degree + 1} ` +
        `interior cells; got ${n}`,
    )
  }
  for (let k = 1; k <= Ng; k++) {
    uExt[Ng - k] = extrapolateLeft(u, degree, k)
    uExt[Ng + n + k - 1] = extrapolateRight(u, degree, k)
  }
}

// Polynomial extrapolation from the left (interior cells 1..deg+1, 1-based)
// to virtual cell index 1 - k. Caller (fillGhostsOneSided) has already
// validated u.length > degree, so u[0..degree] are guaranteed defined.
function extrapolateLeft(u: readonly number[], degree: number, k: number): number {
  // 1-based u[i] == 0-based u[i-1]
  const u1 = u[0]!
  if (degree === 0) return u1
  const u2 = u[1]!
  if (degree === 1) return u1 + k * (u1 - u2)
  const u3 = u[2]!
  if (degree === 2) {
    const K = k
    return (
      (1 + 1.5 * K + 0.5 * K * K) * u1 +
      (-2 * K - K * K) * u2 +
      (0.5 * K + 0.5 * K * K) * u3
    )
  }
  // degree === 3
  const u4 = u[3]!
  const K = k
  return (
    (1 + (11 / 6) * K + K * K + (1 / 6) * K * K * K) * u1 +
    (-3 * K - 2.5 * K * K - 0.5 * K * K * K) * u2 +
    (1.5 * K + 2 * K * K + 0.5 * K * K * K) * u3 +
    ((-1 / 3) * K - 0.5 * K * K - (1 / 6) * K * K * K) * u4
  )
}

function extrapolateRight(u: readonly number[], degree: number, k: number): number {
  const n = u.length
  // 1-based u[n-j] == 0-based u[n-1-j]
  const un = u[n - 1]!
  if (degree === 0) return un
  const unm1 = u[n - 2]!
  if (degree === 1) return un + k * (un - unm1)
  const unm2 = u[n - 3]!
  if (degree === 2) {
    const K = k
    return (
      (1 + 1.5 * K + 0.5 * K * K) * un +
      (-2 * K - K * K) * unm1 +
      (0.5 * K + 0.5 * K * K) * unm2
    )
  }
  // degree === 3
  const unm3 = u[n - 4]!
  const K = k
  return (
    (1 + (11 / 6) * K + K * K + (1 / 6) * K * K * K) * un +
    (-3 * K - 2.5 * K * K - 0.5 * K * K * K) * unm1 +
    (1.5 * K + 2 * K * K + 0.5 * K * K * K) * unm2 +
    ((-1 / 3) * K - 0.5 * K * K - (1 / 6) * K * K * K) * unm3
  )
}

function fillGhostsPrescribed(uExt: number[], Ng: number, prescribe: PrescribeFn): void {
  const nInterior = uExt.length - 2 * Ng
  for (let k = 1; k <= Ng; k++) {
    uExt[Ng - k] = Number(prescribe('left', k))
    uExt[Ng + nInterior + k - 1] = Number(prescribe('right', k))
  }
}
