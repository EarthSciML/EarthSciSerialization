# ESM-specific units standard (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/units_test.jl`

```julia
# docs/units-standard.md: every binding must accept these and agree
        # on dimension semantics so cross-binding documents resolve alike.
        # Mole-fraction family: dimensionless.
        for u in ("mol/mol", "ppm", "ppmv", "ppb", "ppbv", "ppt", "pptv")
            parsed = EarthSciSerialization.parse_units(u)
            @test parsed !== nothing
            @test dimension(parsed) == dimension(Unitful.NoUnits)
```

