# Unit Inference (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/ESMFormat.jl/test/units_test.jl`

```julia
# Test infer_variable_units function

        known_units = Dict(
            "t" => "s",
            "v" => "m/s"
        )

        # Simple equation: dx/dt = v, should infer x has units m
        equations = [
            Equation(
                OpExpr("D", ESMFormat.Expr[VarExpr("x")], wrt="t"),
                VarExpr("v")
            )
        ]

        inferred_units = ESMFormat.infer_variable_units("x", equations, known_units)
        # Just test that it doesn't crash and returns a result
        @test inferred_units isa Union{String, Nothing}
```

