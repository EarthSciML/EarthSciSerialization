# Acceptance 1 — runs end-to-end on a 1D PDE with a matching rule (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/discretize_test.jl`

```julia
esm = _heat_1d_esm(; with_rule=true)
        out = discretize(esm)
        rhs = out["models"]["M"]["equations"][1]["rhs"]
        # After rewrite, RHS should be the indexed form; no grad op left.
        @test !occursin("\"grad\"", JSON3.write(rhs))
        @test occursin("\"index\"", JSON3.write(rhs))
```

