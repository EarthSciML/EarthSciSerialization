# flatten(::Model) convenience (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
vars = Dict{String, ModelVariable}("x" => ModelVariable(StateVariable))
        eqs = [Equation(_deriv("x"), _V("x"))]
        m = Model(vars, eqs)
        flat = flatten(m)
        @test flat isa FlattenedSystem
        @test haskey(flat.state_variables, "anonymous.x")
```

