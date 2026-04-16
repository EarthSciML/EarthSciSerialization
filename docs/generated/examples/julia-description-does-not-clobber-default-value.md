# Description does not clobber default value (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/mtk_metadata_test.jl`

```julia
vars = Dict(
            "x" => ModelVariable(StateVariable; default=2.5,
                description="thing", units="m"),
            "k" => ModelVariable(ParameterVariable; default=0.1),
        )
        eq = Equation(
            OpExpr("D", EarthSciSerialization.Expr[VarExpr("x")], wrt="t"),
            OpExpr("*", EarthSciSerialization.Expr[
                VarExpr("k"), VarExpr("x"),
            ]),
        )
        sys = ModelingToolkit.System(Model(vars, [eq]); name=:Both)

        # Find the unknown x and verify both description and default survived.
        u = first(u for u in ModelingToolkit.unknowns(sys)
                  if occursin("x", string(ModelingToolkit.getname(u))))
        @test ModelingToolkit.getdescription(u) == "thing (units=m)"
        @test Symbolics.getdefaultval(u) == 2.5
```

