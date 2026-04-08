#!/usr/bin/env julia

using ESMFormat

# Test basic operator support in mtk.jl
println("Testing ESM to MTK operator conversion...")

# Create simple expressions using different operators
var_dict = Dict{String, Any}("x" => :x_symbol, "y" => :y_symbol)

# Test each operator mentioned in the task description
test_operators = [
    ("^", OpExpr("^", ESMFormat.Expr[VarExpr("x"), NumExpr(2.0)])),
    ("exp", OpExpr("exp", ESMFormat.Expr[VarExpr("x")])),
    ("log", OpExpr("log", ESMFormat.Expr[VarExpr("x")])),
    ("sin", OpExpr("sin", ESMFormat.Expr[VarExpr("x")])),
    ("cos", OpExpr("cos", ESMFormat.Expr[VarExpr("x")])),
    ("tan", OpExpr("tan", ESMFormat.Expr[VarExpr("x")])),
    ("ifelse", OpExpr("ifelse", ESMFormat.Expr[
        OpExpr(">", ESMFormat.Expr[VarExpr("x"), NumExpr(0.0)]),
        VarExpr("x"),
        NumExpr(0.0)
    ])),
    ("Pre", OpExpr("Pre", ESMFormat.Expr[VarExpr("x")])),
    (">", OpExpr(">", ESMFormat.Expr[VarExpr("x"), VarExpr("y")])),
    ("<", OpExpr("<", ESMFormat.Expr[VarExpr("x"), VarExpr("y")])),
    (">=", OpExpr(">=", ESMFormat.Expr[VarExpr("x"), VarExpr("y")])),
    ("<=", OpExpr("<=", ESMFormat.Expr[VarExpr("x"), VarExpr("y")])),
    ("==", OpExpr("==", ESMFormat.Expr[VarExpr("x"), VarExpr("y")])),
    ("!=", OpExpr("!=", ESMFormat.Expr[VarExpr("x"), VarExpr("y")])),
    ("&&", OpExpr("&&", ESMFormat.Expr[
        OpExpr(">", ESMFormat.Expr[VarExpr("x"), NumExpr(0.0)]),
        OpExpr(">", ESMFormat.Expr[VarExpr("y"), NumExpr(0.0)])
    ])),
    ("||", OpExpr("||", ESMFormat.Expr[
        OpExpr(">", ESMFormat.Expr[VarExpr("x"), NumExpr(0.0)]),
        OpExpr(">", ESMFormat.Expr[VarExpr("y"), NumExpr(0.0)])
    ])),
    ("!", OpExpr("!", ESMFormat.Expr[OpExpr(">", ESMFormat.Expr[VarExpr("x"), NumExpr(0.0)])])),
]

println("\nTesting operators individually:")
for (op_name, expr) in test_operators
    try
        # This will call esm_to_mtk_expr function
        result = ESMFormat.esm_to_mtk_expr(expr, var_dict, :t_symbol)
        println("✓ $op_name: Converted successfully")
    catch e
        println("✗ $op_name: Failed with error: $e")
    end
end

# Test spatial operators that need special handling
spatial_operators = [
    ("grad", OpExpr("grad", ESMFormat.Expr[VarExpr("x")], dim="x")),
    ("div", OpExpr("div", ESMFormat.Expr[VarExpr("x")], dim="y")),
    ("laplacian", OpExpr("laplacian", ESMFormat.Expr[VarExpr("x")])),
]

println("\nTesting spatial operators:")
for (op_name, expr) in spatial_operators
    try
        result = ESMFormat.esm_to_mtk_expr(expr, var_dict, :t_symbol)
        println("✓ $op_name: Converted successfully")
    catch e
        println("✗ $op_name: Failed with error: $e")
    end
end

println("\nOperator testing complete.")