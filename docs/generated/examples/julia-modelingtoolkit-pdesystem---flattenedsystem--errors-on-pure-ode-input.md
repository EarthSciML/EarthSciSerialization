# ModelingToolkit.PDESystem(::FlattenedSystem) errors on pure-ODE input (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/real_mtk_integration_test.jl`

```julia
vars = Dict(
            "x" => ModelVariable(StateVariable; default=1.0),
            "k" => ModelVariable(ParameterVariable; default=0.5),
        )
        eq = Equation(
            OpExpr("D", EarthSciSerialization.Expr[VarExpr("x")], wrt="t"),
            OpExpr("*", EarthSciSerialization.Expr[
                OpExpr("-", EarthSciSerialization.Expr[VarExpr("k")]),
                VarExpr("x"),
            ]),
        )
        flat = flatten(Model(vars, [eq]); name="OnlyODE")
        @test_throws ArgumentError ModelingToolkit.PDESystem(flat; name=:OnlyODE)
```

