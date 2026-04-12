# Reversible first-order reaction A ⇌ B → steady state (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/simulate_e2e_test.jl`

```julia
k1, k2 = 1.0, 0.5
        A0, B0 = 1.0, 0.0
        # Model directly as ODEs so we fully control the equations
        # (the test's purpose is solve correctness, not reaction-to-ODE
        # derivation — that path is covered by test case 3 below).
        vars = Dict{String,ModelVariable}(
            "A" => ModelVariable(StateVariable; default=A0),
            "B" => ModelVariable(StateVariable; default=B0),
            "k1" => ModelVariable(ParameterVariable; default=k1),
            "k2" => ModelVariable(ParameterVariable; default=k2),
        )
        # dA/dt = -k1*A + k2*B
        eqA = Equation(
            OpExpr("D", ESM.Expr[VarExpr("A")], wrt="t"),
            OpExpr("+", ESM.Expr[
                OpExpr("-", ESM.Expr[
                    OpExpr("*", ESM.Expr[VarExpr("k1"), VarExpr("A")]),
                ]),
                OpExpr("*", ESM.Expr[VarExpr("k2"), VarExpr("B")]),
            ]),
        )
        # dB/dt =  k1*A - k2*B
        eqB = Equation(
            OpExpr("D", ESM.Expr[VarExpr("B")], wrt="t"),
            OpExpr("-", ESM.Expr[
                OpExpr("*", ESM.Expr[VarExpr("k1"), VarExpr("A")]),
                OpExpr("*", ESM.Expr[VarExpr("k2"), VarExpr("B")]),
            ]),
        )
        model = Model(vars, [eqA, eqB])

        # Integrate to "steady state". Characteristic time is 1/(k1+k2) = 2/3;
        # t = 50 is ~33 characteristic times, more than enough to settle.
        sol, simp = _solve_ode(model, :AB, (0.0, 50.0))
        Asym = _find_unknown(simp, "A")
        Bsym = _find_unknown(simp, "B")

        A_eq = sol[Asym][
```

