# should generate model code with variables and equations (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/ESMFormat.jl/test/test_codegen.jl`

```julia
file = EsmFile(
                "0.1.0",
                Metadata("Test Model for Python");
                models = Dict(
                    "atmospheric" => Model(
                        Dict(
                            "O3" => ModelVariable(
                                StateVariable;
                                default = 50.0,
                                units = "ppb"
                            ),
                            "k1" => ModelVariable(
                                ParameterVariable;
                                default = 1e-3
                            )
                        ),
                        [
                            Equation(
                                OpExpr("D", ESMFormat.Expr[VarExpr("O3")]),
                                OpExpr("*", ESMFormat.Expr[VarExpr("k1"), VarExpr("O3")])
                            )
                        ]
                    )
                ),
                reaction_systems = Dict{String,ReactionSystem}()
            )

            code = to_python_code(file)

            @test occursin("t = sp.Symbol('t')", code)
            @test occursin("O3 = sp.Function('O3')  # ppb", code)
            @test occursin("k1 = sp.Symbol('k1')", code)
            @test occursin("eq1 = sp.Eq(sp.Derivative(O3(t), t), k1 * O3)", code)
```

