# Units Tests (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/ESMFormat.jl/test/units_test.jl`

```julia
@testset "Unit Parsing" begin
        # Test parse_units function

        # Test dimensionless units
        @test ESMFormat.parse_units("") == Unitful.NoUnits
        @test ESMFormat.parse_units("dimensionless") == Unitful.NoUnits

        # Test basic units
        units_m = ESMFormat.parse_units("m")
        @test units_m !== nothing
        @test dimension(units_m) == Unitful.𝐋

        units_s = ESMFormat.parse_units("s")
        @test units_s !== nothing
        @test dimension(units_s) == Unitful.𝐓

        units_kg = ESMFormat.parse_units("kg")
        @test units_kg !== nothing
        @test dimension(units_kg) == Unitful.𝐌

        # Test compound units
        units_mps = ESMFormat.parse_units("m/s")
        @test units_mps !== nothing
        @test dimension(units_mps) == Unitful.𝐋/Unitful.𝐓

        units_ms2 = ESMFormat.parse_units("m/s^2")
        @test units_ms2 !== nothing
        @test dimension(units_ms2) == Unitful.𝐋/Unitful.𝐓^2

        # Test invalid units
        @test ESMFormat.parse_units("invalid_unit") === nothing
```

