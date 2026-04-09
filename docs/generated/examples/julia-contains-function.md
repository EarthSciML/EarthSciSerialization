# contains function (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/expression_test.jl`

```julia
# Test NumExpr (contains no variables)
        num = NumExpr(3.14)
        @test !EarthSciSerialization.contains(num, "x")

        # Test VarExpr
        var_x = VarExpr("x")
        @test EarthSciSerialization.contains(var_x, "x")
        @test !EarthSciSerialization.contains(var_x, "y")

        # Test OpExpr
        sum_expr = OpExpr("+", EarthSciSerialization.Expr[VarExpr("x"), VarExpr("y")])
        @test EarthSciSerialization.contains(sum_expr, "x")
        @test EarthSciSerialization.contains(sum_expr, "y")
        @test !EarthSciSerialization.contains(sum_expr, "z")

        # Test nested expressions
        nested = OpExpr("*", EarthSciSerialization.Expr[OpExpr("+", EarthSciSerialization.Expr[VarExpr("x"), NumExpr(1.0)]), VarExpr("y")])
        @test EarthSciSerialization.contains(nested, "x")
        @test EarthSciSerialization.contains(nested, "y")
        @test !EarthSciSerialization.contains(nested, "z")

        # Test OpExpr with wrt field
        diff_expr = OpExpr("D", EarthSciSerialization.Expr[VarExpr("x")], wrt="t")
        @test EarthSciSerialization.contains(diff_expr, "x")
        @test EarthSciSerialization.contains(diff_expr, "t")
        @test !EarthSciSerialization.contains(diff_expr, "y")
```

