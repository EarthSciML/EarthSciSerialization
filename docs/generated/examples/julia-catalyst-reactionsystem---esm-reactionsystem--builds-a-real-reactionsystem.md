# Catalyst.ReactionSystem(::ESM ReactionSystem) builds a real ReactionSystem (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/catalyst_extension_test.jl`

```julia
species = [
            EarthSciSerialization.Species("NO"),
            EarthSciSerialization.Species("O3"),
            EarthSciSerialization.Species("NO2"),
        ]
        params = [EarthSciSerialization.Parameter("k", 1.8e-12)]
        rxn_list = EarthSciSerialization.Reaction[
            EarthSciSerialization.Reaction(Dict("NO" => 1, "O3" => 1),
                                           Dict("NO2" => 1),
                                           VarExpr("k")),
        ]
        esm_rsys = EarthSciSerialization.ReactionSystem(species, rxn_list;
                                                        parameters=params)

        cat_rsys = Catalyst.ReactionSystem(esm_rsys; name=:OzonePhoto)
        @test !(cat_rsys isa MockCatalystSystem)
        @test occursin("ReactionSystem", string(typeof(cat_rsys)))

        species_names = Set(string(Catalyst.getname(s))
                            for s in Catalyst.species(cat_rsys))
        @test "NO(t)" in species_names || "NO" in species_names
        @test "O3(t)" in species_names || "O3" in species_names

        param_names = Set(string(Catalyst.getname(p))
                          for p in Catalyst.parameters(cat_rsys))
        @test "k" in param_names
```

