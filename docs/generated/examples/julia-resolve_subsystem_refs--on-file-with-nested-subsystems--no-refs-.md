# resolve_subsystem_refs! on file with nested subsystems (no refs) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/subsystem_ref_test.jl`

```julia
inner_vars = Dict{String, ModelVariable}(
            "x" => ModelVariable(StateVariable, default=1.0)
        )
        inner = Model(inner_vars, Equation[])

        outer_vars = Dict{String, ModelVariable}(
            "y" => ModelVariable(StateVariable, default=2.0)
        )
        outer = Model(outer_vars, Equation[], subsystems=Dict{String, Model}("Inner" => inner))

        models = Dict{String, Model}("Outer" => outer)
        metadata = Metadata("nested_no_refs")
        file = EsmFile("0.1.0", metadata, models=models)

        resolve_subsystem_refs!(file, tempdir())
        @test haskey(file.models["Outer"].subsystems, "Inner")
```

