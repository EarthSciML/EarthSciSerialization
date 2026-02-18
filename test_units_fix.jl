#!/usr/bin/env julia

# Test to verify that the units.jl get() bug has been fixed

using Pkg
Pkg.activate("packages/ESMFormat.jl")

using ESMFormat

# Create test structures
test_var = ESMFormat.ModelVariable(ESMFormat.StateVariable, units="m/s")
test_species = ESMFormat.Species("CO2", molecular_weight=44.01)
test_param = ESMFormat.Parameter("k1", 1.5, units="1/s")
test_expr = ESMFormat.OpExpr("D", ESMFormat.Expr[ESMFormat.VarExpr("x")], wrt="t")

println("Testing units.jl functions that used to have get() bugs...")

# Test validate_model_dimensions
test_model = ESMFormat.Model(
    Dict("x" => test_var),
    [ESMFormat.Equation(ESMFormat.VarExpr("x"), ESMFormat.NumExpr(1.0))]
)

try
    result = ESMFormat.validate_model_dimensions(test_model)
    println("✓ validate_model_dimensions worked, returned: $result")
catch e
    println("✗ validate_model_dimensions failed: $e")
end

# Test validate_reaction_system_dimensions
test_rxn_sys = ESMFormat.ReactionSystem(
    [test_species],
    [ESMFormat.Reaction(Dict("CO2" => 1), Dict("CO2" => 1), ESMFormat.NumExpr(0.1))],
    parameters=[test_param]
)

try
    result = ESMFormat.validate_reaction_system_dimensions(test_rxn_sys)
    println("✓ validate_reaction_system_dimensions worked, returned: $result")
catch e
    println("✗ validate_reaction_system_dimensions failed: $e")
end

# Test get_expression_dimensions with OpExpr containing derivative
var_units = Dict("x" => "m", "t" => "s")

try
    result = ESMFormat.get_expression_dimensions(test_expr, var_units)
    println("✓ get_expression_dimensions for derivative worked, returned: $result")
catch e
    println("✗ get_expression_dimensions for derivative failed: $e")
end

println("\nAll tests completed!")