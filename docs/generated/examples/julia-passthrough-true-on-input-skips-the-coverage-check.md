# passthrough=true on input skips the coverage check (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/discretize_test.jl`

```julia
esm = _heat_1d_esm(; with_rule=false)
        esm["models"]["M"]["equations"][1]["passthrough"] = true
        out = discretize(esm)  # default strict_unrewritten=true is fine
        @test out["models"]["M"]["equations"][1]["passthrough"] === true
```

