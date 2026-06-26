# End-to-end + zero-alloc + cadence loader-refresh tests (ess-14f.6, JL-J3).
#
# JL-J1 (ess-14f.4) built `build_refresh_callback` — the `PresetTimeCallback`
# whose `affect!` samples a Provider, regrids, and writes the live forcing buffer
# in place. JL-J2 (ess-14f.5) built `ESDRegrid` — the reproject + per-method
# regrid applier that lands a provider's RAW native arrays on the sim grid. J3 is
# the INTEGRATION layer: it composes the library's exposed pieces — `build_evaluator`
# (the RHS), `build_refresh_callback` (the cadence callback + tstops), and an
# applier — into an honest `solve(prob, Tsit5(); callback, tstops)` over a loaded
# fixture, and asserts the cadence contract end to end.
#
# It is the Julia sibling of the Rust driver-level harness `segmented_refresh_solve`
# (ess-14f.11) and the Python e2e (ess-2fy). Julia's idiom differs: where the Rust
# driver runs a manual segment-by-segment loop, Julia hands the user a single
# `PresetTimeCallback` + tstops and runs ONE `solve` — the `affect!` fires the
# refresh at each cadence anchor. So this file is, like the Rust one, a documented
# integration test that exercises the consumer surface; it adds NO library API
# (`[[library-exposes-rhs-not-solver]]` holds — the solver is a test-only dep).
#
# Acceptance clauses (bead ess-14f.6) and where each is pinned:
#   • e2e refresh over a fixture — a coupled, discretized, non-PDE forced model is
#     LOADED from `fixtures/refresh/coupled_forced.esm`, wired to a Provider + an
#     applier, and integrated; the coupled closed form is matched to solver tol
#     (testset 1, and the full reproject+regrid path in testset 4).
#   • refresh-once-per-boundary — the Provider is sampled EXACTLY once per cadence
#     anchor and never between, even under many interior solver steps (testset 2;
#     also counted in testset 4).
#   • zero-alloc within a segment — the hot per-step RHS allocates nothing, before
#     AND after a real in-place refresh driven through the callback (testset 3).
#   • CONST/DISCRETE covered — a CONST provider contributes no tstops and is never
#     sampled (materialize-once); a DISCRETE provider refreshes at its anchors;
#     both appear in one scenario (testset 2), with CONST `scale` + DISCRETE `src`
#     also driving the e2e fixture (testset 1).
#
# Offline only: every Provider is an in-memory mock (no network, the CI contract).

using Test
using EarthSciSerialization
using DiffEqCallbacks            # loads EarthSciSerializationDataRefreshExt
using SciMLBase                  # ext co-trigger (u_modified!)
import OrdinaryDiffEqTsit5 as ODE  # Tsit5 + ODEProblem + solve (test-only solver dep)

include("zero_alloc_harness.jl")  # rhs_alloc_bytes — the JL-J0 zero-alloc probe

const ESM = EarthSciSerialization

_refresh_fixture(name) = joinpath(@__DIR__, "fixtures", "refresh", name)

# A mock Provider that LOGS every sample. A DISCRETE provider has non-empty
# `times` and a per-tick (var => field) table; a CONST provider has empty `times`
# (so `provider_is_const` is true, it contributes no tstops, and the callback
# never samples it). `samples` records the `t` of every `provider_sample` call so
# the cadence tests can assert exactly-once-per-boundary and never-in-between.
mutable struct _RefreshLogProvider
    times::Vector{Float64}
    fields::Dict{Float64,Dict{String,Vector{Float64}}}
    samples::Vector{Float64}
end
_RefreshLogProvider(times, fields) =
    _RefreshLogProvider(Float64[t for t in times], fields, Float64[])
ESM.provider_refresh_times(p::_RefreshLogProvider) = p.times
function ESM.provider_sample(p::_RefreshLogProvider, t::Real)
    push!(p.samples, Float64(t))
    tf = Float64(t)
    haskey(p.fields, tf) ||
        error("_RefreshLogProvider has no sample for t=$tf (have $(sort!(collect(keys(p.fields)))))")
    return p.fields[tf]
end

# Scalar initial conditions over the coupled fixture's two 3-cell array states.
function _coupled_ics()
    ics = Dict{String,Float64}()
    for k in 1:3
        ics["c[$k]"] = 0.0
        ics["d[$k]"] = 0.0
    end
    return ics
end

@testset "loader-refresh e2e + zero-alloc + cadence (ess-14f.6, JL-J3)" begin

    @testset "e2e: coupled forced model over a fixture matches the closed form" begin
        # The fixture (loaded, not hand-built): two coupled states over i ∈ [1,3].
        #   D(c[i]) = scale[i]·src[i]   (scale CONST → const_arrays; src DISCRETE → live buffer)
        #   D(d[i]) = c[i]              (coupling: d integrates the forced tracer)
        # Forcing is piecewise-constant per segment, so the run is exact to solver tol.
        file = EarthSciSerialization.load(_refresh_fixture("coupled_forced.esm"))
        @test file isa EarthSciSerialization.EsmFile
        model = file.models["M"]

        scale  = [1.0, 2.0, 3.0]          # CONST factor — materialized once at build
        srcbuf = [1.0, 1.0, 1.0]          # DISCRETE live buffer — the [0,1) segment value
        f!, u0, p, _ts, vm = build_evaluator(file;
            initial_conditions=_coupled_ics(),
            const_arrays=Dict("scale" => scale),    # CONST: inlined once (no tstops)
            param_arrays =Dict("src"  => srcbuf))   # DISCRETE: aliased, refreshed live

        prov = _RefreshLogProvider([1.0, 2.0], Dict(
            1.0 => Dict("src" => [2.0, 2.0, 2.0]),
            2.0 => Dict("src" => [3.0, 3.0, 3.0])))
        cb, tstops = build_refresh_callback(model;
            providers=Dict("src" => prov),
            buffers  =RefreshBuffers(Dict("src" => srcbuf)),   # SAME buffer object as param_arrays
            regrid   =IdentityRegrid())                        # native already on the sim grid
        @test tstops == [1.0, 2.0]

        prob = ODE.ODEProblem(f!, u0, (0.0, 3.0), p)
        sol  = ODE.solve(prob, ODE.Tsit5(); callback=cb, tstops=tstops)
        @test sol.retcode == ODE.SciMLBase.ReturnCode.Success

        # rate r_k = scale .* src_k:  r0=[1,2,3], r1=[2,4,6], r2=[3,6,9].
        #   c(3) = r0+r1+r2 = [6,12,18]                       (accumulated forced source)
        #   d(3) = 2.5·r0 + 1.5·r1 + 0.5·r2 = [7,14,21]       (coupled integral of c)
        c = [sol.u[end][vm["c[$k]"]] for k in 1:3]
        d = [sol.u[end][vm["d[$k]"]] for k in 1:3]
        @test isapprox(c, [6.0, 12.0, 18.0]; atol=1e-7)
        @test isapprox(d, [7.0, 14.0, 21.0]; atol=1e-7)   # dependent var recomputes from the refreshed buffer
        @test srcbuf == [3.0, 3.0, 3.0]                   # buffer holds the LAST refresh (in place, not realloc)
    end

    @testset "cadence: CONST materialized once; DISCRETE once per boundary, no-op between" begin
        # The Julia mirror of Rust's const_materialized_once_discrete_refreshed_once_per_boundary.
        file  = EarthSciSerialization.load(_refresh_fixture("coupled_forced.esm"))
        model = file.models["M"]
        scale  = [1.0, 2.0, 3.0]
        srcbuf = [1.0, 1.0, 1.0]
        f!, u0, p, _ts, _vm = build_evaluator(file;
            initial_conditions=_coupled_ics(),
            const_arrays=Dict("scale" => scale),
            param_arrays =Dict("src"  => srcbuf))

        # DISCRETE `src`: refreshes at THREE interior anchors.
        disc = _RefreshLogProvider([1.0, 2.0, 3.0], Dict(
            1.0 => Dict("src" => [2.0, 2.0, 2.0]),
            2.0 => Dict("src" => [3.0, 3.0, 3.0]),
            3.0 => Dict("src" => [4.0, 4.0, 4.0])))
        # CONST `scale`: empty refresh_times ⇒ provider_is_const ⇒ contributes no
        # tstops, is dropped from the callback, and is never sampled during the
        # solve (the materialize-once-at-setup witness). It need NOT be a buffer:
        # _group_discrete_providers drops CONST providers before the buffer check.
        const_scale = _RefreshLogProvider(Float64[], Dict{Float64,Dict{String,Vector{Float64}}}())
        @test provider_is_const(const_scale)

        cb, tstops = build_refresh_callback(model;
            providers=Dict("src" => disc, "scale" => const_scale),
            buffers  =RefreshBuffers(Dict("src" => srcbuf)))
        @test tstops == [1.0, 2.0, 3.0]   # union of the DISCRETE anchors; the CONST provider adds none

        # Cap the step size so the solver takes MANY interior steps. The affect
        # must still fire only at the anchors (no-op between) — proving the refresh
        # is cadence-driven, not per-step.
        prob = ODE.ODEProblem(f!, u0, (0.0, 4.0), p)
        sol  = ODE.solve(prob, ODE.Tsit5(); callback=cb, tstops=tstops, dtmax=0.1)
        @test sol.retcode == ODE.SciMLBase.ReturnCode.Success
        @test length(sol.t) >= 30                 # genuinely many steps within the window

        @test isempty(const_scale.samples)        # CONST: never sampled during the solve
        @test disc.samples == [1.0, 2.0, 3.0]     # DISCRETE: exactly once per boundary, in order
        @test length(disc.samples) == length(tstops)   # one sample per anchor — not per step
        @test srcbuf == [4.0, 4.0, 4.0]           # the refreshes did land (last anchor's value)
    end

    @testset "zero-alloc: per-step RHS allocates nothing, before and after a real refresh" begin
        # The hot per-step path only READS the live buffer, so it must allocate
        # nothing — both before any refresh and after one driven through the full
        # callback machinery (sample → regrid → buf .=), which mutates in place.
        file  = EarthSciSerialization.load(_refresh_fixture("coupled_forced.esm"))
        model = file.models["M"]
        scale  = [1.0, 2.0, 3.0]
        srcbuf = [1.0, 1.0, 1.0]
        f!, u0, p, _ts, _vm = build_evaluator(file;
            initial_conditions=_coupled_ics(),
            const_arrays=Dict("scale" => scale),
            param_arrays =Dict("src"  => srcbuf))
        du = similar(u0)

        @test rhs_alloc_bytes(f!, du, u0, p, 0.0) == 0   # before any refresh

        # Drive an honest solve across a boundary: the callback's affect! performs
        # a real in-place refresh through the machinery, not a hand-poked buffer.
        prov = _RefreshLogProvider([1.0], Dict(1.0 => Dict("src" => [9.0, 9.0, 9.0])))
        cb, tstops = build_refresh_callback(model;
            providers=Dict("src" => prov),
            buffers  =RefreshBuffers(Dict("src" => srcbuf)))
        prob = ODE.ODEProblem(f!, u0, (0.0, 1.5), p)
        sol  = ODE.solve(prob, ODE.Tsit5(); callback=cb, tstops=tstops)
        @test sol.retcode == ODE.SciMLBase.ReturnCode.Success
        @test prov.samples == [1.0]
        @test srcbuf == [9.0, 9.0, 9.0]                  # the buffer was genuinely refreshed in place

        # Still zero-alloc after the real refresh: the refresh happened at the
        # boundary (the affect), never on the per-step path.
        @test rhs_alloc_bytes(f!, du, sol.u[end], p, 1.5) == 0
    end

    @testset "e2e: full ESD regrid path (reproject + regrid) refreshes at cadence, once per boundary" begin
        # The complete provider → callback → REGRID → buffer → RHS path with a real
        # ESDRegrid (campfire LCC surface + conservative overlap remap), driven at
        # cadence. The native field is spatially CONSTANT per segment; conservative
        # regrid preserves a constant exactly on every covered cell (JL-J2), so the
        # forcing each cell sees is that segment's constant and the integral is closed-form.
        CAMPFIRE_SR = "+proj=lcc +lat_1=30.0 +lat_2=60.0 +lat_0=39.0 +lon_0=-97.0 " *
                      "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
        dims = ["x" => ESM.SpatialDim(-2_026_020.2, -1_990_020.2, 2000.0),
                "y" => ESM.SpatialDim(374_725.0, 414_725.0, 2000.0)]
        tg = ESM.build_target_grid(dims, CAMPFIRE_SR)
        ncell = tg.shape[1] * tg.shape[2]

        # Native source grid spanning the target so every target cell is covered.
        _lin(a, b, n) = n == 1 ? [a] : [a + (b - a) / (n - 1) * i for i in 0:n-1]
        src_lon = _lin(minimum(tg.center_lon) - 0.1, maximum(tg.center_lon) + 0.1, 6)
        src_lat = _lin(minimum(tg.center_lat) - 0.1, maximum(tg.center_lat) + 0.1, 5)
        nsrc = length(src_lat) * length(src_lon)
        applier = ESDRegrid(tg, src_lon, src_lat; methods=Dict("wind" => "conservative"))

        # A scalar model reading one regridded cell: D(y) = wind[1]. Because the
        # field is spatially constant per segment, wind[1] equals that constant.
        _v(s)  = VarExpr(String(s))
        _i(x)  = IntExpr(Int64(x))
        _op(o, a...; k...) = OpExpr(String(o), ESM.Expr[a...]; k...)
        _idx(v, is...) = _op("index", _v(v), is...)
        _D(v)  = _op("D", _v(v); wrt="t")
        model = ESM.Model(Dict("y" => ModelVariable(StateVariable)),
            [ESM.Equation(_D("y"), _idx("wind", _i(1)))])
        buf = zeros(ncell)                       # 1-D forcing buffer over the (19,21) sim grid
        f!, u0, p, _ts, vm = build_evaluator(model;
            initial_conditions=Dict("y" => 0.0), param_arrays=Dict("wind" => buf))

        # Materialize the [0,1) field at setup (the consumer's initial load via the
        # SAME applier), then refresh at the interior anchors t=1, 2.
        C0, C1, C2 = 10.0, 25.0, 40.0
        apply_regrid!(applier, buf, "wind", Dict("wind" => fill(C0, nsrc)))
        @test all(v -> isapprox(v, C0; atol=1e-9), buf)   # the regrid filled every sim cell

        prov = _RefreshLogProvider([1.0, 2.0], Dict(
            1.0 => Dict("wind" => fill(C1, nsrc)),
            2.0 => Dict("wind" => fill(C2, nsrc))))
        cb, tstops = build_refresh_callback(model;
            providers=Dict("wind" => prov),
            buffers  =RefreshBuffers(Dict("wind" => buf)),
            regrid   =applier)
        @test tstops == [1.0, 2.0]

        prob = ODE.ODEProblem(f!, u0, (0.0, 3.0), p)
        sol  = ODE.solve(prob, ODE.Tsit5(); callback=cb, tstops=tstops)
        @test sol.retcode == ODE.SciMLBase.ReturnCode.Success
        @test prov.samples == [1.0, 2.0]                  # one provider sample per cadence boundary
        # ∫ = C0·[0,1) + C1·[1,2) + C2·[2,3] = 10 + 25 + 40 = 75
        @test isapprox(sol.u[end][vm["y"]], C0 + C1 + C2; atol=1e-6)
        @test all(v -> isapprox(v, C2; atol=1e-9), buf)   # whole 2-D buffer holds the last regridded constant
    end
end
