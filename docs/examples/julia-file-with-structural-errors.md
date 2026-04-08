# File with structural errors (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/structural_validation_test.jl`

```julia
variables = Dict(
                "x" => ESMFormat.ModelVariable(ESMFormat.StateVariable, default=1.0),
                "y" => ESMFormat.ModelVariable(ESMFormat.StateVariable, default=2.0)
            )
            equations = [
                ESMFormat.Equation(ESMFormat.OpExpr("D", ESMFormat.Expr[ESMFormat.VarExpr("x")], wrt="t"), ESMFormat.NumExpr(1.0))
                # Missing equation for y
            ]
            model = ESMFormat.Model(variables, equations)
            esm_file = ESMFormat.EsmFile("0.1.0", metadata, models=Dict("test_model" => model))

            result = ESMFormat.validate(esm_file)
            @test result isa ESMFormat.ValidationResult
            @test length(result.structural_errors) == 1
            @test result.is_valid == false  # Should be false due to structural errors
```

