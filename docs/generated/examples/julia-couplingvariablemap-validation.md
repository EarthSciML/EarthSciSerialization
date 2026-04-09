# CouplingVariableMap validation (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/structural_validation_test.jl`

```julia
model = EarthSciSerialization.Model(Dict("x" => EarthSciSerialization.ModelVariable(EarthSciSerialization.StateVariable, default=1.0)),
                                  [EarthSciSerialization.Equation(EarthSciSerialization.OpExpr("D", EarthSciSerialization.Expr[EarthSciSerialization.VarExpr("x")], wrt="t"), EarthSciSerialization.NumExpr(1.0))])
            esm_file = EarthSciSerialization.EsmFile("0.1.0", metadata, models=Dict("test_model" => model))

            # Valid variable mapping
            coupling = EarthSciSerialization.CouplingVariableMap("test_model.x", "test_model.x", "identity")
            errors = EarthSciSerialization.validate_coupling_references(esm_file, coupling, "coupling[1]")
            @test isempty(errors)

            # Invalid 'from' reference
            coupling_bad_from = EarthSciSerialization.CouplingVariableMap("invalid.ref", "test_model.x", "identity")
            errors = EarthSciSerialization.validate_coupling_references(esm_file, coupling_bad_from, "coupling[1]")
            @test length(errors) == 1
            @test errors[1].path == "coupling[1].from"
            @test occursin("invalid.ref", errors[1].message)
            @test errors[1].error_type == "unresolved_reference"

            # Invalid 'to' reference
            coupling_bad_to = EarthSciSerialization.CouplingVariableMap("test_model.x", "invalid.ref", "identity")
            errors = EarthSciSerialization.validate_coupling_references(esm_file, coupling_bad_to, "coupling[1]")
            @test length(errors) == 1
            @test errors[1].path == "coupling[1].to"
            @test occursin("invalid.ref", errors[1].message)
            @test errors[1].error_type == "unresolved_reference"
```

