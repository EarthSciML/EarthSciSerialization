# Expression namespacing (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
# Test numeric expression
        num = NumExpr(42.0)
        @test EarthSciSerialization.namespace_expression(num, "Sys") == "42"

        num_float = NumExpr(3.14)
        @test EarthSciSerialization.namespace_expression(num_float, "Sys") == "3.14"

        # Test variable expression
        var = VarExpr("x")
        @test EarthSciSerialization.namespace_expression(var, "Sys") == "Sys.x"

        # Test already-qualified variable
        qual_var = VarExpr("Other.y")
        @test EarthSciSerialization.namespace_expression(qual_var, "Sys") == "Other.y"

        # Test binary op expression
        op = OpExpr("+", EarthSciSerialization.Expr[VarExpr("x"), NumExpr(1.0)])
        result = EarthSciSerialization.namespace_expression(op, "Sys")
        @test occursin("Sys.x", result)
        @test occursin("+", result)
        @test occursin("1", result)

        # Test derivative expression
        deriv = OpExpr("D", EarthSciSerialization.Expr[VarExpr("T")], wrt="t")
        result = EarthSciSerialization.namespace_expression(deriv, "Atm")
        @test occursin("D(", result)
        @test occursin("Atm.T", result)
```

