/**
 * Graph generation utilities for ESM files
 *
 * Provides functions to extract different graph representations from ESM files,
 * as specified in the ESM Libraries Specification Section 4.8.
 */
import type { EsmFile, CouplingEntry } from './types.js';
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
/**
 * Extract the system graph from an ESM file.
 * Returns a directed graph where nodes are model components and edges are coupling rules.
 */
export declare function component_graph(esmFile: EsmFile): ComponentGraph;
/**
 * Utility to check if a component exists in the ESM file
 */
export declare function componentExists(esmFile: EsmFile, componentId: string): boolean;
/**
 * Get the type of a component by its ID
 */
export declare function getComponentType(esmFile: EsmFile, componentId: string): ComponentNode['type'] | null;
//# sourceMappingURL=graph.d.ts.map