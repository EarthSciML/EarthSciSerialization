# §5.4.8 worked example (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/canonicalize_test.jl`

```julia
e = op("+", Any[
            op("*", Any["a", 0]),
            "b",
            op("+", Any["a", 1]),
        ])
        @test canonical_json(e) == "{\"args\":[1,\"a\",\"b\"],\"op\":\"+\"}"
```

