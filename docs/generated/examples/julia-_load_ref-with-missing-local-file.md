# _load_ref with missing local file (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/subsystem_ref_test.jl`

```julia
visited = Set{String}()
        @test_throws EarthSciSerialization.SubsystemRefError begin
            EarthSciSerialization._load_ref("nonexistent_file.esm", tempdir(), visited)
```

