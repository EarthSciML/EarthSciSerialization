# Error Structures (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/error_handling_test.jl`

```julia
# Test ErrorContext creation with keyword arguments
        context = EarthSciSerialization.ErrorContext(
            file_path="test.esm",
            line_number=10,
            column=5
        )
        @test context.file_path == "test.esm"
        @test context.line_number == 10
        @test context.column == 5

        # Test FixSuggestion creation
        suggestion = EarthSciSerialization.FixSuggestion("Try fixing this")
        @test suggestion.description == "Try fixing this"
        @test suggestion.priority == 1  # Default priority

        # Test basic structures exist
        @test EarthSciSerialization.ErrorContext isa DataType
        @test EarthSciSerialization.FixSuggestion isa DataType
        @test EarthSciSerialization.ESMError isa DataType
```

