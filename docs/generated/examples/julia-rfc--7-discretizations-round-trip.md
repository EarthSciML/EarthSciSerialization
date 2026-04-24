# RFC §7 discretizations round-trip (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/discretizations_roundtrip_test.jl`

```julia
@test isdir(_DISC_FIXTURES_DIR)

    fixtures = ["centered_2nd_uniform.esm",
                "upwind_1st_advection.esm",
                "periodic_bc.esm",
                "mpas_cell_div.esm",
                "cross_metric_cartesian.esm"]

    for fname in fixtures
        @testset "Round-trip $(fname)" begin
            path = joinpath(_DISC_FIXTURES_DIR, fname)
            @test isfile(path)

            original_raw = _read_plain(path)

            esm = EarthSciSerialization.load(path)
            @test esm isa EsmFile
            @test esm.discretizations !== nothing
            @test length(esm.discretizations) >= 1

            tmp = tempname() * ".esm"
            try
                EarthSciSerialization.save(esm, tmp)
                reloaded = EarthSciSerialization.load(tmp)

                reloaded_raw = _read_plain(tmp)

                @test haskey(reloaded_raw, "discretizations")
                @test reloaded_raw["discretizations"] == original_raw["discretizations"]

                # Key sets preserved at the Julia struct level too.
                @test Set(keys(esm.discretizations)) == Set(keys(reloaded.discretizations))
            finally
                rm(tmp, force=true)
```

