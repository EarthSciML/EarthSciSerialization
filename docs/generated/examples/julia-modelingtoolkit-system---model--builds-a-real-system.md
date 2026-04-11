# ModelingToolkit.System(::Model) builds a real System (Julia)

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
        model = Model(vars, [eq])
        sys = ModelingToolkit.System(model; name=:RealTest)

        @test !(sys isa MockMTKSystem)
        type_str = string(typeof(sys))
        @test occursin("System", type_str) || occursin("ODE", type_str)

        # After flatten+extension, variables are namespaced as `RealTest.x`
        # and sanitized to `RealTest_x` for symbol construction.
        un_names = Set(string(ModelingToolkit.getname(u))
                       for u in ModelingToolkit.unknowns(sys))
        @test any(occursin("x", n) for n in un_names)

        pn_names = Set(string(ModelingToolkit.getname(p))
                       for p in ModelingToolkit.parameters(sys))
        @test any(occursin("k", n) for n in pn_names)
```

