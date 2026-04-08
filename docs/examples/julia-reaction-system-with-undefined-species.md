# Reaction system with undefined species (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/structural_validation_test.jl`

```julia
species = [ESMFormat.Species("A"), ESMFormat.Species("B")]
            reactions = [
                ESMFormat.Reaction(Dict("A" => 1), Dict("C" => 1), ESMFormat.VarExpr("k1"))  # C not defined
            ]
            rs = ESMFormat.ReactionSystem(species, reactions)
            esm_file = ESMFormat.EsmFile("0.1.0", metadata, reaction_systems=Dict("test_reactions" => rs))

            errors = ESMFormat.validate_structural(esm_file)
            @test length(errors) == 1
            @test errors[1].path == "reaction_systems.test_reactions.reactions[1].products"
            @test occursin("Species 'C' not declared", errors[1].message)
            @test errors[1].error_type == "undefined_species"
```

