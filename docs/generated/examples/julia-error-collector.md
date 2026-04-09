# Error Collector (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/ESMFormat.jl/test/error_handling_test.jl`

```julia
# Test ErrorCollector functionality - just basic existence
        collector = ESMFormat.ErrorCollector()
        @test ESMFormat.ErrorCollector isa DataType
        @test collector isa ESMFormat.ErrorCollector
```

