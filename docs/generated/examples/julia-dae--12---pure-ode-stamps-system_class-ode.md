# DAE §12 — pure ODE stamps system_class=ode (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/discretize_test.jl`

```julia
out = discretize(_scalar_ode_esm())
        @test out["metadata"]["system_class"] == "ode"
        info = out["metadata"]["dae_info"]
        @test info["algebraic_equation_count"] == 0
        @test info["per_model"]["M"] == 0
```

