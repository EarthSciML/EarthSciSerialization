# Registration hook (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/grid_accessor_test.jl`

```julia
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
```

