# End-to-end simulation (solve) tests (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/simulate_e2e_test.jl`

```julia
# ====================================================================
    # 1. Exponential decay  — Model → System → solve
    # ====================================================================
    @testset "Exponential decay: D(x,t) = -k*x" begin
        k_val = 0.1
        x0 = 1.0
        vars = Dict{String,ModelVariable}(
            "x" => ModelVariable(StateVariable; default=x0),
            "k" => ModelVariable(ParameterVariable; default=k_val),
        )
        eq = Equation(
            OpExpr("D", ESM.Expr[VarExpr("x")], wrt="t"),
            OpExpr("*", ESM.Expr[
                OpExpr("-", ESM.Expr[VarExpr("k")]),
                VarExpr("x"),
            ]),
        )
        model = Model(vars, [eq])

        sol, simp = _solve_ode(model, :Decay, (0.0, 10.0))
        x_sym = _find_unknown(simp, "x")
        x_
```

