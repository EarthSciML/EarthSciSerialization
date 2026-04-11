# add_equation appends (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/editing_test.jl`

```julia
m = _make_model()
        new_eq = _make_eq("k", 0.0)  # D(k) = 0*k
        m2 = add_equation(m, new_eq)

        @test length(m2.equations) == length(m.equations) + 1
        @test m2.equations[
```

