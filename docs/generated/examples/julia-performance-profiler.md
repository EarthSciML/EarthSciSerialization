# Performance Profiler (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/error_handling_test.jl`

```julia
# Test PerformanceProfiler functionality - basic existence
        profiler = EarthSciSerialization.PerformanceProfiler()
        @test EarthSciSerialization.PerformanceProfiler isa DataType
        @test profiler isa EarthSciSerialization.PerformanceProfiler

        # Test that start_timer! and
```

