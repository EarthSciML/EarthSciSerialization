# 11. HYBRID: 1D (z) domain is detected (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
domains = Dict{String, Domain}(
            "col" => Domain(spatial=Dict{String,Any}("z"=>Dict())))
        vars = Dict{String, ModelVariable}("T" => ModelVariable(StateVariable))
        # Spatial derivative in RHS via D(T, z).
        eqs = [Equation(_deriv("T"),
                        _op("D", _V("T"); wrt="z"))]
        m = Model(vars, eqs, domain="col")
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t11"),
            models=Dict("Vert" => m),
            domains=domains)
        flat = flatten(file)
        @test :z in flat.indep
```

