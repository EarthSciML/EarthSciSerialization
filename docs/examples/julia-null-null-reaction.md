# Null-null reaction (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/structural_validation_test.jl`

```julia
species = [ESMFormat.Species("A")]
            reactions = [
                ESMFormat.Reaction(Dict{String,Int}(), Dict{String,Int}(), ESMFormat.VarExpr("k1"))  # No reactants or products
            ]
            rs = ESMFormat.ReactionSystem(species, reactions)
            esm_file = ESMFormat.EsmFile("0.1.0", metadata, reaction_systems=Dict("test_reactions" => rs))

            errors = ESMFormat.validate_structural(esm_file)
            @test length(errors) == 1
            @test errors[1].path == "reaction_systems.test_reactions.reactions[1]"
            @test occursin("null-null reaction", errors[1].message)
            @test errors[1].error_type == "null_reaction"
```

