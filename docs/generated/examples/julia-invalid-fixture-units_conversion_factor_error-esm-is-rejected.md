# Invalid fixture units_conversion_factor_error.esm is rejected (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/structural_validation_test.jl`

```julia
fixture_path = joinpath(@__DIR__, "..", "..", "..", "tests", "invalid",
                                    "units_conversion_factor_error.esm")
            if isfile(fixture_path)
                esm_data = EarthSciSerialization.load(fixture_path)
                result = EarthSciSerialization.validate(esm_data)
                @test !result.is_valid
                matching = filter(e -> e.error_type == "unit_inconsistency" &&
                                       occursin("Unit conversion factor is incorrect", e.message),
                                  result.structural_errors)
                @test length(matching) >= 1
                if !isempty(matching)
                    err = matching[1]
                    @test err.path == "/models/BadUnitsModel/variables/converted_pressure"
                    @test occursin("declared_factor=50000", err.message)
                    @test occursin("expected_factor=101325", err.message)
```

