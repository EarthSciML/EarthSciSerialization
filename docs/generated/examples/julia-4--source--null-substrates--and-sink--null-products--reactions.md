# 4. Source (null substrates) and sink (null products) reactions (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
species = [EarthSciSerialization.Species("X")]
        source = EarthSciSerialization.Reaction("src", nothing,
            [EarthSciSerialization.StoichiometryEntry("X", 1)],
            _V("kin"))
        sink = EarthSciSerialization.Reaction("snk",
            [EarthSciSerialization.StoichiometryEntry("X", 1)], nothing,
            _op("*", _V("kout"), _V("X")))
        params = [EarthSciSerialization.Parameter("kin", 1.0),
                  EarthSciSerialization.Parameter("kout", 0.5)]
        rsys = EarthSciSerialization.ReactionSystem(species, [source, sink], parameters=params)
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t4"),
            reaction_systems=Dict("S" => rsys))
        flat = flatten(file)

        eq_X = _find_eq(flat, "S.X")
        @test eq_X !== nothing
        @test _uses_var(eq_X.rhs, "S.kin")
        @test _uses_var(eq_X.rhs, "S.kout")
```

