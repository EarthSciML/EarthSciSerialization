#!/usr/bin/env julia

# Simple script to test graph functionality
# Using direct include to avoid precompilation issues

using Pkg
Pkg.activate(".")

include("src/types.jl")
include("src/error_handling.jl")
include("src/expression.jl")

# Minimal coupling types needed for graph tests
include("src/coupled.jl")

# Graph functionality
include("src/graph.jl")

using JSON3

println("Testing graph functions directly...")

# Test 1: Create simple components for testing
println("\n1. Creating test components...")

# Create a simple model
variables = Dict("x" => ModelVariable(StateVariable, default=1.0))
equations = [Equation(VarExpr("x"), NumExpr(0.0))]
test_model = Model(variables, equations)

# Create a simple reaction system
species = [Species("A"), Species("B")]
reactions = [Reaction(Dict("A"=>1), Dict("B"=>1), VarExpr("k1"))]
parameters = [Parameter("k1", 0.1)]
test_rxn_sys = ReactionSystem(species, reactions, parameters=parameters)

println("✓ Created test components")

# Test 2: Create ESM file
println("\n2. Creating test ESM file...")

models = Dict("TestModel" => test_model)
reaction_systems = Dict("TestReaction" => test_rxn_sys)
data_loaders = Dict{String,DataLoader}()
operators = Dict{String,Operator}()
coupling = CouplingEntry[]

test_file = EsmFile(models, reaction_systems, data_loaders, operators, coupling)
println("✓ Created ESM file")

# Test 3: Test component_graph
println("\n3. Testing component_graph...")
try
    comp_graph = component_graph(test_file)
    println("✓ component_graph works: $(length(comp_graph.nodes)) nodes, $(length(comp_graph.edges)) edges")

    for node in comp_graph.nodes
        println("  Node: $(node.name) ($(node.type))")
    end

catch e
    println("✗ component_graph failed: $e")
    println(stacktrace(catch_backtrace()))
end

# Test 4: Test expression_graph with reaction system
println("\n4. Testing expression_graph (reaction system)...")
try
    expr_graph = expression_graph(test_rxn_sys)
    println("✓ expression_graph works: $(length(expr_graph.nodes)) nodes, $(length(expr_graph.edges)) edges")

    for node in expr_graph.nodes
        println("  Node: $(node.name) ($(node.kind))")
    end

catch e
    println("✗ expression_graph failed: $e")
    println(stacktrace(catch_backtrace()))
end

# Test 5: Test expression_graph with model
println("\n5. Testing expression_graph (model)...")
try
    expr_graph = expression_graph(test_model)
    println("✓ expression_graph works: $(length(expr_graph.nodes)) nodes, $(length(expr_graph.edges)) edges")

    for node in expr_graph.nodes
        println("  Node: $(node.name) ($(node.kind))")
    end

catch e
    println("✗ expression_graph failed: $e")
    println(stacktrace(catch_backtrace()))
end

# Test 6: Test export functions
println("\n6. Testing export functions...")
try
    comp_graph = component_graph(test_file)

    # Test DOT export
    dot_str = to_dot(comp_graph)
    println("✓ to_dot works: $(length(dot_str)) characters")

    # Test Mermaid export
    mermaid_str = to_mermaid(comp_graph)
    println("✓ to_mermaid works: $(length(mermaid_str)) characters")

    # Test JSON export
    json_str = to_json(comp_graph)
    println("✓ to_json works: $(length(json_str)) characters")

catch e
    println("✗ export functions failed: $e")
    println(stacktrace(catch_backtrace()))
end

println("\nGraph testing complete!")