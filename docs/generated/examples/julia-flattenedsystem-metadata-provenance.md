# FlattenedSystem metadata provenance (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
v1 = Dict{String, ModelVariable}("x" => ModelVariable(StateVariable))
        m1 = Model(v1, Equation[])
        v2 = Dict{String, ModelVariable}("y" => ModelVariable(StateVariable))
        m2 = Model(v2, Equation[])
        coupling = CouplingEntry[
            CouplingOperatorApply("my_op"),
            CouplingCallback("cb1"),
        ]
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("mdata"),
            models=Dict("A" => m1, "B" => m2),
            coupling=coupling)
        flat = flatten(file)
        @test "A" in flat.metadata.source_systems
        @test "B" in flat.metadata.source_systems
        @test length(flat.metadata.coupling_rules_applied) == 2
        @test "operator_apply:my_op" in flat.metadata.opaque_coupling_refs
        @test "callback:cb1" in flat.metadata.opaque_coupling_refs
```

