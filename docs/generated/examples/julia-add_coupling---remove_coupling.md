# add_coupling / remove_coupling (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/editing_test.jl`

```julia
file = EsmFile("0.1.0", Metadata("test"); coupling=CouplingEntry[])
        @test length(file.coupling) == 0

        entry1 = CouplingOperatorCompose(["A", "B"]; description="compose AB")
        file1 = add_coupling(file, entry1)
        @test length(file1.coupling) == 1
        @test file1.coupling[1] isa CouplingOperatorCompose
        @test file1.coupling[1].systems == ["A", "B"]

        entry2 = CouplingVariableMap("A.x", "B.y", "identity")
        file2 = add_coupling(file1, entry2)
        @test length(file2.coupling) == 2

        file3 = remove_coupling(file2, 1)
        @test length(file3.coupling) == 1
        @test file3.coupling[1] isa CouplingVariableMap

        # Out-of-bounds remove: warning, unchanged
        file4 = @test_logs (:warn,) match_mode=:any remove_coupling(file3, 99)
        @test length(file4.coupling) == length(file3.coupling)
```

