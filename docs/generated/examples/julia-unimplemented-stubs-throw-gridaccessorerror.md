# Unimplemented stubs throw GridAccessorError (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/grid_accessor_test.jl`

```julia
g = _NotImplAccessor()
        @test_throws EarthSciSerialization.GridAccessorError cell_centers(g, 1, 2)
        @test_throws EarthSciSerialization.GridAccessorError neighbors(g, (1, 2))
        @test_throws EarthSciSerialization.GridAccessorError metric_eval(g, "dx", 1, 2)
```

