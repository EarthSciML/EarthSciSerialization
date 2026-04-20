# Large diagonal system (1024 states) — build + evaluate (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/tree_walk_test.jl`

```julia
N = 1024
        vars = Dict{String,ModelVariable}()
        eqs = Equation[]
        for i in 1:N
            vars["u_$i"] = ModelVariable(StateVariable; default=0.1)
```

