#!/usr/bin/env julia
"""
Basic test for MTK system conversion
"""

using ESMFormat
println("ESMFormat loaded")

# Create a simple test model
vars = Dict(
    "x" => ModelVariable(StateVariable, default=1.0),
    "k" => ModelVariable(ParameterVariable, default=0.5)
)

# Create simple equation: dx/dt = -k*x
lhs = OpExpr("D", [VarExpr("x")], wrt="t")
rhs = OpExpr("*", [OpExpr("-", [VarExpr("k")]), VarExpr("x")])
eq = Equation(lhs, rhs)

model = Model(vars, [eq])
println("Created test model with variables: $(keys(model.variables))")
println("Equation: D(x) = -k * x")

# Test if to_mtk_system function is available
if hasmethod(to_mtk_system, (Model,))
    println("✓ to_mtk_system method is available")

    try
        println("Attempting to convert to MTK system...")
        sys = to_mtk_system(model)
        println("✓ MTK conversion successful!")
        println("System type: $(typeof(sys))")
    catch e
        println("✗ MTK conversion failed: $e")
        println("This might be due to precompilation issues with ModelingToolkit")
    end
else
    println("✗ to_mtk_system method not found")
end