# unregister returns whether an entry existed (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/grid_accessor_test.jl`

```julia
family = "__test_family_hvl4_unreg"
        @test EarthSciSerialization.unregister_grid_accessor!(family) === false
        EarthSciSerialization.register_grid_accessor!(family, (d) -> _RegAccessor(d))
        @test EarthSciSerialization.unregister_grid_accessor!(family) === true
        @test EarthSciSerialization.unregister_grid_accessor!(family) === false
```

