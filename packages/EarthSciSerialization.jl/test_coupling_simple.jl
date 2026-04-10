using EarthSciSerialization

# Simple test of coupling functionality
println("Testing coupling resolution functions...")

# Create simple models
model1_vars = Dict(
    "x" => EarthSciSerialization.ModelVariable(EarthSciSerialization.StateVariable, default=1.0),
    "k1" => EarthSciSerialization.ModelVariable(EarthSciSerialization.ParameterVariable, default=0.1)
)
model1_eqs = [
    EarthSciSerialization.Equation(
        EarthSciSerialization.OpExpr("D", EarthSciSerialization.Expr[EarthSciSerialization.VarExpr("x")], wrt="t"),
        EarthSciSerialization.VarExpr("k1")
    )
]
model1 = EarthSciSerialization.Model(model1_vars, model1_eqs)

model2_vars = Dict(
    "y" => EarthSciSerialization.ModelVariable(EarthSciSerialization.StateVariable, default=1.0),
    "k2" => EarthSciSerialization.ModelVariable(EarthSciSerialization.ParameterVariable, default=0.2)
)
model2_eqs = [
    EarthSciSerialization.Equation(
        EarthSciSerialization.OpExpr("D", EarthSciSerialization.Expr[EarthSciSerialization.VarExpr("y")], wrt="t"),
        EarthSciSerialization.VarExpr("k2")
    )
]
model2 = EarthSciSerialization.Model(model2_vars, model2_eqs)

# Create coupling entries
operator_compose_coupling = EarthSciSerialization.CouplingOperatorCompose(["model1", "model2"])
couple_coupling = EarthSciSerialization.CouplingCouple(
    ["model1", "model2"],
    Dict{String, Any}("equations" => [Dict("from" => "model1.x", "to" => "model2.y", "transform" => "additive")])
)
variable_map_coupling = EarthSciSerialization.CouplingVariableMap("model1.k1", "model2.k2", "identity")

# Create ESM file with coupling
metadata = EarthSciSerialization.Metadata("test-coupled-system")
models = Dict("model1" => model1, "model2" => model2)
coupling = [operator_compose_coupling, couple_coupling, variable_map_coupling]

esm_file = EarthSciSerialization.EsmFile("0.1.0", metadata; models=models, coupling=coupling)

println("Created ESM file with $(length(coupling)) coupling entries")

# Test to_coupled_system function
try
    println("Testing to_coupled_system function...")
    coupled_system = EarthSciSerialization.to_coupled_system(esm_file)
    println("✓ to_coupled_system succeeded")
    println("  - Created coupled system with $(length(coupled_system.systems)) systems")
    println("  - Applied $(length(coupled_system.couplings)) coupling rules")

    # Check systems
    for (name, system) in coupled_system.systems
        println("  - System '$name': $(typeof(system))")
        if system isa EarthSciSerialization.MockMTKSystem
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