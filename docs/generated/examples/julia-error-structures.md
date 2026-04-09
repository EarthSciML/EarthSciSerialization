# Error Structures (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/ESMFormat.jl/test/error_handling_test.jl`

```julia
# Test ErrorContext creation with keyword arguments
        context = ESMFormat.ErrorContext(
            file_path="test.esm",
            line_number=10,
            column=5
        )
        @test context.file_path == "test.esm"
        @test context.line_number == 10
        @test context.column == 5

        # Test FixSuggestion creation
        suggestion = ESMFormat.FixSuggestion("Try fixing this")
        @test suggestion.description == "Try fixing this"
        @test suggestion.priority == 1  # Default priority

        # Test basic structures exist
        @test ESMFormat.ErrorContext isa DataType
        @test ESMFormat.FixSuggestion isa DataType
        @test ESMFormat.ESMError isa DataType
```

