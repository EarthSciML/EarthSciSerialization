# Subtype dispatch (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/grid_accessor_test.jl`

```julia
g = _RectAccessor(8, 4)
        @test cell_centers(g, 2, 2) == (0.25, 0.5)
        @test neighbors(g, (2, 2)) == [(1, 2), (3, 2), (2, 1), (2, 3)]
        @test metric_eval(g, "dx", 0, 0) ≈ 0.125
        @test metric_eval(g, "dy", 0, 0) ≈ 0.25
        @test_throws EarthSciSerialization.GridAccessorError metric_eval(g, "nope", 0, 0)
```

