# Reservoir species (constant=true) maps to isconstantspecies (gt-ertm) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/catalyst_extension_test.jl`

```julia
# Reservoir species must flow through Catalyst as parameters with the
        # isconstantspecies=true metadata (modern Catalyst rejects this
        # metadata on @species). The reverse direction recovers them as ESM
        # species with constant=true rather than as ordinary parameters.
        species = [
            EarthSciSerialization.Species("O2"; constant=true),
            EarthSciSerialization.Species("CH4"; constant=true),
            EarthSciSerialization.Species("OH"),
        ]
        params = [EarthSciSerialization.Parameter("k", 1e-14)]
        rxns = EarthSciSerialization.Reaction[
            EarthSciSerialization.Reaction(Dict("CH4" => 1, "OH" => 1),
                                           Dict("O2" => 1),
                                           VarExpr("k")),
        ]
        esm_rsys = EarthSciSerialization.ReactionSystem(species, rxns;
                                                        parameters=params)
        cat_rsys = Catalyst.ReactionSystem(esm_rsys; name=:Reservoir)

        # Check that O2 and CH4 are constant species (metadata-tagged
        # parameters in Catalyst), while OH remains a state species.
        constant_names = Set(String[])
        for p in Catalyst.parameters(cat_rsys)
            if Catalyst.isconstant(p)
                push!(constant_names, string(Catalyst.getname(p)))
```

