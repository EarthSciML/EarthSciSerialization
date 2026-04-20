# Conformance: discretize (gt-l3dg, manifest-driven) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/conformance_discretize_test.jl`

```julia
@test isfile(_DISC_MANIFEST)

    manifest = JSON3.read(read(_DISC_MANIFEST, String))
    @test manifest.category == "discretize"
    @test !isempty(manifest.fixtures)

    opts = get(manifest, :options, NamedTuple())

    for fixture in manifest.fixtures
        id          = String(fixture.id)
        input_path  = joinpath(_DISC_CONF_DIR, String(fixture.input))
        golden_path = joinpath(_DISC_CONF_DIR, String(fixture.golden))

        @testset "$(id)" begin
            @test isfile(input_path)

            # 1. Run discretize
```

