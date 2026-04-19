# flatten basic (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/canonicalize_test.jl`

```julia
e = op("+", Any[op("+", Any["a", "b"]), "c"])
        @test canonical_json(e) == "{\"args\":[\"a\",\"b\",\"c\"],\"op\":\"+\"}"
```

