# End-to-end pathway test for tree_walk simulation runner (esm-qrj).
#
# Asserts tree_walk works as an OFFICIAL ESS Julia simulation runner:
# the model travels parse → discretize → build_evaluator → solve.

using Test
using JSON3
using EarthSciSerialization
import OrdinaryDiffEqTsit5

const _E2E_REPO_ROOT = normpath(joinpath(@__DIR__, "..", "..", ".."))

@testset "tree_walk e2e: parse → discretize → build_evaluator → solve (esm-qrj)" begin
    fixture = joinpath(_E2E_REPO_ROOT, "tests", "conformance", "discretize",
                       "inputs", "scalar_ode.esm")
    @test isfile(fixture)

    esm = JSON3.read(read(fixture, String))
    discretized = discretize(esm)
    @test discretized isa Dict{String,Any}
    @test discretized["metadata"]["system_class"] == "ode"

    f!, u0, p, tspan_default, var_map = build_evaluator(discretized)
    @test haskey(var_map, "x")
    @test length(u0) == 1
    @test u0[var_map["x"]] == 1.0
    @test p.k == 0.5
    @test tspan_default == (0.0, 1.0)

    prob = OrdinaryDiffEqTsit5.ODEProblem(f!, u0, (0.0, 4.0), p)
    sol = OrdinaryDiffEqTsit5.solve(prob, OrdinaryDiffEqTsit5.Tsit5();
                                    reltol=1e-9, abstol=1e-11)
    @test isapprox(sol.u[end][var_map["x"]], exp(-2.0); rtol=1e-7)
end

@testset "tree_walk e2e: 1D PDE → discretize(lift_1d_arrayop=true) → build_evaluator" begin
    # A 1D periodic advection document whose grad op is rewritten by a
    # centered-difference rule with the 1/(2·dx) coefficient. With
    # lift_1d_arrayop=true the equation lifts to arrayop form and the
    # tree-walk evaluator expands it per cell, so one f! evaluation must
    # reproduce the centered stencil exactly.
    n = 8
    dx = 1.0 / n
    esm = Dict{String,Any}(
        "esm"      => "0.4.0",
        "metadata" => Dict{String,Any}("name" => "advection_1d_lift"),
        "grids"    => Dict{String,Any}(
            "gx" => Dict{String,Any}(
                "family"     => "cartesian",
                "dimensions" => Any[
                    Dict{String,Any}("name" => "i", "size" => n,
                                      "periodic" => true, "spacing" => "uniform"),
                ],
            ),
        ),
        "rules" => Any[
            Dict{String,Any}(
                "name"    => "centered_grad",
                "pattern" => Dict{String,Any}("op" => "grad", "args" => Any["\$u"], "dim" => "\$x"),
                "replacement" => Dict{String,Any}(
                    "op"   => "/",
                    "args" => Any[
                        Dict{String,Any}("op" => "-", "args" => Any[
                            Dict{String,Any}("op" => "index", "args" => Any[
                                "\$u", Dict{String,Any}("op" => "+", "args" => Any["\$x", 1])]),
                            Dict{String,Any}("op" => "index", "args" => Any[
                                "\$u", Dict{String,Any}("op" => "-", "args" => Any["\$x", 1])]),
                        ]),
                        Dict{String,Any}("op" => "*", "args" => Any[2, "dx"]),
                    ],
                ),
            ),
        ],
        "models" => Dict{String,Any}(
            "M" => Dict{String,Any}(
                "grid" => "gx",
                "variables" => Dict{String,Any}(
                    "u" => Dict{String,Any}(
                        "type" => "state", "default" => 0.0, "units" => "1",
                        "shape" => Any["i"], "location" => "cell_center",
                    ),
                    "dx" => Dict{String,Any}(
                        "type" => "parameter", "default" => dx, "units" => "1",
                    ),
                ),
                "equations" => Any[
                    Dict{String,Any}(
                        "lhs" => Dict{String,Any}("op" => "D", "args" => Any["u"], "wrt" => "t"),
                        "rhs" => Dict{String,Any}("op" => "grad", "args" => Any["u"], "dim" => "i"),
                    ),
                ],
            ),
        ),
    )

    discretized = discretize(esm; lift_1d_arrayop=true)
    @test discretized["models"]["M"]["equations"][1]["lhs"]["op"] == "arrayop"

    f!, u0, p, _tspan, var_map = build_evaluator(discretized)
    @test length(u0) == n
    cell_x(i) = (i - 0.5) * dx
    for i in 1:n
        u0[var_map["u[$i]"]] = sin(2π * cell_x(i))
    end
    du = similar(u0)
    f!(du, u0, p, 0.0)

    for i in 1:n
        u_left  = i > 1 ? sin(2π * cell_x(i - 1)) : 0.0
        u_right = i < n ? sin(2π * cell_x(i + 1)) : 0.0
        expected = (u_right - u_left) / (2 * dx)
        @test isapprox(du[var_map["u[$i]"]], expected; rtol=1e-12, atol=1e-12)
    end
end
