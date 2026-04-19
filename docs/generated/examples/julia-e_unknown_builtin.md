# E_UNKNOWN_BUILTIN (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/grids_test.jl`

```julia
bad = Dict(
            "esm" => "0.2.0",
            "metadata" => Dict("name" => "bad"),
            "models" => Dict("M" => Dict(
                "variables" => Dict("T" => Dict("type" => "state", "default" => 0.0)),
                "equations" => Any[Dict("lhs" => "D(T)", "rhs" => "0")],
            )),
            "grids" => Dict("g" => Dict(
                "family" => "cubed_sphere",
                "dimensions" => Any["panel", "i", "j"],
                "extents" => Dict("panel" => Dict("n" => 6),
                                  "i" => Dict("n" => 4),
                                  "j" => Dict("n" => 4)),
                "panel_connectivity" => Dict("neighbors" => Dict(
                    "shape" => Any[6, 4], "rank" => 2,
                    "generator" => Dict("kind" => "builtin",
                                        "name" => "not_a_real_builtin"),
                )),
            )),
        )
        buf = IOBuffer()
        JSON3.write(buf, bad)
        seekstart(buf)
        @test_throws EarthSciSerialization.ParseError EarthSciSerialization.load(buf)
```

