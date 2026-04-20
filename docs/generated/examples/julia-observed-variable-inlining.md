# Observed variable inlining (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/tree_walk_test.jl`

```julia
vars = Dict{String,ModelVariable}(
            "x" => ModelVariable(StateVariable; default=1.0),
            "k" => ModelVariable(ParameterVariable; default=0.5),
            "y" => ModelVariable(ObservedVariable),
        )
        # y = 2*k; D(x) = -y*x
        eqs = [
            Equation(_v("y"), _op("*", _n(2.0), _v("k"))),
            Equation(_D("x"), _op("-", _op("*", _v("y"), _v("x")))),
        ]
        model = Model(vars, eqs)
        f!, u0, p, _tspan, var_map = build_evaluator(model)
        du = similar(u0)
        f!(du, u0, p, 0.0)
        # D(x) = -(2 * 0.5 * 1.0) = -1.0
        @test du[var_map["x"]] == -1.0
```

