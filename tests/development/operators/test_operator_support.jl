#!/usr/bin/env julia

using EarthSciSerialization

# Test basic operator support in mtk.jl
println("Testing ESM to MTK operator conversion...")

# Create simple expressions using different operators
var_dict = Dict{String, Any}("x" => :x_symbol, "y" => :y_symbol)

# Test each operator mentioned in the task description
test_operators = [
    ("^", OpExpr("^", EarthSciSerialization.Expr[VarExpr("x"), NumExpr(2.0)])),
    ("exp", OpExpr("exp", EarthSciSerialization.Expr[VarExpr("x")])),
    ("log", OpExpr("log", EarthSciSerialization.Expr[VarExpr("x")])),
    ("sin", OpExpr("sin", EarthSciSerialization.Expr[VarExpr("x")])),
    ("cos", OpExpr("cos", EarthSciSerialization.Expr[VarExpr("x")])),
    ("tan", OpExpr("tan", EarthSciSerialization.Expr[VarExpr("x")])),
    ("ifelse", OpExpr("ifelse", EarthSciSerialization.Expr[
        OpExpr(">", EarthSciSerialization.Expr[VarExpr("x"), NumExpr(0.0)]),
        VarExpr("x"),
        NumExpr(0.0)
    ])),
    ("Pre", OpExpr("Pre", EarthSciSerialization.Expr[VarExpr("x")])),
    (">", OpExpr(">", EarthSciSerialization.Expr[VarExpr("x"), VarExpr("y")])),
    ("<", OpExpr("<", EarthSciSerialization.Expr[VarExpr("x"), VarExpr("y")])),
    (">=", OpExpr(">=", EarthSciSerialization.Expr[VarExpr("x"), VarExpr("y")])),
    ("<=", OpExpr("<=", EarthSciSerialization.Expr[VarExpr("x"), VarExpr("y")])),
    ("==", OpExpr("==", EarthSciSerialization.Expr[VarExpr("x"), VarExpr("y")])),
    ("!=", OpExpr("!=", EarthSciSerialization.Expr[VarExpr("x"), VarExpr("y")])),
    ("&&", OpExpr("&&", EarthSciSerialization.Expr[
        OpExpr(">", EarthSciSerialization.Expr[VarExpr("x"), NumExpr(0.0)]),
        OpExpr(">", EarthSciSerialization.Expr[VarExpr("y"), NumExpr(0.0)])
    ])),
    ("||", OpExpr("||", EarthSciSerialization.Expr[
        OpExpr(">", EarthSciSerialization.Expr[VarExpr("x"), NumExpr(0.0)]),
        OpExpr(">", EarthSciSerialization.Expr[VarExpr("y"), NumExpr(0.0)])
    ])),
    ("!", OpExpr("!", EarthSciSerialization.Expr[OpExpr(">", EarthSciSerialization.Expr[VarExpr("x"), NumExpr(0.0)])])),
]

println("\nTesting operators individually:")
for (op_name, expr) in test_operators
    try
        # This will call esm_to_mtk_expr function
        result = EarthSciSerialization.esm_to_mtk_expr(expr, var_dict, :t_symbol)
        println("✓ $op_name: Converted successfully")
    catch e
        println("✗ $op_name: Failed with error: $e")
    end
end

# Test spatial operators that need special handling
spatial_operators = [
    ("grad", OpExpr("grad", EarthSciSerialization.Expr[VarExpr("x")], dim="x")),
    ("div", OpExpr("div", EarthSciSerialization.Expr[VarExpr("x")], dim="y")),
    ("laplacian", OpExpr("laplacian", EarthSciSerialization.Expr[VarExpr("x")])),
]

println("\nTesting spatial operators:")
for (op_name, expr) in spatial_operators
    try
        result = EarthSciSerialization.esm_to_mtk_expr(expr, var_dict, :t_symbol)
        println("✓ $op_name: Converted successfully")
    catch e
        println("✗ $op_name: Failed with error: $e")
    end
end

println("\nOperator testing complete.")