# DAE §12 — dae_support=false aborts with E_NO_DAE_SUPPORT (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/discretize_test.jl`

```julia
err = try
            discretize(_mixed_dae_esm(); dae_support=false)
            nothing
        catch e
            e
```

