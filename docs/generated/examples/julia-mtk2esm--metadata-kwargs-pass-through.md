# mtk2esm: metadata kwargs pass through (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/mtk_export_test.jl`

```julia
sys = _toy_ode_system(:Tagged)
    out = mtk2esm(sys; metadata=(;
        description="toy decay chain",
        tags=["migration", "toy"],
        source_ref="earthsciml/UnitTests.jl@abc123",
        authors=["migrator"],
        version="0.2.0",
    ))

    @test out["metadata"]["name"] == "Tagged"
    @test out["metadata"]["description"] == "toy decay chain"
    @test out["metadata"]["authors"] == ["migrator"]
    @test out["metadata"]["tags"] == ["migration", "toy"]

    m = out["models"]["Tagged"]
    # Per-model description + version + source_ref are folded into
    # `reference.notes` — the Model schema has `additionalProperties: false`
    # and only Reference.notes is a schema-sanctioned free-form text slot.
    @test haskey(m, "reference")
    notes = m["reference"]["notes"]
    @test occursin("version: 0.2.0", notes)
    @test occursin("toy decay chain", notes)
    @test occursin("source_ref: earthsciml/UnitTests.jl@abc123", notes)
```

