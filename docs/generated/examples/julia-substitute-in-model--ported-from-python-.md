# substitute-in-model (ported from Python) (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/editing_test.jl`

```julia
@testset "shared fixtures drive model-level substitute" begin
            fixtures_dir = joinpath(@__DIR__, "..", "..", "..", "tests", "substitution")
            fixture_file = joinpath(fixtures_dir, "simple_var_replace.json")
            @test isfile(fixture_file)

            cases = JSON3.read(read(fixture_file, String))
            # simple_var_replace.json is a flat array of {input, bindings, expected}
            @test cases isa JSON3.Array
            @test !isempty(cases)

            for case in cases
                input_expr = ESS.parse_expression(case[:input])
                expected_expr = ESS.parse_expression(case[:expected])
                bindings = Dict{String, ESS.Expr}(
                    string(k) => ESS.parse_expression(v)
                    for (k, v) in pairs(case[:bindings])
                )

                # Wrap the fixture expression as the RHS of a lone equation in
                # a minimal model. The LHS references a state variable the
                # bindings won't touch so we can isolate RHS substitution.
                vars = Dict{String,ModelVariable}(
                    "out" => ModelVariable(StateVariable, default=0.0),
                )
                eq = Equation(VarExpr("out"), input_expr)
                model = Model(vars, Equation[eq])

                result = substitute_in_equations(model, bindings)
                @test length(result.equations) == 1
                @test _expr_equal(result.equations[1].lhs, VarExpr("out"))
                @test _expr_equal(result.equations[1].rhs, expected_expr)
                # variables dict is preserved verbatim
                @test result.variables == model.variables
```

