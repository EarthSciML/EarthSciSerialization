# 2. Mixed ODE + algebraic (v eliminated) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/array_ops_test.jl`

```julia
N = 5
        vars = Dict{String,ESM2.ModelVariable}(
            "u" => ESM2.ModelVariable(ESM2.StateVariable),
            "v" => ESM2.ModelVariable(ESM2.StateVariable),
        )
        # D(u[i]) = v[i]
        eq_ode = ESM2.Equation(
            _arrayop1d(_d_index("u", _var("i")), "i", 1, N),
            _arrayop1d(_idx("v", _var("i")), "i", 1, N))
        # v[i] = -u[i]
        eq_alg = ESM2.Equation(
            _arrayop1d(_idx("v", _var("i")), "i", 1, N),
            _arrayop1d(_op("-", _idx("u", _var("i"))), "i", 1, N))
        model = ESM2.Model(vars, ESM2.Equation[eq_ode, eq_alg])

        sys = MTK2.System(model; name=:MixedODEAlg)
        simp = MTK2.mtkcompile(sys)
        @test length(MTK2.unknowns(simp)) == N  # v eliminated

        u_handle = _arr(simp, :MixedODEAlg, "u")
        u0 = [u_handle[i] => Float64(i) for i in 1:N]
        prob = MTK2.ODEProblem(simp, u0, (0.0, 1.0))
        sol = OrdinaryDiffEqTsit5.solve(prob, OrdinaryDiffEqTsit5.Tsit5(); reltol=1e-8, abstol=1e-10)
        for i in 1:N
            @test sol[u_handle[i]][
```

