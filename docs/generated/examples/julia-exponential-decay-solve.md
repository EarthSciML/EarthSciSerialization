# Exponential decay solve (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/tree_walk_test.jl`

```julia
vars = Dict{String,ModelVariable}(
            "x" => ModelVariable(StateVariable; default=1.0),
            "k" => ModelVariable(ParameterVariable; default=0.1),
        )
        eq = Equation(_D("x"), _op("*", _op("-", _v("k")), _v("x")))
        model = Model(vars, [eq])
        f!, u0, p, _tspan, var_map = build_evaluator(model)
        prob = OrdinaryDiffEqTsit5.ODEProblem(f!, u0, (0.0, 10.0), p)
        sol = OrdinaryDiffEqTsit5.solve(prob, OrdinaryDiffEqTsit5.Tsit5();
                                        reltol=1e-8, abstol=1e-10)
        @test isapprox(sol.u[
```

