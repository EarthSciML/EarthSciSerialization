# _canonical_ref for local paths (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/subsystem_ref_test.jl`

```julia
base = "/tmp/test_dir"
        ref = "sub/model.esm"
        canonical = EarthSciSerialization._canonical_ref(ref, base)
        @test canonical == abspath(joinpath(base, ref))
```

