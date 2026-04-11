# lower_reactions_to_equations helper (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
species = [EarthSciSerialization.Species("A"),
                   EarthSciSerialization.Species("B")]
        rxns = [EarthSciSerialization.Reaction("r1",
            [EarthSciSerialization.StoichiometryEntry("A", 1)],
            [EarthSciSerialization.StoichiometryEntry("B", 1)],
            _V("k"))]
        eqs = lower_reactions_to_equations(rxns, species)
        @test length(eqs) == 2
        # Every equation is a D(species, t) = ... form.
        for eq in eqs
            @test eq.lhs isa EarthSciSerialization.OpExpr
            @test eq.lhs.op == "D"
```

