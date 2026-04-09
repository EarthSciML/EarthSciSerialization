# Expression Types (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/EarthSciSerialization.jl/test/runtests.jl`

```julia
# Test NumExpr
        num_expr = NumExpr(3.14)
        @test num_expr.value == 3.14
        @test num_expr isa EarthSciSerialization.Expr

        # Test VarExpr
        var_expr = VarExpr("x")
        @test var_expr.name == "x"
        @test var_expr isa EarthSciSerialization.Expr

        # Test OpExpr
        op_expr = OpExpr("+", EarthSciSerialization.Expr[NumExpr(1.0), VarExpr("x")])
        @test op_expr.op == "+"
        @test length(op_expr.args) == 2
        @test op_expr.wrt === nothing
        @test op_expr.dim === nothing
        @test op_expr isa EarthSciSerialization.Expr

        # Test OpExpr with optional parameters
        diff_expr = OpExpr("D", EarthSciSerialization.Expr[VarExpr("x")], wrt="t", dim="time")
        @test diff_expr.wrt == "t"
        @test diff_expr.dim == "time"
```

