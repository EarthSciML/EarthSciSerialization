# two_d_faces — staggered locations (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/arrayed_vars_test.jl`

```julia
first, second = roundtrip("two_d_faces.esm")
        for esm in (first, second)
            p = varof(esm, "StaggeredFlow2D", "p")
            @test p.shape == ["x", "y"]
            @test p.location == "cell_center"
            u = varof(esm, "StaggeredFlow2D", "u")
            @test u.shape == ["x", "y"]
            @test u.location == "x_face"
```

