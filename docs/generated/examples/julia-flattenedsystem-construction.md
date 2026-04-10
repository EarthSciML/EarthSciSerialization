# FlattenedSystem construction (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
fs = FlattenedSystem(
            ["Atm.T"],
            ["Atm.k"],
            Dict("Atm.T" => "state", "Atm.k" => "parameter"),
            [FlattenedEquation("Atm.T", "Atm.k * Atm.T", "Atm")],
            FlattenMetadata(["Atm"], String[])
        )
        @test length(fs.state_variables) == 1
        @test length(fs.parameters) == 1
        @test fs.variables["Atm.T"] == "state"
        @test fs.variables["Atm.k"] == "parameter"
```

