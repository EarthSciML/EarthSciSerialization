#!/usr/bin/env julia

# Simple test to reproduce the units.jl get() bug

using Pkg
Pkg.activate("packages/ESMFormat.jl")

using ESMFormat

# Create test structures that would trigger the MethodError
test_var = ESMFormat.ModelVariable(ESMFormat.StateVariable, units="m/s")
test_species = ESMFormat.Species("CO2", molecular_weight=44.01)
test_param = ESMFormat.Parameter("k1", 1.5, units="1/s")
test_expr = ESMFormat.OpExpr("D", ESMFormat.Expr[ESMFormat.VarExpr("x")], wrt="t")

println("Testing get() calls that should fail...")

# These should all throw MethodError due to using get() on structs
try
    result = get(test_var, :units, "")
    println("ERROR: get(ModelVariable, :units, '') should have failed but returned: $result")
catch e
    println("✓ Expected MethodError for ModelVariable: $e")
end

try
    result = get(test_species, :units, "mol/L")
    println("ERROR: get(Species, :units, 'mol/L') should have failed but returned: $result")
catch e
    println("✓ Expected MethodError for Species: $e")
end

try
    result = get(test_param, :units, "")
    println("ERROR: get(Parameter, :units, '') should have failed but returned: $result")
catch e
    println("✓ Expected MethodError for Parameter: $e")
end

try
    result = get(test_expr, :wrt, "t")
    println("ERROR: get(OpExpr, :wrt, 't') should have failed but returned: $result")
catch e
    println("✓ Expected MethodError for OpExpr: $e")
end

println("\nTesting correct field access...")

# These should work
println("ModelVariable.units = $(test_var.units)")
println("Species has no units field")
println("Parameter.units = $(test_param.units)")
println("OpExpr.wrt = $(test_expr.wrt)")