# add_species / remove_species (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/editing_test.jl`

```julia
sys = _make_reaction_system()
        sys2 = add_species(sys, "C", Species("C", default=2.0))
        @test length(sys2.species) == 3
        @test any(s -> s.name == "C", sys2.species)

        # Remove the fresh species (no reaction dep
```

