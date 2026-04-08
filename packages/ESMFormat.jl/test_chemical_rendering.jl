#!/usr/bin/env julia

# Test script for chemical subscript rendering
using Pkg
Pkg.activate(".")
using ESMFormat

println("Testing chemical subscript rendering...")

# Test chemical formula rendering
test_formulas = ["CO2", "H2O", "CH4", "H2SO4", "C6H12O6", "NH3", "O2", "N2O", "SO2"]

println("\nTesting render_chemical_formula:")
for formula in test_formulas
    rendered = render_chemical_formula(formula)
    println("  $formula -> $rendered")
end

# Test format_node_label
println("\nTesting format_node_label:")
test_nodes = ["CO2", "temperature", "k1", "H2SO4_concentration", "reaction_1", "CH3OH"]

for node in test_nodes
    formatted = format_node_label(node)
    println("  $node -> $formatted")
end

# Test with a reaction system containing chemical species
println("\nTesting with chemical reaction system...")

species = [Species("CO2"), Species("H2O"), Species("CH4"), Species("O2")]
reactions = [
    Reaction(Dict("CH4"=>1, "O2"=>2), Dict("CO2"=>1, "H2O"=>2), VarExpr("k1"))
]
parameters = [Parameter("k1", 0.1)]
rxn_sys = ReactionSystem(species, reactions, parameters=parameters)

# Generate expression graph
expr_graph = expression_graph(rxn_sys)

println("Expression graph nodes with chemical rendering:")
for node in expr_graph.nodes
    formatted_name = format_node_label(node.name, node.kind)
    println("  $(node.name) ($(node.kind)) -> $formatted_name")
end

# Export to DOT format and check if subscripts are used
dot_output = to_dot(expr_graph)
println("\nDOT output preview (with chemical subscripts):")
println(dot_output)

println("\nChemical subscript rendering test complete!")