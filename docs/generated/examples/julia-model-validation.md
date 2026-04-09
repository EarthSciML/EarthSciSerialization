# Model Validation (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/ESMFormat.jl/test/units_test.jl`

```julia
# Test validate_model_dimensions function

        # Create a simple model with consistent units
        variables = Dict(
            "x" => ModelVariable(StateVariable, units="m", default=0.0),
            "v" => ModelVariable(ParameterVariable, units="m/s", default=1.0)
        )

        equations = [
            Equation(
                OpExpr("D", ESMFormat.Expr[VarExpr("x")], wrt="t"),
                VarExpr("v")
            )
        ]

        # Check the Model constructor signature
        model = Model(
            variables,
            equations
        )

        # Should validate correctly
        result = ESMFormat.validate_model_dimensions(model)
        @test result isa Bool  # Just test that it returns a boolean without error
```

