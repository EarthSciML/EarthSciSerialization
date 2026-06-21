# Conservative-regridding ASSEMBLY — Julia evaluator conformance.
#
# Bead ess-my4.4.6 (the Julia assembly). RFC semiring-faq-unified-ir §A.8 / §8.1
# / §6.1; CONFORMANCE_SPEC.md §5.8. Composes the full first-order conservative
# regridding pipeline end-to-end on a fixture grid pair and proves the two
# acceptance invariants — CONSERVATION and PARTITION-OF-UNITY — hold to
# tolerance, matching the A.8 decomposition piece by piece:
#
#   F_tgt[j] = (1/A_j[j])·Σ_i A_ij[i,j]·F_src[i],  A_ij = area(src_i ∩ tgt_j),
#   A_j = Σ_i A_ij  (= ConservativeRegridding.jl's dst_areas).
#
# The narrow phase (A_ij) is built HERE by the landed planar intersect_polygon +
# polygon_area kernel (ess-my4.4.3), exactly as ConservativeRegridding.jl fills
# its `intersections` matrix; the assembly fixture
# tests/valid/geometry/conservative_regrid_assembly.esm is then driven through
# build_evaluator with A_ij / F_src / dst_areas supplied as const_arrays. Every
# state is a constant-RHS D-equation from a zero IC, so the derivative
# du = f!(u0) the evaluator returns IS the assembled value — exact, no integrator.
#
# The fixture carries NO inline `tests` block: it needs const_arrays at
# evaluation time, so per CONFORMANCE_SPEC.md §5.8 the other bindings only
# schema-/structurally-validate it (the same gate as intersect_polygon_planar_area)
# while Julia evaluates it numerically here.

using Test
using EarthSciSerialization

const ESS = EarthSciSerialization
const _ASM_REPO_ROOT = normpath(joinpath(@__DIR__, "..", "..", ".."))
const _ASM_FIXTURE = joinpath(_ASM_REPO_ROOT, "tests", "valid", "geometry",
                              "conservative_regrid_assembly.esm")

# The fixture grid pair (planar), domain [0,4]×[0,1]. Two source and two target
# cells tile each of two DISJOINT broad-phase bins — b0 = the x∈[0,2) strip
# (cells 1,2), b1 = x∈[2,4) (cells 3,4) — matching the categorical bin members
# ["b0","b0","b1","b1"] the fixture declares on src_cells/tgt_cells. The target
# grid is the source grid's cell boundaries shifted within each bin, so overlaps
# are fractional (the interesting regridding case) yet both grids tile the same
# domain ⇒ full coverage ⇒ exact conservation.
const _SRC_POLYS = [
    [0.0 0.0; 1.0 0.0; 1.0 1.0; 0.0 1.0],   # src 1, bin b0
    [1.0 0.0; 2.0 0.0; 2.0 1.0; 1.0 1.0],   # src 2, bin b0
    [2.0 0.0; 3.0 0.0; 3.0 1.0; 2.0 1.0],   # src 3, bin b1
    [3.0 0.0; 4.0 0.0; 4.0 1.0; 3.0 1.0],   # src 4, bin b1
]
const _TGT_POLYS = [
    [0.0 0.0; 1.5 0.0; 1.5 1.0; 0.0 1.0],   # tgt 1, bin b0
    [1.5 0.0; 2.0 0.0; 2.0 1.0; 1.5 1.0],   # tgt 2, bin b0
    [2.0 0.0; 3.5 0.0; 3.5 1.0; 2.0 1.0],   # tgt 3, bin b1
    [3.5 0.0; 4.0 0.0; 4.0 1.0; 3.5 1.0],   # tgt 4, bin b1
]
const _F_SRC = [10.0, 20.0, 30.0, 40.0]
# Representative narrow-phase pair the fixture's clip demo clips: src 2 ∩ tgt 1 =
# [1,1.5]×[0,1], a fractional overlap of area 0.5.
const _REP_I, _REP_J = 2, 1

# Build the build-once overlap-area matrix A_ij = polygon_area(intersect_polygon(
# src_i, tgt_j)) via the landed planar kernel — ConservativeRegridding.jl's
# `intersections` matrix of RAW areas.
function _build_Aij()
    n_src, n_tgt = length(_SRC_POLYS), length(_TGT_POLYS)
    A = Matrix{Float64}(undef, n_src, n_tgt)
    for i in 1:n_src, j in 1:n_tgt
        ring = ESS.intersect_polygon(_SRC_POLYS[i], _TGT_POLYS[j], "planar")
        A[i, j] = ESS.polygon_area(ring, "planar")
    end
    return A
end

# Drive the assembly fixture through build_evaluator with the given A_ij and
# atol, returning (A_j, F_tgt, narrow_phase_area). du = f!(u0) at the zero IC IS
# the assembled value for each constant-RHS D-equation.
function _eval_assembly(A_ij::Matrix{Float64}, dst_areas::Vector{Float64}; atol::Float64=1e-12)
    file = ESS.load(_ASM_FIXTURE)
    ics = Dict("narrow_phase_area" => 0.0,
               ("A_j[$j]" => 0.0 for j in 1:length(dst_areas))...,
               ("F_tgt[$j]" => 0.0 for j in 1:length(dst_areas))...)
    f!, u0, p, _, vmap = build_evaluator(
        file; model_name="ConservativeRegridAssembly",
        initial_conditions=ics,
        const_arrays=Dict("A_ij" => A_ij, "F_src" => _F_SRC, "dst_areas" => dst_areas,
                          "src_poly_rep" => _SRC_POLYS[_REP_I],
                          "tgt_poly_rep" => _TGT_POLYS[_REP_J]),
        parameter_overrides=Dict("atol" => atol))
    du = similar(u0)
    f!(du, u0, p, 0.0)
    A_j   = [du[vmap["A_j[$j]"]] for j in 1:length(dst_areas)]
    F_tgt = [du[vmap["F_tgt[$j]"]] for j in 1:length(dst_areas)]
    narrow = du[vmap["narrow_phase_area"]]
    return A_j, F_tgt, narrow
end

@testset "M4 conservative-regridding assembly (ess-my4.4.6)" begin

    A_ij = _build_Aij()
    dst_areas = vec(sum(A_ij; dims=1))   # column sums = A_j = dst_areas
    src_areas = vec(sum(A_ij; dims=2))   # row sums = source cell areas

    @testset "fixture loads (schema + structural)" begin
        @test isfile(_ASM_FIXTURE)
        @test (ESS.load(_ASM_FIXTURE); true)
    end

    # The narrow phase built the expected sparse overlap-area matrix: within each
    # bin a refinement overlap pattern, zero across bins (the join's job), and the
    # source grid is fully covered (row sums = cell areas = 1) ⇒ conservation can
    # be exact.
    @testset "narrow phase A_ij is the expected sparse overlap matrix" begin
        @test A_ij ≈ [1.0 0.0 0.0 0.0;
                      0.5 0.5 0.0 0.0;
                      0.0 0.0 1.0 0.0;
                      0.0 0.0 0.5 0.5]
        @test src_areas ≈ [1.0, 1.0, 1.0, 1.0]
        @test dst_areas ≈ [1.5, 0.5, 1.5, 0.5]
    end

    @testset "end-to-end assembly: A_j, F_tgt, narrow-phase area" begin
        A_j, F_tgt, narrow = _eval_assembly(A_ij, dst_areas)
        # Representative narrow-phase clip area = polygon_area(intersect_polygon(
        # src 2, tgt 1)) = 0.5 = the matching A_ij entry (clip provenance of the
        # build-once factor).
        @test isapprox(narrow, A_ij[_REP_I, _REP_J]; atol=1e-12)
        @test isapprox(narrow, 0.5; atol=1e-12)
        # (3) A_j group-by-j FAQ reproduces the build-once dst_areas row-sums.
        @test A_j ≈ dst_areas
        # (4)+(5) apply + normalize: F_tgt[j] = (1/A_j[j])·Σ_i A_ij[i,j]·F_src[i].
        F_tgt_expected = [sum(A_ij[i, j] * _F_SRC[i] for i in 1:4) / dst_areas[j]
                          for j in 1:4]
        @test F_tgt ≈ F_tgt_expected
        @test F_tgt ≈ [40.0/3, 20.0, 100.0/3, 40.0]
    end

    # ACCEPTANCE INVARIANT 1 — CONSERVATION (§5.8.3): the global remapped mass
    # equals the source mass. Σ_j A_j·F_tgt[j] = Σ_j Σ_i A_ij·F_src[i]
    # = Σ_i F_src[i]·(Σ_j A_ij) = Σ_i A_i·F_src[i] exactly because the target grid
    # fully tiles each source cell (row sums = cell areas).
    @testset "CONSERVATION: Σ_j A_j·F_tgt = Σ_i A_i·F_src" begin
        A_j, F_tgt, _ = _eval_assembly(A_ij, dst_areas)
        mass_tgt = sum(A_j .* F_tgt)
        mass_src = sum(src_areas .* _F_SRC)
        @test isapprox(mass_tgt, mass_src; rtol=1e-12, atol=1e-12)
        @test isapprox(mass_tgt, 100.0; rtol=1e-12)
    end

    # ACCEPTANCE INVARIANT 2 — PARTITION-OF-UNITY (§5.8.3): the regridding weights
    # W_ij = A_ij/A_j sum to 1 over each target cell, BY CONSTRUCTION, because the
    # denominator A_j is the row-sum of the SAME areas in the numerator. Holds
    # regardless of edge-model error — the defining property of the dst_areas
    # normalization.
    @testset "PARTITION-OF-UNITY: Σ_i W_ij = 1 for every target cell" begin
        A_j, _, _ = _eval_assembly(A_ij, dst_areas)
        for j in 1:4
            w_sum = sum(A_ij[i, j] for i in 1:4) / A_j[j]
            @test isapprox(w_sum, 1.0; rtol=1e-12, atol=1e-12)
        end
    end

    # The OVERLAP JOIN is load-bearing: join.on [[i,j]] admits a contraction term
    # only when src and tgt share a bin member. A spurious CROSS-bin overlap entry
    # (src 1 ∈ b0, tgt 3 ∈ b1) must be EXCLUDED by the join — proving the broad
    # phase restricts the candidate set and is not a no-op. Without the join the
    # filter alone (A_ij > atol) would admit the bogus 99.0 and corrupt A_j[3].
    @testset "bin overlap join excludes cross-bin pairs (candidate set)" begin
        contaminated = copy(A_ij)
        contaminated[1, 3] = 99.0     # src cell 1 (b0) × tgt cell 3 (b1): cross-bin
        # dst_areas stays the CLEAN build-once denominator (the bogus entry is not
        # a real overlap); the join must keep A_j[3] at its clean value.
        A_j, F_tgt, _ = _eval_assembly(contaminated, dst_areas)
        @test isapprox(A_j[3], 1.5; rtol=1e-12)               # 99.0 excluded, not 100.5
        @test isapprox(F_tgt[3], 100.0/3; rtol=1e-12)         # apply unaffected too
        # Conservation still holds because the cross-bin term never entered.
        @test isapprox(sum(A_j .* F_tgt), 100.0; rtol=1e-12)
    end

    # The ZERO-AREA FILTER is load-bearing: filter A_ij > atol drops sub-atol
    # slivers, turning the byte-identical CANDIDATE set (from the bin join) into
    # the tolerance-dependent SURVIVING-overlap set (§5.8.5). A WITHIN-bin sliver
    # below atol (src 1 ∈ b0, tgt 2 ∈ b0) must be dropped.
    @testset "zero-area filter drops sub-atol within-bin slivers (surviving set)" begin
        slivered = copy(A_ij)
        slivered[1, 2] = 1e-6         # src 1 (b0) × tgt 2 (b0): within-bin sliver
        # atol above the sliver ⇒ filter drops it; A_j[2] keeps its clean 0.5.
        A_j, _, _ = _eval_assembly(slivered, dst_areas; atol=1e-3)
        @test isapprox(A_j[2], 0.5; rtol=1e-12)
        # atol below the sliver ⇒ filter admits it; A_j[2] now carries the +1e-6.
        A_j_admit, _, _ = _eval_assembly(slivered, dst_areas; atol=1e-12)
        @test isapprox(A_j_admit[2], 0.5 + 1e-6; rtol=1e-9)
    end
end
