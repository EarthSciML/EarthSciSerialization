# substitute_in_equations rewrites expression trees (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/editing_test.jl`

```julia
m = _make_model()  # D(x) = 2*x
        bindings = Dict{String, ESS.Expr}("x" => NumExpr(42.0))
        m2 = substitute_in_equations(m, bindings)

        @test length(m2.equations) == 1
        rhs = m2.equations[1].rhs
        @test rhs isa OpExpr
        # Original expression: ("*", [NumExpr(2.0), VarExpr("x")]) -> x substituted
        @test rhs.args[1] isa NumExpr
        @test rhs.args[1].value == 2.0
        @test rhs.args[2] isa NumExpr
        @test rhs.args[2].value == 42.0
        # variables dict unchanged
        @test haskey(m2.variables, "x")
```

