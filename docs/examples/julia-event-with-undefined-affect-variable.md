# Event with undefined affect variable (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/structural_validation_test.jl`

```julia
variables = Dict(
                "x" => ESMFormat.ModelVariable(ESMFormat.StateVariable, default=1.0)
            )
            equations = [
                ESMFormat.Equation(ESMFormat.OpExpr("D", ESMFormat.Expr[ESMFormat.VarExpr("x")], wrt="t"), ESMFormat.NumExpr(1.0))
            ]
            events = [
                ESMFormat.ContinuousEvent(
                    ESMFormat.Expr[ESMFormat.OpExpr("-", ESMFormat.Expr[ESMFormat.VarExpr("x"), ESMFormat.NumExpr(10.0)])],
                    [ESMFormat.AffectEquation("undefined_var", ESMFormat.NumExpr(0.0))]
                )
            ]
            model = ESMFormat.Model(variables, equations, events=events)
            esm_file = ESMFormat.EsmFile("0.1.0", metadata, models=Dict("test_model" => model))

            errors = ESMFormat.validate_structural(esm_file)
            @test length(errors) == 1
            @test errors[1].path == "models.test_model.events[1].affects[1]"
            @test occursin("Affect target variable 'undefined_var' not declared", errors[1].message)
            @test errors[1].error_type == "undefined_affect_variable"
```

