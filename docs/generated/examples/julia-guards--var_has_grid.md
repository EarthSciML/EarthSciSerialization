# guards: var_has_grid (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/rule_engine_test.jl`

```julia
pat = op("grad", Any[VarExpr("\$u")])
        # name-class grad.dim pattern variable
        pat = OpExpr("grad", ESM_Expr[VarExpr("\$u")]; dim="\$x")
        repl = VarExpr("\$u")
        guards = [Guard("var_has_grid",
                        Dict{String,Any}("pvar" => "\$u", "grid" => "g1"))]
        rule = Rule("drop_grad", pat, guards, repl, nothing)

        ctx_match = RuleContext(
            Dict{String,Dict{String,Any}}(
                "g1" => Dict{String,Any}("spatial_dims" => ["x"])),
            Dict{String,Dict{String,Any}}(
                "T" => Dict{String,Any}("grid" => "g1")))
        out = rewrite(OpExpr("grad", ESM_Expr[VarExpr("T")]; dim="x"),
                      Rule[rule], ctx_match)
        @test out isa VarExpr && out.name == "T"

        # With a variable on the wrong grid, no rewrite.
        ctx_nomatch = RuleContext(
            Dict{String,Dict{String,Any}}(
                "g1" => Dict{String,Any}("spatial_dims" => ["x"])),
            Dict{String,Dict{String,Any}}(
                "T" => Dict{String,Any}("grid" => "g2")))
        out2 = rewrite(OpExpr("grad", ESM_Expr[VarExpr("T")]; dim="x"),
                       Rule[rule], ctx_nomatch)
        @test out2 isa OpExpr && out2.op == "grad"
```

