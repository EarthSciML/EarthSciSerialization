# SchemaError struct (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/validate_test.jl`

```julia
error = ESMFormat.SchemaError("/test/path", "Test error message", "required")
        @test error.path == "/test/path"
        @test error.message == "Test error message"
        @test error.keyword == "required"
```

