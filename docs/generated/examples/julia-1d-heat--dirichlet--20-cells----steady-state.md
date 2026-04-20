# 1D heat (Dirichlet, 20 cells) → steady state (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/tree_walk_test.jl`

```julia
N = 20
        dx = 1.0 / (N + 1)
        α = 0.5
        vars = Dict{String,ModelVariable}()
        eqs = Equation[]
        for i in 1:N
            name = "u_$i"
            # Initial: sin(π x_i). Interior i=1..N, x_i = i*dx.
            u0_i = sinpi(i * dx)
            vars[name] = ModelVariable(StateVariable; default=u0_i)
```

