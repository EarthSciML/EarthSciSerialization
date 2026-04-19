# fixed-point: repeated reductions (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/rule_engine_test.jl`

```julia
# Rule: +($a, 0) -> $a
        rule = Rule("add_zero",
            op("+", Any[VarExpr("\$a"), 0]),
            VarExpr("\$a"))
        # ((x + 0) + 0) -- needs 2 passes
        seed = op("+", Any[op("+", Any["x", 0]), 0])
        out = rewrite(seed, Rule[rule])
        @test canonical_json(out) == "\"x\""
```

