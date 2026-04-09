# EsmFile Display (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/ESMFormat.jl/test/display_test.jl`

```julia
# Test EsmFile show method
        metadata = Metadata("test_model", description="Test model")
        esm_file = EsmFile("0.1.0", metadata)

        io = IOBuffer()
        show(io, esm_file)
        output = String(take!(io))
        # Just test that show produces some output with the basic info
        @test Base.contains(output, "test_model")
        @test Base.contains(output, "0.1.0")
        @test length(output) > 0
```

