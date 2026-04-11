# add_reaction / remove_reaction (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/editing_test.jl`

```julia
sys = _make_reaction_system()
        @test length(sys.reactions) == 1

        rxn2 = Reaction("r2", [SE("B", 1)], [SE("A", 1)], NumExpr(0.1))
        sys2 = add_reaction(sys, rxn2)
        @test length(sys2.reactions) == 2
        @test sys2.reactions[
```

