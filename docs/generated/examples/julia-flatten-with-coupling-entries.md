# Flatten with coupling entries (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
vars1 = Dict{String, ModelVariable}(
            "T" => ModelVariable(StateVariable, default=300.0)
        )
        vars2 = Dict{String, ModelVariable}(
            "SST" => ModelVariable(StateVariable, default=290.0)
        )
        model1 = Model(vars1, Equation[])
        model2 = Model(vars2, Equation[])

        coupling = CouplingEntry[
            CouplingOperatorCompose(["Atm", "Ocean"], description="Compose atmosphere and ocean"),
            CouplingVariableMap("Atm.T", "Ocean.SST", "identity", description="Map T to SST")
        ]

        models = Dict{String, Model}("Atm" => model1, "Ocean" => model2)
        metadata = Metadata("coupling_test")
        file = EsmFile("0.1.0", metadata, models=models, coupling=coupling)

        flat = flatten(file)

        @test length(flat.metadata.coupling_rules) == 2
        @test occursin("operator_compose", flat.metadata.coupling_rules[1])
        @test occursin("variable_map", flat.metadata.coupling_rules[2])
        @test occursin("Atm", flat.metadata.coupling_rules[1])
        @test occursin("Ocean", flat.metadata.coupling_rules[1])
```

