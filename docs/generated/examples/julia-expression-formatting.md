# Expression Formatting (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/ESMFormat.jl/test/display_test.jl`

```julia
# Test NumExpr formatting
        num_expr = NumExpr(3.14)
        @test ESMFormat.format_expression_unicode(num_expr) == "3.14"
        @test ESMFormat.format_expression_latex(num_expr) == "3.14"

        # Test VarExpr formatting
        var_expr = VarExpr("x")
        @test ESMFormat.format_expression_unicode(var_expr) == "x"
        @test ESMFormat.format_expression_latex(var_expr) == "x"

        # Test chemical VarExpr formatting
        chem_var = VarExpr("H2O")
        @test ESMFormat.format_expression_unicode(chem_var) == "H₂O"
        @test ESMFormat.format_expression_latex(chem_var) == "\\mathrm{H_{2}O}"

        # Test basic OpExpr formatting
        add_expr = OpExpr("+", ESMFormat.Expr[NumExpr(1.0), VarExpr("x")])
        @test ESMFormat.format_expression_unicode(add_expr) == "1 + x"  # Julia formats 1.0 as "1"
        @test ESMFormat.format_expression_latex(add_expr) == "1 + x"  # Julia formats 1.0 as "1"
```

