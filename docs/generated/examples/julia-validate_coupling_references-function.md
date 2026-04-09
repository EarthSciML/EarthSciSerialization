# validate_coupling_references function (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/ESMFormat.jl/test/structural_validation_test.jl`

```julia
metadata = ESMFormat.Metadata("test-model")

        @testset "CouplingOperatorCompose validation" begin
            model = ESMFormat.Model(Dict("x" => ESMFormat.ModelVariable(ESMFormat.StateVariable, default=1.0)),
                                  [ESMFormat.Equation(ESMFormat.OpExpr("D", ESMFormat.Expr[ESMFormat.VarExpr("x")], wrt="t"), ESMFormat.NumExpr(1.0))])
            esm_file = ESMFormat.EsmFile("0.1.0", metadata, models=Dict("test_model" => model))

            # Valid system reference
            coupling = ESMFormat.CouplingOperatorCompose(["test_model"])
            errors = ESMFormat.validate_coupling_references(esm_file, coupling, "coupling[1]")
            @test isempty(errors)

            # Invalid system reference
            coupling_bad = ESMFormat.CouplingOperatorCompose(["nonexistent_system"])
            errors = ESMFormat.validate_coupling_references(esm_file, coupling_bad, "coupling[1]")
            @test length(errors) == 1
            @test errors[1].path == "coupling[1].systems[1]"
            @test occursin("nonexistent_system", errors[1].message)
            @test errors[1].error_type == "undefined_system"
```

