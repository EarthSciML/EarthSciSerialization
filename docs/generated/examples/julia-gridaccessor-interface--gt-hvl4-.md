# GridAccessor interface (gt-hvl4) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/grid_accessor_test.jl`

```julia
@testset "Abstract type" begin
        @test EarthSciSerialization.GridAccessor isa Type
        @test isabstracttype(EarthSciSerialization.GridAccessor)
        @test _RectAccessor <: EarthSciSerialization.GridAccessor
```

