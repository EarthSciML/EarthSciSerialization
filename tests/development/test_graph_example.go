package main

import (
	"fmt"
	"log"

	"github.com/ctessum/EarthSciSerialization/packages/esm-format-go/pkg/esm"
)

func main() {
	// Create a simple test ESM file
	file := &esm.EsmFile{
		Esm: "0.1.0",
		Metadata: esm.Metadata{
			Name:    "Graph Test Example",
			Authors: []string{"Test Author"},
		},
		Models: map[string]esm.Model{
			"SimpleODE": {
				Variables: map[string]esm.ModelVariable{
					"x": {Type: "state", Units: stringPtr("m")},
					"v": {Type: "parameter", Units: stringPtr("m/s")},
				},
				Equations: []esm.Equation{
					{
						LHS: esm.ExprNode{Op: "D", Args: []interface{}{"x"}, Wrt: stringPtr("t")},
						RHS: "v",
					},
				},
			},
		},
		ReactionSystems: map[string]esm.ReactionSystem{
			"SimpleReaction": {
				Species: map[string]esm.Species{
					"A": {Units: stringPtr("mol/L")},
					"B": {Units: stringPtr("mol/L")},
				},
				Parameters: map[string]esm.Parameter{
					"k": {Units: stringPtr("1/s")},
				},
				Reactions: []esm.Reaction{
					{
						ID: "R1",
						Substrates: []esm.SubstrateProduct{
							{Species: "A", Stoichiometry: 1},
						},
						Products: []esm.SubstrateProduct{
							{Species: "B", Stoichiometry: 1},
						},
						Rate: esm.ExprNode{
							Op:   "*",
							Args: []interface{}{"k", "A"},
						},
					},
				},
			},
		},
		DataLoaders: map[string]esm.DataLoader{
			"WindData": {
				Type:     "gridded_data",
				LoaderID: "wind_provider",
				Provides: map[string]esm.ProvidedVar{
					"windspeed": {Units: "m/s"},
				},
			},
		},
		Coupling: []interface{}{
			esm.VariableMapCoupling{
				Type:      "variable_map",
				From:      "WindData.windspeed",
				To:        "SimpleODE.v",
				Transform: "identity",
			},
			esm.OperatorComposeCoupling{
				Type:    "operator_compose",
				Systems: [2]string{"SimpleODE", "SimpleReaction"},
			},
		},
	}

	fmt.Println("=== Testing Component Graph ===")

	// Create component graph
	componentGraph := esm.ComponentGraphFromFile(file)

	fmt.Printf("Component Graph has %d nodes and %d edges\n",
		len(componentGraph.Nodes), len(componentGraph.Edges))

	// Display nodes
	fmt.Println("\nNodes:")
	for _, node := range componentGraph.Nodes {
		fmt.Printf("  - %s (%s)", node.ID, node.Type)
		if node.VariableCount != nil {
			fmt.Printf(" - %d vars", *node.VariableCount)
		}
		if node.SpeciesCount != nil {
			fmt.Printf(" - %d species", *node.SpeciesCount)
		}
		fmt.Println()
	}

	// Display edges
	fmt.Println("\nEdges:")
	for _, edge := range componentGraph.Edges {
		direction := "->"
		if edge.Data.Bidirectional {
			direction = "<->"
		}

		label := edge.Data.Type
		if edge.Data.Label != nil {
			label = fmt.Sprintf("%s [%s]", edge.Data.Type, *edge.Data.Label)
		}

		fmt.Printf("  - %s %s %s (%s)\n",
			edge.Source.ID, direction, edge.Target.ID, label)
	}

	fmt.Println("\n=== Testing Expression Graph ===")

	// Create expression graph for the entire file
	expressionGraph := esm.ExpressionGraphFromFile(file)

	fmt.Printf("Expression Graph has %d nodes and %d edges\n",
		len(expressionGraph.Nodes), len(expressionGraph.Edges))

	// Display variable nodes
	fmt.Println("\nVariable Nodes:")
	for _, node := range expressionGraph.Nodes {
		units := "no units"
		if node.Units != nil {
			units = *node.Units
		}
		fmt.Printf("  - %s.%s (%s) [%s]\n",
			node.System, node.Name, node.Kind, units)
	}

	// Display dependency edges
	fmt.Println("\nDependency Edges:")
	for _, edge := range expressionGraph.Edges {
		fmt.Printf("  - %s.%s -> %s.%s (%s)\n",
			edge.Source.System, edge.Source.Name,
			edge.Target.System, edge.Target.Name,
			edge.Data.Relationship)
	}

	fmt.Println("\n=== Testing Graph Export ===")

	// Test DOT export
	fmt.Println("\nComponent Graph (DOT format):")
	dotOutput, err := esm.ExportComponentGraphDOT(componentGraph)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println(dotOutput)

	// Test Mermaid export
	fmt.Println("\nComponent Graph (Mermaid format):")
	mermaidOutput, err := esm.ExportComponentGraphMermaid(componentGraph)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println(mermaidOutput)

	// Test JSON export (abbreviated)
	fmt.Println("\nExpression Graph (JSON format - first few lines):")
	jsonOutput, err := esm.ExportExpressionGraphJSON(expressionGraph)
	if err != nil {
		log.Fatal(err)
	}

	lines := fmt.Sprintf(jsonOutput)
	if len(lines) > 500 {
		fmt.Printf("%s...\n", lines[:500])
	} else {
		fmt.Println(lines)
	}

	fmt.Println("\nGraph functionality test completed successfully!")
}

func stringPtr(s string) *string {
	return &s
}