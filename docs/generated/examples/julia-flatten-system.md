# Flatten System (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
@testset "1. Reactions-only Model" begin
        species = [EarthSciSerialization.Species("A", default=1.0),
                   EarthSciSerialization.Species("B", default=0.0)]
        params = [EarthSciSerialization.Parameter("k", 0.1)]
        rate = _op("*", _V("k"), _V("A"))
        rxns = [EarthSciSerialization.Reaction("r1",
            [EarthSciSerialization.StoichiometryEntry("A", 1)],
            [EarthSciSerialization.StoichiometryEntry("B", 1)],
            rate)]
        rsys = EarthSciSerialization.ReactionSystem(species, rxns, parameters=params)
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t1"),
            reaction_systems=Dict("Chem" => rsys))
        flat = flatten(file)

        @test haskey(flat.state_variables, "Chem.A")
        @test haskey(flat.state_variables, "Chem.B")
        @test haskey(flat.parameters, "Chem.k")
        @test length(flat.equations) == 2

        eq_A = _find_eq(flat, "Chem.A")
        eq_B = _find_eq(flat, "Chem.B")
        @test eq_A !== nothing && eq_B !== nothing
        # d[A]/dt = -k*A
        @test _uses_var(eq_A.rhs, "Chem.k") && _uses_var(eq_A.rhs, "Chem.A")
        # d[B]/dt = +k*A
        @test _uses_var(eq_B.rhs, "Chem.k") && _uses_var(eq_B.rhs, "Chem.A")
```

