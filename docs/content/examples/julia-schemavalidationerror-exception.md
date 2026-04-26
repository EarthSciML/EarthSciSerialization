# SchemaValidationError exception (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/EarthSciSerialization.jl/test/validate_test.jl`

```julia
errors = [EarthSciSerialization.SchemaError("/", "Test error", "required")]
        exception = EarthSciSerialization.SchemaValidationError("Validation failed", errors)
        @test exception.message == "Validation failed"
        @test length(exception.errors) == 1
        @test exception.errors[1].path == "/"
```

