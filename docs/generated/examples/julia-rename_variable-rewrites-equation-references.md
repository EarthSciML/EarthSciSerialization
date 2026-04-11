# rename_variable rewrites equation references (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/editing_test.jl`

```julia
m = _make_model()  # equation: D(x) = 2*x
        m2 = rename_variable(m, "x", "z")

        @test !haskey(m2.variables, "x")
        @test haskey(m2.variables, "z")
        # rewritten equation: D(z) = 2*z
        @test length(m2.equations) == 1
        eq = m2.equations[1]
        @test eq.lhs isa OpExpr
        @test eq.lhs.op == "D"
        @test eq.lhs.args[1] isa VarExpr
        @test eq.lhs.args[1].name == "z"
        @test eq.rhs.args[2] isa VarExpr
        @test eq.rhs.args[2].name == "z"
        # original unchanged
        @test haskey(m.variables, "x")
```

