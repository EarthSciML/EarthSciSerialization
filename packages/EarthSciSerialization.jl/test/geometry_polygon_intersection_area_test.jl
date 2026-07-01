# polygon_intersection_area — the FUSED clip+area scalar leaf (esm-spec §4.2 / §8.6.1).
#
# `polygon_intersection_area(a, b)` returns the SCALAR overlap area of two polygon
# vertex rings under a declared `manifold`, defined to equal
# `polygon_area(intersect_polygon(a, b))` at the same manifold — but with NO exposed
# clip ring / derived index set. It is the fused composition of the two existing
# constituent kernels: the `intersect_polygon` Sutherland–Hodgman clip and the
# `polygon_area` shoelace FAQ (`_polygon_area_via_faq`). Because it evaluates to an
# ordinary Float64 scalar, it drops into any expression — here an ODE RHS — with no
# ragged intermediate.
#
# The shared conformance fixture `polygon_intersection_area_planar.esm` overlaps two
# unit-aligned squares (src (0,0)-(2,0)-(2,2)-(0,2), tgt (1,1)-(3,1)-(3,3)-(1,3)) in
# the [1,2]×[1,2] box, so the planar overlap area is exactly 1.0. The model consumes
# it as `d(area_state)/dt = overlap_area` from a zero IC, so `area_state(1) = 1.0`.

using Test
using EarthSciSerialization
import OrdinaryDiffEqTsit5

const _PIA = EarthSciSerialization
const _PIA_REPO_ROOT = normpath(joinpath(@__DIR__, "..", "..", ".."))
const _PIA_VALID_GEOM = joinpath(_PIA_REPO_ROOT, "tests", "valid", "geometry")

# Two unit-aligned squares overlapping in the [1,2]×[1,2] box → overlap area 1.0.
const _PIA_SQUARE_A = [0.0 0.0; 2.0 0.0; 2.0 2.0; 0.0 2.0]
const _PIA_SQUARE_B = [1.0 1.0; 3.0 1.0; 3.0 3.0; 1.0 3.0]

@testset "polygon_intersection_area — fused clip+area scalar leaf (§8.6.1)" begin

    # --- the fused kernel reuses intersect_polygon + the polygon_area FAQ ---
    @testset "fused kernel equals polygon_area(intersect_polygon(...))" begin
        area = _PIA._polygon_intersection_area(_PIA_SQUARE_A, _PIA_SQUARE_B, "planar")
        @test isapprox(area, 1.0; atol=1e-12)
        # Definitionally equal to the unfused clip → shoelace-area composition.
        oracle = _PIA.polygon_area(
            _PIA.intersect_polygon(_PIA_SQUARE_A, _PIA_SQUARE_B, "planar"), "planar")
        @test isapprox(area, oracle; atol=1e-12)
        # A disjoint pair has zero overlap area (degenerate clip → 0.0).
        far = [5.0 5.0; 6.0 5.0; 6.0 6.0; 5.0 6.0]
        @test _PIA._polygon_intersection_area(_PIA_SQUARE_A, far, "planar") == 0.0
    end

    # --- the shared conformance fixture through build_evaluator + solve ---
    @testset "fixture: area_state(1.0) == 1.0 (build_evaluator → solve)" begin
        path = joinpath(_PIA_VALID_GEOM, "polygon_intersection_area_planar.esm")
        @test isfile(path)
        file = EarthSciSerialization.load(path)

        f!, u0, p, tspan, vmap =
            build_evaluator(file; model_name="PolygonIntersectionAreaPlanar")
        @test haskey(vmap, "area_state")
        @test u0[vmap["area_state"]] == 0.0        # ic(area_state) = 0.0
        @test tspan == (0.0, 1.0)

        # The fused leaf const-folds to the scalar overlap area: d(area_state)/dt =
        # overlap_area = polygon_intersection_area(src_poly, tgt_poly) = 1.0.
        du = similar(u0)
        f!(du, u0, p, 0.0)
        @test isapprox(du[vmap["area_state"]], 1.0; atol=1e-9)

        # Integrate to t = 1: area_state(1) = ∫₀¹ overlap_area dt = 1.0.
        prob = OrdinaryDiffEqTsit5.ODEProblem(f!, u0, tspan, p)
        sol = OrdinaryDiffEqTsit5.solve(prob, OrdinaryDiffEqTsit5.Tsit5();
                                        reltol=1e-10, abstol=1e-12)
        @test isapprox(sol.u[end][vmap["area_state"]], 1.0; atol=1e-9)
    end
end
