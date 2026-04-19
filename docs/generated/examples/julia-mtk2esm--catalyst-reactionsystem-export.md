# mtk2esm: Catalyst ReactionSystem export (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/mtk_export_test.jl`

```julia
rs = _toy_catalyst_system()
    out = mtk2esm(rs)

    @test out["esm"] == "0.1.0"
    @test haskey(out, "reaction_systems")
    @test haskey(out["reaction_systems"], "ToyReactions")

    rs_dict = out["reaction_systems"]["ToyReactions"]
    @test haskey(rs_dict, "species")
    @test haskey(rs_dict, "reactions")
    @test length(rs_dict["reactions"]) == 2

    # Species are serialized as a map keyed by name
    species_map = rs_dict["species"]
    @test species_map isa Dict || species_map isa AbstractDict
    @test haskey(species_map, "A")
    @test haskey(species_map, "B")
```

