# one_d — 1-D cell-centered (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/arrayed_vars_test.jl`

```julia
first, second = roundtrip("one_d.esm")
        for esm in (first, second)
            c = varof(esm, "Diffusion1D", "c")
            @test c.shape == ["x"]
            @test c.location == "cell_center"
            d = varof(esm, "Diffusion1D", "D")
            @test d.shape === nothing
            @test d.location === nothing
```

