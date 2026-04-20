# Acceptance 4 — E_UNREWRITTEN_PDE_OP on unmatched PDE op (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/discretize_test.jl`

```julia
esm = _heat_1d_esm(; with_rule=false)
        err = try
            discretize(esm)
            nothing
        catch e
            e
```

