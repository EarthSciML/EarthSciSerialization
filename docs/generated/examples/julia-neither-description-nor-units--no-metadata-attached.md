# Neither description nor units: no metadata attached (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/mtk_metadata_test.jl`

```julia
vars = Dict(
            "x" => ModelVariable(StateVariable; default=1.0),
            "k" => ModelVariable(ParameterVariable; default=0.1),
        )
        eq = Equation(
            OpExpr("D", EarthSciSerialization.Expr[VarExpr("x")], wrt="t"),
            OpExpr("*", EarthSciSerialization.Expr[
                VarExpr("k"), VarExpr("x"),
            ]),
        )
        sys = ModelingToolkit.System(Model(vars, [eq]); name=:Bare)
        # MTK's getdescription returns "" when VariableDescription isn't set.
        for u in ModelingToolkit.unknowns(sys)
            @test ModelingToolkit.getdescription(u) == ""
```

