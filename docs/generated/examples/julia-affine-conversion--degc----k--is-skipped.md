# Affine conversion (degC -> K) is skipped (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/structural_validation_test.jl`

```julia
# 0 °C = 273.15 K, so the conversion is affine — must not be flagged.
            variables = Dict{String,EarthSciSerialization.ModelVariable}(
                "T_C" => EarthSciSerialization.ModelVariable(
                    EarthSciSerialization.ParameterVariable;
                    units="°C", default=0.0),
                "T_K" => EarthSciSerialization.ModelVariable(
                    EarthSciSerialization.ObservedVariable;
                    units="K",
                    expression=EarthSciSerialization.OpExpr("*",
                        EarthSciSerialization.Expr[
                            EarthSciSerialization.NumExpr(1.0),
                            EarthSciSerialization.VarExpr("T_C"),
                        ])),
            )
            model = EarthSciSerialization.Model(variables, EarthSciSerialization.Equation[])
            errors = EarthSciSerialization.validate_conversion_factor_consistency(model, "/models/M")
            @test isempty(errors)
```

