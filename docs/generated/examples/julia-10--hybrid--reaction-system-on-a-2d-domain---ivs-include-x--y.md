# 10. HYBRID: reaction system on a 2D domain → IVs include x, y (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
domains = Dict{String, Domain}(
            "grid" => Domain(spatial=Dict{String,Any}("x"=>Dict(), "y"=>Dict())))
        species = [EarthSciSerialization.Species("O3", default=1e-6)]
        params = [EarthSciSerialization.Parameter("k", 0.1)]
        rate = _op("*", _V("k"), _V("O3"))
        rxns = [EarthSciSerialization.Reaction("r1",
            [EarthSciSerialization.StoichiometryEntry("O3", 1)], nothing, rate)]
        rsys = EarthSciSerialization.ReactionSystem(species, rxns,
            parameters=params, domain="grid")
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t10"),
            reaction_systems=Dict("Chem" => rsys),
            domains=domains)
        flat = flatten(file)

        @test :t in flat.indep
```

