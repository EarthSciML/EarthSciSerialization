using Test
using ESMFormat

@testset "Simple Expression Test" begin
    # Test basic functionality
    x = VarExpr("x")
    y = VarExpr("y")

    # Test free_variables
    sum_expr = OpExpr("+", ESMFormat.Expr[x, y])
    @test free_variables(sum_expr) == Set(["x", "y"])

    # Test substitute
    bindings = Dict{String,ESMFormat.Expr}("x" => NumExpr(2.0))
    result = substitute(sum_expr, bindings)
    @test result isa OpExpr
    @test result.args[1] == NumExpr(2.0)
    @test result.args[2] == y

    # Test contains
    @test ESMFormat.contains(sum_expr, "x")
    @test ESMFormat.contains(sum_expr, "y")
    @test !ESMFormat.contains(sum_expr, "z")

    # Test evaluate
    eval_bindings = Dict("x" => 2.0, "y" => 3.0)
    @test evaluate(sum_expr, eval_bindings) == 5.0

    # Test simplify
    zero_expr = OpExpr("+", ESMFormat.Expr[x, NumExpr(0.0)])
    @test simplify(zero_expr) == x

    println("All tests passed!")
end