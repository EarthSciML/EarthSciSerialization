# Invalid fixture units_gradient_operator_mismatch.esm is rejected (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/structural_validation_test.jl`

```julia
fixture_path = joinpath(@__DIR__, "..", "..", "..", "tests", "invalid",
                                    "units_gradient_operator_mismatch.esm")
            if isfile(fixture_path)
                esm_data = EarthSciSerialization.load(fixture_path)
                result = EarthSciSerialization.validate(esm_data)
                @test !result.is_valid
                grad_errs = filter(
                    e -> e.error_type == "unit_inconsistency" && occursin("coordinate 'x'", e.message),
                    result.structural_errors)
                @test length(grad_errs) == 1
                @test grad_errs[1].path == "/models/SpatialModel/equations/0"
            else
                @warn "Fixture not found: $fixture_path"
                @test_broken false
```

