import { describe, it, expect } from 'vitest'
import {
  applyStencilGhosted1d,
  StencilEvaluatorError,
  E_GHOST_FILL_UNSUPPORTED,
  E_GHOST_WIDTH_TOO_SMALL,
  E_STENCIL_BAD_INPUT,
  type StencilEntryLike,
} from './stencil-evaluator.js'

// Centered 2nd-order finite difference: stencil = (-1/(2dx), 0, +1/(2dx))
// at offsets ±1. Mirrors the Julia esm-37k testset's `centered_fd`.
const centeredFd: StencilEntryLike[] = [
  {
    selector: { kind: 'cartesian', axis: 'x', offset: -1 },
    coeff: { op: '/', args: [-1, { op: '*', args: [2, 'dx'] }] },
  },
  {
    selector: { kind: 'cartesian', axis: 'x', offset: 1 },
    coeff: { op: '/', args: [1, { op: '*', args: [2, 'dx'] }] },
  },
]

// Reference periodic implementation, as a self-contained witness for the
// "periodic kind" parity test. Mirrors the Julia
// `apply_stencil_periodic_1d` semantics (wrap-around indexing) so that
// the bit-equality test stands on its own without importing a
// TS-binding periodic kernel that does not yet exist.
function applyPeriodicReference(
  stencil: StencilEntryLike[],
  u: number[],
  dx: number,
): number[] {
  const n = u.length
  const out = new Array<number>(n)
  // Compute coefficient values from the same expressions as the kernel.
  // For centered 2nd-order: c_-1 = -1/(2dx), c_+1 = +1/(2dx).
  const coeffs: Array<[number, number]> = stencil.map((s) => {
    if (s.selector.offset === -1) return [-1, -1 / (2 * dx)]
    if (s.selector.offset === 1) return [1, 1 / (2 * dx)]
    throw new Error('reference impl only handles ±1 offsets')
  })
  for (let i = 0; i < n; i++) {
    let acc = 0
    for (const [off, c] of coeffs) {
      const j = ((i + off) % n + n) % n
      acc += c * u[j]!
    }
    out[i] = acc
  }
  return out
}

describe('applyStencilGhosted1d (esm-37k, RFC §5.2.8)', () => {
  describe('periodic kind', () => {
    it('matches the periodic reference bit-equal across ghost widths', () => {
      const n = 32
      const dx = 1 / n
      const u: number[] = []
      for (let i = 1; i <= n; i++) u.push(Math.sin(2 * Math.PI * (i - 0.5) * dx))
      const bindings = new Map([['dx', dx]])
      const ref = applyPeriodicReference(centeredFd, u, dx)
      for (const Ng of [1, 2, 5]) {
        const got = applyStencilGhosted1d(centeredFd, u, bindings, {
          ghostWidth: Ng,
          boundaryPolicy: 'periodic',
        })
        for (let i = 0; i < n; i++) {
          // Bit-equal: periodic ghost fill is the same wrap.
          expect(Object.is(got[i], ref[i])).toBe(true)
        }
      }
    })
  })

  describe('reflecting kind', () => {
    it('produces a one-sided forward difference shape at the boundary', () => {
      // u = cos(πx) on [0,1] cell centers is symmetric across the boundary
      // face, so reflecting fill leaves the centered FD operator
      // self-consistent at the first/last interior cells.
      const n = 16
      const dx = 1 / n
      const u: number[] = []
      for (let i = 1; i <= n; i++) u.push(Math.cos(Math.PI * (i - 0.5) * dx))
      const bindings = new Map([['dx', dx]])
      const got = applyStencilGhosted1d(centeredFd, u, bindings, {
        ghostWidth: 1,
        boundaryPolicy: 'reflecting',
      })
      // First interior cell: ghost is u[0] (mirror) → derivative there
      // uses (u[1] - u[0])/(2dx) — the one-sided forward difference shape.
      expect(got[0]!).toBeCloseTo((u[1]! - u[0]!) / (2 * dx), 12)
      expect(got[n - 1]!).toBeCloseTo((u[n - 1]! - u[n - 2]!) / (2 * dx), 12)
      // Compares acceptably against -π sin(πx) at the deep interior.
      for (let i = 2; i < n - 2; i++) {
        const ref = -Math.PI * Math.sin(Math.PI * (i + 0.5) * dx)
        expect(Math.abs(got[i]! - ref)).toBeLessThan(0.05)
      }
    })

    it('treats neumann_zero alias as reflecting', () => {
      const n = 8
      const dx = 1 / n
      const u: number[] = Array.from({ length: n }, (_, i) => i + 1)
      const bindings = new Map([['dx', dx]])
      const viaReflecting = applyStencilGhosted1d(centeredFd, u, bindings, {
        ghostWidth: 1,
        boundaryPolicy: 'reflecting',
      })
      const viaNeumann = applyStencilGhosted1d(centeredFd, u, bindings, {
        ghostWidth: 1,
        boundaryPolicy: 'neumann_zero',
      })
      for (let i = 0; i < n; i++) expect(viaNeumann[i]).toBe(viaReflecting[i])
    })
  })

  describe('one_sided_extrapolation kind', () => {
    it('linear default is exact on a linear profile', () => {
      // u = 2 + 3i on cell-index space → linear extrapolation is exact, so
      // centered FD reproduces du/dx ≡ slope/dx everywhere.
      const n = 12
      const dx = 0.1
      const u: number[] = Array.from({ length: n }, (_, i) => 2 + 3 * (i + 1))
      const bindings = new Map([['dx', dx]])
      const got = applyStencilGhosted1d(centeredFd, u, bindings, {
        ghostWidth: 1,
        boundaryPolicy: 'one_sided_extrapolation',
      })
      for (const g of got) expect(g).toBeCloseTo(3 / dx, 10)
    })

    it('degree=2 is exact on a quadratic profile', () => {
      const n = 10
      const dx = 0.5
      const u: number[] = Array.from({ length: n }, (_, i) => (i + 1) ** 2)
      const bindings = new Map([['dx', dx]])
      const got = applyStencilGhosted1d(centeredFd, u, bindings, {
        ghostWidth: 1,
        boundaryPolicy: { kind: 'one_sided_extrapolation', degree: 2 },
      })
      // Centered FD on i^2: ((i+1)^2 - (i-1)^2)/(2dx) = 2i/dx.
      for (let i = 1; i <= n; i++) {
        expect(got[i - 1]).toBeCloseTo((2 * i) / dx, 10)
      }
    })

    it('degree=3 is exact on a cubic profile', () => {
      const n = 12
      const dx = 0.25
      const u: number[] = Array.from({ length: n }, (_, i) => (i + 1) ** 3)
      const bindings = new Map([['dx', dx]])
      const got = applyStencilGhosted1d(centeredFd, u, bindings, {
        ghostWidth: 1,
        boundaryPolicy: { kind: 'one_sided_extrapolation', degree: 3 },
      })
      // Centered FD on i^3: ((i+1)^3 - (i-1)^3)/(2dx) = (6i^2 + 2)/(2dx).
      for (let i = 1; i <= n; i++) {
        expect(got[i - 1]).toBeCloseTo((6 * i * i + 2) / (2 * dx), 10)
      }
    })

    it('extrapolate alias defaults degree=1', () => {
      const n = 8
      const dx = 0.1
      const u: number[] = Array.from({ length: n }, (_, i) => 1.5 * (i + 1) + 0.5)
      const bindings = new Map([['dx', dx]])
      const got = applyStencilGhosted1d(centeredFd, u, bindings, {
        ghostWidth: 1,
        boundaryPolicy: 'extrapolate',
      })
      for (const g of got) expect(g).toBeCloseTo(1.5 / dx, 10)
    })
  })

  describe('prescribed kind', () => {
    it('uses caller-supplied ghost values', () => {
      const n = 8
      const dx = 0.1
      const u: number[] = Array.from({ length: n }, (_, i) => i + 1)
      const bindings = new Map([['dx', dx]])
      const calls: Array<[string, number]> = []
      // u[i] = i (1-based) ⇒ supply linear ghosts so derivative is 1/dx.
      const prescribe = (side: 'left' | 'right', k: number): number => {
        calls.push([side, k])
        return side === 'left' ? 1 - k : n + k
      }
      const got = applyStencilGhosted1d(centeredFd, u, bindings, {
        ghostWidth: 1,
        boundaryPolicy: 'prescribed',
        prescribe,
      })
      for (const g of got) expect(g).toBeCloseTo(1 / dx, 10)
      expect(calls).toContainEqual(['left', 1])
      expect(calls).toContainEqual(['right', 1])
    })

    it('ghosted alias requires a prescribe callback', () => {
      const n = 8
      const dx = 0.1
      const u: number[] = Array.from({ length: n }, (_, i) => i + 1)
      const bindings = new Map([['dx', dx]])
      let err: unknown = null
      try {
        applyStencilGhosted1d(centeredFd, u, bindings, {
          ghostWidth: 1,
          boundaryPolicy: 'ghosted',
        })
      } catch (e) {
        err = e
      }
      expect(err).toBeInstanceOf(StencilEvaluatorError)
      expect((err as StencilEvaluatorError).code).toBe(E_STENCIL_BAD_INPUT)
    })
  })

  describe('error paths', () => {
    it('raises E_GHOST_WIDTH_TOO_SMALL when stencil reach exceeds ghostWidth', () => {
      // Standard 4th-order centered FD: offsets ±1 and ±2.
      const wide: StencilEntryLike[] = [
        {
          selector: { kind: 'cartesian', axis: 'x', offset: -2 },
          coeff: { op: '/', args: [1, { op: '*', args: [12, 'dx'] }] },
        },
        {
          selector: { kind: 'cartesian', axis: 'x', offset: -1 },
          coeff: { op: '/', args: [-8, { op: '*', args: [12, 'dx'] }] },
        },
        {
          selector: { kind: 'cartesian', axis: 'x', offset: 1 },
          coeff: { op: '/', args: [8, { op: '*', args: [12, 'dx'] }] },
        },
        {
          selector: { kind: 'cartesian', axis: 'x', offset: 2 },
          coeff: { op: '/', args: [-1, { op: '*', args: [12, 'dx'] }] },
        },
      ]
      const n = 16
      const dx = 1 / n
      const u: number[] = []
      for (let i = 1; i <= n; i++) u.push(Math.sin(2 * Math.PI * (i - 0.5) * dx))
      const bindings = new Map([['dx', dx]])
      let err: unknown = null
      try {
        applyStencilGhosted1d(wide, u, bindings, {
          ghostWidth: 1,
          boundaryPolicy: 'periodic',
        })
      } catch (e) {
        err = e
      }
      expect(err).toBeInstanceOf(StencilEvaluatorError)
      expect((err as StencilEvaluatorError).code).toBe(E_GHOST_WIDTH_TOO_SMALL)
    })

    it('raises E_GHOST_FILL_UNSUPPORTED for panel_dispatch', () => {
      const n = 8
      const dx = 0.1
      const u: number[] = Array.from({ length: n }, (_, i) => i + 1)
      const bindings = new Map([['dx', dx]])
      let err: unknown = null
      try {
        applyStencilGhosted1d(centeredFd, u, bindings, {
          ghostWidth: 1,
          boundaryPolicy: { kind: 'panel_dispatch', interior: 'dist', boundary: 'dist_bnd' },
        })
      } catch (e) {
        err = e
      }
      expect(err).toBeInstanceOf(StencilEvaluatorError)
      expect((err as StencilEvaluatorError).code).toBe(E_GHOST_FILL_UNSUPPORTED)
    })

    it('rejects unknown boundary_policy kind', () => {
      const n = 8
      const dx = 0.1
      const u: number[] = Array.from({ length: n }, (_, i) => i + 1)
      const bindings = new Map([['dx', dx]])
      expect(() =>
        applyStencilGhosted1d(centeredFd, u, bindings, {
          ghostWidth: 1,
          boundaryPolicy: 'not_a_real_kind',
        }),
      ).toThrow(StencilEvaluatorError)
    })

    it('rejects negative ghost_width', () => {
      const n = 8
      const dx = 0.1
      const u: number[] = Array.from({ length: n }, (_, i) => i + 1)
      const bindings = new Map([['dx', dx]])
      expect(() =>
        applyStencilGhosted1d(centeredFd, u, bindings, {
          ghostWidth: -1,
          boundaryPolicy: 'periodic',
        }),
      ).toThrow(StencilEvaluatorError)
    })

    it('rejects an empty stencil', () => {
      const bindings = new Map([['dx', 0.1]])
      expect(() =>
        applyStencilGhosted1d([], [1, 2, 3, 4], bindings, {
          ghostWidth: 1,
          boundaryPolicy: 'periodic',
        }),
      ).toThrow(StencilEvaluatorError)
    })
  })
})
