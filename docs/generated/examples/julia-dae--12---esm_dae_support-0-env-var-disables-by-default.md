# DAE §12 — ESM_DAE_SUPPORT=0 env var disables by default (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/discretize_test.jl`

```julia
saved = get(ENV, "ESM_DAE_SUPPORT", nothing)
        ENV["ESM_DAE_SUPPORT"] = "0"
        try
            err = try
                discretize(_mixed_dae_esm())
                nothing
            catch e
                e
```

