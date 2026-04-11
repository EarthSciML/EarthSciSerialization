# 15. No @eval or __precompile__(false) in flatten.jl (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
flatten_src = read(joinpath(@__DIR__, "..", "src", "flatten.jl"), String)
        @test !occursin("@eval", flatten_src)
        @test !occursin("__precompile__(false)", flatten_src)
```

