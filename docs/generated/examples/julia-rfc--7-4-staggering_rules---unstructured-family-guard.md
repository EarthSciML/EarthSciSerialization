# RFC §7.4 staggering_rules — unstructured-family guard (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/staggering_rules_test.jl`

```julia
path = joinpath(_SR_FIXTURES_DIR, "mpas_c_grid_staggering.esm")
    data = JSON3.read(read(path, String), Dict{String,Any})

    # Mutate the grid to cartesian; the load must reject the staggering rule.
    data["grids"]["mpas_cvmesh"]["family"] = "cartesian"
    data["grids"]["mpas_cvmesh"]["extents"] = Dict("cell" => Dict("n" => "nCells", "spacing" => "uniform"))
    delete!(data["grids"]["mpas_cvmesh"], "connectivity")

    tmp = tempname() * ".esm"
    try
        open(tmp, "w") do io
            JSON3.write(io, data)
```

