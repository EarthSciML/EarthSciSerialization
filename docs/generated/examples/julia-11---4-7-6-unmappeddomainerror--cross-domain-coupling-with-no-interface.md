# 11. §4.7.6 UnmappedDomainError: cross-domain coupling with no interface (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
# Two models on different non-null domains composed without an
        # Interface declaring their mapping. Per §4.7.6, this MUST raise
        # UnmappedDomainError during flatten.
        domains = Dict{String, Domain}(
            "grid_a" => Domain(spatial=Dict{String,Any}("x" => [0.0, 1.0])),
            "grid_b" => Domain(spatial=Dict{String,Any}("x" => [0.0, 2.0])),
        )
        vars_a = Dict{String, ModelVariable}("T" => ModelVariable(StateVariable))
        m_a = Model(vars_a, Equation[Equation(_deriv("T"), _V("T"))],
                    domain="grid_a")
        vars_b = Dict{String, ModelVariable}("S" => ModelVariable(StateVariable))
        m_b = Model(vars_b, Equation[Equation(_deriv("S"), _V("S"))],
                    domain="grid_b")
        coupling = CouplingEntry[
            CouplingOperatorCompose(["A", "B"]),
        ]
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t11_unmapped"),
            models=Dict("A" => m_a, "B" => m_b),
            coupling=coupling,
            domains=domains)  # note: no `interfaces` — that's the error
        err = try
            flatten(file); nothing
        catch e
            e
```

