# Only description (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/mtk_metadata_test.jl`

```julia
vars = Dict(
            "x" => ModelVariable(StateVariable; default=1.0,
                description="population count"),
            "k" => ModelVariable(ParameterVariable; default=0.1),
        )
        eq = Equation(
            OpExpr("D", EarthSciSerialization.Expr[VarExpr("x")], wrt="t"),
            OpExpr("*", EarthSciSerialization.Expr[
                VarExpr("k"), VarExpr("x"),
            ]),
        )
        sys = ModelingToolkit.System(Model(vars, [eq]); name=:Only_Desc)
        descs = [ModelingToolkit.getdescription(u)
                 for u in ModelingToolkit.unknowns(sys)]
        @test "population count" in descs
```

