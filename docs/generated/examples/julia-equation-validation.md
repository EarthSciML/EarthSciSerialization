# Equation Validation (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/units_test.jl`

```julia
# Test validate_equation_dimensions function

        var_units = Dict(
            "x" => "m",
            "t" => "s",
            "v" => "m/s"
        )

        # Test valid equation: dx/dt = v (velocity)
        lhs = OpExpr("D", EarthSciSerialization.Expr[VarExpr("x")], wrt="t")
        rhs = VarExpr("v")
        valid_eq = Equation(lhs, rhs)

        @test EarthSciSerialization.validate_equation_dimensions(valid_eq, var_units) == true

        # Test invalid equation: dx/dt = x (wrong dimensions)
        invalid_rhs = VarExpr("x")  # m, but dx/dt should be m/s
        invalid_eq = Equation(lhs, invalid_rhs)

        @test EarthSciSerialization.validate_equation_dimensions(invalid_eq, var_units) == false
```

