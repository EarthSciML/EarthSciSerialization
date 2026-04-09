using Test
using EarthSciSerialization

@testset "EarthSciSerialization.Expression Operations" begin

    @testset "substitute function" begin
        # Test NumExpr (should remain unchanged)
        num = NumExpr(3.14)
        bindings = Dict{String,EarthSciSerialization.Expr}("x" => NumExpr(2.0))
        @test substitute(num, bindings) === num

        # Test VarExpr with binding
        var_x = VarExpr("x")
        @test substitute(var_x, bindings) === bindings["x"]

        # Test VarExpr without binding (should remain unchanged)
        var_y = VarExpr("y")
        @test substitute(var_y, bindings) === var_y

        # Test OpExpr substitution
        sum_expr = OpExpr("+", EarthSciSerialization.Expr[var_x, var_y])
        result = substitute(sum_expr, bindings)
        @test result isa OpExpr
        @test result.op == "+"
        @test length(result.args) == 2
        @test result.args[1] === bindings["x"]
        @test result.args[2] === var_y

        # Test nested OpExpr substitution
        nested = OpExpr("*", EarthSciSerialization.Expr[OpExpr("+", EarthSciSerialization.Expr[var_x, NumExpr(1.0)]), var_y])
        result = substitute(nested, bindings)
        @test result isa OpExpr
        @test result.op == "*"
        @test result.args[1] isa OpExpr
        @test result.args[1].args[1] === bindings["x"]

        # Test OpExpr with wrt and dim fields
        diff_expr = OpExpr("D", EarthSciSerialization.Expr[var_x], wrt="t", dim="time")
        result = substitute(diff_expr, bindings)
        @test result.wrt == "t"
        @test result.dim == "time"
    end

    @testset "free_variables function" begin
        # Test NumExpr (no variables)
        num = NumExpr(3.14)
        @test free_variables(num) == Set{String}()

        # Test VarExpr (single variable)
        var_x = VarExpr("x")
        @test free_variables(var_x) == Set(["x"])

        # Test OpExpr with multiple variables
        sum_expr = OpExpr("+", EarthSciSerialization.Expr[VarExpr("x"), VarExpr("y")])
        @test free_variables(sum_expr) == Set(["x", "y"])

        # Test nested expressions
        nested = OpExpr("*", EarthSciSerialization.Expr[OpExpr("+", EarthSciSerialization.Expr[VarExpr("x"), NumExpr(1.0)]), VarExpr("y")])
        @test free_variables(nested) == Set(["x", "y"])

        # Test OpExpr with wrt field
        diff_expr = OpExpr("D", EarthSciSerialization.Expr[VarExpr("x")], wrt="t")
        @test free_variables(diff_expr) == Set(["x", "t"])

        # Test expression with repeated variables
        repeated = OpExpr("+", EarthSciSerialization.Expr[VarExpr("x"), VarExpr("x"), VarExpr("y")])
        @test free_variables(repeated) == Set(["x", "y"])
    end

    @testset "contains function" begin
        # Test NumExpr (contains no variables)
        num = NumExpr(3.14)
        @test !EarthSciSerialization.contains(num, "x")

        # Test VarExpr
        var_x = VarExpr("x")
        @test EarthSciSerialization.contains(var_x, "x")
        @test !EarthSciSerialization.contains(var_x, "y")

        # Test OpExpr
        sum_expr = OpExpr("+", EarthSciSerialization.Expr[VarExpr("x"), VarExpr("y")])
        @test EarthSciSerialization.contains(sum_expr, "x")
        @test EarthSciSerialization.contains(sum_expr, "y")
        @test !EarthSciSerialization.contains(sum_expr, "z")

        # Test nested expressions
        nested = OpExpr("*", EarthSciSerialization.Expr[OpExpr("+", EarthSciSerialization.Expr[VarExpr("x"), NumExpr(1.0)]), VarExpr("y")])
        @test EarthSciSerialization.contains(nested, "x")
        @test EarthSciSerialization.contains(nested, "y")
        @test !EarthSciSerialization.contains(nested, "z")

        # Test OpExpr with wrt field
        diff_expr = OpExpr("D", EarthSciSerialization.Expr[VarExpr("x")], wrt="t")
        @test EarthSciSerialization.contains(diff_expr, "x")
        @test EarthSciSerialization.contains(diff_expr, "t")
        @test !EarthSciSerialization.contains(diff_expr, "y")
    end

    @testset "evaluate function" begin
        # Test NumExpr
        num = NumExpr(3.14)
        @test evaluate(num, Dict{String,Float64}()) == 3.14

        # Test VarExpr with binding
        var_x = VarExpr("x")
        bindings = Dict("x" => 2.5)
        @test evaluate(var_x, bindings) == 2.5

        # Test VarExpr without binding (should throw)
        @test_throws UnboundVariableError evaluate(var_x, Dict{String,Float64}())

        # Test arithmetic operations
        @test evaluate(OpExpr("+", EarthSciSerialization.Expr[NumExpr(2.0), NumExpr(3.0)]), Dict{String,Float64}()) == 5.0
        @test evaluate(OpExpr("-", EarthSciSerialization.Expr[NumExpr(5.0), NumExpr(3.0)]), Dict{String,Float64}()) == 2.0
        @test evaluate(OpExpr("*", EarthSciSerialization.Expr[NumExpr(2.0), NumExpr(3.0)]), Dict{String,Float64}()) == 6.0
        @test evaluate(OpExpr("/", EarthSciSerialization.Expr[NumExpr(6.0), NumExpr(3.0)]), Dict{String,Float64}()) == 2.0
        @test evaluate(OpExpr("^", EarthSciSerialization.Expr[NumExpr(2.0), NumExpr(3.0)]), Dict{String,Float64}()) == 8.0

        # Test unary operations
        @test evaluate(OpExpr("+", EarthSciSerialization.Expr[NumExpr(5.0)]), Dict{String,Float64}()) == 5.0
        @test evaluate(OpExpr("-", EarthSciSerialization.Expr[NumExpr(5.0)]), Dict{String,Float64}()) == -5.0

        # Test mathematical functions
        @test evaluate(OpExpr("sin", EarthSciSerialization.Expr[NumExpr(0.0)]), Dict{String,Float64}()) == 0.0
        @test evaluate(OpExpr("cos", EarthSciSerialization.Expr[NumExpr(0.0)]), Dict{String,Float64}()) == 1.0
        @test evaluate(OpExpr("exp", EarthSciSerialization.Expr[NumExpr(0.0)]), Dict{String,Float64}()) == 1.0
        @test evaluate(OpExpr("log", EarthSciSerialization.Expr[NumExpr(1.0)]), Dict{String,Float64}()) == 0.0
        @test evaluate(OpExpr("sqrt", EarthSciSerialization.Expr[NumExpr(4.0)]), Dict{String,Float64}()) == 2.0
        @test evaluate(OpExpr("abs", EarthSciSerialization.Expr[NumExpr(-5.0)]), Dict{String,Float64}()) == 5.0

        # Test constants
        π_result = evaluate(OpExpr("π", EarthSciSerialization.Expr[]), Dict{String,Float64}())
        @test π_result ≈ π
        e_result = evaluate(OpExpr("e", EarthSciSerialization.Expr[]), Dict{String,Float64}())
        @test e_result ≈ ℯ

        # Test complex expression with variables
        expr = OpExpr("+", EarthSciSerialization.Expr[OpExpr("*", EarthSciSerialization.Expr[VarExpr("x"), VarExpr("y")]), NumExpr(1.0)])
        bindings = Dict("x" => 2.0, "y" => 3.0)
        @test evaluate(expr, bindings) == 7.0

        # Test error conditions
        @test_throws DivideError evaluate(OpExpr("/", EarthSciSerialization.Expr[NumExpr(1.0), NumExpr(0.0)]), Dict{String,Float64}())
        @test_throws DomainError evaluate(OpExpr("log", EarthSciSerialization.Expr[NumExpr(-1.0)]), Dict{String,Float64}())
        @test_throws DomainError evaluate(OpExpr("sqrt", EarthSciSerialization.Expr[NumExpr(-1.0)]), Dict{String,Float64}())
        @test_throws ArgumentError evaluate(OpExpr("unknown_op", EarthSciSerialization.Expr[NumExpr(1.0)]), Dict{String,Float64}())
    end

    @testset "simplify function" begin
        # Test NumExpr and VarExpr (already simplified)
        num = NumExpr(3.14)
        @test simplify(num) === num
        var = VarExpr("x")
        @test simplify(var) === var

        # Test constant folding
        @test simplify(OpExpr("+", EarthSciSerialization.Expr[NumExpr(2.0), NumExpr(3.0)])) == NumExpr(5.0)
        @test simplify(OpExpr("*", EarthSciSerialization.Expr[NumExpr(2.0), NumExpr(3.0)])) == NumExpr(6.0)

        # Test additive identity: x + 0 = x
        var_x = VarExpr("x")
        @test simplify(OpExpr("+", EarthSciSerialization.Expr[var_x, NumExpr(0.0)])) === var_x
        @test simplify(OpExpr("+", EarthSciSerialization.Expr[NumExpr(0.0), var_x])) === var_x

        # Test additive identity with all zeros
        @test simplify(OpExpr("+", EarthSciSerialization.Expr[NumExpr(0.0), NumExpr(0.0)])) == NumExpr(0.0)

        # Test multiplicative identity: x * 1 = x
        @test simplify(OpExpr("*", EarthSciSerialization.Expr[var_x, NumExpr(1.0)])) === var_x
        @test simplify(OpExpr("*", EarthSciSerialization.Expr[NumExpr(1.0), var_x])) === var_x

        # Test multiplicative zero: x * 0 = 0
        @test simplify(OpExpr("*", EarthSciSerialization.Expr[var_x, NumExpr(0.0)])) == NumExpr(0.0)
        @test simplify(OpExpr("*", EarthSciSerialization.Expr[NumExpr(0.0), var_x])) == NumExpr(0.0)

        # Test multiplicative identity with all ones
        @test simplify(OpExpr("*", EarthSciSerialization.Expr[NumExpr(1.0), NumExpr(1.0)])) == NumExpr(1.0)

        # Test exponentiation rules
        @test simplify(OpExpr("^", EarthSciSerialization.Expr[var_x, NumExpr(0.0)])) == NumExpr(1.0)
        @test simplify(OpExpr("^", EarthSciSerialization.Expr[var_x, NumExpr(1.0)])) === var_x
        @test simplify(OpExpr("^", EarthSciSerialization.Expr[NumExpr(0.0), NumExpr(2.0)])) == NumExpr(0.0)
        @test simplify(OpExpr("^", EarthSciSerialization.Expr[NumExpr(1.0), var_x])) == NumExpr(1.0)

        # Test subtraction: x - 0 = x
        @test simplify(OpExpr("-", EarthSciSerialization.Expr[var_x, NumExpr(0.0)])) === var_x

        # Test division: x / 1 = x, 0 / x = 0
        @test simplify(OpExpr("/", EarthSciSerialization.Expr[var_x, NumExpr(1.0)])) === var_x
        @test simplify(OpExpr("/", EarthSciSerialization.Expr[NumExpr(0.0), var_x])) == NumExpr(0.0)

        # Test recursive simplification
        nested = OpExpr("*", EarthSciSerialization.Expr[OpExpr("+", EarthSciSerialization.Expr[NumExpr(1.0), NumExpr(2.0)]), var_x])
        simplified = simplify(nested)
        @test simplified isa OpExpr
        @test simplified.op == "*"
        @test simplified.args[1] == NumExpr(3.0)
        @test simplified.args[2] === var_x

        # Test n-ary operations
        n_ary_add = OpExpr("+", EarthSciSerialization.Expr[var_x, NumExpr(0.0), VarExpr("y"), NumExpr(0.0)])
        simplified = simplify(n_ary_add)
        @test simplified isa OpExpr
        @test simplified.op == "+"
        @test length(simplified.args) == 2
        @test var_x in simplified.args
        @test VarExpr("y") in simplified.args
    end

    @testset "Integration tests" begin
        # Test substitute + simplify
        expr = OpExpr("*", EarthSciSerialization.Expr[OpExpr("+", EarthSciSerialization.Expr[VarExpr("x"), NumExpr(0.0)]), VarExpr("y")])
        bindings = Dict{String,EarthSciSerialization.Expr}("y" => NumExpr(1.0))
        substituted = substitute(expr, bindings)
        simplified = simplify(substituted)
        @test simplified === VarExpr("x")

        # Test free_variables + evaluate
        expr = OpExpr("+", EarthSciSerialization.Expr[OpExpr("*", EarthSciSerialization.Expr[VarExpr("x"), VarExpr("y")]), NumExpr(1.0)])
        vars = free_variables(expr)
        @test vars == Set(["x", "y"])

        # Ensure we can evaluate with all free variables
        eval_bindings = Dict("x" => 2.0, "y" => 3.0)
        result = evaluate(expr, eval_bindings)
        @test result == 7.0

        # Test error when missing a variable
        partial_bindings = Dict("x" => 2.0)  # missing "y"
        @test_throws UnboundVariableError evaluate(expr, partial_bindings)
    end
end