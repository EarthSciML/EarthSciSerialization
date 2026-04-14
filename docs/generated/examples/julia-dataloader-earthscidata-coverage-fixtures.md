# DataLoader EarthSciData coverage fixtures (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/data_loader_fixtures_test.jl`

```julia
fixtures_dir = joinpath(@__DIR__, "fixtures", "data_loaders")
    @test isdir(fixtures_dir)

    fixture_files = sort(filter(f ->
```

