# Units fixtures inline tests execution (gt-dt0o) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/units_fixture_consumption_test.jl`

```julia
fixtures_root = joinpath(@__DIR__, "..", "..", "..", "tests", "valid")
    fixtures = ["units_conversions.esm",
                "units_dimensional_analysis.esm",
                "units_propagation.esm"]

    any_tests_across_fixtures = false
    for fname in fixtures
        @testset "$fname" begin
            fpath = joinpath(fixtures_root, fname)
            @test isfile(fpath)
            file = _ESM_UF.load(fpath)
            @test file.models !== nothing

            any_model_tests = false
            for (mname, model) in file.models
                isempty(model.tests) && continue
                any_model_tests = true
                for t in model.tests
                    @testset "$mname/$(t.id)" begin
                        _run_units_test(string(mname), model, t)
```

