# Fractional stoichiometry survives Catalyst → ESM reverse (gt-3ai5) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/catalyst_extension_test.jl`

```julia
# Catalyst ReactionSystems with fractional stoichiometry (e.g.
        # CH3O2+CH3O2 -> 2.0 CH2O + 0.8 HO2) must reverse-convert without
        # Int() truncation. Prior to the fix, Int(0.8) raised InexactError.
        species = [
            EarthSciSerialization.Species("CH3O2"),
            EarthSciSerialization.Species("CH2O"),
            EarthSciSerialization.Species("HO2"),
        ]
        params = [EarthSciSerialization.Parameter("k", 1.0e-13)]
        rxns = EarthSciSerialization.Reaction[
            EarthSciSerialization.Reaction(Dict("CH3O2" => 2.0),
                                           Dict("CH2O" => 2.0, "HO2" => 0.8),
                                           VarExpr("k")),
        ]
        esm_rsys = EarthSciSerialization.ReactionSystem(species, rxns;
                                                        parameters=params)
        cat_rsys = Catalyst.ReactionSystem(esm_rsys; name=:FracStoich)
        recovered = EarthSciSerialization.ReactionSystem(cat_rsys)
        @test length(recovered.reactions) == 1
        rxn = recovered.reactions[1]
        # rxn.reactants / rxn.products return Dict{String,Float64} via the
        # backward-compatibility getproperty intercept.
        @test rxn.reactants["CH3O2"] ≈ 2.0
        @test rxn.products["CH2O"]  ≈ 2.0
        @test rxn.products["HO2"]   ≈ 0.8
```

