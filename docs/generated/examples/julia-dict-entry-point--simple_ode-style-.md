# Dict entry point (simple_ode style) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/tree_walk_test.jl`

```julia
esm = Dict(
            "esm" => "0.2.0",
            "metadata" => Dict("name" => "DecayDict"),
            "models" => Dict(
                "Decay" => Dict(
                    "variables" => Dict(
                        "N" => Dict("type" => "state", "default" => 100.0),
                        "lambda" => Dict("type" => "parameter", "default" => 0.1),
                    ),
                    "equations" => [Dict(
                        "lhs" => Dict("op" => "D", "args" => ["N"], "wrt" => "t"),
                        "rhs" => Dict("op" => "*",
                                      "args" => [Dict("op" => "-", "args" => ["lambda"]),
                                                 "N"]),
                    )],
                ),
            ),
        )
        f!, u0, p, _tspan, var_map = build_evaluator(esm)
        prob = OrdinaryDiffEqTsit5.ODEProblem(f!, u0, (0.0, 10.0), p)
        sol = OrdinaryDiffEqTsit5.solve(prob, OrdinaryDiffEqTsit5.Tsit5();
                                        reltol=1e-8, abstol=1e-10)
        @test isapprox(sol.u[
```

