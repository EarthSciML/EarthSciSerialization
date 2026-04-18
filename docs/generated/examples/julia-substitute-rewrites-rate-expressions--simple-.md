# substitute rewrites rate expressions (simple) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/editing_test.jl`

```julia
# Rate: k * param_rate, bindings: param_rate -> A
        rate = OpExpr("*", ESS.Expr[VarExpr("k"), VarExpr("param_rate")])
        rxn = Reaction("R1", [SE("A", 1)], [SE("B", 1)], rate)
        sys = ReactionSystem(
            [Species("A"), Species("B")],
            [rxn];
            parameters=[Parameter("k", 0.1)],
        )

        bindings = Dict{String,ESS.Expr}("param_rate" => VarExpr("A"))
        new_rate = substitute(sys.reactions[1].rate, bindings)

        @test new_rate isa OpExpr
        @test new_rate.op == "*"
        @test new_rate.args[1] isa VarExpr && new_rate.args[1].name == "k"
        @test new_rate.args[2] isa VarExpr && new_rate.args[2].name == "A"

        # Substituting the rate must not disturb coupling references:
        # substrates/products still point to "A" / "B" with the original
        # stoichiometries, and species/parameter lists are unchanged.
        # Raw field access — `.products`/`.reactants` go through a
        # backward-compat Dict shim (see types.jl getproperty).
        @test getfield(sys.reactions[1], :substrates) == [SE("A", 1)]
        @test getfield(sys.reactions[1], :products) == [SE("B", 1)]
        @test [s.name for s in sys.species] == ["A", "B"]
        @test [p.name for p in sys.parameters] == ["k"]
```

