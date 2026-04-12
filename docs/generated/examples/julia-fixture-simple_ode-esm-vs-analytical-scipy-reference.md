# Fixture simple_ode.esm vs analytical/SciPy reference (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/simulate_e2e_test.jl`

```julia
fixture_path = joinpath(@__DIR__, "..", "..", "..", "tests",
                                "simulation", "simple_ode.esm")
        @test isfile(fixture_path)

        esm_file = ESM.load(fixture_path)
        @test esm_file isa EsmFile
        @test !isnothing(esm_file.models)
        @test haskey(esm_file.models, "ExponentialDecay")

        flat = flatten(esm_file)
        sys = MTK.System(flat; name=:ExponentialDecay)
        simp = MTK.mtkcompile(sys)
        prob = MTK.ODEProblem(simp, Dict{Any,Any}(), (0.0, 50.0))
        sol = OrdinaryDiffEqTsit5.solve(prob, OrdinaryDiffEqTsit5.Tsit5();
            reltol=1e-10, abstol=1e-12)

        Nsym = _find_unknown(simp, "N")

        # Reference values lifted directly from
        # tests/simulation/reference_solutions/simple_ode_solution.json
        # (analytical with tol 1e-12). Formula: N(t) = 100 * exp(-0.1 * t).
        ref_times = [0.0, 5.0, 10.0, 20.0, 30.0, 40.0, 50.0]
        ref_vals = [
            100.0,
            60.65306597126334,
            36.787944117144235,
            13.533528323661267,
            4.978706836786395,
            1.8315638888734182,
            0.6737946999085468,
        ]

        for (t, ref) in zip(ref_times, ref_vals)
            @test isapprox(sol(t, idxs=Nsym), ref; rtol=1e-6, atol=1e-10)
```

