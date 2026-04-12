# Mass Action Rate Tests (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/reactions_test.jl`

```julia
species_A = Species("A")
        species_B = Species("B")
        species_C = Species("C")
        species = [species_A, species_B, species_C]

        # Test simple reaction A + B -> C
        reaction = Reaction(
            Dict("A" => 1, "B" => 1),
            Dict("C" => 1),
            VarExpr("k1")
        )

        rate_expr = mass_action_rate(reaction, species)
        @test rate_expr isa OpExpr
        @test rate_expr.op == "*"
        @test length(rate_expr.args) == 3  # k1 * A * B
        @test rate_expr.args[1] isa VarExpr
        @test rate_expr.args[1].name == "k1"

        # Test source reaction: -> A
        source_reaction = Reaction(Dict{String,Int}(), Dict("A" => 1), VarExpr("k_source"))
        source_rate = mass_action_rate(source_reaction, species)
        @test source_rate isa VarExpr
        @test source_rate.name == "k_source"

        # Test higher stoichiometry: 2A -> B
        high_stoich_reaction = Reaction(
            Dict("A" => 2),
            Dict("B" => 1),
            VarExpr("k_high")
        )
        high_rate = mass_action_rate(high_stoich_reaction, species)
        @test high_rate isa OpExpr
        @test high_rate.op == "*"
        @test length(high_rate.args) == 2  # k_high * A^2
        @test high_rate.args[1].name == "k_high"
        @test high_rate.args[2] isa OpExpr
        @test high_rate.args[2].op == "^"
        @test high_rate.args[2].args[1].name == "A"
        @test high_rate.args[2].args[2].value == 2.0

        # Test single reactant: A -> B
        single_reaction = Reaction(
            Dict("A" => 1),
            Dict("B" => 1),
            VarExpr("k_single")
        )
        single_rate = mass_action_rate(single_reaction, species)
        @test single_rate isa OpExpr
        @test single_rate.op == "*"
        @test length(single_rate.args) == 2  # k_single * A

        # gt-p60 regression: if the user-supplied rate already references
        # substrate concentrations (i.e. they gave us a full rate law, not
        # a rate coefficient), mass_action_rate MUST return it unchanged
        # rather than double-applying the substrate multiplication and
        # producing `k*A²*B²` for a `rate=k*A*B` bimolecular reaction.
        full_rate = OpExpr("*",
            EarthSciSerialization.Expr[VarExpr("k_full"),
                                       VarExpr("A"), VarExpr("B")])
        full_reaction = Reaction(
            Dict("A" => 1, "B" => 1),
            Dict("C" => 1),
            full_rate,
        )
        full_result = mass_action_rate(full_reaction, species)
        # Result is exactly the user's rate expression, unwrapped.
        @test full_result === full_rate
        @test full_result isa OpExpr
        @test full_result.op == "*"
        @test length(full_result.args) == 3
        # Each substrate variable appears EXACTLY once in the rate law.
        _uses_full(expr, name) = expr isa VarExpr ? expr.name == name :
            (expr isa OpExpr && any(a -> _uses_full(a, name), expr.args))
        _count_full(expr, name) = if expr isa VarExpr
            expr.name == name ? 1 : 0
        elseif expr isa OpExpr
            isempty(expr.args) ? 0 : sum(a -> _count_full(a, name), expr.args)
        else
            0
```

