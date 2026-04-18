# 3. 1D diffusion stencil N=10 vs scalar ref (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/array_ops_test.jl`

```julia
N = 10
        vars = Dict{String,ESM2.ModelVariable}(
            "u" => ESM2.ModelVariable(ESM2.StateVariable),
        )
        # interior arrayop
        body = _op("+",
            _idx("u", _op("-", _var("i"), _num(1))),
            _op("*", _num(-2), _idx("u", _var("i"))),
            _idx("u", _op("+", _var("i"), _num(1))))
        lint = _arrayop1d(_d_index("u", _var("i")), "i", 2, N-1)
        rint = _arrayop1d(body, "i", 2, N-1)
        eq_int = ESM2.Equation(lint, rint)

        # Scalar BCs
        eq_bc1 = ESM2.Equation(
            _op("D", _idx("u", 1); wrt="t"),
            _op("-", _idx("u", 2), _idx("u", 1)))
        eq_bcN = ESM2.Equation(
            _op("D", _idx("u", N); wrt="t"),
            _op("-", _idx("u", N-1), _idx("u", N)))

        model = ESM2.Model(vars, ESM2.Equation[eq_int, eq_bc1, eq_bcN])

        sys = MTK2.System(model; name=:Diff1D)
        simp = MTK2.mtkcompile(sys)
        @test length(MTK2.unknowns(simp)) == N

        u_handle = _arr(simp, :Diff1D, "u")
        u0 = [u_handle[i] => (i == 5 ? 1.0 : 0.0) for i in 1:N]
        prob = MTK2.ODEProblem(simp, u0, (0.0, 0.5))
        sol = OrdinaryDiffEqTsit5.solve(prob, OrdinaryDiffEqTsit5.Tsit5(); reltol=1e-8, abstol=1e-10)
        @test sol.retcode == ModelingToolkit.SciMLBase.ReturnCode.Success

        # Mass conservation sanity: diffusion preserves the total.
        total_start = sum(sol[u_handle[i]][1] for i in 1:N)
        total_
```

