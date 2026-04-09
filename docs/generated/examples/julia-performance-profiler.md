# Performance Profiler (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/ESMFormat.jl/test/error_handling_test.jl`

```julia
# Test PerformanceProfiler functionality - basic existence
        profiler = ESMFormat.PerformanceProfiler()
        @test ESMFormat.PerformanceProfiler isa DataType
        @test profiler isa ESMFormat.PerformanceProfiler

        # Test that start_timer! and
```

