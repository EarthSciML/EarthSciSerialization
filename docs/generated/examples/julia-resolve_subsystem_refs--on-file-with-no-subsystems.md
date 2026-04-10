# resolve_subsystem_refs! on file with no subsystems (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/subsystem_ref_test.jl`

```julia
metadata = Metadata("no_subsystems")
        file = EsmFile("0.1.0", metadata)
        # Should not error on empty file
        resolve_subsystem_refs!(file, tempdir())
        @test true  # just verifies no error thrown
```

