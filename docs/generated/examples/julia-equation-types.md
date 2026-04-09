# Equation Types (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/runtests.jl`

```julia
# Test Equation
        lhs = OpExpr("D", EarthSciSerialization.Expr[VarExpr("x")], wrt="t")
        rhs = OpExpr("*", EarthSciSerialization.Expr[NumExpr(2.0), VarExpr("x")])
        eq = Equation(lhs, rhs)
        @test eq.lhs == lhs
        @test eq.rhs == rhs

        # Test AffectEquation
        affect_eq = AffectEquation("x", NumExpr(0.0))
        @test affect_eq.lhs == "x"
        @test affect_eq.rhs isa NumExpr
```

