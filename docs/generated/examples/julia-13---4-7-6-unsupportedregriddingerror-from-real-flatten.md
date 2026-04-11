# 13. §4.7.6 UnsupportedRegriddingError from real flatten (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
# An Interface with a regridding.method outside the supported set
        # (`identity` only, at the Julia Core tier) MUST raise
        # UnsupportedRegriddingError at flatten time.
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
            "ab_regrid" => EarthSciSerialization.Interface(
                ["grid_a", "grid_b"],
                Dict{String, Any}("shared" => Dict("grid_a.x" => "grid_b.x"));
                regridding=Dict{String, Any}("method" => "cubic_spline"),
            ),
        )
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t13_regrid"),
            models=Dict("A" => m_a, "B" => m_b),
            coupling=coupling,
            domains=domains,
            interfaces=interfaces)
        err = try
            flatten(file); nothing
        catch e
            e
```

