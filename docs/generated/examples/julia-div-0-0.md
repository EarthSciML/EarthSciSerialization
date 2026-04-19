# div 0/0 (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/canonicalize_test.jl`

```julia
@test_throws CanonicalizeError canonicalize(op("/", Any[0, 0]))
```

