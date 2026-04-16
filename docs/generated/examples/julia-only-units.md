# Only units (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/mtk_metadata_test.jl`

```julia
ext = Base.get_extension(EarthSciSerialization, :EarthSciSerializationMTKExt)
        vars = Dict(
            "T" => ModelVariable(StateVariable; default=300.0, units="K"),
            "k" => ModelVariable(ParameterVariable; default=0.1),
        )
        eq = Equation(
            OpExpr("D", EarthSciSerialization.Expr[VarExpr("T")], wrt="t"),
            OpExpr("*", EarthSciSerialization.Expr[
                VarExpr("k"), VarExpr("T"),
            ]),
        )
        sys = ModelingToolkit.System(Model(vars, [eq]); name=:Only_Units)
        descs = [ModelingToolkit.getdescription(u)
                 for u in ModelingToolkit.unknowns(sys)]
        @test "(units=K)" in descs
```

