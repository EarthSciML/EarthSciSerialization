# Valid model - no errors (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/structural_validation_test.jl`

```julia
variables = Dict(
                "x" => ESMFormat.ModelVariable(ESMFormat.StateVariable, default=1.0),
                "k" => ESMFormat.ModelVariable(ESMFormat.ParameterVariable, default=0.5)
            )
            equations = [
                ESMFormat.Equation(ESMFormat.OpExpr("D", ESMFormat.Expr[ESMFormat.VarExpr("x")], wrt="t"), ESMFormat.VarExpr("k"))
            ]
            model = ESMFormat.Model(variables, equations)
            esm_file = ESMFormat.EsmFile("0.1.0", metadata, models=Dict("test_model" => model))

            errors = ESMFormat.validate_structural(esm_file)
            @test isempty(errors)
```

