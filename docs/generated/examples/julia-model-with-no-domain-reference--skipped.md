# Model with no domain reference: skipped (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/structural_validation_test.jl`

```julia
file = EarthSciSerialization.EsmFile("0.1.0", metadata;
                models=Dict("M" => make_model(nothing)))
            errors = EarthSciSerialization.validate_model_gradient_units(file, file.models["M"], "/models/M")
            @test isempty(errors)
```

