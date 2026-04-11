# 3. Autocatalytic A + B → 2B (net stoich of B is +1) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
species = [EarthSciSerialization.Species("A"),
                   EarthSciSerialization.Species("B")]
        rate = _op("*", _V("k"), _op("*", _V("A"), _V("B")))
        rxns = [EarthSciSerialization.Reaction("r1",
            [EarthSciSerialization.StoichiometryEntry("A", 1),
             EarthSciSerialization.StoichiometryEntry("B", 1)],
            [EarthSciSerialization.StoichiometryEntry("B", 2)],
            rate)]
        params = [EarthSciSerialization.Parameter("k", 0.3)]
        rsys = EarthSciSerialization.ReactionSystem(species, rxns, parameters=params)
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t3"),
            reaction_systems=Dict("Auto" => rsys))
        flat = flatten(file)

        eq_A = _find_eq(flat, "Auto.A")
        eq_B = _find_eq(flat, "Auto.B")
        @test eq_A !== nothing && eq_B !== nothing
        # Net stoich of B = 2 - 1 = +1 → a single positive rate term, no '-' or '*2'.
        # Spot-check: the B equation references k, A, and B.
        @test _uses_var(eq_B.rhs, "Auto.k")
        @test _uses_var(eq_B.rhs, "Auto.A")
        @test _uses_var(eq_B.rhs, "Auto.B")
        # A equation should have a negation (consumed).
        @test eq_A.rhs isa EarthSciSerialization.OpExpr
```

