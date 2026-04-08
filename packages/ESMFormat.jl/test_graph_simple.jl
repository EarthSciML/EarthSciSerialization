#!/usr/bin/env julia

# Test script specifically for graph functionality
using Pkg
Pkg.activate(".")

# Try to load ESMFormat despite warnings
try
    using ESMFormat
    println("ESMFormat loaded successfully (with warnings)")
catch e
    println("Failed to load ESMFormat: $e")
    exit(1)
end

println("Testing graph functions...")

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

# Create metadata
metadata = Metadata(
    "Test graph generation",  # name
    description="Testing graph functionality",
    authors=["Test suite"],
    created="2024-02-16"
)

test_file = EsmFile(
    "1.0",      # ESM version
    metadata,
    models=models,
    reaction_systems=reaction_systems,
    data_loaders=data_loaders,
    operators=operators,
    coupling=coupling
)
println("✓ Created ESM file")

# Test 3: Test component_graph
println("\n3. Testing component_graph...")
try
    comp_graph = component_graph(test_file)
    println("✓ component_graph works: $(length(comp_graph.nodes)) nodes, $(length(comp_graph.edges)) edges")

    for node in comp_graph.nodes
        println("  Node: $(node.name) ($(node.type))")
    end

    # Test export functions with this graph
    println("\n3a. Testing export functions...")

    # Test DOT export
    dot_str = to_dot(comp_graph)
    println("✓ to_dot works: $(length(dot_str)) characters")
    println("DOT preview:")
    println(dot_str)

    # Test Mermaid export
    mermaid_str = to_mermaid(comp_graph)
    println("✓ to_mermaid works: $(length(mermaid_str)) characters")
    println("Mermaid preview:")
    println(mermaid_str)

    # Test JSON export
    json_str = to_json(comp_graph)
    println("✓ to_json works: $(length(json_str)) characters")
    println("JSON preview (first 200 chars):")
    println(json_str[1:min(200, length(json_str))] * (length(json_str) > 200 ? "..." : ""))

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

    if length(expr_graph.edges) > 0
        println("  Edges:")
        for edge in expr_graph.edges
            println("    $(edge.data.source) -> $(edge.data.target) ($(edge.data.relationship))")
        end
    end

catch e
    println("✗ expression_graph (reaction system) failed: $e")
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

    if length(expr_graph.edges) > 0
        println("  Edges:")
        for edge in expr_graph.edges
            println("    $(edge.data.source) -> $(edge.data.target) ($(edge.data.relationship))")
        end
    end

catch e
    println("✗ expression_graph (model) failed: $e")
    println(stacktrace(catch_backtrace()))
end

# Test 6: Test expression_graph with file
println("\n6. Testing expression_graph (file-level)...")
try
    expr_graph = expression_graph(test_file)
    println("✓ expression_graph (file) works: $(length(expr_graph.nodes)) nodes, $(length(expr_graph.edges)) edges")

    for node in expr_graph.nodes
        println("  Node: $(node.name) ($(node.kind), system: $(node.system))")
    end

    if length(expr_graph.edges) > 0
        println("  Edges:")
        for edge in expr_graph.edges[1:min(5, length(expr_graph.edges))]  # Show first 5
            println("    $(edge.data.source) -> $(edge.data.target) ($(edge.data.relationship))")
        end
        if length(expr_graph.edges) > 5
            println("    ... and $(length(expr_graph.edges) - 5) more edges")
        end
    end

catch e
    println("✗ expression_graph (file) failed: $e")
    println(stacktrace(catch_backtrace()))
end

println("\nGraph testing complete!")