/**
 * Variable dependency graph construction and analysis
 *
 * This module provides functions to construct and analyze dependency graphs
 * for variables in ESM files, supporting circular dependency detection,
 * topological sorting, and dead code elimination.
 */

import type { Expr, Model, EsmFile, ReactionSystem, Equation } from '../types.js';
import type { DependencyGraph, DependencyNode, DependencyRelation } from './types.js';
import { freeVariables } from '../expression.js';

/**
 * Build a dependency graph from an ESM file, model, or expression
 * @param target The target to analyze
 * @param options Analysis options
 * @returns Dependency graph with nodes and edges
 */
export function buildDependencyGraph(
  target: EsmFile | Model | ReactionSystem | Expr,
  options: {
    includeParameters?: boolean;
    includeObserved?: boolean;
    mergeAcrossSystems?: boolean;
  } = {}
): DependencyGraph {
  const nodes: DependencyNode[] = [];
  const edges: Array<{ source: string; target: string; data: DependencyRelation }> = [];
  const nodeMap = new Map<string, DependencyNode>();

  const {
    includeParameters = true,
    includeObserved = true,
    mergeAcrossSystems = false
  } = options;

  // Helper to create a scoped variable name
  function scopedName(varName: string, system: string): string {
    return mergeAcrossSystems ? varName : `${system}.${varName}`;
  }

  // Helper to add a node (avoiding duplicates)
  function addNode(name: string, kind: DependencyNode['kind'], system: string, units?: string, definition?: Expr): DependencyNode {
    const scopedVarName = scopedName(name, system);

    if (!nodeMap.has(scopedVarName)) {
      const node: DependencyNode = {
        name: scopedVarName,
        kind,
        system: mergeAcrossSystems ? 'merged' : system,
        units,
        definition,
        depth: 0 // Will be calculated later
      };
      nodes.push(node);
      nodeMap.set(scopedVarName, node);
    }

    return nodeMap.get(scopedVarName)!;
  }

  // Helper to add a dependency edge
  function addDependency(
    sourceVar: string,
    targetVar: string,
    type: DependencyRelation['type'],
    weight: number = 1.0,
    expression?: Expr
  ) {
    const relation: DependencyRelation = {
      source: sourceVar,
      target: targetVar,
      type,
      weight,
      expression
    };

    edges.push({
      source: sourceVar,
      target: targetVar,
      data: relation
    });
  }

  // Process different target types
  if (typeof target === 'object' && target !== null && 'esm' in target) {
    // ESM File
    const esmFile = target as EsmFile;

    // Process all models
    if (esmFile.models) {
      for (const [modelId, model] of Object.entries(esmFile.models)) {
        processModel(model, modelId);
      }
    }

    // Process all reaction systems
    if (esmFile.reaction_systems) {
      for (const [systemId, reactionSystem] of Object.entries(esmFile.reaction_systems)) {
        processReactionSystem(reactionSystem, systemId);
      }
    }

  } else if (typeof target === 'object' && target !== null && 'variables' in target) {
    // Model
    processModel(target as Model, 'default');

  } else if (typeof target === 'object' && target !== null && 'species' in target) {
    // Reaction System
    processReactionSystem(target as ReactionSystem, 'default');

  } else {
    // Single expression - create a simple dependency graph
    processExpression(target as Expr, 'result', 'default');
  }

  // Process a model
  function processModel(model: Model, systemId: string) {
    // Add all variables as nodes
    if (model.variables) {
      for (const [varName, variable] of Object.entries(model.variables)) {
        if (variable.type === 'parameter' && !includeParameters) continue;
        if (variable.type === 'observed' && !includeObserved) continue;

        const node = addNode(varName, variable.type, systemId, variable.units, variable.expression);

        // If variable has a definition expression, create dependencies
        if (variable.expression) {
          const dependencies = freeVariables(variable.expression);
          for (const depVar of dependencies) {
            // Add dependency node if it doesn't exist
            addNode(depVar, 'parameter', systemId); // Default to parameter, will be refined later
            addDependency(
              scopedName(depVar, systemId),
              scopedName(varName, systemId),
              'definition_dependency',
              1.0,
              variable.expression
            );
          }
        }
      }
    }

    // Process equations
    if (model.equations) {
      model.equations.forEach((equation, index) => {
        processEquation(equation, systemId, index);
      });
    }

    // Process subsystems recursively
    if (model.subsystems) {
      for (const [subSystemId, subModel] of Object.entries(model.subsystems)) {
        const fullSubSystemId = mergeAcrossSystems ? systemId : `${systemId}.${subSystemId}`;
        processModel(subModel, fullSubSystemId);
      }
    }
  }

  // Process a reaction system
  function processReactionSystem(reactionSystem: ReactionSystem, systemId: string) {
    // Add species as nodes
    if (reactionSystem.species) {
      for (const [speciesName, species] of Object.entries(reactionSystem.species)) {
        addNode(speciesName, 'species', systemId, species.units);
      }
    }

    // Add parameters as nodes
    if (reactionSystem.parameters && includeParameters) {
      for (const [paramName, parameter] of Object.entries(reactionSystem.parameters)) {
        addNode(paramName, 'parameter', systemId, parameter.units);
      }
    }

    // Process reactions
    if (reactionSystem.reactions) {
      reactionSystem.reactions.forEach((reaction, index) => {
        // Rate expression creates dependencies
        const rateVars = freeVariables(reaction.rate);

        // All species involved in the reaction depend on rate parameters
        const involvedSpecies = new Set<string>();

        if (reaction.reactants) {
          for (const reactant of reaction.reactants) {
            involvedSpecies.add(reactant.species);
          }
        }

        if (reaction.products) {
          for (const product of reaction.products) {
            involvedSpecies.add(product.species);
          }
        }

        // Create dependencies between rate variables and species
        for (const species of involvedSpecies) {
          for (const rateVar of rateVars) {
            addDependency(
              scopedName(rateVar, systemId),
              scopedName(species, systemId),
              'parameter_dependency',
              0.8, // Lower weight for rate dependencies
              reaction.rate
            );
          }
        }
      });
    }
  }

  // Process an equation
  function processEquation(equation: Equation, systemId: string, index: number) {
    const lhsVar = addNode(equation.lhs, 'state', systemId);
    const rhsVars = freeVariables(equation.rhs);

    // Create dependencies from RHS variables to LHS variable
    for (const rhsVar of rhsVars) {
      addNode(rhsVar, 'parameter', systemId); // Default assumption
      addDependency(
        scopedName(rhsVar, systemId),
        scopedName(equation.lhs, systemId),
        'direct',
        1.0,
        equation.rhs
      );
    }
  }

  // Process a single expression
  function processExpression(expr: Expr, targetVar: string, systemId: string) {
    const resultNode = addNode(targetVar, 'observed', systemId, undefined, expr);
    const dependencies = freeVariables(expr);

    for (const depVar of dependencies) {
      addNode(depVar, 'parameter', systemId);
      addDependency(
        scopedName(depVar, systemId),
        scopedName(targetVar, systemId),
        'direct',
        1.0,
        expr
      );
    }
  }

  // Calculate depths using topological sort
  calculateDepths(nodes, edges);

  // Detect circular dependencies
  const circularDeps = detectCircularDependencies(edges);

  // Mark circular edges
  for (const edge of edges) {
    if (circularDeps.some(cycle =>
      cycle.some(node => node === edge.source) &&
      cycle.some(node => node === edge.target)
    )) {
      edge.data.type = 'circular';
    }
  }

  // Build adjacency maps for efficient lookups
  const adjacencyMap = new Map<string, Set<string>>();
  const predecessorMap = new Map<string, Set<string>>();
  const successorMap = new Map<string, Set<string>>();

  // Initialize maps
  for (const node of nodes) {
    adjacencyMap.set(node.name, new Set());
    predecessorMap.set(node.name, new Set());
    successorMap.set(node.name, new Set());
  }

  // Populate maps
  for (const edge of edges) {
    adjacencyMap.get(edge.source)?.add(edge.target);
    adjacencyMap.get(edge.target)?.add(edge.source);
    predecessorMap.get(edge.target)?.add(edge.source);
    successorMap.get(edge.source)?.add(edge.target);
  }

  return {
    nodes,
    edges,

    adjacency(node: string): string[] {
      return Array.from(adjacencyMap.get(node) || []);
    },

    predecessors(node: string): string[] {
      return Array.from(predecessorMap.get(node) || []);
    },

    successors(node: string): string[] {
      return Array.from(successorMap.get(node) || []);
    },

    hasCircularDependencies(): boolean {
      return circularDeps.length > 0;
    },

    getStronglyConnectedComponents(): DependencyNode[][] {
      return circularDeps.map(cycle =>
        cycle.map(nodeName => nodeMap.get(nodeName)!).filter(Boolean)
      );
    },

    topologicalSort(): DependencyNode[] {
      return topologicalSort(nodes, edges);
    }
  };
}

/**
 * Calculate depth levels for nodes using topological ordering
 */
function calculateDepths(nodes: DependencyNode[], edges: Array<{ source: string; target: string; data: DependencyRelation }>) {
  const inDegree = new Map<string, number>();
  const adjacencyList = new Map<string, string[]>();

  // Initialize
  for (const node of nodes) {
    inDegree.set(node.name, 0);
    adjacencyList.set(node.name, []);
  }

  // Build adjacency list and calculate in-degrees
  for (const edge of edges) {
    adjacencyList.get(edge.source)?.push(edge.target);
    inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1);
  }

  // Kahn's algorithm for topological sort with depth calculation
  const queue: string[] = [];
  const nodeMap = new Map<string, DependencyNode>();

  for (const node of nodes) {
    nodeMap.set(node.name, node);
    if (inDegree.get(node.name) === 0) {
      queue.push(node.name);
      node.depth = 0;
    }
  }

  while (queue.length > 0) {
    const current = queue.shift()!;
    const currentNode = nodeMap.get(current)!;

    for (const neighbor of adjacencyList.get(current) || []) {
      const neighborNode = nodeMap.get(neighbor)!;
      const newInDegree = (inDegree.get(neighbor) || 0) - 1;
      inDegree.set(neighbor, newInDegree);

      // Update depth
      neighborNode.depth = Math.max(neighborNode.depth, currentNode.depth + 1);

      if (newInDegree === 0) {
        queue.push(neighbor);
      }
    }
  }
}

/**
 * Detect circular dependencies using DFS
 */
function detectCircularDependencies(edges: Array<{ source: string; target: string; data: DependencyRelation }>): string[][] {
  const graph = new Map<string, string[]>();
  const visited = new Set<string>();
  const recStack = new Set<string>();
  const cycles: string[][] = [];

  // Build adjacency list
  for (const edge of edges) {
    if (!graph.has(edge.source)) {
      graph.set(edge.source, []);
    }
    graph.get(edge.source)?.push(edge.target);
  }

  function dfs(node: string, path: string[]): void {
    visited.add(node);
    recStack.add(node);
    path.push(node);

    for (const neighbor of graph.get(node) || []) {
      if (!visited.has(neighbor)) {
        dfs(neighbor, [...path]);
      } else if (recStack.has(neighbor)) {
        // Found a cycle
        const cycleStart = path.indexOf(neighbor);
        const cycle = path.slice(cycleStart).concat([neighbor]);
        cycles.push(cycle);
      }
    }

    recStack.delete(node);
  }

  for (const node of graph.keys()) {
    if (!visited.has(node)) {
      dfs(node, []);
    }
  }

  return cycles;
}

/**
 * Perform topological sort of dependency nodes
 */
function topologicalSort(nodes: DependencyNode[], edges: Array<{ source: string; target: string; data: DependencyRelation }>): DependencyNode[] {
  const inDegree = new Map<string, number>();
  const adjacencyList = new Map<string, string[]>();
  const nodeMap = new Map<string, DependencyNode>();

  // Initialize
  for (const node of nodes) {
    inDegree.set(node.name, 0);
    adjacencyList.set(node.name, []);
    nodeMap.set(node.name, node);
  }

  // Build graph
  for (const edge of edges) {
    adjacencyList.get(edge.source)?.push(edge.target);
    inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1);
  }

  // Kahn's algorithm
  const queue: string[] = [];
  const result: DependencyNode[] = [];

  for (const node of nodes) {
    if (inDegree.get(node.name) === 0) {
      queue.push(node.name);
    }
  }

  while (queue.length > 0) {
    const current = queue.shift()!;
    result.push(nodeMap.get(current)!);

    for (const neighbor of adjacencyList.get(current) || []) {
      const newInDegree = (inDegree.get(neighbor) || 0) - 1;
      inDegree.set(neighbor, newInDegree);

      if (newInDegree === 0) {
        queue.push(neighbor);
      }
    }
  }

  return result;
}

/**
 * Find dead variables (those that are defined but never used)
 */
export function findDeadVariables(graph: DependencyGraph): DependencyNode[] {
  const deadVars: DependencyNode[] = [];

  for (const node of graph.nodes) {
    // A variable is dead if it has no successors (nothing depends on it)
    // and it's not a state variable (which are typically outputs)
    if (graph.successors(node.name).length === 0 && node.kind !== 'state') {
      deadVars.push(node);
    }
  }

  return deadVars;
}

/**
 * Find variable dependency chains (paths from parameters to state variables)
 */
export function findDependencyChains(graph: DependencyGraph, startNode: string, maxDepth: number = 10): string[][] {
  const chains: string[][] = [];

  function dfs(currentNode: string, path: string[], visited: Set<string>, depth: number) {
    if (depth > maxDepth || visited.has(currentNode)) {
      return;
    }

    visited.add(currentNode);
    path.push(currentNode);

    const successors = graph.successors(currentNode);
    if (successors.length === 0) {
      // Leaf node - add the complete chain
      chains.push([...path]);
    } else {
      for (const successor of successors) {
        dfs(successor, [...path], new Set(visited), depth + 1);
      }
    }
  }

  dfs(startNode, [], new Set(), 0);
  return chains;
}