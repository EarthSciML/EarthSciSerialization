# mtk2esm: numerical round-trip (toy ODE) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/mtk_export_test.jl`

```julia
sys = _toy_ode_system(:NumRT)
    out = mtk2esm(sys)

    tmpfile = tempname() * ".esm"
    try
        open(tmpfile, "w") do io
            write(io, JSON3.write(out; indent=2))
```

