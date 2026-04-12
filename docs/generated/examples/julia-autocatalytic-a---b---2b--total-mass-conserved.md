# Autocatalytic A + B → 2B: total mass conserved (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/simulate_e2e_test.jl`

```julia
k = 2.0
        A0, B0 = 1.0, 0.01
        # Build as an ESM ReactionSystem → flatten → System path so we
        # exercise the reaction-to-ODE derivation plus the solve loop.
        # NOTE: `mass_action_rate` multiplies the user-supplied rate by the
        # substrate species automatically, so the `rate` below is the rate
        # constant only. Effective rate: k * A * B.
        rxn = ESM.Reaction("auto",
            [ESM.StoichiometryEntry("A", 1), ESM.StoichiometryEntry("B", 1)],
            [ESM.StoichiometryEntry("B", 2)],
            VarExpr("k"))
        rsys = ESM.ReactionSystem(
            [ESM.Species("A"; default=A0), ESM.Species("B"; default=B0)],
            [rxn];
            parameters=[ESM.Parameter("k", k)],
        )
        flat = flatten(rsys; name="Auto")
        sys = MTK.System(flat; name=:Auto)
        simp = MTK.mtkcompile(sys)
        # Logistic time scale: 1/(k * total) = 1/(2 * 1.01) ≈ 0.495. Half-life
        # from x(0)=0.01 takes ~ln((M-x0)/x0)/(k*M) = ln(99)/2.02 ≈ 2.27.
        # Integrate to t = 10 (≈ 20 half-times) — A should be ~0.
        prob = MTK.ODEProblem(simp, Dict{Any,Any}(), (0.0, 10.0))
        sol = OrdinaryDiffEqTsit5.solve(prob, OrdinaryDiffEqTsit5.Tsit5();
            reltol=1e-10, abstol=1e-12, saveat=0.25)

        Asym = _find_unknown(simp, "A")
        Bsym = _find_unknown(simp, "B")

        total0 = A0 + B0
        As = sol[Asym]
        Bs = sol[Bsym]
        @test length(As) == length(Bs)

        # Mass conservation at every stored time step
        totals = As .+ Bs
        @test maximum(abs.(totals .- total0)) < 1e-8

        # Sanity: autocatalysis should drive A → 0, B → total.
        @test As[
```

