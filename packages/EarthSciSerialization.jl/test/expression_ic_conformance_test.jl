# Cross-binding conformance for the `expression` initial-condition type
# (bead ess-gjn, epic campfire-e2e ea-6sh).
#
# The shared golden under tests/valid/initial_conditions/ declares a domain-level
# `expression` initial condition: u's initial field is the existing expression
# AST psi(x) = 0.5 * (1 + tanh((x - 0.3) / 0.15)) evaluated over the spatial grid
# at t=0 (no new primitive). Python evaluates this end-to-end; Julia loads it as
# the shared contract — expression-IC evaluation in Julia is deferred per ess-gjn
# (Python-first scope). This test pins that Julia parses the golden, that the
# domain exposes the spatial grid, and that the initial condition carries the
# Expression AST, so the fixture is the lever the Julia evaluator builds against.

using Test
using EarthSciSerialization
using JSON3
const ESS = EarthSciSerialization

const _EXPRIC_REPO_ROOT = normpath(joinpath(@__DIR__, "..", "..", ".."))

@testset "expression initial-condition golden loads (ess-gjn)" begin
    path = joinpath(_EXPRIC_REPO_ROOT, "tests", "valid", "initial_conditions",
                    "expression_ignition_front_1d.esm")
    @test isfile(path)

    # Julia parses the golden into an EsmFile (round-trip / evaluation deferred).
    file = ESS.load(path)
    @test file isa ESS.EsmFile
    @test file.esm == "0.6.0"

    # The domain declares a 1-D spatial grid (x in [0, 1] at grid_spacing 0.25,
    # 5 nodes) and an `expression` initial condition whose value is an Expression
    # AST in the spatial coordinate `x`.
    raw = JSON3.read(read(path, String), Dict)
    dom = raw["domains"]["line"]
    @test haskey(dom["spatial"], "x")
    @test dom["spatial"]["x"]["min"] == 0.0
    @test dom["spatial"]["x"]["max"] == 1.0
    @test dom["spatial"]["x"]["grid_spacing"] == 0.25

    ic = dom["initial_conditions"]
    @test ic["type"] == "expression"
    @test haskey(ic["values"], "u")
    @test ic["values"]["u"]["op"] == "*"  # psi(x) = 0.5 * (1 + tanh(...))

    # The state variable is method-of-lines discretized over the grid.
    model = raw["models"]["IgnitionFront1D"]
    @test model["domain"] == "line"
    @test model["variables"]["u"]["shape"] == ["i"]
end
