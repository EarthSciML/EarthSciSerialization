# File Validation (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/units_test.jl`

```julia
# Test validate_file_dimensions function

        metadata = Metadata("test_units", description="Test model for unit validation")
        esm_file = EsmFile("0.1.0", metadata)

        result = EarthSciSerialization.validate_file_dimensions(esm_file)
        @test result isa Bool
        @test result == true
```

