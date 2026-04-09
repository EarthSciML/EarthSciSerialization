# validate_structural function (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/structural_validation_test.jl`

```julia
metadata = EarthSciSerialization.Metadata("test-model")

        @testset "Missing equation for state variable" begin
            # Create a model with missing equation for state variable
            variables = Dict(
                "x" => EarthSciSerialization.ModelVariable(EarthSciSerialization.StateVariable, default=1.0),
                "y" => EarthSciSerialization.ModelVariable(EarthSciSerialization.StateVariable, default=2.0),
                "k" => EarthSciSerialization.ModelVariable(EarthSciSerialization.ParameterVariable, default=0.5)
            )

            equations = [
                EarthSciSerialization.Equation(EarthSciSerialization.OpExpr("D", EarthSciSerialization.Expr[EarthSciSerialization.VarExpr("x")], wrt="t"), EarthSciSerialization.VarExpr("y"))
                # Missing equation for state variable y
            ]

            model = EarthSciSerialization.Model(variables, equations)
            esm_file = EarthSciSerialization.EsmFile("0.1.0", metadata, models=Dict("test_model" => model))

            errors = EarthSciSerialization.validate_structural(esm_file)
            @test length(errors) == 1
            @test errors[1].path == "models.test_model.equations"
            @test occursin("State variable 'y' has no defining equation", errors[1].message)
            @test errors[1].error_type == "missing_equation"
```

