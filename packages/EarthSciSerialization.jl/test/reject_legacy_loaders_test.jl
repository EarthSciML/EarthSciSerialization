# Load-time rejection of legacy (pre-0.7.0) pure-I/O data-loader shapes
# (esm-spec §8 / RFC pure-io-data-loaders §4.1, bead ess-v9a.7). Mirrors the
# cross-binding conformance fixtures in tests/conformance/migration/0_6_to_0_7/.
using Test
using EarthSciSerialization
using EarthSciSerialization: reject_legacy_data_loader_shapes, LegacyDataLoaderError

const _RLL_REPO_ROOT = normpath(joinpath(@__DIR__, "..", "..", ".."))
const _RLL_FIX_DIR =
    joinpath(_RLL_REPO_ROOT, "tests", "conformance", "migration", "0_6_to_0_7")

@testset "reject legacy pure-I/O data-loader shapes (ess-v9a.7)" begin
    @testset "rejects removed `regridding` with data_loader_regridding_removed" begin
        err = nothing
        try
            EarthSciSerialization.load(joinpath(_RLL_FIX_DIR, "loader_regridding_removed.esm"))
        catch e
            err = e
        end
        @test err isa LegacyDataLoaderError
        @test err.code == "data_loader_regridding_removed"
    end

    @testset "rejects removed `spatial` with data_loader_spatial_removed" begin
        err = nothing
        try
            EarthSciSerialization.load(joinpath(_RLL_FIX_DIR, "loader_spatial_removed.esm"))
        catch e
            err = e
        end
        @test err isa LegacyDataLoaderError
        @test err.code == "data_loader_spatial_removed"
    end

    @testset "accepts the migrated 0.7.0 pure-I/O loader" begin
        file = EarthSciSerialization.load(joinpath(_RLL_FIX_DIR, "loader_migrated.esm"))
        @test file.data_loaders !== nothing
        @test haskey(file.data_loaders, "weather")
    end

    @testset "version-gated: a 0.7.0 file does not trip the legacy check" begin
        raw = Dict{String,Any}(
            "esm" => "0.7.0",
            "data_loaders" => Dict{String,Any}(
                "w" => Dict{String,Any}("regridding" => Dict{String,Any}())))
        @test reject_legacy_data_loader_shapes(raw) === nothing
    end

    @testset "no data_loaders block is a no-op" begin
        raw = Dict{String,Any}("esm" => "0.6.0",
            "models" => Dict{String,Any}())
        @test reject_legacy_data_loader_shapes(raw) === nothing
    end
end
