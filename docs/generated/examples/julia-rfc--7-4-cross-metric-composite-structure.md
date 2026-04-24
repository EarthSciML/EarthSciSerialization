# RFC §7.4 cross-metric composite structure (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/discretizations_roundtrip_test.jl`

```julia
path = joinpath(_DISC_FIXTURES_DIR, "cross_metric_cartesian.esm")
    esm = EarthSciSerialization.load(path)

    @test haskey(esm.discretizations, "laplacian_full_covariant_toy")
    composite = esm.discretizations["laplacian_full_covariant_toy"]

    @test composite["kind"] == "cross_metric"
    @test composite["axes"] == ["xi", "eta"]
    @test composite["terms"] isa AbstractVector
    @test length(composite["terms"]) == 2
    # Composite entries do NOT carry a stencil key.
    @test !haskey(composite, "stencil")

    # Per-axis stencils should still be present and carry a stencil key.
    @test haskey(esm.discretizations["d2_dxi2_uniform"], "stencil")
    @test haskey(esm.discretizations["d2_deta2_uniform"], "stencil")
```

