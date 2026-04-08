#!/usr/bin/env julia

# Simple test script for the new analysis features without full package loading
println("Testing Julia analysis features (simple)...")

# Manual includes to test functionality
include("src/types.jl")
include("src/error_handling.jl")
include("src/expression.jl")
include("src/reactions.jl")

println("✓ Basic includes successful")

# Test stoichiometric_matrix with simple data
species = [Species("A"), Species("B"), Species("C")]
reactions = [Reaction(Dict("A"=>1, "B"=>1), Dict("C"=>1), VarExpr("k1"))]
parameters = [Parameter("k1", 0.1)]
rxn_sys = ReactionSystem(species, reactions, parameters=parameters)

try
    S = stoichiometric_matrix(rxn_sys)
    println("✓ stoichiometric_matrix works: $(size(S)) matrix")
    println("  Expected: [-1, -1, 1] for reaction A + B -> C")
    println("  Actual: $S")
catch e
    println("✗ stoichiometric_matrix failed: $e")
end

# Test derive_odes
try
    model = derive_odes(rxn_sys)
    println("✓ derive_odes works: generated model with $(length(model.equations)) equations")
    println("  Variables: $(length(model.variables))")
catch e
    println("✗ derive_odes failed: $e")
end

println("Analysis features basic test complete!")