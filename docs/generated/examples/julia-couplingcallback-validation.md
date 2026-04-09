# CouplingCallback validation (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/ESMFormat.jl/test/structural_validation_test.jl`

```julia
esm_file = ESMFormat.EsmFile("0.1.0", metadata)

            # Valid callback
            coupling = ESMFormat.CouplingCallback("my_callback")
            errors = ESMFormat.validate_coupling_references(esm_file, coupling, "coupling[1]")
            @test isempty(errors)

            # Empty callback ID
            coupling_bad = ESMFormat.CouplingCallback("")
            errors = ESMFormat.validate_coupling_references(esm_file, coupling_bad, "coupling[1]")
            @test length(errors) == 1
            @test errors[1].path == "coupling[1].callback_id"
            @test occursin("empty", errors[1].message)
            @test errors[1].error_type == "empty_callback_id"
```

