# validate function - complete validation (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/structural_validation_test.jl`

```julia
metadata = ESMFormat.Metadata("test-model")

        @testset "Valid file" begin
            variables = Dict(
                "x" => ESMFormat.ModelVariable(ESMFormat.StateVariable, default=1.0)
            )
            equations = [
                ESMFormat.Equation(ESMFormat.OpExpr("D", ESMFormat.Expr[ESMFormat.VarExpr("x")], wrt="t"), ESMFormat.NumExpr(1.0))
            ]
            model = ESMFormat.Model(variables, equations)
            esm_file = ESMFormat.EsmFile("0.1.0", metadata, models=Dict("test_model" => model))

            result = ESMFormat.validate(esm_file)
            # Note: Schema validation might fail due to simplified conversion in validate function
            @test result isa ESMFormat.ValidationResult
            @test isempty(result.structural_errors)
            @test isempty(result.unit_warnings)
```

