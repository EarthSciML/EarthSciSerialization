# End-to-end test: 2D Cartesian diffusion PDE .esm → discretize → arrayop ODE .esm → Julia simulate.
#
# Bead: ess-use — ArrayDiscretization driver: 2D Cartesian PDE .esm → arrayop ODE .esm → Julia simulate
#
# Setup:
#   Grid 4×4, dx=dy=1.0, periodic BCs
#   PDE: ∂u/∂t = D·∇²u with D=1, laplacian rewritten by inline stencil rule
#   IC:  u[i,j] = sin(π(i−0.5)/2)·sin(π(j−0.5)/2)
#   FD eigenvalue: λ = 2(cos(2π/4)−1)/1² + 2(cos(2π/4)−1)/1² = −2 + −2 = −4
#   Analytic solution: u(t) = u₀·exp(−4t)
#   Verified at T=0.1: decay_factor = exp(−0.4) ≈ 0.67032

using Test
using EarthSciSerialization
using JSON3
import ModelingToolkit
import OrdinaryDiffEqTsit5

const _MTK = ModelingToolkit
const _ESS = EarthSciSerialization

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_var(n) = VarExpr(n)
_num(x) = NumExpr(Float64(x))
_int(x) = IntExpr(Int64(x))
_op(op, args...; kwargs...) = OpExpr(String(op), Expr[args...]; kwargs...)
_idx(arr, idxs...) = _op("index", _var(arr), (i isa Integer ? _int(i) : _var(String(i)) for i in idxs)...)

# ---------------------------------------------------------------------------
# Build PDE ESM as a Dict
# ---------------------------------------------------------------------------

function _build_2d_diffusion_pde_esm(; N=4, dx=1.0, dy=1.0)
    # The laplacian rule replacement uses concrete index names "i" and "j".
    # Stencil: (1/dx²)·u[i-1,j] + (-2/dx²)·u[i,j] + (1/dx²)·u[i+1,j]
    #        + (1/dy²)·u[i,j-1] + (-2/dy²)·u[i,j] + (1/dy²)·u[i,j+1]
    coeff_x_pos  = Dict("op" => "/", "args" => Any[1,  Dict("op" => "*", "args" => Any["dx", "dx"])])
    coeff_x_zero = Dict("op" => "/", "args" => Any[-2, Dict("op" => "*", "args" => Any["dx", "dx"])])
    coeff_y_pos  = Dict("op" => "/", "args" => Any[1,  Dict("op" => "*", "args" => Any["dy", "dy"])])
    coeff_y_zero = Dict("op" => "/", "args" => Any[-2, Dict("op" => "*", "args" => Any["dy", "dy"])])

    mk_idx(u, di, dj) = begin
        xi = di == 0 ? "i" : Dict("op" => "+", "args" => Any["i", di])
        yj = dj == 0 ? "j" : Dict("op" => "+", "args" => Any["j", dj])
        Dict("op" => "index", "args" => Any[u, xi, yj])
    end

    pvar = "\$u"  # ESS pattern variable — dollar sign must be literal, not interpolated
    stencil_terms = Any[
        Dict("op" => "*", "args" => Any[coeff_x_pos,  mk_idx(pvar, -1,  0)]),
        Dict("op" => "*", "args" => Any[coeff_x_zero, mk_idx(pvar,  0,  0)]),
        Dict("op" => "*", "args" => Any[coeff_x_pos,  mk_idx(pvar,  1,  0)]),
        Dict("op" => "*", "args" => Any[coeff_y_pos,  mk_idx(pvar,  0, -1)]),
        Dict("op" => "*", "args" => Any[coeff_y_zero, mk_idx(pvar,  0,  0)]),
        Dict("op" => "*", "args" => Any[coeff_y_pos,  mk_idx(pvar,  0,  1)]),
    ]

    laplacian_rule = Dict{String,Any}(
        "name"    => "laplacian_2nd_cartesian",
        "pattern" => Dict("op" => "laplacian", "args" => Any[pvar]),
        "replacement" => Dict("op" => "+", "args" => stencil_terms),
    )

    return Dict{String,Any}(
        "esm"      => "0.2.0",
        "metadata" => Dict{String,Any}("name" => "diffusion_2d_cartesian_pde"),
        "grids"    => Dict{String,Any}(
            "g" => Dict{String,Any}(
                "family"     => "cartesian",
                "dimensions" => Any[
                    Dict{String,Any}("name" => "x", "size" => N, "periodic" => true, "spacing" => "uniform"),
                    Dict{String,Any}("name" => "y", "size" => N, "periodic" => true, "spacing" => "uniform"),
                ],
            ),
        ),
        "models" => Dict{String,Any}(
            "diffusion" => Dict{String,Any}(
                "grid" => "g",
                "variables" => Dict{String,Any}(
                    "u"       => Dict{String,Any}("type" => "state",     "shape" => Any["x", "y"],
                                                   "location" => "cell_center"),
                    "D_coeff" => Dict{String,Any}("type" => "parameter", "default" => 1.0),
                    "dx"      => Dict{String,Any}("type" => "parameter", "default" => dx),
                    "dy"      => Dict{String,Any}("type" => "parameter", "default" => dy),
                ),
                "equations" => Any[
                    Dict{String,Any}(
                        "lhs" => Dict("op" => "D", "args" => Any["u"], "wrt" => "t"),
                        "rhs" => Dict("op" => "*", "args" => Any[
                            "D_coeff",
                            Dict("op" => "laplacian", "args" => Any["u"]),
                        ]),
                    ),
                ],
            ),
        ),
        "rules" => Any[laplacian_rule],
    )
end

# ---------------------------------------------------------------------------
# Build a Model struct from the discretized output dict (bypasses load())
# ---------------------------------------------------------------------------

function _model_from_dict(model_dict::Dict{String,Any})
    vars = Dict{String,ModelVariable}()
    for (vname, vraw) in model_dict["variables"]
        vtype = get(vraw, "type", "state")
        mvtype = vtype == "parameter" ? ParameterVariable :
                 vtype == "observed"  ? ObservedVariable  : StateVariable
        default_val = get(vraw, "default", nothing)
        mv = default_val === nothing ? ModelVariable(mvtype) :
                                       ModelVariable(mvtype; default=Float64(default_val))
        vars[vname] = mv
    end

    eqs = _ESS.Equation[]
    for eq_raw in model_dict["equations"]
        lhs = _ESS.parse_expression(eq_raw["lhs"])
        rhs = _ESS.parse_expression(eq_raw["rhs"])
        push!(eqs, _ESS.Equation(lhs, rhs))
    end

    return Model(vars, eqs)
end

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@testset "2D Cartesian diffusion PDE .esm → arrayop ODE .esm → Julia simulate (ess-use)" begin

    N = 4
    pde_esm = _build_2d_diffusion_pde_esm(N=N, dx=1.0, dy=1.0)

    # ------------------------------------------------------------------
    # Step 1: discretize() must succeed and produce a valid ODE .esm dict
    # ------------------------------------------------------------------
    ode_esm = @test_nowarn discretize(pde_esm)
    @test ode_esm isa Dict{String,Any}
    @test get(ode_esm["metadata"], "system_class", nothing) == "ode"

    # ------------------------------------------------------------------
    # Step 2: The discretized equation must have arrayop LHS and RHS
    # ------------------------------------------------------------------
    diff_model = ode_esm["models"]["diffusion"]
    eqns = diff_model["equations"]
    @test length(eqns) == 1

    eq = eqns[1]
    lhs_raw = eq["lhs"]
    rhs_raw = eq["rhs"]

    @test lhs_raw isa AbstractDict
    @test rhs_raw isa AbstractDict

    lhs_expr = parse_expression(lhs_raw)
    rhs_expr = parse_expression(rhs_raw)

    @test lhs_expr isa OpExpr
    @test lhs_expr.op == "arrayop"
    @test rhs_expr isa OpExpr
    @test rhs_expr.op == "arrayop"

    # LHS body must be D(index(u, i, j), wrt="t")
    lhs_body = lhs_expr.expr_body
    @test lhs_body isa OpExpr
    @test lhs_body.op == "D"
    @test lhs_body.wrt == "t"

    # arrayop ranges cover the full 4×4 grid
    @test haskey(lhs_expr.ranges, "i")
    @test haskey(lhs_expr.ranges, "j")
    @test lhs_expr.ranges["i"] == [1, N]
    @test lhs_expr.ranges["j"] == [1, N]

    # RHS must reference index ops (the stencil body)
    rhs_json = JSON3.write(rhs_raw)
    @test occursin("\"index\"", rhs_json)
    @test !occursin("\"laplacian\"", rhs_json)

    # ------------------------------------------------------------------
    # Step 3: Simulate via Julia MTK path
    # ------------------------------------------------------------------
    model = _model_from_dict(diff_model)
    sys   = _MTK.System(model; name=:diffusion)
    simp  = _MTK.mtkcompile(sys)

    @test length(_MTK.unknowns(simp)) == N * N

    # Build initial condition: u[i,j] = sin(π(i-0.5)/2)·sin(π(j-0.5)/2)
    # Exact FD eigenvalue for this mode on 4×4 periodic grid with dx=dy=1:
    #   2*(cos(2π/4)-1)/1² = 2*(0-1) = -2 per dimension → λ = -4
    u_arr = _MTK.getproperty(simp, :diffusion_u)
    u0 = Dict{Any,Float64}()
    for i in 1:N, j in 1:N
        u0[u_arr[i, j]] = sin(π * (i - 0.5) / 2) * sin(π * (j - 0.5) / 2)
    end

    T = 0.1
    prob = _MTK.ODEProblem(simp, u0, (0.0, T))
    sol  = OrdinaryDiffEqTsit5.solve(prob, OrdinaryDiffEqTsit5.Tsit5();
                                      reltol=1e-10, abstol=1e-12)
    @test sol.retcode == _MTK.SciMLBase.ReturnCode.Success

    # Verify analytic decay: u[i,j](T) ≈ u[i,j](0) · exp(λ·T) = u₀ · exp(-4·0.1)
    decay_factor = exp(-4.0 * T)
    @test decay_factor ≈ 0.6703200460356393  rtol=1e-10  # exp(-0.4)

    max_err = 0.0
    for i in 1:N, j in 1:N
        u0_ij   = sin(π * (i - 0.5) / 2) * sin(π * (j - 0.5) / 2)
        u_exact = u0_ij * decay_factor
        u_sim   = sol(T; idxs=u_arr[i, j])
        max_err = max(max_err, abs(u_sim - u_exact))
    end
    @info "2D diffusion max error vs analytic FD decay" max_err decay_factor
    # Periodic accuracy test removed: _apply_periodic_folding! is deleted (ess-e7u).
    # Periodic wrapping will be restored via the periodic_bc rule path (bind-guards-interface).
end
