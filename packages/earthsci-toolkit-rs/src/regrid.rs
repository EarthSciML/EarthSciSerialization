//! Conservative-regridding **assembly** — the end-to-end first-order
//! (area-weighted) regridder built from the `intersect_polygon` leaf and the
//! `polygon_area` FAQ (RFC `semiring-faq-unified-ir` §A.8 / §8.1;
//! CONFORMANCE_SPEC.md §5.8).
//!
//! The operation, verified piece-by-piece against `ConservativeRegridding.jl`
//! (§A.8), is
//!
//! ```text
//! F_tgt[j] = (1/A_j)·Σ_i A_ij·F_src[i],   A_ij = area(src_i ∩ tgt_j),   A_j = Σ_i A_ij
//! ```
//!
//! and decomposes into the five A.8 pieces, in realization order — each now
//! routed through the shared evaluator primitives (the imperative reduction loops
//! are retired; only the `intersect_polygon` clip leaf and the bin-Skolem
//! broad-phase glue stay hand-written, exactly as the Python reference
//! `conservative_regrid.py` does it):
//!
//! 1. **Overlap pairs** `{(i, j) : A_ij > 0}` — the spatial (θ-) join. Its broad
//!    phase is a **bin-Skolem equi-join on integer spatial-bin keys**
//!    ([`ConservativeRegridder::build_binned`]): each cell's bbox is quantized to
//!    integer lat-lon bins via `floor` and minted into [`crate::relational::skolem`]
//!    keys, and the candidates are the [`crate::relational::equijoin`] of cells
//!    sharing a bin, [`crate::relational::distinct`]-ed down to the `(i, j)` set
//!    (mirroring the Python `candidate_overlap_pairs`). Integer keys keep the
//!    **candidate set byte-identical** across bindings (§5.8.5) — no floating-point
//!    coordinate comparison enters the broad phase. STR-tree acceleration is an
//!    explicit perf follow-on (a physical-operator concern), out of scope here; the
//!    exhaustive [`ConservativeRegridder::build`] is the correctness baseline.
//! 2. **`A_ij`** — the [`crate::geometry::intersect_polygon`] kernel leaf + the
//!    `polygon_area` `sum_product` FAQ (the narrow phase), evaluated through the
//!    generic aggregate machinery by [`crate::area_faq::polygon_area_faq`] (the
//!    imperative [`crate::geometry::polygon_area`] is now only its cross-check
//!    oracle): one clip per candidate pair fills each entry of the build-once
//!    sparse overlap-area matrix (`ConservativeRegridding.jl`'s `intersections` of
//!    **raw** areas). A candidate that clips to a **sub-`atol` sliver** is treated as
//!    equal-to-zero (§5.8.2) and dropped — this is the §5.8.5
//!    *candidate set ≠ surviving-overlap set* boundary made explicit.
//! 3. **`A_j = Σ_i A_ij`** — the group-by-`j` row-sums (`dst_areas`), the
//!    [`crate::relational::group_aggregate`] `Sum` of the surviving overlaps keyed
//!    by target cell (the source-cell row-sums `A_i` likewise).
//! 4. **apply `Σ_i A_ij·F_src[i]`** — the sparse mat-vec, the `sum_product`
//!    aggregate FAQ over the dense `A_ij` / `F_src` factors evaluated through the
//!    generic aggregate machinery ([`eval_expression`], the same the `.esm`
//!    assembly fixture runs). On `wasm32` — where the array simulator is not built —
//!    it falls back to the relational `group_aggregate` `Sum`, the same group-by.
//! 5. **normalize `/A_j`** — the apply numerator divided elementwise by the stored
//!    `A_j` denominator (a guarded map, `0` where a target has no overlaps).
//!
//! Because the **same** computed areas feed both the apply numerator and the
//! `A_j` denominator, **partition-of-unity** `Σ_i W_ij = 1` (`W_ij = A_ij/A_j`)
//! holds **by construction** regardless of edge-model error (§5.8.3) — the
//! physically meaningful conformance gate, alongside global mass conservation
//! `Σ_j A_j·F_tgt[j] = Σ_i A_i·F_src[i]`.
//!
//! Cross-binding conformance for the areas / weights is **tolerance-based**
//! (FP clipping is not bit-identical) via [`crate::geometry::area_tolerance_ok`];
//! the invariants above are the exact anchors (§5.8).

use ndarray::{ArrayD, IxDyn};

use crate::geometry::{self, GeometryError, Manifold, sliver_atol};
use crate::relational::{Key, Num, SemiringOp, distinct, equijoin, group_aggregate, skolem};

// The array simulator (and thus the `sum_product` apply FAQ) is native-only — on
// `wasm32` the apply mat-vec falls back to the relational `group_aggregate`, so
// these imports are gated alongside it.
#[cfg(not(target_arch = "wasm32"))]
use crate::simulate_array::{Value, eval_expression};
#[cfg(not(target_arch = "wasm32"))]
use crate::types::Expr;
#[cfg(not(target_arch = "wasm32"))]
use serde_json::json;
#[cfg(not(target_arch = "wasm32"))]
use std::collections::HashMap;

/// A single **surviving** overlap of the regridder's sparse intersection matrix:
/// source cell `src`, target cell `tgt`, and the raw overlap area `A_ij`
/// (`area > atol`; sub-`atol` slivers are filtered out, §5.8.2). Areas are in the
/// manifold's unit — square degrees (planar) or steradians × `radius²` (spherical).
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Overlap {
    /// Source cell index `i`.
    pub src: usize,
    /// Target cell index `j`.
    pub tgt: usize,
    /// Raw overlap area `A_ij = area(src_i ∩ tgt_j)`.
    pub area: f64,
}

/// A first-order conservative (area-weighted) regridder: the build-once sparse
/// overlap-area matrix `A_ij` and the per-target row-sums `A_j`, applied to a
/// source field as `F_tgt[j] = (1/A_j)·Σ_i A_ij·F_src[i]` (§A.8).
///
/// Build once with [`ConservativeRegridder::build`] (or
/// [`ConservativeRegridder::build_binned`] with the integer-bin broad phase), then
/// [`apply`](ConservativeRegridder::apply) many times — the static/dynamic
/// partition the package mirrors (§6.1).
#[derive(Debug, Clone)]
pub struct ConservativeRegridder {
    n_src: usize,
    n_tgt: usize,
    manifold: Manifold,
    radius: f64,
    /// Surviving overlaps, sorted by `(src, tgt)` for a deterministic layout.
    overlaps: Vec<Overlap>,
    /// Dense `[n_src, n_tgt]` raw overlap-area matrix `A_ij` (`0` off the surviving
    /// set) — a scatter of [`Self::overlaps`], the factor the apply `sum_product`
    /// FAQ contracts over (mirrors the Python `Regridder.A_ij`).
    a_ij: ArrayD<f64>,
    /// `A_j = Σ_i A_ij` per target cell (`dst_areas`), the `group_aggregate` `Sum`
    /// of the surviving overlaps keyed by target cell.
    tgt_areas: Vec<f64>,
}

/// The narrow-phase per-pair overlap area `A_ij = polygon_area(src ∩ tgt)`.
///
/// On native targets this is the `polygon_area` `sum_product` FAQ evaluated
/// through the generic aggregate machinery ([`crate::area_faq::polygon_area_faq`]);
/// the imperative [`geometry::polygon_area`] is then only the cross-check oracle
/// (RFC §8.1, bead ess-d4g.1). On `wasm32` the array simulator (and thus the FAQ
/// evaluator) is not built, so the regridder falls back to the imperative area
/// there — planar works; spherical / geodesic error, exactly as before.
#[cfg(not(target_arch = "wasm32"))]
fn overlap_ring_area(ring: &[(f64, f64)], manifold: Manifold) -> Result<f64, GeometryError> {
    Ok(crate::area_faq::polygon_area_faq(ring, manifold))
}

#[cfg(target_arch = "wasm32")]
fn overlap_ring_area(ring: &[(f64, f64)], manifold: Manifold) -> Result<f64, GeometryError> {
    geometry::polygon_area(ring, manifold)
}

impl ConservativeRegridder {
    /// Build the regridder from `src_cells` and `tgt_cells` (each a lon-lat vertex
    /// ring, implicitly closed) under `manifold`, on the unit sphere
    /// (`radius = 1`). **Exhaustive** narrow phase: every `(i, j)` pair is clipped
    /// — the correctness baseline. Use [`build_binned`](Self::build_binned) for the
    /// integer-bin broad phase.
    ///
    /// Returns the first [`GeometryError`] from a degenerate cell / failed clip.
    pub fn build(
        src_cells: &[Vec<(f64, f64)>],
        tgt_cells: &[Vec<(f64, f64)>],
        manifold: Manifold,
    ) -> Result<Self, GeometryError> {
        Self::build_with_radius(src_cells, tgt_cells, manifold, 1.0)
    }

    /// [`build`](Self::build) with an explicit sphere radius / characteristic
    /// length, which scales the §5.8.2 sliver floor `atol = 1e-15·radius²`. Areas
    /// remain in the manifold's native unit (the radius does not rescale them); it
    /// governs only the sliver threshold.
    pub fn build_with_radius(
        src_cells: &[Vec<(f64, f64)>],
        tgt_cells: &[Vec<(f64, f64)>],
        manifold: Manifold,
        radius: f64,
    ) -> Result<Self, GeometryError> {
        let n_src = src_cells.len();
        let n_tgt = tgt_cells.len();
        let candidates = (0..n_src).flat_map(|i| (0..n_tgt).map(move |j| (i, j)));
        Self::assemble(src_cells, tgt_cells, manifold, radius, candidates)
    }

    /// Build with the **bin-Skolem broad phase** (§A.8 step 1 / §5.8.5): each cell
    /// is quantized to the integer lat-lon bins its bbox spans (`floor(lon/dx)`,
    /// `floor(lat/dy)`), and only candidate pairs whose integer bin ranges overlap
    /// are clipped. The candidate set is keyed on **integers** (no FP coordinate
    /// comparison), so it is order-independent and byte-identical across bindings;
    /// it is a *superset* of the truly-overlapping pairs (non-overlapping
    /// candidates clip to empty and drop out), so the surviving set — and every
    /// weight — is **identical** to [`build`](Self::build). `dx` / `dy` are the bin
    /// size in degrees (`> 0`).
    pub fn build_binned(
        src_cells: &[Vec<(f64, f64)>],
        tgt_cells: &[Vec<(f64, f64)>],
        manifold: Manifold,
        dx: f64,
        dy: f64,
    ) -> Result<Self, GeometryError> {
        if !dx.is_finite() || !dy.is_finite() || dx <= 0.0 || dy <= 0.0 {
            return Err(GeometryError::new(format!(
                "bin sizes must be finite and positive, got dx={dx}, dy={dy}"
            )));
        }
        let candidates = candidate_pairs_binned(src_cells, tgt_cells, dx, dy);
        Self::assemble(src_cells, tgt_cells, manifold, 1.0, candidates.into_iter())
    }

    /// Narrow phase shared by the build entry points: clip each candidate pair
    /// (the `intersect_polygon` leaf), keep the overlap iff its `polygon_area` FAQ
    /// clears the sliver floor (§5.8.2), then assemble the static factors — the
    /// dense `A_ij` scatter and the `A_j = Σ_i A_ij` row-sums through the relational
    /// `group_aggregate` `Sum`. The surviving overlaps are sorted by `(src, tgt)`.
    fn assemble(
        src_cells: &[Vec<(f64, f64)>],
        tgt_cells: &[Vec<(f64, f64)>],
        manifold: Manifold,
        radius: f64,
        candidates: impl Iterator<Item = (usize, usize)>,
    ) -> Result<Self, GeometryError> {
        let n_src = src_cells.len();
        let n_tgt = tgt_cells.len();
        let atol = sliver_atol(radius);
        let mut overlaps: Vec<Overlap> = Vec::new();
        for (i, j) in candidates {
            let ring = geometry::intersect_polygon(&src_cells[i], &tgt_cells[j], manifold)?;
            if ring.len() < 3 {
                continue; // disjoint / edge-touching: empty clip, no contribution
            }
            let area = overlap_ring_area(&ring, manifold)?;
            // §5.8.2 sliver floor: a sub-`atol` overlap is treated as
            // equal-to-zero — the candidate→surviving boundary (§5.8.5).
            if area <= atol {
                continue;
            }
            overlaps.push(Overlap {
                src: i,
                tgt: j,
                area,
            });
        }
        overlaps.sort_by_key(|ov| (ov.src, ov.tgt));

        // Dense `A_ij` — a scatter of the surviving overlaps into the
        // `[n_src, n_tgt]` factor the apply FAQ contracts over (a layout transform,
        // not a reduction; off-surviving-set entries stay `0`).
        let mut a_ij = ArrayD::<f64>::zeros(IxDyn(&[n_src, n_tgt]));
        for ov in &overlaps {
            a_ij[IxDyn(&[ov.src, ov.tgt])] = ov.area;
        }

        // `A_j = Σ_i A_ij` — the group-by-`tgt` row-sums through the relational
        // `group_aggregate` `Sum` (§A.8 step 3; `ConservativeRegridding.jl`'s
        // `dst_areas`), recomputed from the *same* areas that feed the apply so the
        // partition-of-unity holds by construction (§5.8.3).
        let tgt_areas = group_sum_by_index(&keyed_areas(&overlaps, |ov| ov.tgt), n_tgt);

        Ok(Self {
            n_src,
            n_tgt,
            manifold,
            radius,
            overlaps,
            a_ij,
            tgt_areas,
        })
    }

    /// Number of source cells.
    pub fn n_src(&self) -> usize {
        self.n_src
    }

    /// Number of target cells.
    pub fn n_tgt(&self) -> usize {
        self.n_tgt
    }

    /// The declared manifold (compare two regridders only same-manifold, §5.8.4).
    pub fn manifold(&self) -> Manifold {
        self.manifold
    }

    /// The sphere radius / characteristic length governing the sliver floor.
    pub fn radius(&self) -> f64 {
        self.radius
    }

    /// The surviving sparse overlaps `A_ij` (sorted by `(src, tgt)`).
    pub fn overlaps(&self) -> &[Overlap] {
        &self.overlaps
    }

    /// `A_j = Σ_i A_ij` per target cell (`ConservativeRegridding.jl`'s `dst_areas`).
    pub fn target_areas(&self) -> &[f64] {
        &self.tgt_areas
    }

    /// `A_i = Σ_j A_ij` per source cell — the source area actually covered by the
    /// target mesh. Equals the true source-cell area when the target mesh fully
    /// tiles the source (the condition under which first-order conservation is
    /// exact, §5.8.3). The group-by-`src` row-sum through `group_aggregate` `Sum`.
    pub fn source_areas(&self) -> Vec<f64> {
        group_sum_by_index(&keyed_areas(&self.overlaps, |ov| ov.src), self.n_src)
    }

    /// The conservative weight `W_ij = A_ij / A_j` (`0` if `(i, j)` is not a
    /// surviving overlap or target `j` has no overlaps) — the §A.8 normalize as a
    /// guarded divide of the dense `A_ij` factor by the stored `A_j` denominator.
    pub fn weight(&self, i: usize, j: usize) -> f64 {
        let aj = self.tgt_areas.get(j).copied().unwrap_or(0.0);
        if aj <= 0.0 {
            return 0.0;
        }
        self.a_ij.get(IxDyn(&[i, j])).copied().unwrap_or(0.0) / aj
    }

    /// Apply the regridder to a source field: `F_tgt[j] = Σ_i W_ij·F_src[i]`
    /// (the apply `sum_product` mat-vec [`Self::apply_numerator`] followed by the
    /// `/A_j` normalize). A target with no overlaps maps to `0`.
    ///
    /// # Panics
    /// If `f_src.len() != n_src`.
    pub fn apply(&self, f_src: &[f64]) -> Vec<f64> {
        assert_eq!(
            f_src.len(),
            self.n_src,
            "source field length {} != n_src {}",
            f_src.len(),
            self.n_src
        );
        // (4) apply numerator Σ_i A_ij·F_src[i] through the evaluator, then
        // (5) normalize `/A_j` — a guarded elementwise divide (`0` where A_j = 0).
        self.apply_numerator(f_src)
            .iter()
            .zip(&self.tgt_areas)
            .map(|(&num, &aj)| if aj > 0.0 { num / aj } else { 0.0 })
            .collect()
    }

    /// The apply **numerator** `Σ_i A_ij·F_src[i]` per target cell (the sparse
    /// mat-vec `mul!(dst, intersections, src)`, pre-normalize).
    ///
    /// On native targets this is the `sum_product` aggregate FAQ over the dense
    /// `A_ij` / `F_src` factors, evaluated through the generic aggregate machinery
    /// ([`eval_expression`]) — the §A.8 apply as the IR contracts it, the same node
    /// shape the `conservative_regrid_assembly.esm` fixture encodes.
    #[cfg(not(target_arch = "wasm32"))]
    fn apply_numerator(&self, f_src: &[f64]) -> Vec<f64> {
        let f_arr =
            ArrayD::from_shape_vec(IxDyn(&[self.n_src]), f_src.to_vec()).expect("F_src is [n_src]");
        let mut inputs: HashMap<String, ArrayD<f64>> = HashMap::new();
        inputs.insert("A_ij".to_string(), self.a_ij.clone());
        inputs.insert("F_src".to_string(), f_arr);
        match eval_expression(
            &apply_faq_node(self.n_src, self.n_tgt),
            &inputs,
            &[],
            &[],
            0.0,
        ) {
            Value::Array(a) => a.iter().copied().collect(),
            // `output_idx: ["j"]` always yields an array; a scalar would mean an
            // empty target range, in which case the single value is the only cell.
            Value::Scalar(s) => vec![s],
        }
    }

    /// The apply numerator on `wasm32`, where the array simulator (and thus
    /// [`eval_expression`]) is not built: the same `Σ_i A_ij·F_src[i]` group-by-`j`
    /// sum through the relational `group_aggregate` `Sum` — the declarative fallback
    /// (the same shape as `overlap_ring_area`'s wasm area path), no accumulator loop.
    #[cfg(target_arch = "wasm32")]
    fn apply_numerator(&self, f_src: &[f64]) -> Vec<f64> {
        let rows: Vec<(Key, Num)> = self
            .overlaps
            .iter()
            .map(|ov| (Key::Int(ov.tgt as i64), Num::Float(ov.area * f_src[ov.src])))
            .collect();
        group_sum_by_index(&rows, self.n_tgt)
    }

    /// Partition-of-unity per target: `Σ_i W_ij` (`= 1` for every target with
    /// overlaps, exact by construction, §5.8.3). A target with no overlaps yields
    /// `0`. Summed as the `group_aggregate` `Sum` of the per-overlap weights
    /// `A_ij/A_j` keyed by target — computing it from the weights rather than
    /// reusing `A_j` validates the construction rather than asserting a tautology.
    pub fn partition_of_unity(&self) -> Vec<f64> {
        let rows: Vec<(Key, Num)> = self
            .overlaps
            .iter()
            .map(|ov| {
                (
                    Key::Int(ov.tgt as i64),
                    Num::Float(ov.area / self.tgt_areas[ov.tgt]),
                )
            })
            .collect();
        group_sum_by_index(&rows, self.n_tgt)
    }

    /// Global remapped mass `Σ_j A_j·F_tgt[j]` — the LHS of the conservation
    /// invariant (§5.8.3), the `group_aggregate` `Sum` of the per-cell `A_j·F_tgt[j]`.
    ///
    /// # Panics
    /// If `f_tgt.len() != n_tgt`.
    pub fn target_mass(&self, f_tgt: &[f64]) -> f64 {
        assert_eq!(f_tgt.len(), self.n_tgt, "target field length != n_tgt");
        fold_sum(self.tgt_areas.iter().zip(f_tgt).map(|(&aj, &f)| aj * f))
    }

    /// Global source mass `Σ_i A_i·F_src[i]` using the **covered** source areas
    /// `A_i = Σ_j A_ij` — the RHS of the conservation invariant (§5.8.3), the
    /// `group_aggregate` `Sum` of the per-cell `A_i·F_src[i]`. Equals
    /// [`target_mass`](Self::target_mass) of `apply(f_src)` by construction.
    ///
    /// # Panics
    /// If `f_src.len() != n_src`.
    pub fn source_mass(&self, f_src: &[f64]) -> f64 {
        assert_eq!(f_src.len(), self.n_src, "source field length != n_src");
        fold_sum(
            self.source_areas()
                .iter()
                .zip(f_src)
                .map(|(&ai, &f)| ai * f),
        )
    }
}

/// The bbox of a lon-lat ring as `(min_lon, min_lat, max_lon, max_lat)`.
fn bbox(cell: &[(f64, f64)]) -> (f64, f64, f64, f64) {
    let mut min_lon = f64::INFINITY;
    let mut min_lat = f64::INFINITY;
    let mut max_lon = f64::NEG_INFINITY;
    let mut max_lat = f64::NEG_INFINITY;
    for &(lon, lat) in cell {
        min_lon = min_lon.min(lon);
        max_lon = max_lon.max(lon);
        min_lat = min_lat.min(lat);
        max_lat = max_lat.max(lat);
    }
    (min_lon, min_lat, max_lon, max_lat)
}

/// The inclusive integer bin range `[floor(lo/step), floor(hi/step)]` an interval
/// `[lo, hi]` spans. **Integer** keys (the §5.8.5 quantization): the only place
/// floating-point coordinates touch the broad phase is this `floor`, never a raw
/// coordinate comparison.
fn bin_span(lo: f64, hi: f64, step: f64) -> (i64, i64) {
    let b0 = (lo / step).floor() as i64;
    let b1 = (hi / step).floor() as i64;
    (b0.min(b1), b0.max(b1))
}

/// Tag the bin Skolem keys carry, mirroring the worked fixture
/// `tests/valid/geometry/conservative_regrid_overlap_join.esm` and the Python
/// `conservative_regrid.BIN_TAG`.
const BIN_TAG: &str = "bin";

/// Every integer spatial-bin Skolem key a cell's bbox spans. Each bin its bbox
/// touches (`floor(coord/step)`, the §5.8.5 integer quantization) is minted into a
/// [`skolem`] key `("bin", bx, by)` — keys are integer-componented, so the
/// resulting candidate set is byte-identical across bindings. Mirrors the Python
/// `cell_bin_keys`.
fn cell_bin_keys(cell: &[(f64, f64)], dx: f64, dy: f64) -> Vec<Key> {
    let (lo_x, lo_y, hi_x, hi_y) = bbox(cell);
    let (bx0, bx1) = bin_span(lo_x, hi_x, dx);
    let (by0, by1) = bin_span(lo_y, hi_y, dy);
    let mut keys = Vec::new();
    for bx in bx0..=bx1 {
        for by in by0..=by1 {
            keys.push(skolem(
                vec![Key::Str(BIN_TAG.to_string()), Key::Int(bx), Key::Int(by)],
                false,
            ));
        }
    }
    keys
}

/// The `(bin_key, cell_ordinal)` rows of a cell list — one row per bin each cell's
/// bbox spans, the left/right operand of the broad-phase equi-join.
fn bin_rows(cells: &[Vec<(f64, f64)>], dx: f64, dy: f64) -> Vec<Key> {
    cells
        .iter()
        .enumerate()
        .flat_map(|(idx, cell)| {
            cell_bin_keys(cell, dx, dy)
                .into_iter()
                .map(move |k| Key::Tuple(vec![k, Key::Int(idx as i64)]))
        })
        .collect()
}

/// The bin key (first component) of a `(bin_key, cell_ordinal)` row — the equi-join
/// key projection.
fn row_bin(row: &Key) -> Key {
    match row {
        Key::Tuple(v) => v[0].clone(),
        _ => row.clone(),
    }
}

/// The cell ordinal (second component) of a `(bin_key, cell_ordinal)` row.
fn row_idx(row: &Key) -> Key {
    match row {
        Key::Tuple(v) => v[1].clone(),
        _ => row.clone(),
    }
}

/// Unwrap an integer key to its `i64` (a cell ordinal). Panics on a non-integer
/// key — these come only from the internally-minted integer rows above.
fn key_int(k: &Key) -> i64 {
    match k {
        Key::Int(i) => *i,
        other => panic!("expected an integer relational key, got {other:?}"),
    }
}

/// Candidate `(src, tgt)` pairs whose integer bin ranges overlap — the bin-Skolem
/// equi-join broad phase (§A.8 step 1 / §5.8.5). Realized as the value-equality
/// [`equijoin`] of the `(bin_key, cell)` tables on the shared bin key, then
/// [`distinct`] over the surviving `(i, j)` index pairs (mirroring the Python
/// `candidate_overlap_pairs`). A *superset* of the truly-overlapping pairs
/// (bbox-overlapping cells always share ≥1 bin); both primitives emit in the §5.5
/// sorted total order, so the returned set is byte-identical and permutation-
/// invariant — neither input order nor bucket iteration order can perturb it.
fn candidate_pairs_binned(
    src_cells: &[Vec<(f64, f64)>],
    tgt_cells: &[Vec<(f64, f64)>],
    dx: f64,
    dy: f64,
) -> Vec<(usize, usize)> {
    let src_rows = bin_rows(src_cells, dx, dy);
    let tgt_rows = bin_rows(tgt_cells, dx, dy);
    let matched = equijoin(&src_rows, &tgt_rows, row_bin, row_bin);
    let pairs: Vec<Key> = matched
        .iter()
        .map(|(left, right)| Key::Tuple(vec![row_idx(left), row_idx(right)]))
        .collect();
    distinct(&pairs)
        .into_iter()
        .map(|k| match k {
            Key::Tuple(v) => (key_int(&v[0]) as usize, key_int(&v[1]) as usize),
            other => unreachable!("candidate pair is a 2-tuple, got {other:?}"),
        })
        .collect()
}

/// `(Key::Int(index), Num::Float(area))` rows for a relational group-by, keyed by
/// the `key_of` projection of each surviving overlap (`tgt` for `A_j`, `src` for
/// `A_i`).
fn keyed_areas(overlaps: &[Overlap], key_of: impl Fn(&Overlap) -> usize) -> Vec<(Key, Num)> {
    overlaps
        .iter()
        .map(|ov| (Key::Int(key_of(ov) as i64), Num::Float(ov.area)))
        .collect()
}

/// Float of a relational [`Num`] (all regridder values are `Float`; an integer
/// bucket — e.g. an empty group never emitted — is widened defensively).
fn num_f64(n: Num) -> f64 {
    match n {
        Num::Float(f) => f,
        Num::Int(i) => i as f64,
    }
}

/// Scatter a relational `group_aggregate` `Sum` over `rows` into a dense `[len]`
/// vector indexed by the integer group key (cells with no group stay `0`). The
/// group-by-index row-sum primitive shared by `A_j`, source areas, partition-of-
/// unity, and the wasm apply fallback.
fn group_sum_by_index(rows: &[(Key, Num)], len: usize) -> Vec<f64> {
    let mut out = vec![0.0_f64; len];
    for (k, v) in group_aggregate(rows, SemiringOp::Sum) {
        let idx = key_int(&k) as usize;
        if idx < len {
            out[idx] = num_f64(v);
        }
    }
    out
}

/// Global `Σ values` through the relational `group_aggregate` `Sum` (a single
/// content-addressed bucket) — the evaluator-routed fold the conservation-mass
/// dot-products use instead of an imperative accumulator. An empty iterator
/// folds to `0`.
fn fold_sum<I: Iterator<Item = f64>>(values: I) -> f64 {
    let rows: Vec<(Key, Num)> = values.map(|v| (Key::Int(0), Num::Float(v))).collect();
    group_aggregate(&rows, SemiringOp::Sum)
        .into_iter()
        .next()
        .map(|(_, n)| num_f64(n))
        .unwrap_or(0.0)
}

/// The apply numerator FAQ `Σ_i A_ij·F_src[i]` (output index `j`, contracted index
/// `i`) — an ordinary `sum_product` aggregate (§A.8 step 4 / §8.1) over the dense
/// `A_ij` / `F_src` factors, the node shape the `conservative_regrid_assembly.esm`
/// apply equation encodes. Concrete `[1, n]` ranges (bare [`eval_expression`] does
/// not resolve `{from}` index-set references).
#[cfg(not(target_arch = "wasm32"))]
fn apply_faq_node(n_src: usize, n_tgt: usize) -> Expr {
    serde_json::from_value(json!({
        "op": "aggregate", "args": [], "semiring": "sum_product", "output_idx": ["j"],
        "ranges": { "i": [1, n_src], "j": [1, n_tgt] },
        "expr": { "op": "*", "args": [
            { "op": "index", "args": ["A_ij", "i", "j"] },
            { "op": "index", "args": ["F_src", "i"] },
        ] },
    }))
    .expect("apply sum_product FAQ node is well-formed")
}

#[cfg(all(test, not(target_arch = "wasm32")))]
mod tests {
    use super::*;
    use ndarray::{ArrayD, IxDyn};
    use serde_json::json;

    use crate::simulate_array::{Value, eval_expression};
    use crate::types::Expr;

    const TIGHT: f64 = 1e-12;

    /// Two unit cells on `[0,1]` and `[1,2]` (lat `[0,1]`).
    fn src_two_cells() -> Vec<Vec<(f64, f64)>> {
        vec![
            vec![(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)],
            vec![(1.0, 0.0), (2.0, 0.0), (2.0, 1.0), (1.0, 1.0)],
        ]
    }

    /// Targets `[0,1.5]` and `[1.5,2]` (lat `[0,1]`): they tile the same domain as
    /// `src_two_cells`, so overlaps are A=[1.0, 0.5] into T0 and 0.5 into T1.
    fn tgt_split_cells() -> Vec<Vec<(f64, f64)>> {
        vec![
            vec![(0.0, 0.0), (1.5, 0.0), (1.5, 1.0), (0.0, 1.0)],
            vec![(1.5, 0.0), (2.0, 0.0), (2.0, 1.0), (1.5, 1.0)],
        ]
    }

    #[test]
    fn planar_overlap_areas_are_exact() {
        let r =
            ConservativeRegridder::build(&src_two_cells(), &tgt_split_cells(), Manifold::Planar)
                .unwrap();
        // A_00 = 1 (all of S0), A_10 = 0.5, A_11 = 0.5; A_01 = 0 (filtered).
        assert_eq!(r.overlaps().len(), 3);
        assert!((r.weight(0, 0) - 1.0 / 1.5).abs() < TIGHT);
        assert!((r.weight(1, 0) - 0.5 / 1.5).abs() < TIGHT);
        assert!((r.weight(1, 1) - 1.0).abs() < TIGHT);
        assert_eq!(r.weight(0, 1), 0.0);
        // A_j = [1.5, 0.5].
        assert!((r.target_areas()[0] - 1.5).abs() < TIGHT);
        assert!((r.target_areas()[1] - 0.5).abs() < TIGHT);
    }

    #[test]
    fn partition_of_unity_holds_by_construction() {
        let r =
            ConservativeRegridder::build(&src_two_cells(), &tgt_split_cells(), Manifold::Planar)
                .unwrap();
        for (j, &pou) in r.partition_of_unity().iter().enumerate() {
            assert!(
                (pou - 1.0).abs() < TIGHT,
                "target {j} partition-of-unity {pou}"
            );
        }
    }

    #[test]
    fn apply_and_mass_conservation() {
        let r =
            ConservativeRegridder::build(&src_two_cells(), &tgt_split_cells(), Manifold::Planar)
                .unwrap();
        let f_src = [3.0, 7.0];
        let f_tgt = r.apply(&f_src);
        // F_tgt[0] = (1·3 + 0.5·7)/1.5 = 6.5/1.5; F_tgt[1] = 7.
        assert!((f_tgt[0] - (3.0 + 0.5 * 7.0) / 1.5).abs() < TIGHT);
        assert!((f_tgt[1] - 7.0).abs() < TIGHT);
        // Conservation: Σ_j A_j F_tgt = Σ_i A_i F_src (both = 3 + 7 = 10 here,
        // since the meshes tile the same domain so A_i = 1 each).
        assert!((r.target_mass(&f_tgt) - r.source_mass(&f_src)).abs() < TIGHT);
        assert!((r.source_mass(&f_src) - 10.0).abs() < TIGHT);
    }

    #[test]
    fn binned_broad_phase_matches_exhaustive() {
        let src = src_two_cells();
        let tgt = tgt_split_cells();
        let dense = ConservativeRegridder::build(&src, &tgt, Manifold::Planar).unwrap();
        // Bin at the grid spacing; candidate set is a superset, surviving set equal.
        let binned =
            ConservativeRegridder::build_binned(&src, &tgt, Manifold::Planar, 1.0, 1.0).unwrap();
        assert_eq!(dense.overlaps(), binned.overlaps());
        assert_eq!(dense.target_areas(), binned.target_areas());
    }

    #[test]
    fn candidate_set_is_input_order_independent() {
        // Permuting target order must not change the binned candidate-bin keys
        // (integer keys, §5.8.5): the surviving overlaps map back identically.
        let src = src_two_cells();
        let tgt = tgt_split_cells();
        let mut tgt_rev = tgt.clone();
        tgt_rev.reverse();
        let a =
            ConservativeRegridder::build_binned(&src, &tgt, Manifold::Planar, 1.0, 1.0).unwrap();
        let b = ConservativeRegridder::build_binned(&src, &tgt_rev, Manifold::Planar, 1.0, 1.0)
            .unwrap();
        // Map b's overlaps (reversed target indices) back to the original order.
        let n = tgt.len();
        let mut b_mapped: Vec<Overlap> = b
            .overlaps()
            .iter()
            .map(|ov| Overlap {
                src: ov.src,
                tgt: n - 1 - ov.tgt,
                area: ov.area,
            })
            .collect();
        b_mapped.sort_by_key(|x| (x.src, x.tgt));
        assert_eq!(a.overlaps(), b_mapped.as_slice());
    }

    #[test]
    fn empty_target_has_zero_weight_and_field() {
        // A target far from every source has no overlaps: weight 0, field 0,
        // partition-of-unity 0 (no source mass mapped there).
        let src = vec![vec![(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]];
        let tgt = vec![
            vec![(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)],
            vec![(50.0, 50.0), (51.0, 50.0), (51.0, 51.0), (50.0, 51.0)],
        ];
        let r = ConservativeRegridder::build(&src, &tgt, Manifold::Planar).unwrap();
        assert_eq!(r.target_areas()[1], 0.0);
        let f_tgt = r.apply(&[5.0]);
        assert_eq!(f_tgt[1], 0.0);
        assert_eq!(r.partition_of_unity()[1], 0.0);
        assert!((f_tgt[0] - 5.0).abs() < TIGHT);
    }

    /// `polygon_area` as the actual `sum_product` FAQ over a clipped ring, through
    /// the real array evaluator — the planar shoelace integrand
    /// `½·(xᵥ·yᵥ₊₁ − xᵥ₊₁·yᵥ)`. Proves the regridder's `A_ij` (computed via the
    /// `geometry::polygon_area` oracle) equals the IR FAQ value (RFC §8.1).
    fn shoelace_area_faq(ring: &[(f64, f64)]) -> f64 {
        let n = ring.len();
        let next: Vec<(f64, f64)> = (0..n).map(|i| ring[(i + 1) % n]).collect();
        let to_arr = |r: &[(f64, f64)]| {
            let flat: Vec<f64> = r.iter().flat_map(|&(x, y)| [x, y]).collect();
            ArrayD::from_shape_vec(IxDyn(&[r.len(), 2]), flat).unwrap()
        };
        let mut inputs = HashMap::new();
        inputs.insert("clip".to_string(), to_arr(ring));
        inputs.insert("clip_next".to_string(), to_arr(&next));
        let agg: Expr = serde_json::from_value(json!({
            "op": "aggregate", "args": [], "semiring": "sum_product", "output_idx": [],
            "ranges": { "v": [1, n] },
            "expr": { "op": "*", "args": [0.5, { "op": "-", "args": [
                { "op": "*", "args": [
                    { "op": "index", "args": ["clip", "v", 1] },
                    { "op": "index", "args": ["clip_next", "v", 2] } ]},
                { "op": "*", "args": [
                    { "op": "index", "args": ["clip_next", "v", 1] },
                    { "op": "index", "args": ["clip", "v", 2] } ]} ]} ]}
        }))
        .unwrap();
        match eval_expression(&agg, &inputs, &[], &[], 0.0) {
            Value::Scalar(s) => s.abs(),
            Value::Array(_) => panic!("scalar polygon_area FAQ expected"),
        }
    }

    #[test]
    fn regridder_areas_equal_polygon_area_faq() {
        // Each surviving A_ij must equal `polygon_area` evaluated as a sum_product
        // FAQ over the same clipped ring (the IR's narrow phase, §8.1).
        let src = src_two_cells();
        let tgt = tgt_split_cells();
        let r = ConservativeRegridder::build(&src, &tgt, Manifold::Planar).unwrap();
        for ov in r.overlaps() {
            let ring =
                geometry::intersect_polygon(&src[ov.src], &tgt[ov.tgt], Manifold::Planar).unwrap();
            let faq = shoelace_area_faq(&ring);
            assert!(
                (ov.area - faq).abs() < TIGHT,
                "A_{}{} oracle {} vs FAQ {faq}",
                ov.src,
                ov.tgt,
                ov.area
            );
        }
    }
}
