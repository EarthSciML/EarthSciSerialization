# sibling-field pattern vars (name class) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/rule_engine_test.jl`

```julia
# Rule: D($u, wrt=$x) -> index($u, $x)
        pat = OpExpr("D", ESM_Expr[VarExpr("\$u")]; wrt="\$x")
        repl = OpExpr("index", ESM_Expr[VarExpr("\$u"), VarExpr("\$x")])
        rule = Rule("deriv_index", pat, repl)

        seed = OpExpr("D", ESM_Expr[VarExpr("T")]; wrt="t")
        out = rewrite(seed, Rule[rule])
        @test out isa OpExpr
        @test out.op == "index"
        @test length(out.args) == 2
        @test (out.args[1] isa VarExpr) && out.args[1].name == "T"
        @test (out.args[2] isa VarExpr) && out.args[2].name == "t"
```

