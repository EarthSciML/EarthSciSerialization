# type-preserving identity elim (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/canonicalize_test.jl`

```julia
# *(1, x) -> "x"
        @test canonical_json(op("*", Any[1, "x"])) == "\"x\""
        # *(1.0, x) keeps the 1.0
        @test canonical_json(op("*", Any[1.0, "x"])) == "{\"args\":[1.0,\"x\"],\"op\":\"*\"}"
```

