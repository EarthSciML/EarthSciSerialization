# Large 2D advection (64×64, periodic BC) — build+solve time (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/tree_walk_test.jl`

```julia
Nx, Ny = 64, 64
        dx = 1.0 / Nx
        dy = 1.0 / Ny
        vx, vy = 1.0, 0.5
        vars = Dict{String,ModelVariable}()
        eqs = Equation[]
        # Initial condition: a single bump at (0.5, 0.5).
        for i in 1:Nx, j in 1:Ny
            x = (i - 0.5) * dx
            y = (j - 0.5) * dy
            u0 = exp(-((x - 0.5)^2 + (y - 0.5)^2) / 0.02)
            vars["u_$(i)_$(j)"] = ModelVariable(StateVariable; default=u0)
```

