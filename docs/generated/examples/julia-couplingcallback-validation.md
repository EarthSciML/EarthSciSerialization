# CouplingCallback validation (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/structural_validation_test.jl`

```julia
esm_file = EarthSciSerialization.EsmFile("0.1.0", metadata)

            # Valid callback
            coupling = EarthSciSerialization.CouplingCallback("my_callback")
            errors = EarthSciSerialization.validate_coupling_references(esm_file, coupling, "coupling[1]")
            @test isempty(errors)

            # Empty callback ID
            coupling_bad = EarthSciSerialization.CouplingCallback("")
            errors = EarthSciSerialization.validate_coupling_references(esm_file, coupling_bad, "coupling[1]")
            @test length(errors) == 1
            @test errors[1].path == "coupling[1].callback_id"
            @test occursin("empty", errors[1].message)
            @test errors[1].error_type == "empty_callback_id"
```

