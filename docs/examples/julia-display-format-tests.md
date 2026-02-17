# Display Format Tests (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/runtests.jl`

```julia
# Test pretty-printing matches display fixtures
            display_fixtures_dir = joinpath(@__DIR__, "..", "..", "..", "tests", "display")

            if isdir(display_fixtures_dir)
                display_files = filter(f ->
```

