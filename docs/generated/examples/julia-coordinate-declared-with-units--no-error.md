# Coordinate declared with units: no error (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/structural_validation_test.jl`

```julia
domains = Dict("default" => EarthSciSerialization.Domain(
                spatial=Dict{String,Any}("x" => Dict("min" => 0.0, "max" => 10.0, "units" => "m"))))
            file = EarthSciSerialization.EsmFile("0.1.0", metadata;
                models=Dict("M" => make_model("default")),
                domains=domains)
            errors = EarthSciSerialization.validate_model_gradient_units(file, file.models["M"], "/models/M")
            @test isempty(errors)
```

