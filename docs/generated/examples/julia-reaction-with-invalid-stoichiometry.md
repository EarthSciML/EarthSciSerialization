# Reaction with invalid stoichiometry (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/ESMFormat.jl/test/structural_validation_test.jl`

```julia
species = [ESMFormat.Species("A"), ESMFormat.Species("B")]
            reactions = [
                ESMFormat.Reaction("rxn1", [ESMFormat.StoichiometryEntry("A", -1)], [ESMFormat.StoichiometryEntry("B", 1)], ESMFormat.VarExpr("k1"))  # Negative stoichiometry
            ]
            rs = ESMFormat.ReactionSystem(species, reactions)
            esm_file = ESMFormat.EsmFile("0.1.0", metadata, reaction_systems=Dict("test_reactions" => rs))

            errors = ESMFormat.validate_structural(esm_file)
            @test length(errors) == 1
            @test errors[1].path == "reaction_systems.test_reactions.reactions[1].substrates"
            @test occursin("non-positive stoichiometry -1", errors[1].message)
            @test errors[1].error_type == "invalid_stoichiometry"
```

