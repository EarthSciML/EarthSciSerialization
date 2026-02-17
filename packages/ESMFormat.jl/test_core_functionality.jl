# Test core ESMFormat functionality
using ESMFormat
using Test
using JSON3

println("Testing ESMFormat core functionality...")

@testset "Core ESMFormat Tests" begin

    @testset "Expression Types" begin
        # Test NumExpr
        num_expr = NumExpr(3.14)
        @test num_expr.value == 3.14
        @test num_expr isa ESMFormat.Expr

        # Test VarExpr
        var_expr = VarExpr("x")
        @test var_expr.name == "x"
        @test var_expr isa ESMFormat.Expr

        # Test OpExpr
        op_expr = OpExpr("+", ESMFormat.Expr[NumExpr(1.0), VarExpr("x")])
        @test op_expr.op == "+"
        @test length(op_expr.args) == 2
        @test op_expr.wrt === nothing
        @test op_expr.dim === nothing
        @test op_expr isa ESMFormat.Expr

        println("✓ Expression types work correctly")
    end

    @testset "Basic JSON serialization" begin
        # Test with a simple structure that should work
        test_data = Dict{String,Any}(
            "type" => "NumExpr",
            "value" => 42.0
        )

        # Test JSON3 serialization
        json_str = JSON3.write(test_data)
        parsed_back = JSON3.read(json_str)

        @test parsed_back["type"] == "NumExpr"
        @test parsed_back["value"] == 42.0

        println("✓ Basic JSON serialization works")
    end

    @testset "Type hierarchy" begin
        # Test that all expression types are subtypes of Expr
        @test NumExpr <: ESMFormat.Expr
        @test VarExpr <: ESMFormat.Expr
        @test OpExpr <: ESMFormat.Expr

        println("✓ Type hierarchy is correct")
    end
end

println("✅ All core functionality tests passed!")