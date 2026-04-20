# BC value canonicalization (no rules) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/discretize_test.jl`

```julia
esm = Dict{String,Any}(
            "esm" => "0.2.0",
            "metadata" => Dict{String,Any}("name" => "bc_plain"),
            "models" => Dict{String,Any}(
                "M" => Dict{String,Any}(
                    "variables" => Dict{String,Any}(
                        "u" => Dict{String,Any}("type" => "state", "default" => 0.0, "units" => "1"),
                    ),
                    "equations" => Any[
                        Dict{String,Any}(
                            "lhs" => Dict{String,Any}("op" => "D", "args" => Any["u"], "wrt" => "t"),
                            "rhs" => 0.0,
                        ),
                    ],
                    "boundary_conditions" => Dict{String,Any}(
                        "u_dirichlet_xmin" => Dict{String,Any}(
                            "variable" => "u",
                            "side"     => "xmin",
                            "kind"     => "dirichlet",
                            # 1 + 0 should canonicalize to 1.
                            "value"    => Dict{String,Any}(
                                "op" => "+", "args" => Any[1, 0],
                            ),
                        ),
                    ),
                ),
            ),
        )
        out = discretize(esm)
        bc_val = out["models"]["M"]["boundary_conditions"]["u_dirichlet_xmin"]["value"]
        @test bc_val == 1
```

