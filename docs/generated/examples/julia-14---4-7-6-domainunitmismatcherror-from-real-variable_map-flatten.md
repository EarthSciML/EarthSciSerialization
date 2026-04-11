# 14. §4.7.6 DomainUnitMismatchError from real variable_map flatten (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
# A variable_map with transform="identity" between two variables
        # carrying DIFFERENT declared units MUST raise DomainUnitMismatchError.
        vars_a = Dict{String, ModelVariable}(
            "T" => ModelVariable(StateVariable; units="K"),
        )
        m_a = Model(vars_a, Equation[Equation(_deriv("T"), _V("T"))])
        vars_b = Dict{String, ModelVariable}(
            "T" => ModelVariable(ParameterVariable; units="degC"),
        )
        m_b = Model(vars_b, Equation[])
        coupling = CouplingEntry[
            CouplingVariableMap("A.T", "B.T", "identity"),
        ]
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t14_units"),
            models=Dict("A" => m_a, "B" => m_b),
            coupling=coupling)
        err = try
            flatten(file); nothing
        catch e
            e
```

