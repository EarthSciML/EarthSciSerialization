# DAE §12 — mixed DAE stamps system_class=dae (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/discretize_test.jl`

```julia
out = discretize(_mixed_dae_esm())
        @test out["metadata"]["system_class"] == "dae"
        info = out["metadata"]["dae_info"]
        @test info["algebraic_equation_count"] == 1
        @test info["per_model"]["M"] == 1
```

