# 8. 2D ArrayOp (M,N)=(4,3) analytical (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/array_ops_test.jl`

```julia
M, Nd = 4, 3
        vars = Dict{String,ESM2.ModelVariable}(
            "u" => ESM2.ModelVariable(ESM2.StateVariable),
        )
        lhs = _arrayop2d(_op("D", _idx("u", _var("i"), _var("j")); wrt="t"),
                         "i", 1, M, "j", 1, Nd)
        rhs = _arrayop2d(_op("-", _idx("u", _var("i"), _var("j"))),
                         "i", 1, M, "j", 1, Nd)
        eq = ESM2.Equation(lhs, rhs)
        model = ESM2.Model(vars, ESM2.Equation[eq])

        sys = MTK2.System(model; name=:ODE2D)
        simp = MTK2.mtkcompile(sys)
        @test length(MTK2.unknowns(simp)) == M * Nd

        u_handle = _arr(simp, :ODE2D, "u")
        u0 = [u_handle[i, j] => Float64(i + j) for i in 1:M for j in 1:Nd]
        prob = MTK2.ODEProblem(simp, u0, (0.0, 1.0))
        sol = OrdinaryDiffEqDefault.solve(prob; reltol=1e-8, abstol=1e-10)
        for i in 1:M, j in 1:Nd
            @test sol[u_handle[i, j]][
```

