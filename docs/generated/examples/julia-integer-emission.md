# integer emission (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/canonicalize_test.jl`

```julia
for (v, want) in [(1, "1"), (-42, "-42"), (0, "0")]
            @test canonical_json(IntExpr(v)) == want
```

