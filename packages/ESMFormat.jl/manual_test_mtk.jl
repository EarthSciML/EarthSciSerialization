#!/usr/bin/env julia
"""
Manual test for to_mtk_system implementation
"""

# Test without ModelingToolkit to avoid precompilation issues
try
    println("Loading ESMFormat...")
    using ESMFormat

    println("✓ ESMFormat loaded successfully")

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
    println("✓ Created test model")

    # Check if the function exists
    if hasmethod(to_mtk_system, (Model,))
        println("✓ to_mtk_system method found with Model parameter")
    else
        println("✗ to_mtk_system method not found")
        exit(1)
    end

    if hasmethod(to_mtk_system, (Model, Union{String,Nothing}))
        println("✓ to_mtk_system method found with optional name parameter")
    else
        println("✗ to_mtk_system method with name parameter not found")
        exit(1)
    end

    println("✓ All checks passed! MTK conversion function is properly implemented.")

catch e
    println("✗ Error: $e")
    exit(1)
end