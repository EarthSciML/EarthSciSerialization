# Expression Formatting (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/display_test.jl`

```julia
# Test NumExpr formatting
        num_expr = NumExpr(3.14)
        @test EarthSciSerialization.format_expression_unicode(num_expr) == "3.14"
        @test EarthSciSerialization.format_expression_latex(num_expr) == "3.14"

        # Test VarExpr formatting
        var_expr = VarExpr("x")
        @test EarthSciSerialization.format_expression_unicode(var_expr) == "x"
        @test EarthSciSerialization.format_expression_latex(var_expr) == "x"

        # Test chemical VarExpr formatting
        chem_var = VarExpr("H2O")
        @test EarthSciSerialization.format_expression_unicode(chem_var) == "H₂O"
        @test EarthSciSerialization.format_expression_latex(chem_var) == "\\mathrm{H_{2}O}"

        # Test basic OpExpr formatting
        add_expr = OpExpr("+", EarthSciSerialization.Expr[NumExpr(1.0), VarExpr("x")])
        @test EarthSciSerialization.format_expression_unicode(add_expr) == "1 + x"  # Julia formats 1.0 as "1"
        @test EarthSciSerialization.format_expression_latex(add_expr) == "1 + x"  # Julia formats 1.0 as "1"
```

