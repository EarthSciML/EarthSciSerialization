# resolve_subsystem_refs! on file with reaction systems but no refs (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/subsystem_ref_test.jl`

```julia
species = [Species("O3", default=1e-6)]
        rsys = ReactionSystem(species, Reaction[])
        rsys_dict = Dict{String, ReactionSystem}("Chem" => rsys)
        metadata = Metadata("rsys_no_refs")
        file = EsmFile("0.1.0", metadata, reaction_systems=rsys_dict)

        resolve_subsystem_refs!(file, tempdir())
        @test haskey(file.reaction_systems, "Chem")
```

