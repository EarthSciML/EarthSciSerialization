# FlattenMetadata construction (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
meta = FlattenMetadata(["Atm", "Ocean"], ["operator_compose(Atm + Ocean)"])
        @test meta.source_systems == ["Atm", "Ocean"]
        @test length(meta.coupling_rules) == 1
```

