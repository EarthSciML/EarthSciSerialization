# Conversion factor mismatch flagged (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/structural_validation_test.jl`

```julia
variables = Dict{String,EarthSciSerialization.ModelVariable}(
                "p_atm" => EarthSciSerialization.ModelVariable(
                    EarthSciSerialization.ParameterVariable;
                    units="atm", default=1.0),
                "converted_pressure" => EarthSciSerialization.ModelVariable(
                    EarthSciSerialization.ObservedVariable;
                    units="Pa",
                    expression=EarthSciSerialization.OpExpr("*",
                        EarthSciSerialization.Expr[
                            EarthSciSerialization.NumExpr(50000.0),
                            EarthSciSerialization.VarExpr("p_atm"),
                        ])),
            )
            model = EarthSciSerialization.Model(variables, EarthSciSerialization.Equation[])
            errors = EarthSciSerialization.validate_conversion_factor_consistency(model, "/models/M")
            @test length(errors) == 1
            @test errors[1].error_type == "unit_inconsistency"
            @test errors[1].path == "/models/M/variables/converted_pressure"
            @test occursin("declared_factor=50000", errors[1].message)
            @test occursin("expected_factor=101325", errors[1].message)
```

