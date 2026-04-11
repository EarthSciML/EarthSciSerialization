# merge combines two ESM files (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/editing_test.jl`

```julia
model_a = Model(Dict("x" => ModelVariable(StateVariable, default=1.0)), Equation[])
        model_b = Model(Dict("y" => ModelVariable(StateVariable, default=2.0)), Equation[])

        file_a = EsmFile("0.1.0", Metadata("a");
                         models=Dict("A" => model_a),
                         coupling=CouplingEntry[CouplingOperatorCompose(["A", "A"])])
        file_b = EsmFile("0.1.0", Metadata("b");
                         models=Dict("B" => model_b),
                         coupling=CouplingEntry[CouplingVariableMap("A.x", "B.y", "identity")])

        merged = ESS.merge(file_a, file_b)
        @test length(merged.models) == 2
        @test haskey(merged.models, "A")
        @test haskey(merged.models, "B")
        @test length(merged.coupling) == 2
        # file_b metadata wins
        @test merged.metadata.name == "b"
```

