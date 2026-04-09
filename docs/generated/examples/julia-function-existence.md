# Function Existence (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/error_handling_test.jl`

```julia
# Test that key functions are defined (but may have interface issues)
        @test isdefined(EarthSciSerialization, :ErrorCode)
        @test isdefined(EarthSciSerialization, :ErrorContext)
        @test isdefined(EarthSciSerialization, :FixSuggestion)
        @test isdefined(EarthSciSerialization, :ESMError)
        @test isdefined(EarthSciSerialization, :ErrorCollector)
        @test isdefined(EarthSciSerialization, :PerformanceProfiler)
```

