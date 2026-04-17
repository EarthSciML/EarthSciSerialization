# Conformance: round-trip (manifest-driven) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/conformance_round_trip_test.jl`

```julia
@test isfile(_MANIFEST_PATH)

    manifest = JSON3.read(read(_MANIFEST_PATH, String))
    @test manifest.category == "round_trip"
    @test !isempty(manifest.fixtures)

    for fixture in manifest.fixtures
        id = String(fixture.id)
        fixture_path = joinpath(_TESTS_DIR, String(fixture.path))

        @testset "$(id)" begin
            if !isfile(fixture_path)
                @warn "Conformance fixture not found, skipping" id=id path=fixture_path
                @test_broken isfile(fixture_path)
                continue
```

