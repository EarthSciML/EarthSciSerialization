# compose (convenience for operator_compose) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/editing_test.jl`

```julia
file = EsmFile("0.1.0", Metadata("test"); coupling=CouplingEntry[])
        file2 = compose(file, "Atmosphere", "Ocean")
        @test length(file2.coupling) == 1
        entry = file2.coupling[1]
        @test entry isa CouplingOperatorCompose
        @test entry.systems == ["Atmosphere", "Ocean"]
```

