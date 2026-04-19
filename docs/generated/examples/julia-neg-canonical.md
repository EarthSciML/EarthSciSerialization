# neg canonical (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/canonicalize_test.jl`

```julia
@test canonical_json(op("neg", Any[op("neg", Any["x"])])) == "\"x\""
        @test canonical_json(op("neg", Any[5])) == "-5"
        @test canonical_json(op("-", Any[0, "x"])) == "{\"args\":[\"x\"],\"op\":\"neg\"}"
```

