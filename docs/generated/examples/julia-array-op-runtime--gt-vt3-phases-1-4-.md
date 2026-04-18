# Array-op runtime (gt-vt3 Phases 1-4) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/array_ops_test.jl`

```julia
# ================================================================
    # Case 1 — Pure ODE on u[i], N=5, analytical u_i(t) = i * exp(-t).
    #   lhs = arrayop (i,) D(u[i]) i in 1:5
    #   rhs = arrayop (i,) -u[i] i in 1:5
    # ================================================================
    @testset "1. Pure ODE N=5 analytical" begin
        N = 5
        vars = Dict{String,ESM2.ModelVariable}(
            "u" => ESM2.ModelVariable(ESM2.StateVariable),
        )
        lhs = _arrayop1d(_d_index("u", _var("i")), "i", 1, N)
        rhs = _arrayop1d(_op("-", _idx("u", _var("i"))), "i", 1, N)
        eq = ESM2.Equation(lhs, rhs)
        model = ESM2.Model(vars, ESM2.Equation[eq])

        sys = MTK2.System(model; name=:PureODE)
        simp = MTK2.mtkcompile(sys)
        @test length(MTK2.unknowns(simp)) == N

        u_handle = _arr(simp, :PureODE, "u")
        u0 = [u_handle[i] => Float64(i) for i in 1:N]
        prob = MTK2.ODEProblem(simp, u0, (0.0, 1.0))
        sol = OrdinaryDiffEqTsit5.solve(prob, OrdinaryDiffEqTsit5.Tsit5(); reltol=1e-8, abstol=1e-10)
        for i in 1:N
            @test sol[u_handle[i]][
```

