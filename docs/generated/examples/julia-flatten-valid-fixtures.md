# Flatten valid fixtures (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/flatten_test.jl`

```julia
valid_fixtures_dir = joinpath(@__DIR__, "..", "..", "..", "tests", "valid")
        if isdir(valid_fixtures_dir)
            valid_files = filter(f ->
```

