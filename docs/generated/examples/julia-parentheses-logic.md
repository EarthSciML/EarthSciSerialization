# Parentheses Logic (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/ESMFormat.jl/test/display_test.jl`

```julia
# Create test expressions
        add_expr = OpExpr("+", ESMFormat.Expr[NumExpr(1.0), VarExpr("x")])
        mul_expr = OpExpr("*", ESMFormat.Expr[VarExpr("y"), VarExpr("z")])

        # Test needs_parentheses
        @test ESMFormat.needs_parentheses("*", add_expr, false) == true   # (1 + x) * ...
        @test ESMFormat.needs_parentheses("+", mul_expr, false) == false  # y*z + ...
        @test ESMFormat.needs_parentheses("-", add_expr, true) == true    # ... - (1 + x)
        @test ESMFormat.needs_parentheses("*", mul_expr, false) == false  # y*z * ...
```

