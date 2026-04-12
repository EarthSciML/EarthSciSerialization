# Robertson stiff benchmark — reference values to reltol 1e-4 (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/simulate_e2e_test.jl`

```julia
A0, B0, C0 = 1.0, 0.0, 0.0
        vars = Dict{String,ModelVariable}(
            "A" => ModelVariable(StateVariable; default=A0),
            "B" => ModelVariable(StateVariable; default=B0),
            "C" => ModelVariable(StateVariable; default=C0),
        )
        _n(x) = NumExpr(x)
        _v(n) = VarExpr(n)
        _op(op, args...; kw...) = OpExpr(op, ESM.Expr[args...]; kw...)

        # dA/dt = -0.04*A + 1e4*B*C
        eqA = Equation(
            _op("D", _v("A"); wrt="t"),
            _op("+", _op("*", _n(-0.04), _v("A")),
                     _op("*", _n(1.0e4), _v("B"), _v("C"))),
        )
        # dB/dt =  0.04*A - 1e4*B*C - 3e7*B*B
        eqB = Equation(
            _op("D", _v("B"); wrt="t"),
            _op("-",
                _op("-",
                    _op("*", _n(0.04), _v("A")),
                    _op("*", _n(1.0e4), _v("B"), _v("C"))),
                _op("*", _n(3.0e7), _v("B"), _v("B"))),
        )
        # dC/dt =  3e7*B*B
        eqC = Equation(
            _op("D", _v("C"); wrt="t"),
            _op("*", _n(3.0e7), _v("B"), _v("B")),
        )
        model = Model(vars, [eqA, eqB, eqC])

        sys = MTK.System(model; name=:Robertson)
        simp = MTK.mtkcompile(sys)
        prob = MTK.ODEProblem(simp, Dict{Any,Any}(), (0.0, 4.0e10))
        sol = OrdinaryDiffEqRosenbrock.solve(prob, OrdinaryDiffEqRosenbrock.Rodas5P();
            reltol=1e-10, abstol=1e-14)

        Asym = _find_unknown(simp, "A")
        Bsym = _find_unknown(simp, "B")
        Csym = _find_unknown(simp, "C")

        # Reference values from Hairer & Wanner, "Solving ODEs II",
        # Table 1.4, p.3 (Robertson problem). Six significant digits.
        refs = [
            (0.4,     0.98517,     3.3864e-5,   0.014796),
            (4.0,     0.90551,     2.2405e-5,   0.094464),
            (40.0,    0.71583,     9.1856e-6,   0.28416),
            (400.0,   0.45053,     3.2229e-6,   0.54946),
            (4000.0,  0.18320,     8.9416e-7,   0.81680),
            (40000.0, 0.038996,    1.6225e-7,   0.96100),
        ]

        for (t, A_ref, B_ref, C_ref) in refs
            A_val = sol(t, idxs=Asym)
            B_val = sol(t, idxs=Bsym)
            C_val = sol(t, idxs=Csym)
            # Hairer & Wanner reference values are 5 significant digits.
            # Allow rtol = 5e-4 so a numerical solution matching H&W's
            # tabulated digits exactly still passes.
            @test isapprox(A_val, A_ref; rtol=5e-4)
            @test isapprox(B_val, B_ref; rtol=5e-3)  # B is tiny; looser rtol
            @test isapprox(C_val, C_ref; rtol=5e-4)
            # Mass conservation: A + B + C = 1 always
            @test isapprox(A_val + B_val + C_val, 1.0; atol=1e-6)
```

