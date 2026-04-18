# substitute_in_equations preserves variable metadata (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/editing_test.jl`

```julia
vars = Dict{String,ModelVariable}(
                "x" => ModelVariable(StateVariable,
                                     default=1.0,
                                     description="state var",
                                     units="kg"),
                "param" => ModelVariable(ParameterVariable,
                                         default=0.5,
                                         description="rate",
                                         units="1/s"),
            )
            # D(x) = param
            lhs = OpExpr("D", ESS.Expr[VarExpr("x")], wrt="t")
            rhs = VarExpr("param")
            model = Model(vars, Equation[Equation(lhs, rhs)])

            bindings = Dict{String,ESS.Expr}("param" => NumExpr(0.5))
            result = substitute_in_equations(model, bindings)

            # Equations rewritten
            @test length(result.equations) == 1
            @test result.equations[1].rhs == NumExpr(0.5)
            # Variables dict and all per-variable metadata preserved (attribute-
            # preservation analog of Python's test_substitute_in_model_with_metadata)
            @test result.variables == model.variables
            x = result.variables["x"]
            @test x.type == StateVariable
            @test x.default == 1.0
            @test x.description == "state var"
            @test x.units == "kg"
            p = result.variables["param"]
            @test p.default == 0.5
            @test p.units == "1/s"
            @test p.description == "rate"
            # Events/subsystems/domain/tolerance containers preserved
            @test result.discrete_events === model.discrete_events
            @test result.continuous_events === model.continuous_events
            @test result.subsystems === model.subsystems
            @test result.domain === model.domain
            @test result.tolerance === model.tolerance
```

