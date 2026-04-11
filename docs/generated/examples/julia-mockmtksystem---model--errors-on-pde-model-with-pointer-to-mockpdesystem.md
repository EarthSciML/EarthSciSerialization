# MockMTKSystem(::Model) errors on PDE model with pointer to MockPDESystem (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/mtk_catalyst_test.jl`

```julia
domains = Dict{String,Domain}(
            "col" => Domain(spatial=Dict{String,Any}("x" => Dict())))
        vars = Dict{String,ModelVariable}(
            "u" => ModelVariable(StateVariable; default=1.0),
            "D" => ModelVariable(ParameterVariable; default=0.1),
        )
        # PDE: du/dt = D * grad(grad(u, x), x)  (spatial derivatives present)
        eq = Equation(
            OpExpr("D", EarthSciSerialization.Expr[VarExpr("u")], wrt="t"),
            OpExpr("*", EarthSciSerialization.Expr[
                VarExpr("D"),
                OpExpr("grad", EarthSciSerialization.Expr[
                    OpExpr("grad", EarthSciSerialization.Expr[VarExpr("u")], dim="x"),
                ], dim="x"),
            ])
        )
        model = Model(vars, [eq], domain="col")
        file = EsmFile("0.1.0", Metadata("Diffuse");
            models=Dict("Diffuse" => model), domains=domains)
        flat = flatten(file)
        @test :x in flat.indep
```

