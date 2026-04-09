# Error Collector (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/error_handling_test.jl`

```julia
# Test ErrorCollector functionality - just basic existence
        collector = EarthSciSerialization.ErrorCollector()
        @test EarthSciSerialization.ErrorCollector isa DataType
        @test collector isa EarthSciSerialization.ErrorCollector
```

