# scalar_no_shape — regression (no shape/location fields) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/arrayed_vars_test.jl`

```julia
first, second = roundtrip("scalar_no_shape.esm")
        for esm in (first, second)
            v = varof(esm, "Scalar0D", "x")
            @test v.shape === nothing
            @test v.location === nothing
            k = varof(esm, "Scalar0D", "k")
            @test k.shape === nothing
            @test k.location === nothing
```

