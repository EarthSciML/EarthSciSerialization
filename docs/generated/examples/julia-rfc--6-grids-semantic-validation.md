# RFC §6 grids semantic validation (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/grids_test.jl`

```julia
# Loader-backed metric array with an unknown loader -> E_UNKNOWN_LOADER
    @testset "E_UNKNOWN_LOADER" begin
        bad = Dict(
            "esm" => "0.2.0",
            "metadata" => Dict("name" => "bad"),
            "models" => Dict("M" => Dict(
                "variables" => Dict("T" => Dict("type" => "state", "default" => 0.0)),
                "equations" => Any[Dict("lhs" => "D(T)", "rhs" => "0")],
            )),
            "grids" => Dict("g" => Dict(
                "family" => "cartesian",
                "dimensions" => Any["x"],
                "extents" => Dict("x" => Dict("n" => 8, "spacing" => "uniform")),
                "metric_arrays" => Dict("dx" => Dict(
                    "rank" => 0,
                    "generator" => Dict("kind" => "loader",
                                        "loader" => "nope",
                                        "field" => "dx"),
                )),
            )),
        )
        buf = IOBuffer()
        JSON3.write(buf, bad)
        seekstart(buf)
        @test_throws EarthSciSerialization.ParseError EarthSciSerialization.load(buf)
```

