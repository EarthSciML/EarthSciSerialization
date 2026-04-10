# Subsystem Reference Resolution Tests (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/subsystem_ref_test.jl`

```julia
@testset "SubsystemRefError construction" begin
        err = EarthSciSerialization.SubsystemRefError("test error")
        @test err.message == "test error"
        @test err isa Exception
```

