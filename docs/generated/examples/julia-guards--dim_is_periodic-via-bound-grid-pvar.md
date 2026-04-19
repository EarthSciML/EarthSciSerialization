# guards: dim_is_periodic via bound grid pvar (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/rule_engine_test.jl`

```julia
# Pattern binds $g via var_has_grid, then dim_is_periodic consumes it.
        pat = op("grad", Any[VarExpr("\$u")])
        pat = OpExpr("grad", ESM_Expr[VarExpr("\$u")]; dim="\$x")
        repl = op("index", Any[VarExpr("\$u"), VarExpr("\$x")])
        guards = [
            Guard("var_has_grid",
                  Dict{String,Any}("pvar" => "\$u", "grid" => "\$g")),
            Guard("dim_is_periodic",
                  Dict{String,Any}("pvar" => "\$x", "grid" => "\$g")),
        ]
        rule = Rule("p_wrap", pat, guards, repl, nothing)
        ctx = RuleContext(
            Dict{String,Dict{String,Any}}(
                "g1" => Dict{String,Any}(
                    "spatial_dims" => ["x"],
                    "periodic_dims" => ["x"])),
            Dict{String,Dict{String,Any}}(
                "T" => Dict{String,Any}("grid" => "g1")))
        out = rewrite(OpExpr("grad", ESM_Expr[VarExpr("T")]; dim="x"),
                      Rule[rule], ctx)
        @test out isa OpExpr && out.op == "index"
```

