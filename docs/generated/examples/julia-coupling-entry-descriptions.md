# Coupling entry descriptions (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
entry1 = CouplingOperatorCompose(["A", "B"], description="Test compose")
        desc1 = EarthSciSerialization.describe_coupling_entry(entry1)
        @test occursin("operator_compose", desc1)
        @test occursin("A + B", desc1)
        @test occursin("Test compose", desc1)

        entry2 = CouplingVariableMap("A.x", "B.y", "identity")
        desc2 = EarthSciSerialization.describe_coupling_entry(entry2)
        @test occursin("variable_map", desc2)
        @test occursin("A.x", desc2)
        @test occursin("B.y", desc2)
        @test occursin("identity", desc2)

        entry3 = CouplingVariableMap("A.x", "B.y", "conversion_factor", factor=2.5)
        desc3 = EarthSciSerialization.describe_coupling_entry(entry3)
        @test occursin("2.5", desc3)

        entry4 = CouplingOperatorApply("MyOp", description="Apply op")
        desc4 = EarthSciSerialization.describe_coupling_entry(entry4)
        @test occursin("operator_apply", desc4)
        @test occursin("MyOp", desc4)

        entry5 = CouplingCallback("cb1", description="A callback")
        desc5 = EarthSciSerialization.describe_coupling_entry(entry5)
        @test occursin("callback", desc5)
        @test occursin("cb1", desc5)
```

