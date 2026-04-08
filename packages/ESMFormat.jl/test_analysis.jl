#!/usr/bin/env julia

# Test script for the new analysis features
using Pkg
Pkg.activate(".")
using ESMFormat

# Test basic functionality of the analysis features

println("Testing Julia analysis features...")

# Test 1: Create a simple reaction system and test derive_odes (already implemented)
println("\n1. Testing derive_odes (existing functionality)...")
species = [Species("A"), Species("B"), Species("C")]
reactions = [Reaction(Dict("A"=>1, "B"=>1), Dict("C"=>1), VarExpr("k1"))]
parameters = [Parameter("k1", 0.1)]
rxn_sys = ReactionSystem(species, reactions, parameters=parameters)

try
    model = derive_odes(rxn_sys)
    println("✓ derive_odes works: generated model with $(length(model.equations)) equations")
catch e
    println("✗ derive_odes failed: $e")
end

# Test 2: Test stoichiometric_matrix (existing functionality)
println("\n2. Testing stoichiometric_matrix...")
try
    S = stoichiometric_matrix(rxn_sys)
    println("✓ stoichiometric_matrix works: $(size(S)) matrix")
    println("  Matrix: $S")
catch e
    println("✗ stoichiometric_matrix failed: $e")
end

# Test 3: Test component_graph
println("\n3. Testing component_graph...")
try
    # Create a simple ESM file
    models = Dict("TestModel" => Model(
        Dict("x" => ModelVariable(StateVariable, default=1.0)),
        [Equation(VarExpr("x"), NumExpr(0.0))]
    ))

    reaction_systems = Dict("TestReaction" => rxn_sys)

    file = EsmFile(
        models,
        reaction_systems,
        Dict{String,DataLoader}(),
        Dict{String,Operator}(),
        CouplingEntry[]
    )

    graph = component_graph(file)
    println("✓ component_graph works: $(length(graph.nodes)) nodes, $(length(graph.edges)) edges")

    for node in graph.nodes
        println("  Node: $(node.name) ($(node.type))")
    end

catch e
    println("✗ component_graph failed: $e")
end

# Test 4: Test expression_graph
println("\n4. Testing expression_graph...")
try
    # Test with the reaction system
    graph = expression_graph(rxn_sys)
    println("✓ expression_graph works: $(length(graph.nodes)) nodes, $(length(graph.edges)) edges")

    for node in graph.nodes
        println("  Node: $(node.name) ($(node.kind))")
    end

catch e
    println("✗ expression_graph failed: $e")
end

# Test 5: Test unit validation
println("\n5. Testing unit validation...")
try
    # Test parse_units
    units = parse_units("mol/L")
    println("✓ parse_units works: parsed 'mol/L'")

    # Test with a simple model
    model = Model(
        Dict(
            "x" => ModelVariable(StateVariable, default=1.0, units="mol/L"),
            "k" => ModelVariable(ParameterVariable, default=0.1, units="1/s")
        ),
        [Equation(VarExpr("x"), OpExpr("*", [VarExpr("k"), VarExpr("x")]))]
    )

    is_valid = validate_model_dimensions(model)
    println("✓ validate_model_dimensions works: result = $is_valid")

catch e
    println("✗ unit validation failed: $e")
end

# Test 6: Test editing operations
println("\n6. Testing editing operations...")
try
    # Test add_variable
    original_model = Model(
        Dict("x" => ModelVariable(StateVariable, default=1.0)),
        [Equation(VarExpr("x"), NumExpr(0.0))]
    )

    new_var = ModelVariable(ParameterVariable, default=0.5)
    updated_model = add_variable(original_model, "y", new_var)

    println("✓ add_variable works: $(length(original_model.variables)) -> $(length(updated_model.variables)) variables")

    # Test add_equation
    new_equation = Equation(VarExpr("y"), NumExpr(1.0))
    updated_model2 = add_equation(updated_model, new_equation)

    println("✓ add_equation works: $(length(updated_model.equations)) -> $(length(updated_model2.equations)) equations")

catch e
    println("✗ editing operations failed: $e")
end

# Test 7: Test export formats
println("\n7. Testing export formats...")
try
    # Create a simple graph for testing
    models = Dict("Model1" => Model(
        Dict("x" => ModelVariable(StateVariable, default=1.0)),
        [Equation(VarExpr("x"), NumExpr(0.0))]
    ))

    file = EsmFile(
        models,
        Dict{String,ReactionSystem}(),
        Dict{String,DataLoader}(),
        Dict{String,Operator}(),
        CouplingEntry[]
    )

    graph = component_graph(file)

    # Test DOT export
    dot_str = to_dot(graph)
    println("✓ to_dot works: $(length(dot_str)) characters")

    # Test Mermaid export
    mermaid_str = to_mermaid(graph)
    println("✓ to_mermaid works: $(length(mermaid_str)) characters")

    # Test JSON export
    json_str = to_json(graph)
    println("✓ to_json works: $(length(json_str)) characters")

catch e
    println("✗ export formats failed: $e")
end

println("\nAnalysis features testing complete!")