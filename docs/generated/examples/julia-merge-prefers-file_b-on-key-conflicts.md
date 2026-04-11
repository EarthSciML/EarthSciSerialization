# merge prefers file_b on key conflicts (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/editing_test.jl`

```julia
m1 = Model(Dict("x" => ModelVariable(StateVariable, default=1.0)), Equation[])
        m2 = Model(Dict("x" => ModelVariable(StateVariable, default=999.0)), Equation[])

        fa = EsmFile("0.1.0", Metadata("a"); models=Dict("Shared" => m1))
        fb = EsmFile("0.1.0", Metadata("b"); models=Dict("Shared" => m2))

        merged = ESS.merge(fa, fb)
        @test length(merged.models) == 1
        # file_b takes precedence
        @test merged.models["Shared"].variables["x"].default == 999.0
```

