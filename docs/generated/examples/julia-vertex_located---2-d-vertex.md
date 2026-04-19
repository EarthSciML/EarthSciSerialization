# vertex_located — 2-D vertex (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/arrayed_vars_test.jl`

```julia
first, second = roundtrip("vertex_located.esm")
        for esm in (first, second)
            phi = varof(esm, "VertexScalar2D", "phi")
            @test phi.shape == ["x", "y"]
            @test phi.location == "vertex"
```

