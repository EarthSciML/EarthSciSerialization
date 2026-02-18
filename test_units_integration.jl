#!/usr/bin/env julia

# Integration test to ensure the specific get() bugs in units.jl are fixed

using Pkg
Pkg.activate("packages/ESMFormat.jl")

using ESMFormat

println("Testing specific functions that had get() bugs...")

# Test 1: validate_model_dimensions with ModelVariable units access
println("\n1. Testing validate_model_dimensions (line 218 fix)...")
test_var_with_units = ESMFormat.ModelVariable(ESMFormat.StateVariable, units="m/s")
test_var_no_units = ESMFormat.ModelVariable(ESMFormat.ParameterVariable)
model_with_units = ESMFormat.Model(
    Dict("x" => test_var_with_units, "y" => test_var_no_units),
    [ESMFormat.Equation(ESMFormat.VarExpr("x"), ESMFormat.VarExpr("y"))]
)

try
    result = ESMFormat.validate_model_dimensions(model_with_units)
    println("✓ ModelVariable units access works: $result")
catch e
    println("✗ ModelVariable units access failed: $e")
    exit(1)
end

# Test 2: validate_reaction_system_dimensions with Parameter units access
println("\n2. Testing validate_reaction_system_dimensions (line 250 fix)...")
param_with_units = ESMFormat.Parameter("k1", 1.5, units="1/s")
param_no_units = ESMFormat.Parameter("k2", 2.0)
test_species = ESMFormat.Species("A")

rxn_sys = ESMFormat.ReactionSystem(
    [test_species],
    [ESMFormat.Reaction(Dict("A" => 1), Dict("A" => 1), ESMFormat.VarExpr("k1"))],
    parameters=[param_with_units, param_no_units]
)

try
    result = ESMFormat.validate_reaction_system_dimensions(rxn_sys)
    println("✓ Parameter units access works: $result")
catch e
    println("✗ Parameter units access failed: $e")
    exit(1)
end

# Test 3: get_expression_dimensions with OpExpr wrt access
println("\n3. Testing get_expression_dimensions (line 165 fix)...")
derivative_with_wrt = ESMFormat.OpExpr("D", ESMFormat.Expr[ESMFormat.VarExpr("x")], wrt="t")
derivative_no_wrt = ESMFormat.OpExpr("D", ESMFormat.Expr[ESMFormat.VarExpr("y")])
var_units = Dict("x" => "m", "y" => "kg", "t" => "s")

try
    result1 = ESMFormat.get_expression_dimensions(derivative_with_wrt, var_units)
    result2 = ESMFormat.get_expression_dimensions(derivative_no_wrt, var_units)
    println("✓ OpExpr wrt access works: with_wrt=$result1, no_wrt=$result2")
catch e
    println("✗ OpExpr wrt access failed: $e")
    exit(1)
end

# Test 4: Check that Species doesn't use units field (line 245 fix)
println("\n4. Testing Species doesn't access units field (line 245 fix)...")
species1 = ESMFormat.Species("CO2", molecular_weight=44.01)
species2 = ESMFormat.Species("O2")

# This should work without trying to access species.units
rxn_sys2 = ESMFormat.ReactionSystem(
    [species1, species2],
    [],  # No reactions
    parameters=[]
)

try
    result = ESMFormat.validate_reaction_system_dimensions(rxn_sys2)
    println("✓ Species units handling works: $result")
catch e
    println("✗ Species units handling failed: $e")
    exit(1)
end

println("\n🎉 All units.jl get() bugs have been fixed!")
println("The functions now properly access struct fields instead of using get().")