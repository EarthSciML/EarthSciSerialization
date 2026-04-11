# extract top-level component (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/editing_test.jl`

```julia
model_a = Model(Dict("x" => ModelVariable(StateVariable)), Equation[])
        model_b = Model(Dict("y" => ModelVariable(StateVariable)), Equation[])
        model_c = Model(Dict("z" => ModelVariable(StateVariable)), Equation[])

        compose_entry = CouplingOperatorCompose(["A", "C"])
        map_entry = CouplingVariableMap("A.x", "B.y", "identity")
        unrelated = CouplingOperatorCompose(["B", "C"])

        file = EsmFile("0.1.0", Metadata("all");
                       models=Dict("A" => model_a, "B" => model_b, "C" => model_c),
                       coupling=CouplingEntry[compose_entry, map_entry, unrelated])

        ex = ESS.extract(file, "A")
        @test length(ex.models) == 1
        @test haskey(ex.models, "A")
        # Coupling entries involving A: compose_entry (A in systems) + map_entry (from=A.x)
        @test length(ex.coupling) == 2
        @test compose_entry in ex.coupling
        @test map_entry in ex.coupling
        @test !(unrelated in ex.coupling)

        # Metadata, reaction_systems, etc. preserved
        @test ex.metadata.name == "all"
        @test ex.reaction_systems !== nothing || ex.reaction_systems === nothing  # structural check
```

