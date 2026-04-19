# Invalid fixture units_dimensional_constant_error.esm is rejected (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/structural_validation_test.jl`

```julia
fixture_path = joinpath(@__DIR__, "..", "..", "..", "tests", "invalid", "units_dimensional_constant_error.esm")
            if isfile(fixture_path)
                esm_data = EarthSciSerialization.load(fixture_path)
                result = EarthSciSerialization.validate(esm_data)
                @test !result.is_valid
                matching = filter(e -> e.error_type == "unit_inconsistency" &&
                                       occursin("Physical constant used with incorrect dimensional analysis", e.message),
                                  result.structural_errors)
                @test length(matching) >= 1
                if !isempty(matching)
                    err = matching[1]
                    @test err.path == "/models/ConstantUnitsModel/variables/gas_law_calculation"
                    @test occursin("R", err.message)
                    @test occursin("kcal/mol", err.message)
                    @test occursin("J/(mol*K)", err.message)
```

