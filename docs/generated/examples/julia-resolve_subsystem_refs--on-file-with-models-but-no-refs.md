# resolve_subsystem_refs! on file with models but no refs (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/subsystem_ref_test.jl`

```julia
vars = Dict{String, ModelVariable}(
            "T" => ModelVariable(StateVariable, default=300.0)
        )
        model = Model(vars, Equation[])
        models = Dict{String, Model}("Atm" => model)
        metadata = Metadata("model_no_refs")
        file = EsmFile("0.1.0", metadata, models=models)

        resolve_subsystem_refs!(file, tempdir())
        @test haskey(file.models, "Atm")
```

