# Reaction with invalid stoichiometry (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/EarthSciSerialization.jl/test/structural_validation_test.jl`

```julia
species = [EarthSciSerialization.Species("A"), EarthSciSerialization.Species("B")]
            reactions = [
                EarthSciSerialization.Reaction(Dict("A" => -1), Dict("B" => 1), EarthSciSerialization.VarExpr("k1"))  # Negative stoichiometry
            ]
            rs = EarthSciSerialization.ReactionSystem(species, reactions)
            esm_file = EarthSciSerialization.EsmFile("0.1.0", metadata, reaction_systems=Dict("test_reactions" => rs))

            errors = EarthSciSerialization.validate_structural(esm_file)
            @test length(errors) == 1
            @test errors[1].path == "reaction_systems.test_reactions.reactions[1].reactants"
            @test occursin("non-positive stoichiometry -1", errors[1].message)
            @test errors[1].error_type == "invalid_stoichiometry"
```

