# mtk2esm_gaps pre-flight on gap-free system (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/mtk_export_test.jl`

```julia
sys = _toy_ode_system(:Clean)
    gaps = mtk2esm_gaps(sys)
    @test gaps isa Vector{GapReport}
    @test isempty(gaps)  # no brownians declared
```

