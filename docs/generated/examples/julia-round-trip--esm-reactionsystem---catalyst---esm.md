# Round-trip: ESM ReactionSystem → Catalyst → ESM (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/catalyst_extension_test.jl`

```julia
species = [
            EarthSciSerialization.Species("A"),
            EarthSciSerialization.Species("B"),
        ]
        params = [EarthSciSerialization.Parameter("k", 1.0)]
        rxns = EarthSciSerialization.Reaction[
            EarthSciSerialization.Reaction(Dict("A" => 1), Dict("B" => 1),
                                           VarExpr("k")),
        ]
        esm_rsys = EarthSciSerialization.ReactionSystem(species, rxns;
                                                        parameters=params)
        cat_rsys = Catalyst.ReactionSystem(esm_rsys; name=:AB)
        recovered = EarthSciSerialization.ReactionSystem(cat_rsys)
        @test length(recovered.species) == 2
        @test length(recovered.parameters) == 1
        @test length(recovered.reactions) == 1
```

