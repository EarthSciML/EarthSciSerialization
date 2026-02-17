# Basic Functionality (Julia)

**Source:** `/home/ctessum/EarthSciSerialization/packages/ESMFormat.jl/test/compat_test.jl`

```julia
using ESMFormat

        # Test basic type creation
        @test_nowarn NumExpr(1.0)
        @test_nowarn VarExpr("x")
        @test_nowarn OpExpr("+", ESMFormat.Expr[NumExpr(1.0), NumExpr(2.0)])
        println("Basic expression types work ✓")

        # Test model creation
        variables = Dict("x" => ModelVariable(StateVariable))
        equations = [Equation(VarExpr("x"), NumExpr(1.0))]
        @test_nowarn Model(variables, equations)
        println("Model creation works ✓")

        # Test serialization roundtrip
        model = Model(variables, equations)
        esm_file = EsmFile("1.0", Dict("test" => model))

        json_str = ESMFormat.serialize(esm_file)
        @test isa(json_str, String)

        parsed = ESMFormat.parse(json_str)
        @test isa(parsed, EsmFile)
        println("Serialization roundtrip works ✓")
```

