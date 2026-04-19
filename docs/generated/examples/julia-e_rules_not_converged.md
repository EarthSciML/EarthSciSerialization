# E_RULES_NOT_CONVERGED (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/rule_engine_test.jl`

```julia
# Rule: $a -> +($a, 0)  (each pass rewrites root once then seals;
        # next pass walks the new root and rewrites again forever).
        # With max_passes=3 this must abort.
        pat = VarExpr("\$a")
        repl = op("+", Any[VarExpr("\$a"), 0])
        rule = Rule("explode", pat, repl)
        @test_throws RuleEngineError rewrite(VarExpr("x"), Rule[rule];
                                             max_passes=3)
        # Confirm error code.
        caught = nothing
        try
            rewrite(VarExpr("x"), Rule[rule]; max_passes=3)
        catch e
            caught = e
```

