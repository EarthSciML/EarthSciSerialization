# 12. HYBRID: grad operator detected in IVs (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
vars = Dict{String, ModelVariable}("c" => ModelVariable(StateVariable))
        eqs = [Equation(_deriv("c"), _op("grad", _V("c"); dim="x"))]
        m = Model(vars, eqs)
        file = EarthSciSerialization.EsmFile("0.1.0",
            EarthSciSerialization.Metadata("t12"),
            models=Dict("Adv" => m))
        flat = flatten(file)
        @test :x in flat.indep
```

