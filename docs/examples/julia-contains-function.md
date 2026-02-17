# contains function (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/expression_test.jl`

```julia
# Test NumExpr (contains no variables)
        num = NumExpr(3.14)
        @test !ESMFormat.contains(num, "x")

        # Test VarExpr
        var_x = VarExpr("x")
        @test ESMFormat.contains(var_x, "x")
        @test !ESMFormat.contains(var_x, "y")

        # Test OpExpr
        sum_expr = OpExpr("+", ESMFormat.Expr[VarExpr("x"), VarExpr("y")])
        @test ESMFormat.contains(sum_expr, "x")
        @test ESMFormat.contains(sum_expr, "y")
        @test !ESMFormat.contains(sum_expr, "z")

        # Test nested expressions
        nested = OpExpr("*", ESMFormat.Expr[OpExpr("+", ESMFormat.Expr[VarExpr("x"), NumExpr(1.0)]), VarExpr("y")])
        @test ESMFormat.contains(nested, "x")
        @test ESMFormat.contains(nested, "y")
        @test !ESMFormat.contains(nested, "z")

        # Test OpExpr with wrt field
        diff_expr = OpExpr("D", ESMFormat.Expr[VarExpr("x")], wrt="t")
        @test ESMFormat.contains(diff_expr, "x")
        @test ESMFormat.contains(diff_expr, "t")
        @test !ESMFormat.contains(diff_expr, "y")
```

