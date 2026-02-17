# ValidationResult struct (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/structural_validation_test.jl`

```julia
schema_errors = [ESMFormat.SchemaError("/", "Schema error", "required")]
        structural_errors = [ESMFormat.StructuralError("models.test", "Structural error", "missing_equation")]
        unit_warnings = ["Unit warning"]

        # Test constructor
        result = ESMFormat.ValidationResult(schema_errors, structural_errors, unit_warnings=unit_warnings)
        @test result.is_valid == false
        @test length(result.schema_errors) == 1
        @test length(result.structural_errors) == 1
        @test length(result.unit_warnings) == 1

        # Test valid case
        result_valid = ESMFormat.ValidationResult(ESMFormat.SchemaError[], ESMFormat.StructuralError[])
        @test result_valid.is_valid == true
        @test isempty(result_valid.schema_errors)
        @test isempty(result_valid.structural_errors)
        @test isempty(result_valid.unit_warnings)
```

