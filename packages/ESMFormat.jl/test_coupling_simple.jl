using ESMFormat

# Simple test of coupling functionality
println("Testing coupling resolution functions...")

# Create simple models
model1_vars = Dict(
    "x" => ESMFormat.ModelVariable(ESMFormat.StateVariable, default=1.0),
    "k1" => ESMFormat.ModelVariable(ESMFormat.ParameterVariable, default=0.1)
)
model1_eqs = [
    ESMFormat.Equation(
        ESMFormat.OpExpr("D", ESMFormat.Expr[ESMFormat.VarExpr("x")], wrt="t"),
        ESMFormat.VarExpr("k1")
    )
]
model1 = ESMFormat.Model(model1_vars, model1_eqs)

model2_vars = Dict(
    "y" => ESMFormat.ModelVariable(ESMFormat.StateVariable, default=1.0),
    "k2" => ESMFormat.ModelVariable(ESMFormat.ParameterVariable, default=0.2)
)
model2_eqs = [
    ESMFormat.Equation(
        ESMFormat.OpExpr("D", ESMFormat.Expr[ESMFormat.VarExpr("y")], wrt="t"),
        ESMFormat.VarExpr("k2")
    )
]
model2 = ESMFormat.Model(model2_vars, model2_eqs)

# Create coupling entries
operator_compose_coupling = ESMFormat.CouplingOperatorCompose(["model1", "model2"])
couple2_coupling = ESMFormat.CouplingCouple2(
    ["model1", "model2"],
    ["coupletype1", "coupletype2"],
    Dict{String, Any}("equations" => [Dict("from" => "model1.x", "to" => "model2.y", "transform" => "additive")])
)
variable_map_coupling = ESMFormat.CouplingVariableMap("model1.k1", "model2.k2", "identity")

# Create ESM file with coupling
metadata = ESMFormat.Metadata("test-coupled-system")
models = Dict("model1" => model1, "model2" => model2)
coupling = [operator_compose_coupling, couple2_coupling, variable_map_coupling]

esm_file = ESMFormat.EsmFile("0.1.0", metadata; models=models, coupling=coupling)

println("Created ESM file with $(length(coupling)) coupling entries")

# Test to_coupled_system function
try
    println("Testing to_coupled_system function...")
    coupled_system = ESMFormat.to_coupled_system(esm_file)
    println("✓ to_coupled_system succeeded")
    println("  - Created coupled system with $(length(coupled_system.systems)) systems")
    println("  - Applied $(length(coupled_system.couplings)) coupling rules")

    # Check systems
    for (name, system) in coupled_system.systems
        println("  - System '$name': $(typeof(system))")
        if system isa ESMFormat.MockMTKSystem
            println("    States: $(system.states)")
            println("    Parameters: $(system.parameters)")
            println("    Equations: $(system.equations)")
        end
    end

catch e
    println("✗ to_coupled_system failed: $e")
    println("Stacktrace:")
    for (i, frame) in enumerate(stacktrace(catch_backtrace()))
        println("  $i: $frame")
        if i > 10  # Limit stacktrace depth
            break
        end
    end
end

println("Test completed.")