# Round-trip: Model → System → Model (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/real_mtk_integration_test.jl`

```julia
vars = Dict(
            "x" => ModelVariable(StateVariable; default=2.0),
            "k" => ModelVariable(ParameterVariable; default=0.3),
        )
        eq = Equation(
            OpExpr("D", EarthSciSerialization.Expr[VarExpr("x")], wrt="t"),
            OpExpr("*", EarthSciSerialization.Expr[
                OpExpr("-", EarthSciSerialization.Expr[VarExpr("k")]),
                VarExpr("x"),
            ]),
        )
        original = Model(vars, [eq])
        sys = ModelingToolkit.System(original; name=:RT)
        recovered = EarthSciSerialization.Model(sys)
        @test recovered isa Model
        # After round-trip, the variables carry the namespaced name from
        # flatten (e.g. `RT_x`, `RT_k` after sanitization for symbol use).
        state_vars = [v for (n, v) in recovered.variables
                      if v.type == StateVariable]
        param_vars = [v for (n, v) in recovered.variables
                      if v.type == ParameterVariable]
        @test length(state_vars) == 1
        @test length(param_vars) == 1
```

