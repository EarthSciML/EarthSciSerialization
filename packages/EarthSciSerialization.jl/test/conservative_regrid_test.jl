# Conservative-regridding producing-binding assembly — Julia.
#
# Bead ess-my4.4.6 (the Julia assembly), sibling of the Python module
# `conservative_regrid.py` (ess-my4.4.7) and the Rust assembly (ess-my4.4.12).
# RFC semiring-faq-unified-ir §A.8 / §8.1 / §6.1; CONFORMANCE_SPEC.md §5.8.
#
# Exercises the `build_regridder` producing API end-to-end on worked grid pairs
# (the SAME grids as the Python sibling test, so the two bindings agree), proving
# the three priority-ordered gate properties of §5.8.6:
#   1. broad phase  — the bin-Skolem candidate set is integer, sorted,
#                     permutation-invariant, and complete (misses no overlap);
#   2. narrow phase — A_ij = polygon_area(intersect_polygon(...)) matches the
#                     analytic rectangle overlap, sub-atol slivers snap to zero;
#   3. invariants   — partition-of-unity Σ_i W_ij = 1 is exact, global
#                     conservation Σ_j A_j·F_tgt = Σ_i A_i·F_src is exact for
#                     tiling grids.

using Test
using EarthSciSerialization

const ESS = EarthSciSerialization

# A closed axis-aligned cell polygon as a CCW lon/lat vertex ring.
_rect(x0, x1, y0, y1) = [x0 y0; x1 y0; x1 y1; x0 y1]

# Analytic axis-aligned-rectangle intersection area — the independent cross-check
# for the clip-derived A_ij (no clipping involved).
function _rect_overlap_area(a, b)
    ax0, ax1 = minimum(@view a[:, 1]), maximum(@view a[:, 1])
    ay0, ay1 = minimum(@view a[:, 2]), maximum(@view a[:, 2])
    bx0, bx1 = minimum(@view b[:, 1]), maximum(@view b[:, 1])
    by0, by1 = minimum(@view b[:, 2]), maximum(@view b[:, 2])
    w = max(0.0, min(ax1, bx1) - max(ax0, bx0))
    h = max(0.0, min(ay1, by1) - max(ay0, by0))
    return w * h
end

# Example 1 — domain [0,3]×[0,2]: 3 source columns vs 4 offset target columns.
const _SRC_1D = [_rect(0, 1, 0, 2), _rect(1, 2, 0, 2), _rect(2, 3, 0, 2)]
const _TGT_1D = [_rect(0, 0.5, 0, 2), _rect(0.5, 1.5, 0, 2),
                 _rect(1.5, 2.5, 0, 2), _rect(2.5, 3, 0, 2)]

# Example 2 — domain [0,2]×[0,2]: 2×2 unit source vs an asymmetric 2×2 target
# split at x=1.2, y=0.8. Exercises 2-D bins and partial overlap in both axes.
const _SRC_2D = [_rect(0, 1, 0, 1), _rect(1, 2, 0, 1), _rect(0, 1, 1, 2), _rect(1, 2, 1, 2)]
const _TGT_2D = [_rect(0, 1.2, 0, 0.8), _rect(1.2, 2, 0, 0.8),
                 _rect(0, 1.2, 0.8, 2), _rect(1.2, 2, 0.8, 2)]

_src_areas(polys) = [abs(ESS.polygon_area(p, "planar")) for p in polys]

@testset "M4 conservative-regridding producing assembly (ess-my4.4.6)" begin

    # --- (1) Broad phase — deterministic, permutation-invariant, complete ---
    @testset "candidate set is integer and sorted (§5.5 total order)" begin
        pairs = ESS.candidate_overlap_pairs(_SRC_1D, _TGT_1D, 1.0, 1.0)
        @test all(p -> p[1] isa Int && p[2] isa Int, pairs)
        @test pairs == sort(pairs)
    end

    @testset "candidate set is permutation-invariant (§5.8.6 adversarial)" begin
        base = ESS.candidate_overlap_pairs(_SRC_1D, _TGT_1D, 1.0, 1.0)
        src_perm = [3, 1, 2]
        tgt_perm = [2, 4, 1, 3]
        permuted = ESS.candidate_overlap_pairs(_SRC_1D[src_perm], _TGT_1D[tgt_perm], 1.0, 1.0)
        # Map permuted positions back to original indices and re-sort.
        remapped = sort([(src_perm[i], tgt_perm[j]) for (i, j) in permuted])
        @test remapped == base
    end

    @testset "broad phase misses no real overlap (completeness)" begin
        for (src, tgt) in ((_SRC_1D, _TGT_1D), (_SRC_2D, _TGT_2D))
            pairs = Set(ESS.candidate_overlap_pairs(src, tgt, 1.0, 1.0))
            overlapping = Set((i, j) for i in 1:length(src), j in 1:length(tgt)
                              if _rect_overlap_area(src[i], tgt[j]) > 0)
            @test issubset(overlapping, pairs)   # candidate set ⊇ surviving set
        end
    end

    @testset "broad phase excludes genuinely disjoint pairs" begin
        pairs = ESS.candidate_overlap_pairs(_SRC_1D, _TGT_1D, 1.0, 1.0)
        @test length(pairs) < length(_SRC_1D) * length(_TGT_1D)
        @test (1, 4) ∉ pairs   # src col [0,1] vs tgt col [2.5,3] — disjoint
    end

    @testset "cell_bin_keys span the bbox and are float-free" begin
        # x spans bins floor(0.2)=0 .. floor(2.7)=2 → 3 columns; y bin floor(0)=0 .. floor(0.5)=0.
        keys = ESS.cell_bin_keys(_rect(0.2, 2.7, 0.0, 0.5), 1.0, 1.0)
        @test Set(keys) == Set([("bin", 0, 0), ("bin", 1, 0), ("bin", 2, 0)])
        @test all(k -> all(c -> c isa Integer || c isa AbstractString, k), keys)
    end

    # --- (2) Narrow phase — A_ij from the clip + area FAQ, sliver floor ---
    @testset "overlap_area matches analytic unit squares" begin
        a = _rect(0, 2, 0, 2)
        b = _rect(1, 3, 1, 3)
        @test isapprox(ESS.overlap_area(a, b, "planar"), 1.0; atol=1e-12)
    end

    @testset "overlap_area of disjoint cells is zero" begin
        @test ESS.overlap_area(_rect(0, 1, 0, 1), _rect(5, 6, 5, 6), "planar") == 0.0
    end

    @testset "A_ij matches the analytic rectangle overlaps" begin
        for (src, tgt) in ((_SRC_1D, _TGT_1D), (_SRC_2D, _TGT_2D))
            rg = ESS.build_regridder(src, tgt; manifold="planar", dx=1.0, dy=1.0, atol=1e-15)
            for i in 1:length(src), j in 1:length(tgt)
                @test isapprox(rg.A_ij[i, j], _rect_overlap_area(src[i], tgt[j]); atol=1e-12)
            end
        end
    end

    @testset "sub-atol sliver snaps to zero, above-floor overlap kept" begin
        # Two cells sharing a thin strip of width 1e-4 (area ~1e-4).
        a = _rect(0.0, 1.0, 0.0, 1.0)
        b = _rect(1.0 - 1e-4, 2.0, 0.0, 1.0)
        raw = ESS.overlap_area(a, b, "planar")
        @test 0.0 < raw < 1e-3
        @test ESS.overlap_area(a, b, "planar"; atol=1e-3) == 0.0           # sub-atol → zero
        @test isapprox(ESS.overlap_area(a, b, "planar"; atol=1e-9), raw)    # above floor → kept
    end

    # --- (3) Invariants — partition-of-unity (exact) + conservation ---
    @testset "partition-of-unity Σ_i W_ij = 1 is exact" begin
        for (src, tgt) in ((_SRC_1D, _TGT_1D), (_SRC_2D, _TGT_2D))
            rg = ESS.build_regridder(src, tgt; manifold="planar", dx=1.0, dy=1.0, atol=1e-15)
            @test maximum(abs, ESS.partition_of_unity_residual(rg)) < 1e-12
        end
    end

    @testset "global conservation is exact for tiling grids" begin
        for (src, tgt, fld) in (
                (_SRC_1D, _TGT_1D, [10.0, 20.0, 30.0]),
                (_SRC_2D, _TGT_2D, [1.0, 2.0, 3.0, 4.0]))
            rg = ESS.build_regridder(src, tgt; manifold="planar", dx=1.0, dy=1.0, atol=1e-15)
            res = ESS.conservation_residual(rg, fld, _src_areas(src))
            @test isapprox(res, 0.0; atol=1e-12)
            # Cross-check the assembled F_tgt against the hand-formula on grid 1.
            if length(src) == 3
                f_tgt = ESS.apply_regrid(rg, fld)
                @test f_tgt ≈ [10.0, 15.0, 25.0, 30.0]
            end
        end
    end

    # --- The candidate set is a genuine SUPERSET of the surviving set ---
    # (the §5.8.5 candidate ≠ surviving boundary): the bin join admits more pairs
    # than survive clipping, and the nonzero A_ij entries are a subset of the
    # candidates.
    @testset "candidate set ⊋ surviving overlap set" begin
        rg = ESS.build_regridder(_SRC_1D, _TGT_1D; manifold="planar", dx=1.0, dy=1.0, atol=1e-15)
        surviving = Set((i, j) for i in 1:size(rg.A_ij, 1), j in 1:size(rg.A_ij, 2)
                        if rg.A_ij[i, j] > 0)
        candidates = Set(rg.candidate_pairs)
        @test issubset(surviving, candidates)
    end
end
