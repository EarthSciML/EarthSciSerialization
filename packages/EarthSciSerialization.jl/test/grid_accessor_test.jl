# grid_accessor_test.jl — GridAccessor interface contract (gt-hvl4).
#
# Verifies the ESS-side trait surface that concrete ESD impls plug into:
# abstract type, default error fallbacks, subtype dispatch, and the
# register/make/unregister hook.

using Test
using EarthSciSerialization

# Test structs are defined at module scope (outside @testset) so they have
# normal module-level semantics — @testset does not hoist struct defs.

struct _NotImplAccessor <: EarthSciSerialization.GridAccessor end

struct _RectAccessor <: EarthSciSerialization.GridAccessor
    nx::Int
    ny::Int
end
EarthSciSerialization.cell_centers(g::_RectAccessor, i::Integer, j::Integer) =
    (Float64(i) / g.nx, Float64(j) / g.ny)
EarthSciSerialization.neighbors(g::_RectAccessor, cell::NTuple{2,Int}) =
    NTuple{2,Int}[(cell[1] - 1, cell[2]), (cell[1] + 1, cell[2]),
                  (cell[1], cell[2] - 1), (cell[1], cell[2] + 1)]
function EarthSciSerialization.metric_eval(g::_RectAccessor, name::AbstractString,
                                            ::Integer, ::Integer)
    name == "dx" && return 1.0 / g.nx
    name == "dy" && return 1.0 / g.ny
    throw(EarthSciSerialization.GridAccessorError("unknown metric '$name'"))
end

struct _RegAccessor <: EarthSciSerialization.GridAccessor
    data::Dict{String,Any}
end

@testset "GridAccessor interface (gt-hvl4)" begin

    @testset "Abstract type" begin
        @test EarthSciSerialization.GridAccessor isa Type
        @test isabstracttype(EarthSciSerialization.GridAccessor)
        @test _RectAccessor <: EarthSciSerialization.GridAccessor
    end

    @testset "Unimplemented stubs throw GridAccessorError" begin
        g = _NotImplAccessor()
        @test_throws EarthSciSerialization.GridAccessorError cell_centers(g, 1, 2)
        @test_throws EarthSciSerialization.GridAccessorError neighbors(g, (1, 2))
        @test_throws EarthSciSerialization.GridAccessorError metric_eval(g, "dx", 1, 2)
    end

    @testset "GridAccessorError message surfaces the concrete type" begin
        g = _NotImplAccessor()
        try
            cell_centers(g, 0, 0)
            @test false  # unreachable
        catch e
            @test e isa EarthSciSerialization.GridAccessorError
            @test occursin("_NotImplAccessor", e.message)
            io = IOBuffer()
            showerror(io, e)
            @test occursin("GridAccessorError", String(take!(io)))
        end
    end

    @testset "Subtype dispatch" begin
        g = _RectAccessor(8, 4)
        @test cell_centers(g, 2, 2) == (0.25, 0.5)
        @test neighbors(g, (2, 2)) == [(1, 2), (3, 2), (2, 1), (2, 3)]
        @test metric_eval(g, "dx", 0, 0) ≈ 0.125
        @test metric_eval(g, "dy", 0, 0) ≈ 0.25
        @test_throws EarthSciSerialization.GridAccessorError metric_eval(g, "nope", 0, 0)
    end

    @testset "Registration hook" begin
        factory = (d) -> _RegAccessor(d)
        family  = "__test_family_hvl4"
        try
            @test EarthSciSerialization.register_grid_accessor!(family, factory) === nothing
            @test family in EarthSciSerialization.registered_grid_families()
            @test EarthSciSerialization.grid_accessor_factory(family) === factory

            acc = EarthSciSerialization.make_grid_accessor(family,
                Dict{String,Any}("foo" => "bar"))
            @test acc isa _RegAccessor
            @test acc.data["foo"] == "bar"

            # Re-registration returns the previous factory.
            factory2 = (d) -> _RegAccessor(d)
            @test EarthSciSerialization.register_grid_accessor!(family, factory2) === factory
            @test EarthSciSerialization.grid_accessor_factory(family) === factory2
        finally
            EarthSciSerialization.unregister_grid_accessor!(family)
        end
        @test !(family in EarthSciSerialization.registered_grid_families())
        @test_throws EarthSciSerialization.GridAccessorError EarthSciSerialization.grid_accessor_factory(family)
        @test_throws EarthSciSerialization.GridAccessorError EarthSciSerialization.make_grid_accessor(
            family, Dict{String,Any}())
    end

    @testset "unregister returns whether an entry existed" begin
        family = "__test_family_hvl4_unreg"
        @test EarthSciSerialization.unregister_grid_accessor!(family) === false
        EarthSciSerialization.register_grid_accessor!(family, (d) -> _RegAccessor(d))
        @test EarthSciSerialization.unregister_grid_accessor!(family) === true
        @test EarthSciSerialization.unregister_grid_accessor!(family) === false
    end
end
