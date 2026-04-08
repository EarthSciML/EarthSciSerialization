# validate_structural function (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/structural_validation_test.jl`

```julia
metadata = ESMFormat.Metadata("test-model")

        @testset "Missing equation for state variable" begin
            # Create a model with missing equation for state variable
            variables = Dict(
                "x" => ESMFormat.ModelVariable(ESMFormat.StateVariable, default=1.0),
                "y" => ESMFormat.ModelVariable(ESMFormat.StateVariable, default=2.0),
                "k" => ESMFormat.ModelVariable(ESMFormat.ParameterVariable, default=0.5)
            )

            equations = [
                ESMFormat.Equation(ESMFormat.OpExpr("D", ESMFormat.Expr[ESMFormat.VarExpr("x")], wrt="t"), ESMFormat.VarExpr("y"))
                # Missing equation for state variable y
            ]

            model = ESMFormat.Model(variables, equations)
            esm_file = ESMFormat.EsmFile("0.1.0", metadata, models=Dict("test_model" => model))

            errors = ESMFormat.validate_structural(esm_file)
            @test length(errors) == 1
            @test errors[1].path == "models.test_model.equations"
            @test occursin("State variable 'y' has no defining equation", errors[1].message)
            @test errors[1].error_type == "missing_equation"
```

