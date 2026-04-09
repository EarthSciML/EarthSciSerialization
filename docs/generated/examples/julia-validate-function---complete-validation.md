# validate function - complete validation (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/structural_validation_test.jl`

```julia
metadata = EarthSciSerialization.Metadata("test-model")

        @testset "Valid file" begin
            variables = Dict(
                "x" => EarthSciSerialization.ModelVariable(EarthSciSerialization.StateVariable, default=1.0)
            )
            equations = [
                EarthSciSerialization.Equation(EarthSciSerialization.OpExpr("D", EarthSciSerialization.Expr[EarthSciSerialization.VarExpr("x")], wrt="t"), EarthSciSerialization.NumExpr(1.0))
            ]
            model = EarthSciSerialization.Model(variables, equations)
            esm_file = EarthSciSerialization.EsmFile("0.1.0", metadata, models=Dict("test_model" => model))

            result = EarthSciSerialization.validate(esm_file)
            # Note: Schema validation might fail due to simplified conversion in validate function
            @test result isa EarthSciSerialization.ValidationResult
            @test isempty(result.structural_errors)
            @test isempty(result.unit_warnings)
```

