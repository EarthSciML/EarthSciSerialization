# remove_equation by LHS pattern (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/editing_test.jl`

```julia
m = _make_model()
        m = add_equation(m, _make_eq("k", 0.0))
        # Pattern must match the stored lhs by `==` — for OpExpr that is
        # `===` in the default struct, so reuse the exact lhs object here.
        pattern = m.equations[1].lhs
        m2 = remove_equation(m, pattern)
        @test length(m2.equations) == 1
        remaining = m2.equations[1]
        @test remaining.lhs.args[1].name == "k"

        # Pattern with no match: warns and returns unchanged
        bogus = OpExpr("D", ESS.Expr[VarExpr("nonexistent")], wrt="t")
        m3 = @test_logs (:warn,) match_mode=:any remove_equation(m2, bogus)
        @test length(m3.equations) == length(m2.equations)
```

