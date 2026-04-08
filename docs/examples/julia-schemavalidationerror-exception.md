# SchemaValidationError exception (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/validate_test.jl`

```julia
errors = [ESMFormat.SchemaError("/", "Test error", "required")]
        exception = ESMFormat.SchemaValidationError("Validation failed", errors)
        @test exception.message == "Validation failed"
        @test length(exception.errors) == 1
        @test exception.errors[1].path == "/"
```

