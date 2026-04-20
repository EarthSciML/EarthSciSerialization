# DAE §12 — pure ODE passes even with dae_support=false (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/discretize_test.jl`

```julia
out = discretize(_scalar_ode_esm(); dae_support=false)
        @test out["metadata"]["system_class"] == "ode"
```

