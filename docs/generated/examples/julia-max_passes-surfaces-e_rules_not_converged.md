# max_passes surfaces E_RULES_NOT_CONVERGED (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/discretize_test.jl`

```julia
# Rule `x -> x + 0` canonicalizes back to `x` → but a pattern that
        # refuses to fix-point: `$a -> $a + 1` on any variable `y` forever.
        esm = Dict{String,Any}(
            "esm" => "0.2.0",
            "metadata" => Dict{String,Any}("name" => "loop"),
            "rules" => Any[
                Dict{String,Any}(
                    "name" => "never",
                    "pattern" => "\$a",
                    "replacement" => Dict{String,Any}(
                        "op" => "+", "args" => Any["\$a", 1],
                    ),
                ),
            ],
            "models" => Dict{String,Any}(
                "M" => Dict{String,Any}(
                    "variables" => Dict{String,Any}(
                        "y" => Dict{String,Any}("type" => "state", "default" => 0.0, "units" => "1"),
                    ),
                    "equations" => Any[
                        Dict{String,Any}(
                            "lhs" => Dict{String,Any}("op" => "D", "args" => Any["y"], "wrt" => "t"),
                            "rhs" => "y",
                        ),
                    ],
                ),
            ),
        )
        err = try
            discretize(esm; max_passes=3)
            nothing
        catch e
            e
```

