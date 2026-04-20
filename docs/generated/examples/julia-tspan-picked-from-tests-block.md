# tspan picked from tests block (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/tree_walk_test.jl`

```julia
vars = Dict{String,ModelVariable}(
            "x" => ModelVariable(StateVariable; default=1.0),
            "k" => ModelVariable(ParameterVariable; default=0.1),
        )
        eq = Equation(_D("x"), _op("*", _op("-", _v("k")), _v("x")))
        tests = [ESM.Test("default_span",
                       ESM.TimeSpan(0.0, 25.0),
                       ESM.Assertion[]; description="default")]
        model = Model(vars, [eq]; tests=tests)
        _, _, _, tspan_default, _ = build_evaluator(model)
        @test tspan_default == (0.0, 25.0)
```

