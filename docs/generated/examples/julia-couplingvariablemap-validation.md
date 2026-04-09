# CouplingVariableMap validation (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/ESMFormat.jl/test/structural_validation_test.jl`

```julia
model = ESMFormat.Model(Dict("x" => ESMFormat.ModelVariable(ESMFormat.StateVariable, default=1.0)),
                                  [ESMFormat.Equation(ESMFormat.OpExpr("D", ESMFormat.Expr[ESMFormat.VarExpr("x")], wrt="t"), ESMFormat.NumExpr(1.0))])
            esm_file = ESMFormat.EsmFile("0.1.0", metadata, models=Dict("test_model" => model))

            # Valid variable mapping
            coupling = ESMFormat.CouplingVariableMap("test_model.x", "test_model.x", "identity")
            errors = ESMFormat.validate_coupling_references(esm_file, coupling, "coupling[1]")
            @test isempty(errors)

            # Invalid 'from' reference
            coupling_bad_from = ESMFormat.CouplingVariableMap("invalid.ref", "test_model.x", "identity")
            errors = ESMFormat.validate_coupling_references(esm_file, coupling_bad_from, "coupling[1]")
            @test length(errors) == 1
            @test errors[1].path == "coupling[1].from"
            @test occursin("invalid.ref", errors[1].message)
            @test errors[1].error_type == "unresolved_reference"

            # Invalid 'to' reference
            coupling_bad_to = ESMFormat.CouplingVariableMap("test_model.x", "invalid.ref", "identity")
            errors = ESMFormat.validate_coupling_references(esm_file, coupling_bad_to, "coupling[1]")
            @test length(errors) == 1
            @test errors[1].path == "coupling[1].to"
            @test occursin("invalid.ref", errors[1].message)
            @test errors[1].error_type == "unresolved_reference"
```

