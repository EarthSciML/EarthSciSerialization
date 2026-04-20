# DAE §12 — explicit dae_support=true overrides ESM_DAE_SUPPORT=0 (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/discretize_test.jl`

```julia
saved = get(ENV, "ESM_DAE_SUPPORT", nothing)
        ENV["ESM_DAE_SUPPORT"] = "0"
        try
            out = discretize(_mixed_dae_esm(); dae_support=true)
            @test out["metadata"]["system_class"] == "dae"
        finally
            if saved === nothing
                delete!(ENV, "ESM_DAE_SUPPORT")
            else
                ENV["ESM_DAE_SUPPORT"] = saved
```

