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
