# 9. Nested subsystems produce full dot paths (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
inner_v = Dict{String, ModelVariable}("v" => ModelVariable(StateVariable))
        inner = Model(inner_v, Equation[])
        outer_v = Dict{String, ModelVariable}("u" => ModelVariable(StateVariable))
        outer = Model(outer_v, Equation[],
            subsystems=Dict{String, Model}("Child" => inner))

        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t9"),
            models=Dict("Parent" => outer))
        flat = flatten(file)

        @test haskey(flat.state_variables, "Parent.u")
        @test haskey(flat.state_variables, "Parent.Child.v")
```

