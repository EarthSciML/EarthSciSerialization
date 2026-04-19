# Arrayed variables (RFC §10.2) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/arrayed_vars_test.jl`

```julia
fixture_dir = joinpath(@__DIR__, "..", "..", "..", "tests", "fixtures", "arrayed_vars")

    function roundtrip(name::String)
        path = joinpath(fixture_dir, name)
        first = EarthSciSerialization.load(path)
        tmp = tempname() * ".esm"
        EarthSciSerialization.save(tmp, first)
        second = EarthSciSerialization.load(tmp)
        rm(tmp; force=true)
        return first, second
```

