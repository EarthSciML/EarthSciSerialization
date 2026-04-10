# Circular reference detection (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/subsystem_ref_test.jl`

```julia
# Simulate a cycle by pre-loading the visited set
        visited = Set{String}()
        ref = "/tmp/circular.esm"
        push!(visited, abspath(ref))

        @test_throws EarthSciSerialization.SubsystemRefError begin
            EarthSciSerialization._load_ref("circular.esm", "/tmp", visited)
```

