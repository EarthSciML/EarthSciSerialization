# Units Tests (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/units_test.jl`

```julia
@testset "Unit Parsing" begin
        # Test parse_units function

        # Test dimensionless units
        @test EarthSciSerialization.parse_units("") == Unitful.NoUnits
        @test EarthSciSerialization.parse_units("dimensionless") == Unitful.NoUnits

        # Test basic units
        units_m = EarthSciSerialization.parse_units("m")
        @test units_m !== nothing
        @test dimension(units_m) == Unitful.𝐋

        units_s = EarthSciSerialization.parse_units("s")
        @test units_s !== nothing
        @test dimension(units_s) == Unitful.𝐓

        units_kg = EarthSciSerialization.parse_units("kg")
        @test units_kg !== nothing
        @test dimension(units_kg) == Unitful.𝐌

        # Test compound units
        units_mps = EarthSciSerialization.parse_units("m/s")
        @test units_mps !== nothing
        @test dimension(units_mps) == Unitful.𝐋/Unitful.𝐓

        units_ms2 = EarthSciSerialization.parse_units("m/s^2")
        @test units_ms2 !== nothing
        @test dimension(units_ms2) == Unitful.𝐋/Unitful.𝐓^2

        # Test invalid units
        @test EarthSciSerialization.parse_units("invalid_unit") === nothing
```

