# Correct conversion factor passes (Julia)

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
                            EarthSciSerialization.NumExpr(101325.0),
                            EarthSciSerialization.VarExpr("p_atm"),
                        ])),
            )
            model = EarthSciSerialization.Model(variables, EarthSciSerialization.Equation[])
            errors = EarthSciSerialization.validate_conversion_factor_consistency(model, "/models/M")
            @test isempty(errors)
```

