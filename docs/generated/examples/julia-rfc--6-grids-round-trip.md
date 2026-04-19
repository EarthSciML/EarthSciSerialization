# RFC §6 grids round-trip (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/grids_test.jl`

```julia
@test isdir(_GRIDS_FIXTURES_DIR)

    fixtures = ["cartesian_uniform.esm",
                "unstructured_mpas.esm",
                "cubed_sphere_c48.esm"]

    for fname in fixtures
        @testset "Round-trip $(fname)" begin
            path = joinpath(_GRIDS_FIXTURES_DIR, fname)
            @test isfile(path)

            # 1. Load the original fixture
            original = EarthSciSerialization.load(path)
            @test original isa EsmFile
            @test original.grids !== nothing
            @test length(original.grids) >= 1

            # 2. Save and reload
            tmp = tempname() * ".esm"
            try
                EarthSciSerialization.save(original, tmp)
                reloaded = EarthSciSerialization.load(tmp)

                # Grid dict keys preserved
                @test Set(keys(original.grids)) == Set(keys(reloaded.grids))

                # Deep equality of each Grid's opaque dict
                for gname in keys(original.grids)
                    @test original.grids[gname].data == reloaded.grids[gname].data
```

