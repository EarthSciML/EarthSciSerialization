# Acceptance 1 — runs end-to-end on a scalar ODE (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/discretize_test.jl`

```julia
esm = _scalar_ode_esm()
        out = discretize(esm)
        @test out isa Dict{String,Any}
        @test haskey(out["metadata"], "discretized_from")
        @test out["metadata"]["discretized_from"]["name"] == "scalar_ode"
        @test "discretized" in String.(out["metadata"]["tags"])
        # Input must not be mutated.
        @test !haskey(esm["metadata"], "discretized_from")
```

