# Event with undefined affect variable (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/structural_validation_test.jl`

```julia
variables = Dict(
                "x" => EarthSciSerialization.ModelVariable(EarthSciSerialization.StateVariable, default=1.0)
            )
            equations = [
                EarthSciSerialization.Equation(EarthSciSerialization.OpExpr("D", EarthSciSerialization.Expr[EarthSciSerialization.VarExpr("x")], wrt="t"), EarthSciSerialization.NumExpr(1.0))
            ]
            events = [
                EarthSciSerialization.ContinuousEvent(
                    EarthSciSerialization.Expr[EarthSciSerialization.OpExpr("-", EarthSciSerialization.Expr[EarthSciSerialization.VarExpr("x"), EarthSciSerialization.NumExpr(10.0)])],
                    [EarthSciSerialization.AffectEquation("undefined_var", EarthSciSerialization.NumExpr(0.0))]
                )
            ]
            model = EarthSciSerialization.Model(variables, equations, continuous_events=events)
            esm_file = EarthSciSerialization.EsmFile("0.1.0", metadata, models=Dict("test_model" => model))

            errors = EarthSciSerialization.validate_structural(esm_file)
            @test length(errors) == 1
            @test errors[1].path == "models.test_model.continuous_events[1].affects[1]"
            @test occursin("Affect target variable 'undefined_var' not declared", errors[1].message)
            @test errors[1].error_type == "undefined_affect_variable"
```

