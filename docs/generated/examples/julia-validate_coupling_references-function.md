# validate_coupling_references function (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/structural_validation_test.jl`

```julia
metadata = EarthSciSerialization.Metadata("test-model")

        @testset "CouplingOperatorCompose validation" begin
            model = EarthSciSerialization.Model(Dict("x" => EarthSciSerialization.ModelVariable(EarthSciSerialization.StateVariable, default=1.0)),
                                  [EarthSciSerialization.Equation(EarthSciSerialization.OpExpr("D", EarthSciSerialization.Expr[EarthSciSerialization.VarExpr("x")], wrt="t"), EarthSciSerialization.NumExpr(1.0))])
            esm_file = EarthSciSerialization.EsmFile("0.1.0", metadata, models=Dict("test_model" => model))

            # Valid system reference
            coupling = EarthSciSerialization.CouplingOperatorCompose(["test_model"])
            errors = EarthSciSerialization.validate_coupling_references(esm_file, coupling, "coupling[1]")
            @test isempty(errors)

            # Invalid system reference
            coupling_bad = EarthSciSerialization.CouplingOperatorCompose(["nonexistent_system"])
            errors = EarthSciSerialization.validate_coupling_references(esm_file, coupling_bad, "coupling[1]")
            @test length(errors) == 1
            @test errors[1].path == "coupling[1].systems[1]"
            @test occursin("nonexistent_system", errors[1].message)
            @test errors[1].error_type == "undefined_system"
```

