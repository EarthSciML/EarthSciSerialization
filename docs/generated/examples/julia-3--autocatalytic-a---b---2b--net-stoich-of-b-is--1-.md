# 3. Autocatalytic A + B → 2B (net stoich of B is +1) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
species = [EarthSciSerialization.Species("A"),
                   EarthSciSerialization.Species("B")]
        # Pass k as the rate constant. `mass_action_rate` multiplies by the
        # substrate concentrations (A and B) to form the full rate expression.
        rate = _V("k")
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

        # Net stoich of B = 2 - 1 = +1. The reaction lowering MUST take the
        # `stoich == 1` branch, which passes the mass_action_rate expression
        # through unmodified — i.e. eq_B.rhs is exactly `k * A * B` with:
        #
        #   - a top-level OpExpr("*") (not "+" and not "-")
        #   - no leading NumExpr coefficient (no `2*rate` artifact)
        #   - references to k, A, and B
        #
        # This distinguishes the correct +1 case from the incorrect
        # structures `2*rate + (-rate)` (would be top-level "+"),
        # `2*rate` (would have a leading NumExpr(2)), or `-rate` (would be
        # top-level unary "-").
        @test eq_B.rhs isa EarthSciSerialization.OpExpr
        top_B = eq_B.rhs::EarthSciSerialization.OpExpr
        @test top_B.op == "*"
        @test top_B.op != "+"
        @test top_B.op != "-"
        @test !any(a -> a isa EarthSciSerialization.NumExpr, top_B.args)
        @test _uses_var(eq_B.rhs, "Auto.k")
        @test _uses_var(eq_B.rhs, "Auto.A")
        @test _uses_var(eq_B.rhs, "Auto.B")

        # Net stoich of A = -1. The A equation MUST take the `stoich == -1`
        # branch, which wraps the mass_action_rate term in a unary negation.
        # Structurally: eq_A.rhs is OpExpr("-", [rate_expr]) — a unary minus
        # with exactly one arg that itself contains k, A, and B.
        @test eq_A.rhs isa EarthSciSerialization.OpExpr
        top_A = eq_A.rhs::EarthSciSerialization.OpExpr
        @test top_A.op == "-"
        @test length(top_A.args) == 1
        @test _uses_var(eq_A.rhs, "Auto.k")
        @test _uses_var(eq_A.rhs, "Auto.A")
        @test _uses_var(eq_A.rhs, "Auto.B")
```

