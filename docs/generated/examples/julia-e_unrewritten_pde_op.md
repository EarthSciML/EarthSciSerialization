# E_UNREWRITTEN_PDE_OP (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/rule_engine_test.jl`

```julia
# grad() remains — should error.
        expr = OpExpr("grad", ESM_Expr[VarExpr("T")]; dim="x")
        @test_throws RuleEngineError check_unrewritten_pde_ops(expr)

        # After rewriting to index(), check passes.
        expr2 = op("index", Any["T", "x"])
        @test check_unrewritten_pde_ops(expr2) === nothing
```

