# Parentheses Logic (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/display_test.jl`

```julia
# Create test expressions
        add_expr = OpExpr("+", EarthSciSerialization.Expr[NumExpr(1.0), VarExpr("x")])
        mul_expr = OpExpr("*", EarthSciSerialization.Expr[VarExpr("y"), VarExpr("z")])

        # Test needs_parentheses
        @test EarthSciSerialization.needs_parentheses("*", add_expr, false) == true   # (1 + x) * ...
        @test EarthSciSerialization.needs_parentheses("+", mul_expr, false) == false  # y*z + ...
        @test EarthSciSerialization.needs_parentheses("-", add_expr, true) == true    # ... - (1 + x)
        @test EarthSciSerialization.needs_parentheses("*", mul_expr, false) == false  # y*z * ...
```

