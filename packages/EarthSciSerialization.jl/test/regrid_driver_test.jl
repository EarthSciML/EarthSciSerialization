# C4 regrid driver — reproject + per-method regrid + lev=min (ess-14f.5, JL-J2).
#
# The Julia sibling of the Rust `regrid_*.rs` (ess-14f.10) and Python
# `data_loaders/regrid_*.py` (ess-2fy) drivers. These tests carry the SAME inline
# goldens the Rust/Python suites do (the C4 driver has no shared JSON fixture —
# Python and Rust hardcode identical literals; Julia is the third copy), at the
# same tolerances: LCC inverse 1e-9, forward rel 1e-7/abs 1e-4, roundtrip 1e-6,
# central-meridian 1e-12, bspline 1e-12, conservative planar PoU/conservation
# 1e-12 + F_tgt 1e-9, cell_average/lev_min exact, end-to-end 1e-9.
#
# Plus the JL-J2 consumer seam: `ESDRegrid` (the RegridApplier backed by the
# driver, geometry cached once at setup) driven directly and through the JL-J1
# `build_refresh_callback` cadence wiring.

using Test
using EarthSciSerialization
import GeometryOps        # trigger EarthSciSerializationGeometryOpsExt (spherical clip)
import GeoInterface
import DiffEqCallbacks    # trigger EarthSciSerializationDataRefreshExt
import SciMLBase
import OrdinaryDiffEqTsit5 as ODE

const ESS = EarthSciSerialization

# ----------------------------------------------------------------------------
# Shared parameter sets (identical to the Python/Rust goldens)
# ----------------------------------------------------------------------------

const CAMPFIRE_SR = "+proj=lcc +lat_1=30.0 +lat_2=60.0 +lat_0=39.0 +lon_0=-97.0 " *
                    "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"

# WRF cone params (note lat_0 = 38.999996, distinct from CAMPFIRE_SR).
_wrf() = Dict{String,Any}("lat_1" => 30.0, "lat_2" => 60.0, "lat_0" => 38.999996,
                          "lon_0" => -97.0, "R" => 6_370_000.0)
# NEI2016 cone params.
_nei() = Dict{String,Any}("lat_1" => 33.0, "lat_2" => 45.0, "lat_0" => 40.0,
                          "lon_0" => -97.0, "R" => 6_370_997.0)

_campfire_dims() = ["x" => ESS.SpatialDim(-2_026_020.2, -1_990_020.2, 2000.0),
                    "y" => ESS.SpatialDim(374_725.0, 414_725.0, 2000.0)]

_linspace(a, b, n) = n == 1 ? [a] : [a + (b - a) / (n - 1) * i for i in 0:n-1]

# 20-corner lambert_conformal_construction golden: (x, y, lon, lat), abs 1e-9.
const _CONSTRUCT_WRF = [
    (-2e6, -1.5e6, -116.10017801101773, 23.320805943967475),
    (-1e6, -1.5e6, -106.68789739792601, 24.883956953152033),
    (0.0, -1.5e6, -97.0, 25.415772540363083),
    (1e6, -1.5e6, -87.31210260207399, 24.883956953152033),
    (2e6, -1.5e6, -77.89982198898227, 23.320805943967475),
    (-2e6, -0.5e6, -118.62443079701725, 31.92388539661814),
    (-1e6, -0.5e6, -108.01300959338514, 33.76904204570805),
    (0.0, -0.5e6, -97.0, 34.39829502737979),
    (1e6, -0.5e6, -85.98699040661486, 33.76904204570805),
    (2e6, -0.5e6, -75.37556920298275, 31.92388539661814),
    (-2e6, 0.5e6, -121.89275561686046, 40.7292258345734),
    (-1e6, 0.5e6, -109.75450863032499, 42.90012555470361),
    (0.0, 0.5e6, -97.0, 43.64290686620447),
    (1e6, 0.5e6, -84.24549136967501, 42.90012555470361),
    (2e6, 0.5e6, -72.10724438313954, 40.7292258345734),
    (-2e6, 1.5e6, -126.27323349556194, 49.51039356753986),
    (-1e6, 1.5e6, -112.14243848502849, 52.06011386781491),
    (0.0, 1.5e6, -97.0, 52.93698916474947),
    (1e6, 1.5e6, -81.85756151497151, 52.06011386781491),
    (2e6, 1.5e6, -67.72676650443806, 49.51039356753986),
]

# A native data provider returning per-tick flat C-order fields (the JL-J2 e2e
# mock; provider protocol methods live in the data binding / a test mock).
mutable struct _NativeProv
    times::Vector{Float64}
    fields::Dict{Float64,Dict{String,Vector{Float64}}}
end
ESS.provider_refresh_times(p::_NativeProv) = p.times
ESS.provider_sample(p::_NativeProv, t::Real) = p.fields[Float64(t)]

@testset "C4 regrid driver (ess-14f.5, JL-J2)" begin

    # ========================================================================
    # reproject.jl
    # ========================================================================
    @testset "reproject: parse_proj_string" begin
        p = ESS.parse_proj_string(CAMPFIRE_SR)
        @test ESS.proj_text(p, "proj") == "lcc"
        @test ESS.proj_number(p, "lat_1") == 30.0
        @test ESS.proj_number(p, "lat_2") == 60.0
        @test ESS.proj_number(p, "lat_0") == 39.0
        @test ESS.proj_number(p, "lon_0") == -97.0
        @test ESS.proj_text(p, "datum") == "WGS84"
        @test p["no_defs"] === true
        @test ESS.proj_number(p, "x_0") == 0.0   # +x_0=0 parses as a number, not a flag
    end

    @testset "reproject: LCC inverse matches ESD construction golden (1e-9)" begin
        params = _wrf()
        for (x, y, glon, glat) in _CONSTRUCT_WRF
            lon, lat = ESS.lcc_inverse(x, y, params)
            @test abs(lon - glon) < 1e-9
            @test abs(lat - glat) < 1e-9
        end
    end

    @testset "reproject: LCC forward matches ESD reproject golden (rel 1e-7/abs 1e-4)" begin
        coords = [(-97.0, 39.0), (-120.0, 35.0), (-75.0, 40.0), (-90.0, 45.0),
                  (-100.0, 25.0), (-80.0, 48.0), (-110.0, 31.0), (-104.0, 42.5)]
        fwd_wrf = [(0.0, 0.43226828519254923),
                   (-2028208.5469169607, -140947.28851322923),
                   (1795192.9893785124, 356152.97854254674),
                   (530758.079019565, 668954.7596800169),
                   (-309853.2783964032, -1541532.7554675443),
                   (1213070.0930733175, 1097145.5185974697),
                   (-1228247.943920761, -773888.551179463),
                   (-554207.2432213802, 401411.8990695188)]
        fwd_nei = [(0.0, -110589.55965320487),
                   (-2066463.053651542, -290403.0815928243),
                   (1845776.3535729724, 224515.92418459523),
                   (549842.4483977046, 575299.4792623082),
                   (-309377.09304183396, -1668877.3176074345),
                   (1266623.2685378056, 1007635.9929630421),
                   (-1239963.1270495383, -909332.8255445026),
                   (-571190.8151147817, 298694.874228091)]
        approx_rel_abs(got, want) = abs(got - want) <= 1e-4 + 1e-7 * abs(want)
        for (params, golden) in ((_wrf(), fwd_wrf), (_nei(), fwd_nei))
            for ((lon, lat), (gx, gy)) in zip(coords, golden)
                x, y = ESS.lcc_forward(lon, lat, params)
                @test approx_rel_abs(x, gx)
                @test approx_rel_abs(y, gy)
            end
        end
    end

    @testset "reproject: roundtrip, central meridian, longlat identity, errors" begin
        xs = [-2e6, -1e6, 0.0, 1e6, 2e6]
        ys = [-1.5e6, 0.0, 1.5e6, 0.5e6, -0.5e6]
        for params in (_wrf(), _nei())
            cone = ESS.lcc_cone(params)
            for (x, y) in zip(xs, ys)
                lon, lat = ESS.lcc_inverse_cone(x, y, cone)
                x2, y2 = ESS.lcc_forward_cone(lon, lat, cone)
                @test abs(x2 - x) < 1e-6
                @test abs(y2 - y) < 1e-6
            end
            lon, _ = ESS.lcc_inverse(0.0, 0.5e6, params)   # central meridian → lon_0
            @test abs(lon - (-97.0)) < 1e-12
        end
        for sr in ("+proj=longlat +datum=WGS84", nothing, "")
            for (x, y) in ((-97.0, 39.0), (10.0, -20.0), (0.0, 0.0))
                @test ESS.reproject_xy_to_lonlat(x, y, sr) == (x, y)
            end
        end
        @test_throws ESS.RegridError ESS.reprojector_from_spatial_ref("+proj=merc +datum=WGS84")
        @test_throws ESS.RegridError ESS.lcc_cone(Dict{String,Any}("lon_0" => -97.0))
    end

    # ========================================================================
    # regrid_kernels.jl
    # ========================================================================
    @testset "kernels: locate_1d clamps and brackets" begin
        base, s = ESS.locate_1d([-1.0, 0.5, 2.0, 3.7, 9.0], [0.0, 1.0, 2.0, 3.0, 4.0])
        @test base == [1, 1, 3, 4, 4]
        @test isapprox(s, [0.0, 0.5, 0.0, 0.7, 1.0]; atol=1e-12)
    end

    @testset "kernels: bspline goldens (1e-12)" begin
        lin = ESS.bspline_regrid_linear_1d([2.0, 5.0, 8.0, 11.0, 14.0], [1, 2, 3, 4],
                                           [0.5, 0.5, 0.2999999999999998, 0.0])
        @test isapprox(lin, [3.5, 6.5, 8.899999999999999, 11.0]; atol=1e-12)

        cub = ESS.bspline_regrid_cubic_1d(
            [2.0, 1.5, 1.0, -0.10000000000000009, -2.4000000000000004, -6.5,
             -13.000000000000002], [1, 2, 3, 4], [0.5, 0.5, 0.2999999999999998, 0.0])
        @test isapprox(cub, [1.2875, 0.5625, -0.6367000000000003, -2.4000000000000004]; atol=1e-12)

        # f[r, c] == Rust Array2 row-major [[r-1, c-1]].
        f = [1.0 0.5 0.0 -0.5; 3.0 2.8 2.6 2.4; 5.0 5.1 5.2 5.3; 7.0 7.4 7.8 8.2]
        bil = ESS.bspline_regrid_bilinear_2d(f, [1, 2, 3, 2], [1, 3, 2, 1],
                                             [0.5, 0.5, 0.0, 0.19999999999999996],
                                             [0.5, 0.0, 0.30000000000000004, 0.7])
        @test isapprox(bil, [1.825, 3.9, 5.13, 3.3019999999999996]; atol=1e-12)
    end

    rect(x0, x1, y0, y1) = [x0 y0; x1 y0; x1 y1; x0 y1]
    src_polys() = [rect(0.0, 1.0, 0.0, 1.0), rect(1.0, 2.0, 0.0, 1.0), rect(2.0, 3.0, 0.0, 1.0)]
    tgt_polys() = [rect(0.0, 1.5, 0.0, 1.0), rect(1.5, 2.0, 0.0, 1.0), rect(2.0, 3.0, 0.0, 1.0)]

    @testset "kernels: conservative invariants planar" begin
        F_tgt, A, A_j = ESS.conservative_regrid([10.0, 20.0, 30.0], src_polys(), tgt_polys(),
                                                "planar", 1e-15)
        for j in eachindex(A_j)
            if A_j[j] > 0.0
                wsum = sum(A[i, j] / A_j[j] for i in axes(A, 1))
                @test abs(wsum - 1.0) < 1e-12             # partition of unity
            end
        end
        source_mass = sum(sum(A[i, j] for j in axes(A, 2)) * [10.0, 20.0, 30.0][i] for i in axes(A, 1))
        target_mass = sum(A_j[j] * F_tgt[j] for j in eachindex(A_j))
        @test abs(target_mass - source_mass) <= 1e-12 * abs(source_mass)
        @test isapprox(F_tgt, [40.0 / 3.0, 20.0, 30.0]; atol=1e-9)
    end

    @testset "kernels: conservative spherical invariants (GeometryOps clip)" begin
        # Julia's spherical area uses the closed-form excess; the absolute A_j may
        # differ from Rust's S2 golden across engines, so assert the manifold-
        # invariant properties (PoU, conservation, constant preservation) — the
        # primary cross-binding gate per CONFORMANCE_SPEC §5.8 — not the S2 literal.
        F_tgt, A, A_j = ESS.conservative_regrid([10.0, 20.0, 30.0], src_polys(), tgt_polys(),
                                                "spherical", 1e-15)
        for j in eachindex(A_j)
            if A_j[j] > 0.0
                @test abs(sum(A[i, j] / A_j[j] for i in axes(A, 1)) - 1.0) < 1e-12
            end
        end
        source_mass = sum(sum(A[i, j] for j in axes(A, 2)) * [10.0, 20.0, 30.0][i] for i in axes(A, 1))
        target_mass = sum(A_j[j] * F_tgt[j] for j in eachindex(A_j))
        @test abs(target_mass - source_mass) <= 1e-9 * abs(source_mass)
        # A constant field is preserved on every covered target cell.
        Fc, _, Ajc = ESS.conservative_regrid([5.0, 5.0, 5.0], src_polys(), tgt_polys(),
                                             "spherical", 1e-15)
        for j in eachindex(Ajc)
            Ajc[j] > 0.0 && @test isapprox(Fc[j], 5.0; atol=1e-9)
        end
    end

    @testset "kernels: cell_average golden (exact)" begin
        got = ESS.cell_average_regrid([10.0, 20.0, 30.0], [0.3, 0.7, 1.5], [0.5, 0.2, 0.5],
                                      [0.0, 1.0, 2.0], [0.0, 0.0, 0.0], 1.0, 1.0, -999.0)
        @test got == [15.0, 30.0, -999.0]
    end

    # ========================================================================
    # regrid_driver.jl
    # ========================================================================
    @testset "driver: build_target_grid campfire surface" begin
        tg = ESS.build_target_grid(_campfire_dims(), CAMPFIRE_SR)
        @test tg.dims == ["x", "y"]
        @test tg.shape == [19, 21]
        @test length(tg.corner_rings) == 19 * 21
        @test size(tg.corner_rings[1]) == (4, 2)
        @test -122.0 < minimum(tg.center_lon) && maximum(tg.center_lon) < -121.0
        @test 39.0 < minimum(tg.center_lat) && maximum(tg.center_lat) < 40.5
    end

    @testset "driver: build_target_grid_from_domain matches explicit" begin
        domain = ESS.Domain(spatial=Dict{String,Any}(
            "x" => Dict("min" => -2026020.2, "max" => -1990020.2, "grid_spacing" => 2000.0),
            "y" => Dict("min" => 374725.0, "max" => 414725.0, "grid_spacing" => 2000.0)))
        tg = ESS.build_target_grid_from_domain(domain, CAMPFIRE_SR)
        explicit = ESS.build_target_grid(_campfire_dims(), CAMPFIRE_SR)
        @test tg.shape == explicit.shape
        @test tg.center_lon == explicit.center_lon
        @test tg.center_lat == explicit.center_lat
    end

    @testset "driver: edges_from_centers reflects ends; lev_min golden" begin
        @test ESS.edges_from_centers([0.0, 1.0, 2.0, 3.0]) == [-0.5, 0.5, 1.5, 2.5, 3.5]

        # (i, j, lev) row-major data; reduce on lev axis (3); min lev value 1.0 at index 2.
        data = [111.0, 112, 113, 121, 122, 123, 211, 212, 213, 221, 222, 223]
        f3 = Array{Float64}(undef, 2, 2, 3)
        for i in 0:1, j in 0:1, k in 0:2
            f3[i+1, j+1, k+1] = data[i * 6 + j * 3 + k + 1]
        end
        surf = ESS.lev_min_reduce(f3, [3.0, 1.0, 2.0], 3)
        @test size(surf) == (2, 2)
        @test surf == [112.0 122.0; 212.0 222.0]
    end

    # A field linear in lon/lat, reproduced exactly by bilinear sampling.
    function _linear_source(src_lon, src_lat)
        nlat = length(src_lat); nlon = length(src_lon)
        [2.0 * src_lon[b] + 3.0 * src_lat[a] for a in 1:nlat, b in 1:nlon]
    end

    @testset "driver: regrid pipeline bspline linear exact (1e-9)" begin
        tg = ESS.build_target_grid(_campfire_dims(), CAMPFIRE_SR)
        src_lon = _linspace(minimum(tg.center_lon) - 0.1, maximum(tg.center_lon) + 0.1, 6)
        src_lat = _linspace(minimum(tg.center_lat) - 0.1, maximum(tg.center_lat) + 0.1, 5)
        field = _linear_source(src_lon, src_lat)
        out = ESS.regrid_field(field, src_lon, src_lat, tg, "bspline")
        @test length(out) == length(tg.center_lon)
        for k in eachindex(out)
            @test abs(out[k] - (2.0 * tg.center_lon[k] + 3.0 * tg.center_lat[k])) < 1e-9
        end
    end

    @testset "driver: regrid pipeline 3D lev=min then bspline (1e-9)" begin
        tg = ESS.build_target_grid(_campfire_dims(), CAMPFIRE_SR)
        src_lon = _linspace(minimum(tg.center_lon) - 0.1, maximum(tg.center_lon) + 0.1, 6)
        src_lat = _linspace(minimum(tg.center_lat) - 0.1, maximum(tg.center_lat) + 0.1, 5)
        base = _linear_source(src_lon, src_lat)        # surface (min-lev) slice
        nlat = length(src_lat); nlon = length(src_lon)
        # (lev=3, lat, lon) ascending lev; surface (min lev) is slice 1 == base.
        f3 = Array{Float64}(undef, 3, nlat, nlon)
        for l in 1:3, a in 1:nlat, b in 1:nlon
            f3[l, a, b] = base[a, b] + 100.0 * (l - 1)
        end
        out = ESS.regrid_loader_field(f3, src_lon, src_lat, tg, "bspline";
                                      lev_coord=[1.0, 2.0, 3.0], lev_axis=1)
        for k in eachindex(out)
            @test abs(out[k] - (2.0 * tg.center_lon[k] + 3.0 * tg.center_lat[k])) < 1e-9
        end
    end

    @testset "driver: regrid pipeline conservative preserves constant (1e-9)" begin
        tg = ESS.build_target_grid(_campfire_dims(), CAMPFIRE_SR)
        src_lon = _linspace(minimum(tg.center_lon) - 0.1, maximum(tg.center_lon) + 0.1, 6)
        src_lat = _linspace(minimum(tg.center_lat) - 0.1, maximum(tg.center_lat) + 0.1, 5)
        field = fill(288.0, length(src_lat), length(src_lon))
        out = ESS.regrid_field(field, src_lon, src_lat, tg, "conservative")
        @test count(!=(0.0), out) == length(out)        # every target cell covered
        for v in out
            @test abs(v - 288.0) < 1e-9
        end
    end

    # ========================================================================
    # ESDRegrid applier (the JL-J2 consumer seam; geometry cached once)
    # ========================================================================
    @testset "ESDRegrid: bspline applier reproduces a linear field in place" begin
        tg = ESS.build_target_grid(_campfire_dims(), CAMPFIRE_SR)
        src_lon = _linspace(minimum(tg.center_lon) - 0.1, maximum(tg.center_lon) + 0.1, 6)
        src_lat = _linspace(minimum(tg.center_lat) - 0.1, maximum(tg.center_lat) + 0.1, 5)
        applier = ESDRegrid(tg, src_lon, src_lat; methods=Dict("wind" => "bspline"))
        # Native field flat in C-order [lat, lon].
        field = _linear_source(src_lon, src_lat)
        flat = [field[a, b] for a in axes(field, 1) for b in axes(field, 2)]
        buf = zeros(tg.shape[1], tg.shape[2])
        ret = apply_regrid!(applier, buf, "wind", Dict("wind" => flat))
        @test ret === buf                                # mutated in place, not rebound
        for i in 1:tg.shape[1], j in 1:tg.shape[2]
            k = (i - 1) * tg.shape[2] + j                # C-order index of cell (i, j)
            @test abs(buf[i, j] - (2.0 * tg.center_lon[k] + 3.0 * tg.center_lat[k])) < 1e-9
        end
    end

    @testset "ESDRegrid: conservative applier preserves a constant; geometry cached once" begin
        tg = ESS.build_target_grid(_campfire_dims(), CAMPFIRE_SR)
        src_lon = _linspace(minimum(tg.center_lon) - 0.1, maximum(tg.center_lon) + 0.1, 6)
        src_lat = _linspace(minimum(tg.center_lat) - 0.1, maximum(tg.center_lat) + 0.1, 5)
        applier = ESDRegrid(tg, src_lon, src_lat; methods=Dict("t" => "conservative"))
        # The overlap matrix is built at setup; refresh is the cheap matvec.
        @test applier.conservative !== nothing
        @test size(applier.conservative.A) == (length(src_lat) * length(src_lon), length(tg.center_lon))
        flat = fill(288.0, length(src_lat) * length(src_lon))
        buf = zeros(tg.shape[1] * tg.shape[2])           # 1-D buffer, column-major over (n0, n1)
        apply_regrid!(applier, buf, "t", Dict("t" => flat))
        @test all(v -> abs(v - 288.0) < 1e-9, buf)
        # A second refresh reuses the cached geometry and tracks the new values.
        apply_regrid!(applier, buf, "t", Dict("t" => fill(300.0, length(flat))))
        @test all(v -> abs(v - 300.0) < 1e-9, buf)
    end

    @testset "ESDRegrid: 3D lev=min applier; RegridSpec constructor; cell_average" begin
        tg = ESS.build_target_grid(_campfire_dims(), CAMPFIRE_SR)
        src_lon = _linspace(minimum(tg.center_lon) - 0.1, maximum(tg.center_lon) + 0.1, 6)
        src_lat = _linspace(minimum(tg.center_lat) - 0.1, maximum(tg.center_lat) + 0.1, 5)
        nlat = length(src_lat); nlon = length(src_lon)
        base = _linear_source(src_lon, src_lat)
        # Build a 3-D native field, flat C-order [lev, lat, lon].
        flat3 = Float64[]
        for l in 1:3, a in 1:nlat, b in 1:nlon
            push!(flat3, base[a, b] + 100.0 * (l - 1))
        end
        # Drive via the RegridSpec convenience constructor.
        specs = Dict("q" => ESS.RegridSpec(method="bspline"))
        applier = ESDRegrid(tg, src_lon, src_lat, specs; lev_coords=Dict("q" => [1.0, 2.0, 3.0]))
        buf = zeros(tg.shape[1], tg.shape[2])
        apply_regrid!(applier, buf, "q", Dict("q" => flat3))
        for i in 1:tg.shape[1], j in 1:tg.shape[2]
            k = (i - 1) * tg.shape[2] + j
            @test abs(buf[i, j] - (2.0 * tg.center_lon[k] + 3.0 * tg.center_lat[k])) < 1e-9
        end

        # cell_average through the applier matches the direct kernel.
        ca = ESDRegrid(tg, src_lon, src_lat; methods=Dict("p" => "cell_average"),
                       missing_values=Dict("p" => -999.0))
        field = _linear_source(src_lon, src_lat)
        flat = [field[a, b] for a in 1:nlat for b in 1:nlon]
        buf2 = zeros(tg.shape[1] * tg.shape[2])
        apply_regrid!(ca, buf2, "p", Dict("p" => flat))
        direct = ESS.regrid_field(field, src_lon, src_lat, tg, "cell_average"; missing_value=-999.0)
        buf2m = reshape(buf2, tg.shape[1], tg.shape[2])
        for i in 1:tg.shape[1], j in 1:tg.shape[2]
            k = (i - 1) * tg.shape[2] + j
            @test buf2m[i, j] == direct[k]
        end
    end

    @testset "ESDRegrid: guards" begin
        tg = ESS.build_target_grid(_campfire_dims(), CAMPFIRE_SR)
        src_lon = _linspace(minimum(tg.center_lon) - 0.1, maximum(tg.center_lon) + 0.1, 6)
        src_lat = _linspace(minimum(tg.center_lat) - 0.1, maximum(tg.center_lat) + 0.1, 5)
        applier = ESDRegrid(tg, src_lon, src_lat; methods=Dict("wind" => "bspline"))
        # No method configured for a variable.
        @test_throws RefreshError apply_regrid!(applier, zeros(tg.shape...), "other",
                                                Dict("other" => zeros(30)))
        # Native field with the wrong element count.
        @test_throws RefreshError apply_regrid!(applier, zeros(tg.shape...), "wind",
                                                Dict("wind" => zeros(7)))
        # Buffer size mismatch.
        @test_throws RefreshError apply_regrid!(applier, zeros(5), "wind",
                                                Dict("wind" => zeros(length(src_lat) * length(src_lon))))
        # Unknown method at construction.
        @test_throws ESS.RegridError ESDRegrid(tg, src_lon, src_lat; methods=Dict("v" => "nope"))
    end

    @testset "ESDRegrid: drives build_refresh_callback at cadence (e2e)" begin
        # A small 2x2 sim grid fed by an identity-projection ESDRegrid: the native
        # 2x2 field is conservatively regridded onto the 2x2 target and refreshed at
        # cadence anchors, driving an honest Tsit5 solve. D(y) = sum of the four
        # forcing cells; with piecewise-constant forcing the integral is exact.
        dims = ["x" => ESS.SpatialDim(0.0, 1.0, 1.0), "y" => ESS.SpatialDim(0.0, 1.0, 1.0)]
        tg = ESS.build_target_grid(dims, nothing)        # identity (longlat) reprojection
        @test tg.shape == [2, 2]
        # Source grid = target centers, so conservative regrid is ~identity per cell.
        applier = ESDRegrid(tg, tg.centers["x"], tg.centers["y"]; methods=Dict("forcing" => "conservative"))

        _n(x) = NumExpr(Float64(x))
        _i(x) = IntExpr(Int64(x))
        _v(s) = VarExpr(String(s))
        _op(o, a...; k...) = OpExpr(String(o), ESS.Expr[a...]; k...)
        _idx(v, is...) = _op("index", _v(v), is...)
        _D(v) = _op("D", _v(v); wrt="t")
        # D(y) = forcing[1]+forcing[2]+forcing[3]+forcing[4]  (the four buffer cells)
        rhs = _op("+", _op("+", _idx("forcing", _i(1)), _idx("forcing", _i(2))),
                  _op("+", _idx("forcing", _i(3)), _idx("forcing", _i(4))))
        model = ESS.Model(Dict("y" => ModelVariable(StateVariable)), [ESS.Equation(_D("y"), rhs)])
        buf = ones(4)                                     # 1-D buffer over the 2x2 grid
        f!, u0, p, _ts, vm = build_evaluator(model;
            initial_conditions=Dict("y" => 0.0), param_arrays=Dict("forcing" => buf))

        # Native samples (flat C-order [lat, lon]) refreshed at t=1, 2.
        prov = _NativeProv([1.0, 2.0], Dict(
            1.0 => Dict("forcing" => [2.0, 2.0, 2.0, 2.0]),   # each cell 2  → sum 8
            2.0 => Dict("forcing" => [3.0, 3.0, 3.0, 3.0])))  # each cell 3  → sum 12

        cb, tstops = build_refresh_callback(model;
            providers=Dict("forcing" => prov),
            buffers=RefreshBuffers(Dict("forcing" => buf)), regrid=applier)
        @test tstops == [1.0, 2.0]

        prob = ODE.ODEProblem(f!, u0, (0.0, 3.0), p)
        sol = ODE.solve(prob, ODE.Tsit5(); callback=cb, tstops=tstops)
        @test sol.retcode == ODE.SciMLBase.ReturnCode.Success
        # ∫ = 4·[0,1) + 8·[1,2) + 12·[2,3] = 4 + 8 + 12 = 24
        @test isapprox(sol.u[end][vm["y"]], 24.0; atol=1e-8)
        @test buf ≈ fill(3.0, 4)                          # holds the last refreshed values
    end
end
