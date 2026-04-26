# Null-null reaction (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/EarthSciSerialization.jl/test/structural_validation_test.jl`

```julia
species = [EarthSciSerialization.Species("A")]
            reactions = [
                EarthSciSerialization.Reaction(Dict{String,Int}(), Dict{String,Int}(), EarthSciSerialization.VarExpr("k1"))  # No reactants or products
            ]
            rs = EarthSciSerialization.ReactionSystem(species, reactions)
            esm_file = EarthSciSerialization.EsmFile("0.1.0", metadata, reaction_systems=Dict("test_reactions" => rs))

            errors = EarthSciSerialization.validate_structural(esm_file)
            @test length(errors) == 1
            @test errors[1].path == "reaction_systems.test_reactions.reactions[1]"
            @test occursin("null-null reaction", errors[1].message)
            @test errors[1].error_type == "null_reaction"
```

