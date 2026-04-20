# strict_unrewritten=false stamps passthrough and retains op (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/discretize_test.jl`

```julia
esm = _heat_1d_esm(; with_rule=false)
        out = discretize(esm; strict_unrewritten=false)
        eqn = out["models"]["M"]["equations"][1]
        @test eqn["passthrough"] === true
        @test occursin("\"grad\"", JSON3.write(eqn["rhs"]))
```

