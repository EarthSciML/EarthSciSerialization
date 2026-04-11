# remove_equation by index (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/editing_test.jl`

```julia
m = _make_model()
        m = add_equation(m, _make_eq("k", 0.0))
        @test length(m.equations) == 2

        m2 = remove_equation(m, 1)
        @test length(m2.equations) == 1

        # Out-of-bounds: returns original with warning
        m3 = @test_logs (:warn,) match_mode=:any remove_equation(m2, 99)
        @test length(m3.equations) == length(m2.equations)
```

