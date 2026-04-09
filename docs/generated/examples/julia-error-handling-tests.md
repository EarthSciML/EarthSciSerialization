# Error Handling Tests (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/error_handling_test.jl`

```julia
@testset "Error Codes" begin
        # Test that error codes are defined
        @test EarthSciSerialization.JSON_PARSE_ERROR isa EarthSciSerialization.ErrorCode
        @test EarthSciSerialization.SCHEMA_VALIDATION_ERROR isa EarthSciSerialization.ErrorCode
        @test EarthSciSerialization.UNDEFINED_REFERENCE isa EarthSciSerialization.ErrorCode
        @test EarthSciSerialization.EXPRESSION_PARSE_ERROR isa EarthSciSerialization.ErrorCode
        @test EarthSciSerialization.COUPLING_RESOLUTION_ERROR isa EarthSciSerialization.ErrorCode

        # Test that error codes have expected integer values
        @test Int(EarthSciSerialization.JSON_PARSE_ERROR) == 1001
        @test Int(EarthSciSerialization.SCHEMA_VALIDATION_ERROR) == 1002
        @test Int(EarthSciSerialization.UNDEFINED_REFERENCE) == 2002
        @test Int(EarthSciSerialization.EXPRESSION_PARSE_ERROR) == 3001
```

