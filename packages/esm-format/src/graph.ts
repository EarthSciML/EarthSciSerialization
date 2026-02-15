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
export function component_graph(esmFile: EsmFile): ComponentGraph {
  const nodes: ComponentNode[] = [];
  const edges: CouplingEdge[] = [];

  // Extract nodes from different component types

  // Models
  if (esmFile.models) {
    for (const [id, model] of Object.entries(esmFile.models)) {
      nodes.push({
        id,
        name: id,
        type: 'model',
        description: model.reference?.notes,
        reference: model.reference
      });
    }
  }

  // Reaction systems
  if (esmFile.reaction_systems) {
    for (const [id, reactionSystem] of Object.entries(esmFile.reaction_systems)) {
      nodes.push({
        id,
        name: id,
        type: 'reaction_system',
        description: reactionSystem.reference?.notes,
        reference: reactionSystem.reference
      });
    }
  }

  // Data loaders
  if (esmFile.data_loaders) {
    for (const [id, dataLoader] of Object.entries(esmFile.data_loaders)) {
      nodes.push({
        id,
        name: id,
        type: 'data_loader',
        description: dataLoader.reference?.notes,
        reference: dataLoader.reference
      });
    }
  }

  // Operators
  if (esmFile.operators) {
    for (const [id, operator] of Object.entries(esmFile.operators)) {
      nodes.push({
        id,
        name: id,
        type: 'operator',
        description: operator.reference?.notes,
        reference: operator.reference
      });
    }
  }

  // Extract edges from coupling entries
  if (esmFile.coupling) {
    esmFile.coupling.forEach((coupling, index) => {
      const edgeId = `coupling-${index}`;

      switch (coupling.type) {
        case 'operator_compose':
          // operator_compose connects multiple systems
          if (coupling.systems && coupling.systems.length >= 2) {
            // Create edges between consecutive systems
            for (let i = 0; i < coupling.systems.length - 1; i++) {
              edges.push({
                id: `${edgeId}-${i}`,
                from: coupling.systems[i],
                to: coupling.systems[i + 1],
                type: 'operator_compose',
                label: 'compose',
                description: coupling.description,
                coupling
              });
            }
          }
          break;

        case 'couple2':
          // couple2 connects exactly two systems
          if (coupling.systems && coupling.systems.length === 2) {
            edges.push({
              id: edgeId,
              from: coupling.systems[0],
              to: coupling.systems[1],
              type: 'couple2',
              label: 'couple',
              description: coupling.description,
              coupling
            });
          }
          break;

        case 'variable_map':
          // variable_map connects two variables from different components
          if (coupling.from && coupling.to) {
            const fromParts = coupling.from.split('.');
            const toParts = coupling.to.split('.');

            if (fromParts.length >= 2 && toParts.length >= 2) {
              const fromComponent = fromParts[0];
              const toComponent = toParts[0];
              const variable = fromParts.slice(1).join('.');

              edges.push({
                id: edgeId,
                from: fromComponent,
                to: toComponent,
                type: 'variable_map',
                label: variable,
                description: coupling.description || `${coupling.from} → ${coupling.to}`,
                coupling
              });
            }
          }
          break;

        case 'operator_apply':
          // operator_apply applies an operator to a system
          if (coupling.operator && coupling.system) {
            edges.push({
              id: edgeId,
              from: coupling.operator,
              to: coupling.system,
              type: 'operator_apply',
              label: 'apply',
              description: coupling.description,
              coupling
            });
          }
          break;

        case 'callback':
          // callback connects a source to a target via a callback function
          if (coupling.source && coupling.target) {
            edges.push({
              id: edgeId,
              from: coupling.source,
              to: coupling.target,
              type: 'callback',
              label: coupling.callback || 'callback',
              description: coupling.description,
              coupling
            });
          }
          break;

        default:
          console.warn(`Unknown coupling type: ${(coupling as any).type}`);
          break;
      }
    });
  }

  return { nodes, edges };
}

/**
 * Utility to check if a component exists in the ESM file
 */
export function componentExists(esmFile: EsmFile, componentId: string): boolean {
  return !!(
    esmFile.models?.[componentId] ||
    esmFile.reaction_systems?.[componentId] ||
    esmFile.data_loaders?.[componentId] ||
    esmFile.operators?.[componentId]
  );
}

/**
 * Get the type of a component by its ID
 */
export function getComponentType(esmFile: EsmFile, componentId: string): ComponentNode['type'] | null {
  if (esmFile.models?.[componentId]) return 'model';
  if (esmFile.reaction_systems?.[componentId]) return 'reaction_system';
  if (esmFile.data_loaders?.[componentId]) return 'data_loader';
  if (esmFile.operators?.[componentId]) return 'operator';
  return null;
}