# Invalid fixture units_reaction_rate_mismatch.esm is rejected (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/structural_validation_test.jl`

```julia
fixture_path = joinpath(@__DIR__, "..", "..", "..", "tests", "invalid", "units_reaction_rate_mismatch.esm")
            if isfile(fixture_path)
                esm_data = EarthSciSerialization.load(fixture_path)
                result = EarthSciSerialization.validate(esm_data)
                @test !result.is_valid
                @test any(e -> e.error_type == "unit_inconsistency", result.structural_errors)
            else
                @warn "Fixture not found: $fixture_path"
                @test_broken false
```

