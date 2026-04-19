# mtk2esm: JSON-serializable output (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/mtk_export_test.jl`

```julia
sys = _toy_ode_system()
    out = mtk2esm(sys)
    # Must round-trip through JSON without errors
    s = JSON3.write(out)
    parsed = JSON3.read(s)
    @test parsed["esm"] == "0.1.0"
    @test haskey(parsed["models"], "ToyDecay")
```

