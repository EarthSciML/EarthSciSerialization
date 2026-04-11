# ModelingToolkit.System(::Model) errors on PDE model with pointer to PDESystem (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/real_mtk_integration_test.jl`

```julia
domains = Dict{String,Domain}(
            "col" => Domain(spatial=Dict{String,Any}("z" => Dict())))
        vars = Dict{String,ModelVariable}(
            "u" => ModelVariable(StateVariable; default=1.0),
            "D" => ModelVariable(ParameterVariable; default=0.1),
        )
        eq = Equation(
            OpExpr("D", EarthSciSerialization.Expr[VarExpr("u")], wrt="t"),
            OpExpr("*", EarthSciSerialization.Expr[
                VarExpr("D"),
                OpExpr("grad", EarthSciSerialization.Expr[
                    OpExpr("grad", EarthSciSerialization.Expr[VarExpr("u")], dim="z"),
                ], dim="z"),
            ]),
        )
        model = Model(vars, [eq], domain="col")
        file = EsmFile("0.1.0", Metadata("Diffuse");
            models=Dict("Diffuse" => model), domains=domains)
        flat = flatten(file)
        @test :z in flat.indep
```

