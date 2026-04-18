# rename_variable across a model (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/editing_test.jl`

```julia
# Model with two equations that both reference the variable being
            # renamed, plus a parameter that should survive untouched.
            vars = Dict{String,ModelVariable}(
                "C" => ModelVariable(StateVariable,
                                     default=1.0,
                                     description="concentration",
                                     units="mol/m^3"),
                "k" => ModelVariable(ParameterVariable, default=0.1, units="1/s"),
            )
            eq1 = Equation(
                OpExpr("D", ESS.Expr[VarExpr("C")], wrt="t"),
                OpExpr("*", ESS.Expr[NumExpr(-1.0), VarExpr("k"), VarExpr("C")]),
            )
            eq2 = Equation(
                VarExpr("C"),
                OpExpr("*", ESS.Expr[NumExpr(2.0), VarExpr("C")]),
            )
            model = Model(vars, Equation[eq1, eq2])

            renamed = rename_variable(model, "C", "O3")

            # Variable dict: old name gone, new name present, metadata carried over
            @test !haskey(renamed.variables, "C")
            @test haskey(renamed.variables, "O3")
            o3 = renamed.variables["O3"]
            @test o3.type == StateVariable
            @test o3.default == 1.0
            @test o3.description == "concentration"
            @test o3.units == "mol/m^3"
            # Unrelated variable untouched
            @test renamed.variables["k"].default == 0.1
            @test renamed.variables["k"].units == "1/s"

            # Equation rewriting: every VarExpr("C") → VarExpr("O3")
            @test length(renamed.equations) == 2
            @test _expr_equal(renamed.equations[1].lhs.args[1], VarExpr("O3"))
            mul = renamed.equations[1].rhs
            @test _expr_equal(mul.args[3], VarExpr("O3"))
            @test _expr_equal(mul.args[2], VarExpr("k"))  # other vars untouched
            @test _expr_equal(renamed.equations[2].lhs, VarExpr("O3"))
            @test _expr_equal(renamed.equations[2].rhs.args[2], VarExpr("O3"))

            # Original model is not mutated
            @test haskey(model.variables, "C")
            @test !haskey(model.variables, "O3")
```

