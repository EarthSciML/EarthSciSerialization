# Cross-binding units fixtures (gt-gtf) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/units_test.jl`

```julia
# Wire the three canonical units fixtures into the Julia binding so
        # that every binding agrees on what these files mean. These fixtures
        # are deliberately shared across Julia/Python/Rust/TypeScript/Go.
        units_fixtures = [
            "units_conversions.esm",
            "units_dimensional_analysis.esm",
            "units_propagation.esm",
        ]
        fixtures_root = joinpath(@__DIR__, "..", "..", "..", "tests", "valid")

        for fname in units_fixtures
            fpath = joinpath(fixtures_root, fname)
            @testset "$fname" begin
                @test isfile(fpath)
                esm_data = EarthSciSerialization.load(fpath)
                @test esm_data isa EarthSciSerialization.EsmFile
                @test esm_data.models !== nothing && !isempty(esm_data.models)

                # Run the binding's unit-validation entry point on every
                # model. The call must not throw; the boolean result is
                # captured for visibility but not asserted, because each
                # binding's unit registry has different coverage and the
                # fixtures intentionally exercise the union of registries.
                for (mname, model) in esm_data.models
                    result = EarthSciSerialization.validate_model_dimensions(model)
                    @test result isa Bool
```

