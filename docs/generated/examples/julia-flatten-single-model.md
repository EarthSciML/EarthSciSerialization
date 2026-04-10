# Flatten single model (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
vars = Dict{String, ModelVariable}(
            "T" => ModelVariable(StateVariable, default=300.0, description="Temperature"),
            "k" => ModelVariable(ParameterVariable, default=0.1),
            "obs" => ModelVariable(ObservedVariable)
        )

        lhs = OpExpr("D", EarthSciSerialization.Expr[VarExpr("T")], wrt="t")
        rhs = OpExpr("*", EarthSciSerialization.Expr[VarExpr("k"), VarExpr("T")])
        eqs = [Equation(lhs, rhs)]

        model = Model(vars, eqs)
        models = Dict{String, Model}("Atmosphere" => model)
        metadata = Metadata("single_model_test")
        file = EsmFile("0.1.0", metadata, models=models)

        flat = flatten(file)

        @test "Atmosphere.T" in flat.state_variables
        @test "Atmosphere.k" in flat.parameters
        @test flat.variables["Atmosphere.T"] == "state"
        @test flat.variables["Atmosphere.k"] == "parameter"
        @test flat.variables["Atmosphere.obs"] == "observed"
        @test length(flat.equations) == 1
        @test flat.equations[1].source_system == "Atmosphere"
        @test occursin("Atmosphere.T", flat.equations[1].lhs)
        @test occursin("Atmosphere.k", flat.equations[1].rhs)
        @test "Atmosphere" in flat.metadata.source_systems
```

