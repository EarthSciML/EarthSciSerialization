# §5.4.6 float format table (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/canonicalize_test.jl`

```julia
cases = [
            (1.0, "1.0"),
            (-3.0, "-3.0"),
            (0.0, "0.0"),
            (-0.0, "-0.0"),
            (2.5, "2.5"),
            (1e25, "1e25"),
            (5e-324, "5e-324"),
            (1e-7, "1e-7"),
        ]
        for (v, want) in cases
            @test format_canonical_float(v) == want
```

