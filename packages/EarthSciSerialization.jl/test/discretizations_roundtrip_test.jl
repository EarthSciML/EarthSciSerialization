"""
discretizations_roundtrip_test.jl — Round-trip coverage for the §7
`discretizations` top-level schema, including the §7.4
`CrossMetricStencilRule` composite variant (esm-vwo).

These tests load the canonical discretization fixtures, re-serialize,
reload, and assert the discretizations tree survives intact at the JSON
level. The Julia binding holds discretization entries opaquely as
`Dict{String,Any}` because stencil coefficients and applies_to patterns
carry pattern-variable strings (\$u, \$x, \$target) that don't map onto
the Expression coercion pipeline; the round-trip contract is structural
equivalence of the top-level `discretizations` subtree.
"""

using Test
using EarthSciSerialization
using JSON3

const _DISC_FIXTURES_DIR = joinpath(@__DIR__, "..", "..", "..", "tests", "discretizations")

_plainify(x::JSON3.Array)  = Any[_plainify(v) for v in x]
_plainify(x::JSON3.Object) = Dict{String,Any}(string(k) => _plainify(v) for (k, v) in pairs(x))
_plainify(x::AbstractDict) = Dict{String,Any}(string(k) => _plainify(v) for (k, v) in pairs(x))
_plainify(x::AbstractVector) = Any[_plainify(v) for v in x]
_plainify(x) = x

function _read_plain(path::String)
    raw = JSON3.read(read(path, String))
    return _plainify(raw)
end

@testset "RFC §7 discretizations round-trip" begin
    @test isdir(_DISC_FIXTURES_DIR)

    fixtures = ["centered_2nd_uniform.esm",
                "upwind_1st_advection.esm",
                "periodic_bc.esm",
                "mpas_cell_div.esm",
                "cross_metric_cartesian.esm",
                "grid_dispatch_ppm.esm"]

    for fname in fixtures
        @testset "Round-trip $(fname)" begin
            path = joinpath(_DISC_FIXTURES_DIR, fname)
            @test isfile(path)

            original_raw = _read_plain(path)

            esm = EarthSciSerialization.load(path)
            @test esm isa EsmFile
            @test esm.discretizations !== nothing
            @test length(esm.discretizations) >= 1

            tmp = tempname() * ".esm"
            try
                EarthSciSerialization.save(esm, tmp)
                reloaded = EarthSciSerialization.load(tmp)

                reloaded_raw = _read_plain(tmp)

                @test haskey(reloaded_raw, "discretizations")
                @test reloaded_raw["discretizations"] == original_raw["discretizations"]

                # Key sets preserved at the Julia struct level too.
                @test Set(keys(esm.discretizations)) == Set(keys(reloaded.discretizations))
            finally
                rm(tmp, force=true)
            end
        end
    end
end

@testset "RFC §7.4 cross-metric composite structure" begin
    path = joinpath(_DISC_FIXTURES_DIR, "cross_metric_cartesian.esm")
    esm = EarthSciSerialization.load(path)

    @test haskey(esm.discretizations, "laplacian_full_covariant_toy")
    composite = esm.discretizations["laplacian_full_covariant_toy"]

    @test composite["kind"] == "cross_metric"
    @test composite["axes"] == ["xi", "eta"]
    @test composite["terms"] isa AbstractVector
    @test length(composite["terms"]) == 2
    # Composite entries do NOT carry a stencil key.
    @test !haskey(composite, "stencil")

    # Per-axis stencils should still be present and carry a stencil key.
    @test haskey(esm.discretizations["d2_dxi2_uniform"], "stencil")
    @test haskey(esm.discretizations["d2_deta2_uniform"], "stencil")
end

@testset "RFC §7.8 grid_dispatch structure" begin
    path = joinpath(_DISC_FIXTURES_DIR, "grid_dispatch_ppm.esm")
    esm = EarthSciSerialization.load(path)

    @test haskey(esm.discretizations, "ppm_advection")
    scheme = esm.discretizations["ppm_advection"]

    # Parent-level grid_family / stencil are absent; the body lives in
    # grid_dispatch variants (RFC §7.8 mutual-exclusion contract).
    @test !haskey(scheme, "grid_family")
    @test !haskey(scheme, "stencil")
    @test scheme["grid_dispatch"] isa AbstractVector
    @test length(scheme["grid_dispatch"]) == 2

    families = [v["grid_family"] for v in scheme["grid_dispatch"]]
    @test families == ["cartesian", "cubed_sphere"]

    # Each variant carries its own stencil body.
    @test length(scheme["grid_dispatch"][1]["stencil"]) == 4
    @test length(scheme["grid_dispatch"][2]["stencil"]) == 2
end
