# MTK parity — random f! samples match (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/tree_walk_test.jl`

```julia
N = 10
        dx = 1.0 / (N + 1)
        α = 0.75
        vars = Dict{String,ModelVariable}()
        eqs = Equation[]
        for i in 1:N
            vars["u_$i"] = ModelVariable(StateVariable; default=sinpi(i * dx))
```

