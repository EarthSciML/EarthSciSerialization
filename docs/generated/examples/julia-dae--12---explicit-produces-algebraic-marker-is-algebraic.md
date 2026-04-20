# DAE §12 — explicit produces:algebraic marker is algebraic (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/discretize_test.jl`

```julia
esm = _scalar_ode_esm()
        # Stamp produces:algebraic on the differential equation. The
        # classifier reads the marker first, so the equation must count
        # as algebraic even though its LHS is a time derivative.
        esm["models"]["M"]["equations"][1]["produces"] = "algebraic"
        out = discretize(esm)
        @test out["metadata"]["system_class"] == "dae"
        @test out["metadata"]["dae_info"]["algebraic_equation_count"] == 1
```

