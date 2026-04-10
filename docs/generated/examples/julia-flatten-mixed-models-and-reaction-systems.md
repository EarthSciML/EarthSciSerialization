# Flatten mixed models and reaction systems (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
model_vars = Dict{String, ModelVariable}(
            "T" => ModelVariable(StateVariable, default=300.0)
        )
        model = Model(model_vars, Equation[])

        species = [Species("O3", default=1e-6)]
        rsys = ReactionSystem(species, Reaction[])

        models = Dict{String, Model}("Climate" => model)
        rsys_dict = Dict{String, ReactionSystem}("Chemistry" => rsys)
        metadata = Metadata("mixed_test")
        file = EsmFile("0.1.0", metadata, models=models, reaction_systems=rsys_dict)

        flat = flatten(file)

        @test "Climate.T" in flat.state_variables
        @test "Chemistry.O3" in flat.state_variables
        @test flat.variables["Climate.T"] == "state"
        @test flat.variables["Chemistry.O3"] == "species"
        @test length(flat.metadata.source_systems) == 2
```

