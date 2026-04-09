/**
 * Graph generation utilities for ESM files
 *
 * Provides functions to extract different graph representations from ESM files,
 * as specified in the ESM Libraries Specification Section 4.8.
 */
import type { EsmFile, CouplingEntry, Model, ReactionSystem, Equation, Reaction, Expr } from './types.js';
/** Graph node representing a component in the system */
export interface ComponentNode {
    /** Unique identifier for this component */
    id: string;
    /** Display name for the component */
    name: string;
    /** Type of component */
    type: 'model' | 'reaction_system' | 'data_loader' | 'operator';
    /** Optional description */
    description?: string;
    /** Optional reference information */
    reference?: any;
    /** Metadata with counts for this component */
    metadata: {
        /** Number of variables */
        var_count: number;
        /** Number of equations */
        eq_count: number;
        /** Number of species (for reaction systems) */
        species_count: number;
    };
}
/** Graph edge representing a coupling relationship */
export interface CouplingEdge {
    /** Unique identifier for this edge */
    id: string;
    /** Source component ID */
    from: string;
    /** Target component ID */
    to: string;
    /** Type of coupling */
    type: CouplingEntry['type'];
    /** Display label for the edge */
    label: string;
    /** Optional description */
    description?: string;
    /** Full coupling entry for editing */
    coupling: CouplingEntry;
}
/** System graph representation with components and couplings */
export interface ComponentGraph {
    /** All components in the system */
    nodes: ComponentNode[];
    /** All coupling relationships */
    edges: CouplingEdge[];
}
/** Graph interface with adjacency methods as specified in task */
export interface Graph<N, E> {
    /** All nodes in the graph */
    nodes: N[];
    /** All edges in the graph */
    edges: Array<{
        source: string;
        target: string;
        data: E;
    }>;
    /** Get adjacent nodes for a given node */
    adjacency(node: string): string[];
    /** Get predecessor nodes for a given node */
    predecessors(node: string): string[];
    /** Get successor nodes for a given node */
    successors(node: string): string[];
}
/** Graph node representing a variable/parameter/species in the system */
export interface VariableNode {
    /** Unique identifier for this variable (scoped, e.g., "Transport.temperature") */
    name: string;
    /** Type of variable */
    kind: 'state' | 'parameter' | 'observed' | 'species';
    /** Units if specified */
    units?: string;
    /** System/component this variable belongs to */
    system: string;
}
/** Graph edge representing a dependency between variables */
export interface DependencyEdge {
    /** Source variable name */
    source: string;
    /** Target variable name */
    target: string;
    /** Type of dependency relationship */
    relationship: 'additive' | 'multiplicative' | 'rate' | 'stoichiometric';
    /** Index of equation/reaction that creates this dependency */
    equation_index: number;
    /** The expression that created this dependency */
    expression: Expr;
}
/**
 * Extract the system graph from an ESM file.
 * Returns a directed graph where nodes are model components and edges are coupling rules.
 */
export declare function component_graph(esmFile: EsmFile): ComponentGraph;
/**
 * Extract the system graph from an ESM file as specified in task.
 * Returns a directed graph where nodes are model components and edges are coupling rules.
 * Implements the Graph interface with adjacency methods.
 */
export declare function componentGraph(file: EsmFile): Graph<ComponentNode, CouplingEdge>;
/**
 * Utility to check if a component exists in the ESM file
 */
export declare function componentExists(esmFile: EsmFile, componentId: string): boolean;
/**
 * Get the type of a component by its ID
 */
export declare function getComponentType(esmFile: EsmFile, componentId: string): ComponentNode['type'] | null;
/**
 * Extract variable-level dependency graph from an ESM file, model, reaction system, equation, reaction, or expression.
 * Creates a directed graph where nodes are variables/parameters/species and edges represent dependencies.
 *
 * @param target The target to analyze (EsmFile, Model, ReactionSystem, Equation, Reaction, or Expr)
 * @param options Optional settings for graph generation
 * @returns Graph with VariableNode nodes and DependencyEdge edges
 */
export declare function expressionGraph(target: EsmFile | Model | ReactionSystem | Equation | Reaction | Expr, options?: {
    merge_coupled?: boolean;
}): Graph<VariableNode, DependencyEdge>;
/**
 * Export graph as Graphviz DOT format.
 * Node shapes: box for models, ellipse for data_loaders, diamond for operators.
 * Edge styles: solid for compose, dashed for variable_map.
 */
export declare function toDot<N, E>(graph: Graph<N, E>): string;
/**
 * Export graph as Mermaid flowchart format for Markdown embedding.
 */
export declare function toMermaid<N, E>(graph: Graph<N, E>): string;
/**
 * Export graph as JSON adjacency list format for web consumption.
 */
export declare function toJsonGraph<N, E>(graph: Graph<N, E>): string;
//# sourceMappingURL=graph.d.ts.map