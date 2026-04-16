# State variable carries description + units (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/mtk_metadata_test.jl`

```julia
ext = Base.get_extension(EarthSciSerialization, :EarthSciSerializationMTKExt)

        vars = Dict(
            "sea_level_rise" => ModelVariable(StateVariable;
                default=0.0, description="sea level rise", units="m"),
            "k" => ModelVariable(ParameterVariable; default=0.1,
                description="decay rate", units="1/s"),
        )
        eq = Equation(
            OpExpr("D", EarthSciSerialization.Expr[VarExpr("sea_level_rise")],
                wrt="t"),
            OpExpr("*", EarthSciSerialization.Expr[
                VarExpr("k"), VarExpr("sea_level_rise"),
            ]),
        )
        model = Model(vars, [eq])
        sys = ModelingToolkit.System(model; name=:SLR)

        # Pull the unknowns/parameters off the real System and check their
        # description metadata survives the round-trip into MTK.
        u_descs = [ModelingToolkit.getdescription(u)
                   for u in ModelingToolkit.unknowns(sys)]
        p_descs = [ModelingToolkit.getdescription(p)
                   for p in ModelingToolkit.parameters(sys)]

        @test "sea level rise (units=m)" in u_descs
        @test "decay rate (units=1/s)" in p_descs
```

