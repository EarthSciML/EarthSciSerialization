# RFC §7.4 staggering_rules round-trip (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/staggering_rules_test.jl`

```julia
path = joinpath(_SR_FIXTURES_DIR, "mpas_c_grid_staggering.esm")
    @test isfile(path)

    original = EarthSciSerialization.load(path)
    @test original isa EsmFile
    @test original.staggering_rules !== nothing
    @test haskey(original.staggering_rules, "mpas_c_grid_staggering")

    rule = original.staggering_rules["mpas_c_grid_staggering"]
    @test rule isa StaggeringRule
    @test rule.data["kind"] == "unstructured_c_grid"
    @test rule.data["grid"] == "mpas_cvmesh"
    @test rule.data["edge_normal_convention"] == "outward_from_first_cell"
    @test rule.data["cell_quantity_locations"]["u"] == "edge_midpoint"

    tmp = tempname() * ".esm"
    try
        EarthSciSerialization.save(original, tmp)
        reloaded = EarthSciSerialization.load(tmp)

        @test Set(keys(original.staggering_rules)) == Set(keys(reloaded.staggering_rules))
        @test original.staggering_rules["mpas_c_grid_staggering"].data ==
              reloaded.staggering_rules["mpas_c_grid_staggering"].data

        # JSON-tree equivalence against the original on disk.
        disk_tree = _sr_read_plain(path)
        reloaded_tree = _sr_read_plain(tmp)
        @test disk_tree["staggering_rules"] == reloaded_tree["staggering_rules"]
    finally
        isfile(tmp) && rm(tmp)
```

