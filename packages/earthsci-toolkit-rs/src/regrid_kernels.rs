//! Horizontal regridding kernels mirroring the ESD `regridding/*` rules (bead
//! ess-14f.10), the Rust sibling of Python
//! `earthsci_toolkit.data_loaders.regrid_kernels`.
//!
//! The C4 driver ([`crate::regrid_driver`]) selects one of these by the
//! per-variable [`crate::types::RegridSpec`] `method`. Each kernel is the numeric
//! realisation of an ESD declarative rule — the C4 bridge is an explicit
//! orchestration that reproduces the rule arithmetic rather than evaluating the
//! `.esm` AST, so the fold orders below match the rule ASTs (and the Python
//! goldens) exactly:
//!
//! * `bspline` → `regridding/bspline_regrid.esm` (degree-1 `Linear1D` /
//!   `Bilinear2D` tensor product and degree-3 `Cubic1D`).
//! * `conservative` → `regridding/conservative_regrid_overlap_join.esm`: the
//!   overlap-area matrix `A_ij = area(src_i ∩ tgt_j)`, column sums
//!   `A_j = Σ_i A_ij` and the partition-of-unity apply
//!   `F_tgt[j] = (1/A_j)·Σ_i A_ij·F_src[i]`. The per-pair overlap area reuses the
//!   landed M4 geometry kernels ([`crate::geometry::intersect_polygon`] +
//!   [`crate::geometry::polygon_area`]) — no new primitive. Conservation and
//!   partition-of-unity hold by construction for any manifold.
//! * `cell_average` → `regridding/point_cell_average_regrid.esm`: bin scattered
//!   points into target cells and average, emitting `missing_value` for empty
//!   cells.

use ndarray::{Array1, Array2, Axis};

use crate::geometry::{Manifold, intersect_polygon, polygon_area};

/// Raised when a regrid kernel receives inconsistent inputs (mismatched lengths,
/// too few source nodes) or the underlying geometry kernel fails. Mirrors Python
/// `RegridKernelError`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RegridKernelError {
    message: String,
}

impl RegridKernelError {
    pub(crate) fn new(message: impl Into<String>) -> Self {
        RegridKernelError {
            message: message.into(),
        }
    }

    /// The underlying failure reason.
    pub fn message(&self) -> &str {
        &self.message
    }
}

impl std::fmt::Display for RegridKernelError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "regrid kernel error: {}", self.message)
    }
}

impl std::error::Error for RegridKernelError {}

/// The conservative remap output `(F_tgt, A, A_j)`: the regridded target values,
/// the `[n_src, n_tgt]` overlap-area matrix `A`, and the target-cell areas `A_j`
/// (the `dst_areas` column sums). Returned by [`conservative_regrid`].
pub type ConservativeRegrid = (Vec<f64>, Array2<f64>, Vec<f64>);

// --------------------------------------------------------------------------
// Source-grid location: target query -> (1-based base node, fractional offset s)
// --------------------------------------------------------------------------

/// Locate `query` points within ascending 1-D `nodes`.
///
/// Returns `(base, s)` where `base` is the **1-based** index of the lower
/// bracketing node and `s` the fractional offset into `[node[base],
/// node[base+1])` — the `base`/`s` host inputs the `bspline_regrid` rule
/// consumes. With `clamp` (the bilinear-default extrapolation), out-of-range
/// queries clamp `s` to `[0, 1]` so edge values are held. Mirrors Python
/// `locate_1d`: `searchsorted(side="right") − 1`, base index clipped to
/// `[0, n−2]`.
pub fn locate_1d(
    query: &[f64],
    nodes: &[f64],
    clamp: bool,
) -> Result<(Vec<usize>, Vec<f64>), RegridKernelError> {
    if nodes.len() < 2 {
        return Err(RegridKernelError::new(
            "locate_1d needs at least 2 source nodes",
        ));
    }
    let max_base0 = (nodes.len() - 2) as i64;
    let mut base = Vec::with_capacity(query.len());
    let mut s = Vec::with_capacity(query.len());
    for &q in query {
        // searchsorted(side="right") = count of nodes <= q (ascending).
        let sr = nodes.partition_point(|&x| x <= q) as i64;
        let idx = (sr - 1).clamp(0, max_base0) as usize;
        let x0 = nodes[idx];
        let x1 = nodes[idx + 1];
        let mut frac = if x1 != x0 { (q - x0) / (x1 - x0) } else { 0.0 };
        if clamp {
            frac = frac.clamp(0.0, 1.0);
        }
        base.push(idx + 1); // 1-based base
        s.push(frac);
    }
    Ok((base, s))
}

// --------------------------------------------------------------------------
// bspline_regrid.esm — byte-exact fold order
// --------------------------------------------------------------------------

/// `BSplineRegridLinear1D`: `(1−s)·F[base] + s·F[base+1]` (1-based `base`),
/// evaluated per query point. Mirrors Python `bspline_regrid_linear_1d`.
pub fn bspline_regrid_linear_1d(f_src: &[f64], base: &[usize], s: &[f64]) -> Vec<f64> {
    base.iter()
        .zip(s.iter())
        .map(|(&b, &sk)| {
            let b0 = b - 1;
            let t0 = (1.0 - sk) * f_src[b0];
            let t1 = sk * f_src[b0 + 1];
            t0 + t1
        })
        .collect()
}

/// `BSplineRegridCubic1D`: degree-3 Lagrange cardinal sum over 4 nodes.
///
/// Reproduces the rule's flat n-ary fold: each weight product is
/// `((coeff·f1)·f2)·f3` and the four terms sum left-to-right `((t0+t1)+t2)+t3`.
/// Mirrors Python `bspline_regrid_cubic_1d`.
pub fn bspline_regrid_cubic_1d(f_src: &[f64], base: &[usize], s: &[f64]) -> Vec<f64> {
    let term = |coeff: f64, factors: &[f64], f_k: f64| -> f64 {
        let mut wp = coeff;
        for &f in factors {
            wp *= f;
        }
        wp * f_k
    };
    base.iter()
        .zip(s.iter())
        .map(|(&b, &sk)| {
            let b0 = b - 1;
            let t0 = term(-1.0 / 6.0, &[sk, sk - 1.0, sk - 2.0], f_src[b0]);
            let t1 = term(1.0 / 2.0, &[sk + 1.0, sk - 1.0, sk - 2.0], f_src[b0 + 1]);
            let t2 = term(-1.0 / 2.0, &[sk + 1.0, sk, sk - 2.0], f_src[b0 + 2]);
            let t3 = term(1.0 / 6.0, &[sk + 1.0, sk, sk - 1.0], f_src[b0 + 3]);
            ((t0 + t1) + t2) + t3
        })
        .collect()
}

/// `BSplineRegridBilinear2D`: degree-1 tensor product over a `[x, y]` grid.
///
/// `f_src` is indexed `[x_index, y_index]`; `base_x`/`base_y` are 1-based. Term
/// and factor order match the rule AST (`((t0+t1)+t2)+t3`). Mirrors Python
/// `bspline_regrid_bilinear_2d`.
pub fn bspline_regrid_bilinear_2d(
    f_src: &Array2<f64>,
    base_x: &[usize],
    base_y: &[usize],
    s_x: &[f64],
    s_y: &[f64],
) -> Vec<f64> {
    let mut out = Vec::with_capacity(base_x.len());
    for k in 0..base_x.len() {
        let bx = base_x[k] - 1;
        let by = base_y[k] - 1;
        let sx = s_x[k];
        let sy = s_y[k];
        let t0 = ((1.0 - sx) * (1.0 - sy)) * f_src[[bx, by]];
        let t1 = (sx * (1.0 - sy)) * f_src[[bx + 1, by]];
        let t2 = ((1.0 - sx) * sy) * f_src[[bx, by + 1]];
        let t3 = (sx * sy) * f_src[[bx + 1, by + 1]];
        out.push(((t0 + t1) + t2) + t3);
    }
    out
}

// --------------------------------------------------------------------------
// conservative_regrid_overlap_join.esm — geometry-derived overlap assembly
// --------------------------------------------------------------------------

/// Build `A_ij = area(src_i ∩ tgt_j)` via the landed M4 geometry kernels.
///
/// Each ring is a slice of `(lon, lat)` vertices (implicitly closed, the
/// [`crate::geometry::intersect_polygon`] contract). Overlap areas at or below
/// `atol` are dropped to exactly `0` (the rule's `filter: A_ij > atol` sliver
/// gate). Returns the dense `[n_src, n_tgt]` raw-area matrix. Mirrors Python
/// `overlap_area_matrix`.
pub fn overlap_area_matrix(
    src_rings: &[Vec<(f64, f64)>],
    tgt_rings: &[Vec<(f64, f64)>],
    manifold: Manifold,
    atol: f64,
) -> Result<Array2<f64>, RegridKernelError> {
    let n_s = src_rings.len();
    let n_t = tgt_rings.len();
    let mut a = Array2::<f64>::zeros((n_s, n_t));
    for i in 0..n_s {
        for j in 0..n_t {
            let clip = intersect_polygon(&src_rings[i], &tgt_rings[j], manifold)
                .map_err(|e| RegridKernelError::new(e.message().to_string()))?;
            if clip.len() < 3 {
                continue;
            }
            // `polygon_area` closes the ring internally (modular shoelace / the
            // great-circle fan), so the open `intersect_polygon` output is passed
            // directly — net area over the n distinct overlap vertices, matching
            // Python's `polygon_area(close_ring(clip))` (which strips the closure).
            let area = polygon_area(&clip, manifold)
                .map_err(|e| RegridKernelError::new(e.message().to_string()))?;
            if area > atol {
                a[[i, j]] = area;
            }
        }
    }
    Ok(a)
}

/// First-order conservative remap of cell values `f_src` src→tgt.
///
/// Returns `(F_tgt, A, A_j)` where `A` is the overlap-area matrix, `A_j` the
/// target-cell areas (column sums = the `dst_areas` denominator) and
/// `F_tgt[j] = (1/A_j)·Σ_i A_ij·F_src[i]`. Empty target cells (`A_j == 0`) yield
/// `0`. Mass is conserved (`Σ_j A_j·F_tgt = Σ_ij A_ij·F_src`) and the weights
/// `A_ij/A_j` partition unity over each covered target cell. Mirrors Python
/// `conservative_regrid`.
pub fn conservative_regrid(
    f_src: &[f64],
    src_rings: &[Vec<(f64, f64)>],
    tgt_rings: &[Vec<(f64, f64)>],
    manifold: Manifold,
    atol: f64,
) -> Result<ConservativeRegrid, RegridKernelError> {
    let a = overlap_area_matrix(src_rings, tgt_rings, manifold, atol)?;
    if f_src.len() != a.nrows() {
        return Err(RegridKernelError::new(format!(
            "F_src length {} != source cell count {}",
            f_src.len(),
            a.nrows()
        )));
    }
    let a_j = a.sum_axis(Axis(0)); // column sums, len n_tgt
    let f = Array1::from(f_src.to_vec());
    let num = a.t().dot(&f); // num[j] = Σ_i A_ij·F_i
    let f_tgt: Vec<f64> = num
        .iter()
        .zip(a_j.iter())
        .map(|(&n, &aj)| if aj > 0.0 { n / aj } else { 0.0 })
        .collect();
    Ok((f_tgt, a, a_j.to_vec()))
}

// --------------------------------------------------------------------------
// point_cell_average_regrid.esm — scattered-point binning + cell average
// --------------------------------------------------------------------------

/// Average scattered station values into target cells by integer bin.
///
/// Mirrors `PointCellAverageRegrid` (and Python `cell_average_regrid`): a station
/// and a cell match when their `(floor(lon/dx), floor(lat/dy))` bins are equal;
/// the cell value is the mean of its matched stations, or `missing_value` when no
/// station lands in it.
#[allow(clippy::too_many_arguments)]
pub fn cell_average_regrid(
    station_val: &[f64],
    station_lon: &[f64],
    station_lat: &[f64],
    cell_lon: &[f64],
    cell_lat: &[f64],
    dx: f64,
    dy: f64,
    missing_value: f64,
) -> Vec<f64> {
    let s_bin_x: Vec<i64> = station_lon
        .iter()
        .map(|&v| (v / dx).floor() as i64)
        .collect();
    let s_bin_y: Vec<i64> = station_lat
        .iter()
        .map(|&v| (v / dy).floor() as i64)
        .collect();
    let mut out = Vec::with_capacity(cell_lon.len());
    for j in 0..cell_lon.len() {
        let cbx = (cell_lon[j] / dx).floor() as i64;
        let cby = (cell_lat[j] / dy).floor() as i64;
        let mut sum = 0.0;
        let mut count = 0usize;
        for i in 0..station_val.len() {
            if s_bin_x[i] == cbx && s_bin_y[i] == cby {
                sum += station_val[i];
                count += 1;
            }
        }
        out.push(if count > 0 {
            sum / count as f64
        } else {
            missing_value
        });
    }
    out
}

#[cfg(all(test, not(target_arch = "wasm32")))]
mod tests {
    use super::*;

    const TIGHT: f64 = 1e-12;

    fn rect(x0: f64, x1: f64, y0: f64, y1: f64) -> Vec<(f64, f64)> {
        vec![(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    }

    fn src_polys() -> Vec<Vec<(f64, f64)>> {
        vec![
            rect(0.0, 1.0, 0.0, 1.0),
            rect(1.0, 2.0, 0.0, 1.0),
            rect(2.0, 3.0, 0.0, 1.0),
        ]
    }

    fn tgt_polys() -> Vec<Vec<(f64, f64)>> {
        vec![
            rect(0.0, 1.5, 0.0, 1.0),
            rect(1.5, 2.0, 0.0, 1.0),
            rect(2.0, 3.0, 0.0, 1.0),
        ]
    }

    #[test]
    fn locate_1d_clamps_and_brackets() {
        let nodes = [0.0, 1.0, 2.0, 3.0, 4.0];
        let (base, s) = locate_1d(&[-1.0, 0.5, 2.0, 3.7, 9.0], &nodes, true).unwrap();
        assert_eq!(base, vec![1, 1, 3, 4, 4]);
        assert!((s[0] - 0.0).abs() < TIGHT); // clamped below
        assert!((s[1] - 0.5).abs() < TIGHT);
        assert!((s[2] - 0.0).abs() < TIGHT); // exactly on node 2 -> base 3, s 0
        assert!((s[3] - 0.7).abs() < TIGHT);
        assert!((s[4] - 1.0).abs() < TIGHT); // clamped above
    }

    #[test]
    fn bspline_linear_golden() {
        let out = bspline_regrid_linear_1d(
            &[2.0, 5.0, 8.0, 11.0, 14.0],
            &[1, 2, 3, 4],
            &[0.5, 0.5, 0.2999999999999998, 0.0],
        );
        let want = [3.5, 6.5, 8.899999999999999, 11.0];
        for (g, w) in out.iter().zip(want.iter()) {
            assert!((g - w).abs() < TIGHT, "{g} vs {w}");
        }
    }

    #[test]
    fn bspline_cubic_golden() {
        let out = bspline_regrid_cubic_1d(
            &[
                2.0,
                1.5,
                1.0,
                -0.10000000000000009,
                -2.4000000000000004,
                -6.5,
                -13.000000000000002,
            ],
            &[1, 2, 3, 4],
            &[0.5, 0.5, 0.2999999999999998, 0.0],
        );
        let want = [1.2875, 0.5625, -0.6367000000000003, -2.4000000000000004];
        for (g, w) in out.iter().zip(want.iter()) {
            assert!((g - w).abs() < TIGHT, "{g} vs {w}");
        }
    }

    #[test]
    fn bspline_bilinear_golden() {
        let f = Array2::from_shape_vec(
            (4, 4),
            vec![
                1.0, 0.5, 0.0, -0.5, //
                3.0, 2.8, 2.6, 2.4, //
                5.0, 5.1, 5.2, 5.3, //
                7.0, 7.4, 7.8, 8.2,
            ],
        )
        .unwrap();
        let out = bspline_regrid_bilinear_2d(
            &f,
            &[1, 2, 3, 2],
            &[1, 3, 2, 1],
            &[0.5, 0.5, 0.0, 0.19999999999999996],
            &[0.5, 0.0, 0.30000000000000004, 0.7],
        );
        let want = [1.825, 3.9, 5.13, 3.3019999999999996];
        for (g, w) in out.iter().zip(want.iter()) {
            assert!((g - w).abs() < TIGHT, "{g} vs {w}");
        }
    }

    #[test]
    fn conservative_invariants_planar() {
        let f_src = [10.0, 20.0, 30.0];
        let (f_tgt, a, a_j) =
            conservative_regrid(&f_src, &src_polys(), &tgt_polys(), Manifold::Planar, 1e-15)
                .unwrap();
        // Partition of unity: weights over each covered target cell sum to 1.
        for j in 0..a_j.len() {
            if a_j[j] > 0.0 {
                let wsum: f64 = (0..a.nrows()).map(|i| a[[i, j]] / a_j[j]).sum();
                assert!((wsum - 1.0).abs() < TIGHT, "PoU col {j}: {wsum}");
            }
        }
        // Global conservation: target mass == source mass.
        let source_mass: f64 = (0..a.nrows())
            .map(|i| (0..a_j.len()).map(|j| a[[i, j]]).sum::<f64>() * f_src[i])
            .sum();
        let target_mass: f64 = a_j.iter().zip(f_tgt.iter()).map(|(aj, ft)| aj * ft).sum();
        assert!(
            (target_mass - source_mass).abs() <= 1e-12 * source_mass.abs(),
            "conservation {target_mass} vs {source_mass}"
        );
        // Field values (planar areas).
        let want = [40.0 / 3.0, 20.0, 30.0];
        for (g, w) in f_tgt.iter().zip(want.iter()) {
            assert!((g - w).abs() < 1e-9, "F_tgt {g} vs {w}");
        }
    }

    #[test]
    fn conservative_spherical_golden() {
        // Rust ships the native s2bindings backend, so the spherical overlap path
        // — which Python skips when `spherely` is absent — is exercised here
        // against the Python golden (both wrap the same S2 core; rtol 1e-9).
        let f_src = [10.0, 20.0, 30.0];
        let (f_tgt, a, a_j) = conservative_regrid(
            &f_src,
            &src_polys(),
            &tgt_polys(),
            Manifold::Spherical,
            1e-15,
        )
        .unwrap();
        let a_j_want = [
            0.00045691356105173966,
            0.00015230194360827846,
            0.00030460968486220217,
        ];
        for (g, w) in a_j.iter().zip(a_j_want.iter()) {
            assert!((g - w).abs() <= 1e-9 * w.abs(), "A_j {g} vs {w}");
        }
        let f_tgt_want = [13.333319235239143, 20.0, 29.999999999999996];
        for (g, w) in f_tgt.iter().zip(f_tgt_want.iter()) {
            assert!((g - w).abs() <= 1e-9 * w.abs(), "F_tgt {g} vs {w}");
        }
        for j in 0..a_j.len() {
            if a_j[j] > 0.0 {
                let wsum: f64 = (0..a.nrows()).map(|i| a[[i, j]] / a_j[j]).sum();
                assert!((wsum - 1.0).abs() < TIGHT, "PoU col {j}: {wsum}");
            }
        }
    }

    #[test]
    fn cell_average_point_golden() {
        let got = cell_average_regrid(
            &[10.0, 20.0, 30.0],
            &[0.3, 0.7, 1.5],
            &[0.5, 0.2, 0.5],
            &[0.0, 1.0, 2.0],
            &[0.0, 0.0, 0.0],
            1.0,
            1.0,
            -999.0,
        );
        assert_eq!(got, vec![15.0, 30.0, -999.0]);
    }
}
