# non-finite errors (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/canonicalize_test.jl`

```julia
for f in [NaN, Inf, -Inf]
            @test_throws CanonicalizeError canonicalize(NumExpr(f))
```

