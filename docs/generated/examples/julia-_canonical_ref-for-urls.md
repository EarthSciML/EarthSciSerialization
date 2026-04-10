# _canonical_ref for URLs (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/subsystem_ref_test.jl`

```julia
ref = "https://example.com/model.esm"
        canonical = EarthSciSerialization._canonical_ref(ref, "/tmp")
        @test canonical == ref
```

