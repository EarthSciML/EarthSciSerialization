# Flatten model with subsystems (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
# Inner subsystem
        inner_vars = Dict{String, ModelVariable}(
            "x" => ModelVariable(StateVariable, default=1.0)
        )
        inner_model = Model(inner_vars, Equation[])

        # Outer model with subsystem
        outer_vars = Dict{String, ModelVariable}(
            "y" => ModelVariable(StateVariable, default=2.0)
        )
        outer_model = Model(outer_vars, Equation[],
                           subsystems=Dict{String, Model}("Inner" => inner_model))

        models = Dict{String, Model}("Outer" => outer_model)
        metadata = Metadata("subsystem_test")
        file = EsmFile("0.1.0", metadata, models=models)

        flat = flatten(file)

        @test "Outer.y" in flat.state_variables
        @test "Outer.Inner.x" in flat.state_variables
        @test flat.variables["Outer.y"] == "state"
        @test flat.variables["Outer.Inner.x"] == "state"
```

