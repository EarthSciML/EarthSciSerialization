# substitute preserves reaction-system structure (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/editing_test.jl`

```julia
# Rate is a bare variable "param"; binding param -> k swaps the rate
        # reference onto an existing parameter.
        rxn = Reaction("R1", nothing, [SE("A", 1)], VarExpr("param"))
        sys = ReactionSystem(
            [Species("A", default=18.0)],
            [rxn];
            parameters=[Parameter("k", 0.1; units="1/s")],
        )

        bindings = Dict{String,ESS.Expr}("param" => VarExpr("k"))
        new_rate = substitute(sys.reactions[1].rate, bindings)

        # Rewritten rate is the bound VarExpr.
        @test new_rate isa VarExpr && new_rate.name == "k"

        # Species/parameter metadata and reaction identity untouched —
        # ensures coupling references (species names, parameter names,
        # reaction ids) remain consistent across substitution.
        @test sys.species[1].default == 18.0
        @test sys.parameters[1].units == "1/s"
        @test sys.reactions[1].id == "R1"
        @test getfield(sys.reactions[1], :products) == [SE("A", 1)]
```

