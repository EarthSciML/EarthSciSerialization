# Acceptance 3 — output re-parses through parse_expression (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/discretize_test.jl`

```julia
esm = _scalar_ode_esm()
        out = discretize(esm)
        rhs = out["models"]["M"]["equations"][1]["rhs"]
        parsed = EarthSciSerialization.parse_expression(rhs)
        @test parsed isa EarthSciSerialization.Expr
```

