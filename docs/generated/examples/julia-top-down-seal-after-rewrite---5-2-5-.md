# top-down seal after rewrite (§5.2.5) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/rule_engine_test.jl`

```julia
# Rule: $a + $a -> 2*$a
        pat = op("+", Any[VarExpr("\$a"), VarExpr("\$a")])
        repl = op("*", Any[2, VarExpr("\$a")])
        rule = Rule("double", pat, repl)

        # Input: ((x + x) + (x + x))
        inner = op("+", Any["x", "x"])
        seed = OpExpr("+", ESM_Expr[inner, inner])

        # Pass 1: root matches ($a := (x+x)). Replacement is 2 * (x+x).
        # Seal: do not desc
```

