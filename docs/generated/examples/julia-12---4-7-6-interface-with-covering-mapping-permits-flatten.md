# 12. §4.7.6 Interface with covering mapping permits flatten (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
# Companion to case 11: same two-domain file, but with an Interface
        # that explicitly covers both domains (identity regridding). flatten
        # MUST NOT throw in this case — it should complete normally.
        domains = Dict{String, Domain}(
            "grid_a" => Domain(spatial=Dict{String,Any}("x" => [0.0, 1.0])),
            "grid_b" => Domain(spatial=Dict{String,Any}("x" => [0.0, 1.0])),
        )
        vars_a = Dict{String, ModelVariable}("T" => ModelVariable(StateVariable))
        m_a = Model(vars_a, Equation[Equation(_deriv("T"), _V("T"))],
                    domain="grid_a")
        vars_b = Dict{String, ModelVariable}("T" => ModelVariable(StateVariable))
        m_b = Model(vars_b, Equation[Equation(_deriv("T"), _V("T"))],
                    domain="grid_b")
        coupling = CouplingEntry[
            CouplingOperatorCompose(["A", "B"]),
        ]
        interfaces = Dict{String, EarthSciSerialization.Interface}(
            "ab_identity" => EarthSciSerialization.Interface(
                ["grid_a", "grid_b"],
                Dict{String, Any}("shared" => Dict("grid_a.x" => "grid_b.x"));
                regridding=Dict{String, Any}("method" => "identity"),
            ),
        )
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t12_interface_ok"),
            models=Dict("A" => m_a, "B" => m_b),
            coupling=coupling,
            domains=domains,
            interfaces=interfaces)
        flat = flatten(file)
        @test flat isa FlattenedSystem
```

