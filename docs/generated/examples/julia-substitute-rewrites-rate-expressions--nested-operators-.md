# substitute rewrites rate expressions (nested operators) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/editing_test.jl`

```julia
# Rate: k * temp^2, bindings: k -> 0.1, temp -> T
        inner = OpExpr("^", ESS.Expr[VarExpr("temp"), NumExpr(2.0)])
        rate = OpExpr("*", ESS.Expr[VarExpr("k"), inner])
        # Source reaction (no substrates) to mirror the Python fixture shape.
        rxn = Reaction("R1", nothing, [SE("A", 1)], rate)
        sys = ReactionSystem([Species("A")], [rxn])

        bindings = Dict{String,ESS.Expr}(
            "k" => NumExpr(0.1),
            "temp" => VarExpr("T"),
        )
        new_rate = substitute(sys.reactions[1].rate, bindings)

        # Expected: 0.1 * (T ^ 2)
        @test new_rate isa OpExpr && new_rate.op == "*"
        @test new_rate.args[1] isa NumExpr && new_rate.args[1].value == 0.1
        @test new_rate.args[2] isa OpExpr && new_rate.args[2].op == "^"
        @test new_rate.args[2].args[1] isa VarExpr &&
              new_rate.args[2].args[1].name == "T"
        @test new_rate.args[2].args[2] isa NumExpr &&
              new_rate.args[2].args[2].value == 2.0

        # Source reaction shape preserved: substrates remain `nothing`,
        # products still reference species "A". Use getfield to bypass the
        # Dict-returning property shim.
        @test getfield(sys.reactions[1], :substrates) === nothing
        @test getfield(sys.reactions[1], :products) == [SE("A", 1)]
```

