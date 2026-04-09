# Show Methods (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/ESMFormat.jl/test/display_test.jl`

```julia
# Test Expr show methods
        num_expr = NumExpr(2.5)

        # Test plain text output
        io = IOBuffer()
        show(io, "text/plain", num_expr)
        @test String(take!(io)) == "2.5"

        # Test LaTeX output
        show(io, "text/latex", num_expr)
        @test String(take!(io)) == "2.5"

        # Test ASCII output
        show(io, "text/ascii", num_expr)
        @test String(take!(io)) == "2.5"

        # Test more complex expressions with ASCII MIME type
        mul_expr = OpExpr("*", ESMFormat.Expr[VarExpr("x"), NumExpr(2.0)])
        show(io, "text/ascii", mul_expr)
        @test String(take!(io)) == "x*2"

        pow_expr = OpExpr("^", ESMFormat.Expr[VarExpr("x"), NumExpr(2.0)])
        show(io, "text/ascii", pow_expr)
        @test String(take!(io)) == "x^2"

        # Test chemical formula in ASCII (no subscripts)
        chem_var = VarExpr("H2O")
        show(io, "text/ascii", chem_var)
        @test String(take!(io)) == "H2O"  # Plain ASCII, no Unicode subscripts
```

