#!/usr/bin/env julia
"""
Test script for spatial operators (grad, div, laplacian) in MTK conversion
"""

using ESMFormat

println("Testing spatial operators...")

# Create simple variable dictionary for testing
var_dict = Dict{String, Any}("u" => "test_u", "v" => "test_v")
t = "test_t"

# Test spatial operators
test_cases = [
    ("grad(u, x)", OpExpr("grad", ESMFormat.Expr[VarExpr("u")], dim="x")),
    ("grad(u, y)", OpExpr("grad", ESMFormat.Expr[VarExpr("u")], dim="y")),
    ("div(v, x)", OpExpr("div", ESMFormat.Expr[VarExpr("v")], dim="x")),
    ("div(v, y)", OpExpr("div", ESMFormat.Expr[VarExpr("v")], dim="y")),
    ("laplacian(u)", OpExpr("laplacian", ESMFormat.Expr[VarExpr("u")])),
]

println("\nTesting spatial operators with mock MTK:")
for (desc, expr) in test_cases
    println("\nTesting: $desc")
    try
        # Test the esm_to_mtk_expr function directly
        result = ESMFormat.esm_to_mtk_expr(expr, var_dict, t)
        println("  ✓ SUCCESS: Expression converted")
        println("    Result type: $(typeof(result))")
        println("    Result: $result")
    catch e
        println("  ✗ FAILED: $e")
        println("    Stacktrace: $(stacktrace())")
    end
end

println("\n" * "="^60)
println("Testing full MTK system conversion with spatial operators")

# Create a simple model with spatial operators
vars = Dict{String,ModelVariable}(
    "u" => ModelVariable(StateVariable, default=1.0),
    "k" => ModelVariable(ParameterVariable, default=0.5)
)

# Equation: du/dt = -k*laplacian(u)
lhs = OpExpr("D", ESMFormat.Expr[VarExpr("u")], wrt="t")
rhs = OpExpr("*", ESMFormat.Expr[
    OpExpr("-", ESMFormat.Expr[VarExpr("k")]),
    OpExpr("laplacian", ESMFormat.Expr[VarExpr("u")])
])
eq = Equation(lhs, rhs)
model = Model(vars, [eq])

println("\nTesting to_mtk_system with spatial operators:")
try
    sys = to_mtk_system(model, "SpatialTestModel")
    println("  ✓ SUCCESS: MTK system created")
    println("    System type: $(typeof(sys))")
    if sys isa MockMTKSystem
        println("    Using mock system (MTK not available)")
        println("    States: $(sys.states)")
        println("    Parameters: $(sys.parameters)")
        println("    Equations: $(length(sys.equations))")
    else
        println("    Using real MTK system")
    end
catch e
    println("  ✗ FAILED: $e")
    # Print more detailed error info
    println("    Error type: $(typeof(e))")
    if e isa BoundsError
        println("    BoundsError: likely issue with accessing expression arguments")
    elseif e isa MethodError
        println("    MethodError: likely issue with MTK function calls")
    end
end

println("\nSpatial operator testing complete.")