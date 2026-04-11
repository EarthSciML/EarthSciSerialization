# 7. variable_map param_to_var substitutes and removes parameter (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
vars = Dict{String, ModelVariable}(
            "T" => ModelVariable(StateVariable),
            "k" => ModelVariable(ParameterVariable, default=0.1),
            "external" => ModelVariable(ParameterVariable, default=1.0),
        )
        eqs = [Equation(_deriv("T"),
                        _op("*", _V("external"), _op("*", _V("k"), _V("T"))))]
        model = Model(vars, eqs)

        source_vars = Dict{String, ModelVariable}(
            "value" => ModelVariable(StateVariable, default=0.5),
        )
        source_model = Model(source_vars, Equation[])

        coupling = CouplingEntry[
            CouplingVariableMap("Source.value", "Target.external", "param_to_var"),
        ]
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t7"),
            models=Dict("Target" => model, "Source" => source_model),
            coupling=coupling)
        flat = flatten(file)

        # Target.external should be removed from parameters.
        @test !haskey(flat.parameters, "Target.external")
        # The Target.T equation should now reference Source.value.
        eq = _find_eq(flat, "Target.T")
        @test eq !== nothing
        @test _uses_var(eq.rhs, "Source.value")
```

