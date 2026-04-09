# Function Existence (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/ESMFormat.jl/test/error_handling_test.jl`

```julia
# Test that key functions are defined (but may have interface issues)
        @test isdefined(ESMFormat, :ErrorCode)
        @test isdefined(ESMFormat, :ErrorContext)
        @test isdefined(ESMFormat, :FixSuggestion)
        @test isdefined(ESMFormat, :ESMError)
        @test isdefined(ESMFormat, :ErrorCollector)
        @test isdefined(ESMFormat, :PerformanceProfiler)
```

