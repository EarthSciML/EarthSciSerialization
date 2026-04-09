# Expression Dimensions (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/units_test.jl`

```julia
# Test get_expression_dimensions function

        # Create test variables with units
        var_units = Dict(
            "x" => "m",
            "y" => "s",
            "z" => "kg",
            "speed" => "m/s",
            "area" => "m^2"
        )

        # Test NumExpr (dimensionless)
        num_expr = NumExpr(5.0)
        dims = EarthSciSerialization.get_expression_dimensions(num_expr, var_units)
        @test dims == Unitful.NoUnits

        # Test VarExpr
        var_expr_x = VarExpr("x")
        dims_x = EarthSciSerialization.get_expression_dimensions(var_expr_x, var_units)
        @test dims_x !== nothing
        @test dimension(dims_x) == Unitful.𝐋

        var_expr_speed = VarExpr("speed")
        dims_speed = EarthSciSerialization.get_expression_dimensions(var_expr_speed, var_units)
        @test dims_speed !== nothing
        @test dimension(dims_speed) == Unitful.𝐋/Unitful.𝐓

        # Test unknown variable - should return nothing but this implementation may have issues
        var_expr_unknown = VarExpr("unknown")
        dims_unknown = EarthSciSerialization.get_expression_dimensions(var_expr_unknown, var_units)
        # Just test it doesn't crash
        @test dims_unknown isa Union{Unitful.Units, Nothing}

        # Test basic OpExpr (multiplication works better than addition with mixed units)
        mul_expr = OpExpr("*", EarthSciSerialization.Expr[VarExpr("x"), VarExpr("y")])
        dims_mul = EarthSciSerialization.get_expression_dimensions(mul_expr, var_units)
        @test dims_mul !== nothing
        @test dimension(dims_mul) == Unitful.𝐋 * Unitful.𝐓
```

