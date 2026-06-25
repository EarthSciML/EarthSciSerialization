# Space- and time-varying boundary-condition VALUES (ess-x1w).
#
# Feasibility verdict (declarative-or-fail gate — both sub-cases feasible over
# EXISTING vocabulary; no new primitive, no imperative BC path):
#
#   * TEMPORAL  value=g(t):  works with ZERO discretizer change. `t` is a free
#     symbol (tree-walk _NK_TIME; MTK independent var) supplied by the
#     integrator. A BC value is canonicalized by `_discretize_bc!`, stashed
#     value-agnostically on `bc["value"]`, and spliced into the per-cell
#     makearray boundary region by `_apply_makearray_bcs!`; `t` resolves per
#     evaluation time.
#
#   * SPATIAL   value=f(x):  reuses the IC coordinate-binding vocabulary. The
#     value already flows value-agnostically into the per-cell boundary region;
#     the only gap was that a BARE coordinate symbol is unbound at eval time.
#     `_apply_makearray_bcs!` now rewrites each coordinate symbol to
#     `index(coord_<dim>, <loop_idx>)` (the SAME substitution
#     `_try_materialize_ic_arrayop!` applies to initialization RHSs), so the
#     single-cell boundary region binds the loop index and the `coord_<dim>`
#     const_array of cell centers is read at the boundary/corner cell.
#
# Value-agnostic ⇒ kind-agnostic: the substitution runs on the already-rewritten
# ghost, so a coordinate/time term in a dirichlet value, a neumann flux value,
# or a robin gamma coefficient all resolve identically (the ESD *_bc.json ghost
# rules — external to this repo — substitute value/coeffs symbolically and need
# no change). Dirichlet is exercised through schema-clean .esm fixtures
# (tests/spatial/bc_{spatial,temporal}_value.esm); neumann/robin reuse the same
# generic engine but need a ghost rule, supplied inline here (the top-level
# `rules` field is a discretizer extension not in esm-schema.json, so it stays
# out of the shared fixtures). Julia is the reference; coord_<dim> is supplied
# as a const_array at evaluation time. Cross-binding parity is a sibling bead.

using Test
using JSON3
using EarthSciSerialization

const _BC_REPO_ROOT = normpath(joinpath(@__DIR__, "..", "..", ".."))

_load_esm(rel) = JSON3.read(read(joinpath(_BC_REPO_ROOT, rel), String))

# Uniform cell centers for a non-periodic axis: (i - 0.5) * dx.
_centers(n, dx) = Float64[(i - 0.5) * dx for i in 1:n]

# A 1-D diffusion stencil (1/dx²)·u[i-1] + (-2/dx²)·u[i] + (1/dx²)·u[i+1] for a
# single state variable `var`, written directly as index ops so the lift sees
# the out-of-range boundary reads.
function _stencil_1d(var)
    inv  = Dict("op"=>"/", "args"=>Any[1,  Dict("op"=>"*","args"=>Any["dx","dx"])])
    invn = Dict("op"=>"/", "args"=>Any[-2, Dict("op"=>"*","args"=>Any["dx","dx"])])
    Dict("op"=>"+","args"=>Any[
        Dict("op"=>"*","args"=>Any[inv,  Dict("op"=>"index","args"=>Any[var, Dict("op"=>"-","args"=>Any["i",1])])]),
        Dict("op"=>"*","args"=>Any[invn, Dict("op"=>"index","args"=>Any[var, "i"])]),
        Dict("op"=>"*","args"=>Any[inv,  Dict("op"=>"index","args"=>Any[var, Dict("op"=>"+","args"=>Any["i",1])])]),
    ])
end

# Single-model 1-D ESM with one xmin BC (given kind/fields) + a zero-Dirichlet
# xmax cap, and an optional discretizer `rules` list (for neumann/robin ghosts).
function _model_1d(var, bc_left; rules=Any[])
    esm = Dict{String,Any}(
        "esm"=>"0.2.0", "metadata"=>Dict{String,Any}("name"=>"bc_inline"),
        "grids"=>Dict{String,Any}("g1"=>Dict{String,Any}("family"=>"cartesian",
            "dimensions"=>Any[Dict{String,Any}("name"=>"x","size"=>5,"periodic"=>false,"spacing"=>"uniform")])),
        "models"=>Dict{String,Any}("M"=>Dict{String,Any}("grid"=>"g1",
            "variables"=>Dict{String,Any}(
                var =>Dict{String,Any}("type"=>"state","default"=>0.0,"shape"=>Any["x"],"location"=>"cell_center"),
                "dx"=>Dict{String,Any}("type"=>"parameter","default"=>1.0)),
            "equations"=>Any[Dict{String,Any}(
                "lhs"=>Dict("op"=>"D","args"=>Any[var],"wrt"=>"t"),
                "rhs"=>_stencil_1d(var))],
            "boundary_conditions"=>Dict{String,Any}(
                "left"=>bc_left,
                "right"=>Dict{String,Any}("variable"=>var,"side"=>"xmax","kind"=>"dirichlet","value"=>0.0)))))
    isempty(rules) || (esm["rules"] = rules)
    return esm
end

# Inline ghost rule: ghost = index($u,0) + <bound>; value-agnostic in the bound.
_neumann_rule() = Dict{String,Any}("name"=>"neu",
    "pattern"=>Dict("op"=>"bc","kind"=>"neumann","side"=>"\$side","args"=>Any["\$u","\$val"]),
    "replacement"=>Dict("op"=>"+","args"=>Any[Dict("op"=>"index","args"=>Any["\$u",0]),"\$val"]))
_robin_rule() = Dict{String,Any}("name"=>"rob",
    "pattern"=>Dict("op"=>"bc","kind"=>"robin","side"=>"\$side","args"=>Any["\$u","\$a","\$b","\$g"]),
    "replacement"=>Dict("op"=>"+","args"=>Any[Dict("op"=>"index","args"=>Any["\$u",0]),"\$g"]))

@testset "Space/time-varying boundary-condition values (ess-x1w)" begin

    cx5 = _centers(5, 1.0)            # 5 cells, dx=1 → 0.5,1.5,2.5,3.5,4.5

    # =====================================================================
    # SPATIAL: value/coefficient = f(coordinate) resolves per boundary cell
    # =====================================================================
    @testset "spatial f(x) — dirichlet / neumann / robin (1D) + edge (2D)" begin
        esm = _load_esm("tests/spatial/bc_spatial_value.esm")
        disc = discretize(esm; lift_1d_arrayop=true)

        # --- Dirichlet (fixture): value = sin(pi*x) on xmin --------------
        # u0≡0 ⇒ du[1] = ghost_xmin / dx² = sin(pi * coord_x[1]) (dx=1).
        let
            f!, u0, p, _, vm = build_evaluator(disc; model_name="dirichlet_1d",
                                               const_arrays=Dict("coord_x" => cx5))
            du = similar(u0); fill!(u0, 0.0); f!(du, u0, p, 0.0)
            @test isapprox(du[vm["u[1]"]], sin(pi * cx5[1]); atol=1e-12)  # = sin(pi/2) = 1
            @test isapprox(du[vm["u[5]"]], 0.0; atol=1e-12)              # xmax value 0
        end

        # --- Neumann (inline rule): flux value = x on xmin ---------------
        # ghost = index($u,0) + value ⇒ at u0≡0, ghost = coord_x[1].
        let
            bc = Dict{String,Any}("variable"=>"u","side"=>"xmin","kind"=>"neumann","value"=>"x")
            disc_n = discretize(_model_1d("u", bc; rules=Any[_neumann_rule()]); lift_1d_arrayop=true)
            f!, u0, p, _, vm = build_evaluator(disc_n; model_name="M",
                                               const_arrays=Dict("coord_x" => cx5))
            du = similar(u0); fill!(u0, 0.0); f!(du, u0, p, 0.0)
            @test isapprox(du[vm["u[1]"]], cx5[1]; atol=1e-12)           # = 0.5
            @test isapprox(du[vm["u[5]"]], 0.0; atol=1e-12)
        end

        # --- Robin (inline rule): gamma coefficient = 2*x on xmin --------
        # ghost = index($u,0) + gamma ⇒ at u0≡0, ghost = 2*coord_x[1].
        let
            bc = Dict{String,Any}("variable"=>"u","side"=>"xmin","kind"=>"robin",
                                  "robin_alpha"=>1.0,"robin_beta"=>1.0,
                                  "robin_gamma"=>Dict("op"=>"*","args"=>Any[2.0,"x"]))
            disc_r = discretize(_model_1d("u", bc; rules=Any[_robin_rule()]); lift_1d_arrayop=true)
            f!, u0, p, _, vm = build_evaluator(disc_r; model_name="M",
                                               const_arrays=Dict("coord_x" => cx5))
            du = similar(u0); fill!(u0, 0.0); f!(du, u0, p, 0.0)
            @test isapprox(du[vm["u[1]"]], 2.0 * cx5[1]; atol=1e-12)     # = 1.0
            @test isapprox(du[vm["u[5]"]], 0.0; atol=1e-12)
        end

        # --- 2D (fixture): Dirichlet value = x + 10*y along the ymin EDGE -
        # Each cell along the edge sees its OWN x-coordinate: the proof that the
        # coordinate is resolved PER boundary cell, not as one uniform value.
        let
            cx4 = _centers(4, 1.0); cy4 = _centers(4, 1.0)
            f!, u0, p, _, vm = build_evaluator(disc; model_name="dirichlet_2d_edge",
                                   const_arrays=Dict("coord_x" => cx4, "coord_y" => cy4))
            du = similar(u0); fill!(u0, 0.0); f!(du, u0, p, 0.0)
            # Interior-of-edge cells (no x-boundary): du[i,1] = coord_x[i] + 10*coord_y[1].
            @test isapprox(du[vm["w[2,1]"]], cx4[2] + 10*cy4[1]; atol=1e-12)  # 1.5 + 5 = 6.5
            @test isapprox(du[vm["w[3,1]"]], cx4[3] + 10*cy4[1]; atol=1e-12)  # 2.5 + 5 = 7.5
            # Distinct per-cell values ⇒ genuine per-cell coordinate resolution.
            @test du[vm["w[2,1]"]] != du[vm["w[3,1]"]]
        end
    end

    # =====================================================================
    # TEMPORAL: value/coefficient = g(t) evaluated per timestep
    # =====================================================================
    @testset "temporal g(t) — dirichlet / robin (1D)" begin
        # --- Dirichlet (fixture): value = sin(t) on xmin ----------------
        # u0≡0 ⇒ du[1] = ghost_xmin(t)/dx² = sin(t); xmax value 1 ⇒ du[5]=1.
        let
            esm = _load_esm("tests/spatial/bc_temporal_value.esm")
            disc = discretize(esm; lift_1d_arrayop=true)
            f!, u0, p, _, vm = build_evaluator(disc; model_name="dirichlet_1d_t")
            du = similar(u0); fill!(u0, 0.0)
            for tt in (0.0, pi/2, pi, 3pi/2)
                f!(du, u0, p, tt)
                @test isapprox(du[vm["u[1]"]], sin(tt); atol=1e-12)   # tracks g(t) per step
                @test isapprox(du[vm["u[5]"]], 1.0;     atol=1e-12)   # constant value 1
            end
        end

        # --- Robin (inline rule): gamma coefficient = cos(t) on xmin -----
        # ghost = index($u,0) + gamma ⇒ at u0≡0, du[1] = cos(t).
        let
            bc = Dict{String,Any}("variable"=>"u","side"=>"xmin","kind"=>"robin",
                                  "robin_alpha"=>1.0,"robin_beta"=>1.0,
                                  "robin_gamma"=>Dict("op"=>"cos","args"=>Any["t"]))
            disc_rt = discretize(_model_1d("u", bc; rules=Any[_robin_rule()]); lift_1d_arrayop=true)
            f!, u0, p, _, vm = build_evaluator(disc_rt; model_name="M")
            du = similar(u0); fill!(u0, 0.0)
            for tt in (0.0, pi/2, pi)
                f!(du, u0, p, tt)
                @test isapprox(du[vm["u[1]"]], cos(tt); atol=1e-12)
                @test isapprox(du[vm["u[5]"]], 0.0;     atol=1e-12)   # xmax value 0 in inline model
            end
        end
    end
end
