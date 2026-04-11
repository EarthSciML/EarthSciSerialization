# Extension-gated: removed exports are gone (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/real_mtk_integration_test.jl`

```julia
# These names were removed as part of the extension refactor. They
        # must not exist as exported symbols of the main package.
        @test !isdefined(EarthSciSerialization, :to_mtk_system)
        @test !isdefined(EarthSciSerialization, :to_catalyst_system)
        @test !isdefined(EarthSciSerialization, :from_mtk_system)
        @test !isdefined(EarthSciSerialization, :from_catalyst_system)
        @test !isdefined(EarthSciSerialization, :check_mtk_availability)
        @test !isdefined(EarthSciSerialization, :check_catalyst_availability)
        # The mock fallbacks DO exist.
        @test isdefined(EarthSciSerialization, :MockMTKSystem)
        @test isdefined(EarthSciSerialization, :MockPDESystem)
        @test isdefined(EarthSciSerialization, :MockCatalystSystem)
```

