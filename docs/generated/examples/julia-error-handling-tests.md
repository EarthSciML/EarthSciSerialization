# Error Handling Tests (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/ESMFormat.jl/test/error_handling_test.jl`

```julia
@testset "Error Codes" begin
        # Test that error codes are defined
        @test ESMFormat.JSON_PARSE_ERROR isa ESMFormat.ErrorCode
        @test ESMFormat.SCHEMA_VALIDATION_ERROR isa ESMFormat.ErrorCode
        @test ESMFormat.UNDEFINED_REFERENCE isa ESMFormat.ErrorCode
        @test ESMFormat.EXPRESSION_PARSE_ERROR isa ESMFormat.ErrorCode
        @test ESMFormat.COUPLING_RESOLUTION_ERROR isa ESMFormat.ErrorCode

        # Test that error codes have expected integer values
        @test Int(ESMFormat.JSON_PARSE_ERROR) == 1001
        @test Int(ESMFormat.SCHEMA_VALIDATION_ERROR) == 1002
        @test Int(ESMFormat.UNDEFINED_REFERENCE) == 2002
        @test Int(ESMFormat.EXPRESSION_PARSE_ERROR) == 3001
```

