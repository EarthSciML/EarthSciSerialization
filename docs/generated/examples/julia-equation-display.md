# Equation Display (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/display_test.jl`

```julia
# Test Equation show method
        lhs = OpExpr("D", EarthSciSerialization.Expr[VarExpr("x")], wrt="t")
        rhs = OpExpr("*", EarthSciSerialization.Expr[NumExpr(2.0), VarExpr("x")])
        eq = Equation(lhs, rhs)

        io = IOBuffer()
        show(io, eq)
        output = String(take!(io))
        # Just test that show produces some output that looks like an equation
        @test Base.contains(output, "x")
        @test Base.contains(output, "=")
        @test length(output) > 0
```

