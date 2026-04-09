# CouplingOperatorApply validation (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/structural_validation_test.jl`

```julia
operator = EarthSciSerialization.Operator("test_op", ["x"])
            esm_file = EarthSciSerialization.EsmFile("0.1.0", metadata, operators=Dict("test_op" => operator))

            # Valid operator reference
            coupling = EarthSciSerialization.CouplingOperatorApply("test_op")
            errors = EarthSciSerialization.validate_coupling_references(esm_file, coupling, "coupling[1]")
            @test isempty(errors)

            # Invalid operator reference
            coupling_bad = EarthSciSerialization.CouplingOperatorApply("nonexistent_op")
            errors = EarthSciSerialization.validate_coupling_references(esm_file, coupling_bad, "coupling[1]")
            @test length(errors) == 1
            @test errors[1].path == "coupling[1].operator"
            @test occursin("nonexistent_op", errors[1].message)
            @test errors[1].error_type == "undefined_operator"
```

