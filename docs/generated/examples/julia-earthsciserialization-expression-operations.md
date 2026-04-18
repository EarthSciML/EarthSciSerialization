# EarthSciSerialization.Expression Operations (Julia)

**Source:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/test/expression_test.jl`

```julia
@testset "substitute function" begin
        # Unit-level behaviors not expressible as fixture cases:
        # object-identity preservation, wrt/dim passthrough.
        num = NumExpr(3.14)
        bindings = Dict{String,EarthSciSerialization.Expr}("x" => NumExpr(2.0))
        @test substitute(num, bindings) === num

        var_x = VarExpr("x")
        @test substitute(var_x, bindings) === bindings["x"]

        var_y = VarExpr("y")
        @test substitute(var_y, bindings) === var_y

        diff_expr = OpExpr("D", EarthSciSerialization.Expr[var_x], wrt="t", dim="time")
        result = substitute(diff_expr, bindings)
        @test result.wrt == "t"
        @test result.dim == "time"
```

