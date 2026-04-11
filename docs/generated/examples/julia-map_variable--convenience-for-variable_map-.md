# map_variable (convenience for variable_map) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/editing_test.jl`

```julia
file = EsmFile("0.1.0", Metadata("test"); coupling=CouplingEntry[])
        file2 = map_variable(file, "Atmosphere.T", "Ocean.T_surf"; transform="identity")
        @test length(file2.coupling) == 1
        entry = file2.coupling[1]
        @test entry isa CouplingVariableMap
        @test entry.from == "Atmosphere.T"
        @test entry.to == "Ocean.T_surf"
        @test entry.transform == "identity"
```

