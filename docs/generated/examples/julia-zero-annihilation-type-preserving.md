# zero annihilation type-preserving (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/canonicalize_test.jl`

```julia
@test canonical_json(op("*", Any[0, "x"])) == "0"
        @test canonical_json(op("*", Any[0.0, "x"])) == "0.0"
        @test canonical_json(op("*", Any[-0.0, "x"])) == "-0.0"
```

