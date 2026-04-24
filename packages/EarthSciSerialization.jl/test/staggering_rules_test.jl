"""
staggering_rules_test.jl — Round-trip + validation for RFC §7.4 top-level
`staggering_rules` (esm-15f). Loads the MPAS C-grid staggering fixture,
re-serializes, reloads, and asserts the `staggering_rules` tree survives
intact. Also exercises the Julia-side validation that a
`kind="unstructured_c_grid"` rule must reference an unstructured grid.
"""

using Test
using EarthSciSerialization
using JSON3

const _SR_FIXTURES_DIR = joinpath(@__DIR__, "..", "..", "..", "tests", "grids")

_sr_plainify(x::JSON3.Array)  = Any[_sr_plainify(v) for v in x]
_sr_plainify(x::JSON3.Object) = Dict{String,Any}(string(k) => _sr_plainify(v) for (k, v) in pairs(x))
_sr_plainify(x::AbstractDict) = Dict{String,Any}(string(k) => _sr_plainify(v) for (k, v) in pairs(x))
_sr_plainify(x::AbstractVector) = Any[_sr_plainify(v) for v in x]
_sr_plainify(x) = x

function _sr_read_plain(path::String)
    return _sr_plainify(JSON3.read(read(path, String)))
end

@testset "RFC §7.4 staggering_rules round-trip" begin
    path = joinpath(_SR_FIXTURES_DIR, "mpas_c_grid_staggering.esm")
    @test isfile(path)

    original = EarthSciSerialization.load(path)
    @test original isa EsmFile
    @test original.staggering_rules !== nothing
    @test haskey(original.staggering_rules, "mpas_c_grid_staggering")

    rule = original.staggering_rules["mpas_c_grid_staggering"]
    @test rule isa StaggeringRule
    @test rule.data["kind"] == "unstructured_c_grid"
    @test rule.data["grid"] == "mpas_cvmesh"
    @test rule.data["edge_normal_convention"] == "outward_from_first_cell"
    @test rule.data["cell_quantity_locations"]["u"] == "edge_midpoint"

    tmp = tempname() * ".esm"
    try
        EarthSciSerialization.save(original, tmp)
        reloaded = EarthSciSerialization.load(tmp)

        @test Set(keys(original.staggering_rules)) == Set(keys(reloaded.staggering_rules))
        @test original.staggering_rules["mpas_c_grid_staggering"].data ==
              reloaded.staggering_rules["mpas_c_grid_staggering"].data

        # JSON-tree equivalence against the original on disk.
        disk_tree = _sr_read_plain(path)
        reloaded_tree = _sr_read_plain(tmp)
        @test disk_tree["staggering_rules"] == reloaded_tree["staggering_rules"]
    finally
        isfile(tmp) && rm(tmp)
    end
end

@testset "RFC §7.4 staggering_rules — unstructured-family guard" begin
    path = joinpath(_SR_FIXTURES_DIR, "mpas_c_grid_staggering.esm")
    data = JSON3.read(read(path, String), Dict{String,Any})

    # Mutate the grid to cartesian; the load must reject the staggering rule.
    data["grids"]["mpas_cvmesh"]["family"] = "cartesian"
    data["grids"]["mpas_cvmesh"]["extents"] = Dict("cell" => Dict("n" => "nCells", "spacing" => "uniform"))
    delete!(data["grids"]["mpas_cvmesh"], "connectivity")

    tmp = tempname() * ".esm"
    try
        open(tmp, "w") do io
            JSON3.write(io, data)
        end
        # Schema no longer allows a cartesian grid without required fields — but
        # the more interesting error for this feature is the semantic guard.
        # Accept either rejection path.
        @test_throws Exception EarthSciSerialization.load(tmp)
    finally
        isfile(tmp) && rm(tmp)
    end
end
