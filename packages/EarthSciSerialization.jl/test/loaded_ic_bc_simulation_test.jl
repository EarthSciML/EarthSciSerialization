# End-to-end simulation of the worked scoped-reference-`ic` fixture
# `tests/valid/advection_reaction_loaded_ic_bc.esm` through the Julia tree-walk
# runner (`EarthSciSerialization.simulate`).
#
# What this exercises:
#   * A REAL `reaction_systems` Chemistry (O3/NO/NO2, R1/R2) lowered to generic
#     per-species ODEs, then SPATIALLY LIFTED onto the 4×2 lon/lat grid by
#     `operator_compose(Chemistry, Advection)` + `lifting:"pointwise"`. The
#     flattener's pointwise lift (`_apply_pointwise_lift!`) array-ifies the merged
#     reaction+advection state ODEs so the reaction network runs per grid cell.
#   * SCOPED-REFERENCE `ic` resolution (spec §11.4.1): `ChemistryICs` hosts
#     `ic(Chemistry.O3) ~ InitialConditions.O3_init` (and NO, NO2). Each target is
#     the grid-shaped (lifted) reaction species, and each RHS is a LOADED FIELD.
#     `build_evaluator` (`_resolve_field_ic`) folds the loaded [lon,lat] field into
#     u0 cell-by-cell — the star feature.
#   * Per-species, two-arg `grad(f, inflow, dim:lon)` templates (loaded Dirichlet
#     western inflow, one distinct field per species) lowered to makearray at load.
#
# The loaded fields (initial conditions, per-species inflow, wind) are supplied
# here as `const_arrays`, standing in for the data loaders declared in the
# fixture. The reaction system's own inline `tests` block is the source of truth:
# this runner executes every assertion in it.
using Test
using EarthSciSerialization
import OrdinaryDiffEqTsit5: Tsit5
const _ESS_IC = EarthSciSerialization

# Loaded fields for the run (see the fixture's `data_loaders`). [lon,lat] = [4,2];
# Julia column-major, so row = lon index, column = lat index.
const _LOADED_CONST_ARRAYS = Dict{String,Any}(
    # Initial-condition fields — RHS of the scoped-reference `ic` equations. Keyed
    # by the loader-qualified names used in the `ic` RHS.
    "InitialConditions.O3_init"  => [38.0 42.0; 39.0 43.0; 41.0 45.0; 43.0 47.0],
    "InitialConditions.NO_init"  => [0.10 0.12; 0.11 0.13; 0.09 0.14; 0.12 0.15],
    "InitialConditions.NO2_init" => [1.0  1.2;  1.1  1.3;  0.9  1.4;  1.2  1.5],
    # Meteorology wind field bound to the grid-shaped Advection parameter.
    "Advection.u_wind" => [2.0 2.2; 2.1 2.3; 2.2 2.4; 2.3 2.5],
    # Per-species western-inflow fields (shaped over the lat boundary).
    "Advection.O3_inflow"  => [35.0, 36.0],
    "Advection.NO_inflow"  => [0.20, 0.25],
    "Advection.NO2_inflow" => [1.5, 1.6],
)

# Resolve (rel, abs) precedence: assertion → test → model (unset field = 0).
function _ic_bc_resolve_tol(model_tol, test_tol, assertion_tol)
    for cand in (assertion_tol, test_tol, model_tol)
        cand === nothing && continue
        r = cand.rel === nothing ? 0.0 : cand.rel
        a = cand.abs === nothing ? 0.0 : cand.abs
        return (r, a)
    end
    return (1.0e-6, 0.0)
end

# Index of `t` in the saved time grid (exact match; the run `saveat`s the
# assertion times so a stored point exists).
function _time_index(times::Vector{Float64}, t::Float64)
    for (i, tv) in enumerate(times)
        isapprox(tv, t; atol = 1e-9) && return i
    end
    error("no saved time point at t=$t (saved: $times)")
end

@testset "advection_reaction_loaded_ic_bc.esm — scoped-ref ic + loaded BC simulation" begin
    fixture = joinpath(@__DIR__, "..", "..", "..", "tests", "valid",
                       "advection_reaction_loaded_ic_bc.esm")
    @test isfile(fixture)

    file = _ESS_IC.load(fixture)
    # The lifted reaction network's `tests` block lives on the reaction system.
    chem = file.reaction_systems["Chemistry"]
    @test !isempty(chem.tests)

    for t in chem.tests
        @testset "$(t.id)" begin
            # `saveat` the exact assertion times so each is a stored point.
            atimes = sort!(unique(Float64[a.time for a in t.assertions]))
            tspan = (t.time_span.start, t.time_span.stop)

            r = _ESS_IC.simulate(fixture, tspan; alg = Tsit5(),
                                 const_arrays = _LOADED_CONST_ARRAYS,
                                 reltol = 1e-9, abstol = 1e-11,
                                 saveat = atimes)
            @test r.success && r.retcode == :Success

            for a in t.assertions
                # `a.variable` is model-local (e.g. "O3[1,1]"); the flattened /
                # simulated element is namespaced under the Chemistry model.
                key = "Chemistry." * a.variable
                @test haskey(r.var_map, key)
                ti = _time_index(r.t, Float64(a.time))
                actual = r[key][ti]
                rel, abs_ = _ic_bc_resolve_tol(chem.tolerance, t.tolerance, a.tolerance)
                if rel > 0
                    @test isapprox(actual, a.expected; rtol = rel, atol = abs_)
                else
                    @test isapprox(actual, a.expected; atol = abs_)
                end
            end
        end
    end
end
