# Coordinate dim absent from domain.spatial: silent fallback (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/structural_validation_test.jl`

```julia
# Mirrors the TS binding's behaviour: if `node.dim` isn't in the
            # domain's spatial table we can't resolve it, so we assume the
            # legacy metre denominator and emit nothing.
            domains = Dict("default" => EarthSciSerialization.Domain(
                spatial=Dict{String,Any}("y" => Dict("min" => 0.0, "max" => 10.0, "units" => "m"))))
            file = EarthSciSerialization.EsmFile("0.1.0", metadata;
                models=Dict("M" => make_model("default")),
                domains=domains)
            errors = EarthSciSerialization.validate_model_gradient_units(file, file.models["M"], "/models/M")
            @test isempty(errors)
```

