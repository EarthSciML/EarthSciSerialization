# discretize() pipeline (RFC §11, gt-gbs2) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/discretize_test.jl`

```julia
# Helper: a minimal scalar ODE model, no PDE ops anywhere.
    function _scalar_ode_esm()
        return Dict{String,Any}(
            "esm" => "0.2.0",
            "metadata" => Dict{String,Any}(
                "name" => "scalar_ode",
                "description" => "dx/dt = -k * x",
            ),
            "models" => Dict{String,Any}(
                "M" => Dict{String,Any}(
                    "variables" => Dict{String,Any}(
                        "x" => Dict{String,Any}("type" => "state", "default" => 1.0, "units" => "1"),
                        "k" => Dict{String,Any}("type" => "parameter", "default" => 0.5, "units" => "1/s"),
                    ),
                    "equations" => Any[
                        Dict{String,Any}(
                            "lhs" => Dict{String,Any}("op" => "D", "args" => Any["x"], "wrt" => "t"),
                            "rhs" => Dict{String,Any}("op" => "*", "args" => Any[
                                Dict{String,Any}("op" => "-", "args" => Any["k"]),
                                "x",
                            ]),
                        ),
                    ],
                ),
            ),
        )
```

