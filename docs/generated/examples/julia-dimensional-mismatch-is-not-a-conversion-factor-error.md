# Dimensional mismatch is not a conversion-factor error (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/structural_validation_test.jl`

```julia
# atm vs m — dimensionally incompatible; other checks handle this,
            # this check silently skips.
            variables = Dict{String,EarthSciSerialization.ModelVariable}(
                "p_atm" => EarthSciSerialization.ModelVariable(
                    EarthSciSerialization.ParameterVariable;
                    units="atm", default=1.0),
                "x" => EarthSciSerialization.ModelVariable(
                    EarthSciSerialization.ObservedVariable;
                    units="m",
                    expression=EarthSciSerialization.OpExpr("*",
                        EarthSciSerialization.Expr[
                            EarthSciSerialization.NumExpr(2.0),
                            EarthSciSerialization.VarExpr("p_atm"),
                        ])),
            )
            model = EarthSciSerialization.Model(variables, EarthSciSerialization.Equation[])
            errors = EarthSciSerialization.validate_conversion_factor_consistency(model, "/models/M")
            @test isempty(errors)
```

