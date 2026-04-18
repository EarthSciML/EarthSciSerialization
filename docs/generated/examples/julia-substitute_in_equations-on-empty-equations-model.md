# substitute_in_equations on empty-equations model (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/editing_test.jl`

```julia
vars = Dict{String,ModelVariable}(
                "x" => ModelVariable(StateVariable, default=1.0),
            )
            model = Model(vars, Equation[])

            result = substitute_in_equations(model, Dict{String,ESS.Expr}("a" => VarExpr("b")))
            @test isempty(result.equations)
            @test result.variables == model.variables
```

