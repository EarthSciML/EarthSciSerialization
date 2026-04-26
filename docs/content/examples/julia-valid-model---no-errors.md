# Valid model - no errors (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/EarthSciSerialization.jl/test/structural_validation_test.jl`

```julia
variables = Dict(
                "x" => EarthSciSerialization.ModelVariable(EarthSciSerialization.StateVariable, default=1.0),
                "k" => EarthSciSerialization.ModelVariable(EarthSciSerialization.ParameterVariable, default=0.5)
            )
            equations = [
                EarthSciSerialization.Equation(EarthSciSerialization.OpExpr("D", EarthSciSerialization.Expr[EarthSciSerialization.VarExpr("x")], wrt="t"), EarthSciSerialization.VarExpr("k"))
            ]
            model = EarthSciSerialization.Model(variables, equations)
            esm_file = EarthSciSerialization.EsmFile("0.1.0", metadata, models=Dict("test_model" => model))

            errors = EarthSciSerialization.validate_structural(esm_file)
            @test isempty(errors)
```

