# simple match + replace (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/rule_engine_test.jl`

```julia
# Rule: +($a, 0) -> $a
        pat = op("+", Any[VarExpr("\$a"), 0])
        repl = VarExpr("\$a")
        rule = Rule("add_zero", pat, repl)
        seed = op("+", Any["x", 0])
        out = rewrite(seed, Rule[rule])
        @test canonical_json(out) == "\"x\""
```

