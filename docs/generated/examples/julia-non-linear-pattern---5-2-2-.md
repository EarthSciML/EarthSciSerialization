# non-linear pattern (§5.2.2) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/rule_engine_test.jl`

```julia
# Rule: -($a, $a) -> 0
        pat = op("-", Any[VarExpr("\$a"), VarExpr("\$a")])
        repl = IntExpr(0)
        rule = Rule("self_minus", pat, repl)

        # Match: a - a
        m1 = match_pattern(pat, op("-", Any["x", "x"]))
        @test m1 !== nothing
        @test haskey(m1, "\$a")

        # No match: a - b
        m2 = match_pattern(pat, op("-", Any["x", "y"]))
        @test m2 === nothing
```

