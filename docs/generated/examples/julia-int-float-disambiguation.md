# int/float disambiguation (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/canonicalize_test.jl`

```julia
a = op("+", Any[1.0, 2.5])
        b = op("+", Any[1, 2.5])
        ja = canonical_json(a)
        jb = canonical_json(b)
        @test ja != jb
        @test occursin("1.0", ja)
```

