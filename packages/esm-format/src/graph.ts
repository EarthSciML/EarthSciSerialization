/**
 * Graph generation utilities for ESM files
 *
 * Provides functions to extract different graph representations from ESM files,
 * as specified in the ESM Libraries Specification Section 4.8.
 */

import type { EsmFile, CouplingEntry, Model, ReactionSystem, Equation, Reaction, Expr } from './types.js';
import { freeVariables } from './expression.js';

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
  edges: Array<{ source: string; target: string; data: E }>;
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
        reference: model.reference,
        metadata: {
          var_count: model.variables ? Object.keys(model.variables).length : 0,
          eq_count: model.equations ? model.equations.length : 0,
          species_count: 0
        }
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
        reference: reactionSystem.reference,
        metadata: {
          var_count: 0,
          eq_count: reactionSystem.reactions ? reactionSystem.reactions.length : 0,
          species_count: reactionSystem.species ? Object.keys(reactionSystem.species).length : 0
        }
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
        reference: dataLoader.reference,
        metadata: {
          var_count: dataLoader.variables ? dataLoader.variables.length : 0,
          eq_count: 0,
          species_count: 0
        }
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
        reference: operator.reference,
        metadata: {
          var_count: 0,
          eq_count: 0,
          species_count: 0
        }
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
 * Extract the system graph from an ESM file as specified in task.
 * Returns a directed graph where nodes are model components and edges are coupling rules.
 * Implements the Graph interface with adjacency methods.
 */
export function componentGraph(file: EsmFile): Graph<ComponentNode, CouplingEdge> {
  // Reuse the existing component_graph logic to get nodes and edges
  const componentGraphData = component_graph(file);

  // Convert CouplingEdge format to Graph edge format
  const graphEdges = componentGraphData.edges.map(edge => ({
    source: edge.from,
    target: edge.to,
    data: edge
  }));

  // Build adjacency lists for efficient lookups
  const adjacencyMap = new Map<string, Set<string>>();
  const predecessorMap = new Map<string, Set<string>>();
  const successorMap = new Map<string, Set<string>>();

  // Initialize maps for all nodes
  for (const node of componentGraphData.nodes) {
    adjacencyMap.set(node.id, new Set());
    predecessorMap.set(node.id, new Set());
    successorMap.set(node.id, new Set());
  }

  // Build adjacency relationships from edges
  for (const edge of graphEdges) {
    const { source, target } = edge;

    // Adjacency includes both predecessors and successors
    adjacencyMap.get(source)?.add(target);
    adjacencyMap.get(target)?.add(source);

    // Predecessors (nodes that point TO this node)
    predecessorMap.get(target)?.add(source);

    // Successors (nodes that this node points TO)
    successorMap.get(source)?.add(target);
  }

  return {
    nodes: componentGraphData.nodes,
    edges: graphEdges,

    adjacency(node: string): string[] {
      return Array.from(adjacencyMap.get(node) || []);
    },

    predecessors(node: string): string[] {
      return Array.from(predecessorMap.get(node) || []);
    },

    successors(node: string): string[] {
      return Array.from(successorMap.get(node) || []);
    }
  };
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

/**
 * Extract variable-level dependency graph from an ESM file, model, reaction system, equation, reaction, or expression.
 * Creates a directed graph where nodes are variables/parameters/species and edges represent dependencies.
 *
 * @param target The target to analyze (EsmFile, Model, ReactionSystem, Equation, Reaction, or Expr)
 * @param options Optional settings for graph generation
 * @returns Graph with VariableNode nodes and DependencyEdge edges
 */
export function expressionGraph(
  target: EsmFile | Model | ReactionSystem | Equation | Reaction | Expr,
  options: { merge_coupled?: boolean } = {}
): Graph<VariableNode, DependencyEdge> {
  const nodes: VariableNode[] = [];
  const edges: Array<{ source: string; target: string; data: DependencyEdge }> = [];
  const nodeMap = new Map<string, VariableNode>();

  // Helper function to add a node (avoiding duplicates)
  function addNode(name: string, kind: VariableNode['kind'], units?: string, system: string = 'default') {
    const scopedName = system !== 'default' ? `${system}.${name}` : name;
    if (!nodeMap.has(scopedName)) {
      const node: VariableNode = { name: scopedName, kind, units, system };
      nodes.push(node);
      nodeMap.set(scopedName, node);
    }
    return scopedName;
  }

  // Helper function to add dependency edge
  function addDependency(
    sourceVar: string,
    targetVar: string,
    relationship: DependencyEdge['relationship'],
    equationIndex: number,
    expression: Expr
  ) {
    const edgeData: DependencyEdge = {
      source: sourceVar,
      target: targetVar,
      relationship,
      equation_index: equationIndex,
      expression
    };

    edges.push({
      source: sourceVar,
      target: targetVar,
      data: edgeData
    });
  }

  // Handle different target types
  if (typeof target === 'object' && 'esm' in target) {
    // EsmFile - process all models and reaction systems
    const esmFile = target as EsmFile;

    // Process models
    if (esmFile.models) {
      for (const [modelId, model] of Object.entries(esmFile.models)) {
        processModel(model, modelId);
      }
    }

    // Process reaction systems
    if (esmFile.reaction_systems) {
      for (const [systemId, reactionSystem] of Object.entries(esmFile.reaction_systems)) {
        processReactionSystem(reactionSystem, systemId);
      }
    }

    // Process coupling if merge_coupled is requested
    if (options.merge_coupled && esmFile.coupling) {
      processCoupling(esmFile.coupling);
    }

  } else if (typeof target === 'object' && 'variables' in target) {
    // Model
    processModel(target as Model, 'default');

  } else if (typeof target === 'object' && 'species' in target) {
    // ReactionSystem
    processReactionSystem(target as ReactionSystem, 'default');

  } else if (typeof target === 'object' && 'lhs' in target) {
    // Equation
    processEquation(target as Equation, 0, 'default');

  } else if (typeof target === 'object' && 'reactants' in target) {
    // Reaction
    processReaction(target as Reaction, 0, 'default');

  } else {
    // Expression - analyze dependencies within the expression itself
    processExpression(target as Expr, 'expr_result', 0, 'default');
  }

  // Helper function to process a model
  function processModel(model: Model, systemId: string) {
    // Add all variables as nodes
    for (const [varName, variable] of Object.entries(model.variables)) {
      addNode(varName, variable.type, variable.units, systemId);

      // If it's an observed variable with an expression, create dependencies
      if (variable.type === 'observed' && variable.expression) {
        const observedVar = addNode(varName, 'observed', variable.units, systemId);
        const freeVars = freeVariables(variable.expression);

        for (const freeVar of freeVars) {
          const sourceVar = addNode(freeVar, 'parameter', undefined, systemId); // Default to parameter; could be refined
          addDependency(sourceVar, observedVar, 'multiplicative', -1, variable.expression);
        }
      }
    }

    // Process equations
    if (model.equations) {
      model.equations.forEach((equation, index) => {
        processEquation(equation, index, systemId);
      });
    }

    // Process subsystems recursively
    if (model.subsystems) {
      for (const [subSystemId, subModel] of Object.entries(model.subsystems)) {
        const fullSubSystemId = systemId !== 'default' ? `${systemId}.${subSystemId}` : subSystemId;
        processModel(subModel, fullSubSystemId);
      }
    }
  }

  // Helper function to process a reaction system
  function processReactionSystem(reactionSystem: ReactionSystem, systemId: string) {
    // Add species as nodes
    for (const [speciesName, species] of Object.entries(reactionSystem.species)) {
      addNode(speciesName, 'species', species.units, systemId);
    }

    // Add parameters as nodes
    for (const [paramName, parameter] of Object.entries(reactionSystem.parameters)) {
      addNode(paramName, 'parameter', parameter.units, systemId);
    }

    // Process reactions
    reactionSystem.reactions.forEach((reaction, index) => {
      processReaction(reaction, index, systemId);
    });

    // Process constraint equations if present
    if (reactionSystem.constraint_equations) {
      reactionSystem.constraint_equations.forEach((equation, index) => {
        processEquation(equation, index + reactionSystem.reactions.length, systemId);
      });
    }
  }

  // Helper function to process an equation
  function processEquation(equation: Equation, equationIndex: number, systemId: string) {
    const lhsVar = addNode(equation.lhs, 'state', undefined, systemId); // LHS is typically a state variable
    const rhsVars = freeVariables(equation.rhs);

    // Create dependencies from all RHS variables to the LHS variable
    for (const rhsVar of rhsVars) {
      const sourceVar = addNode(rhsVar, 'parameter', undefined, systemId); // Default to parameter; could be refined based on context
      addDependency(sourceVar, lhsVar, 'additive', equationIndex, equation.rhs);
    }
  }

  // Helper function to process a reaction
  function processReaction(reaction: Reaction, reactionIndex: number, systemId: string) {
    // Get rate expression variables
    const rateVars = freeVariables(reaction.rate);

    // Process reactants - they are consumed (negative stoichiometry)
    if (reaction.reactants) {
      for (const reactant of reaction.reactants) {
        const reactantVar = addNode(reactant.species, 'species', undefined, systemId);

        // Rate parameters affect the reactant species
        for (const rateVar of rateVars) {
          const paramVar = addNode(rateVar, 'parameter', undefined, systemId);
          addDependency(paramVar, reactantVar, 'rate', reactionIndex, reaction.rate);
        }
      }
    }

    // Process products - they are produced (positive stoichiometry)
    if (reaction.products) {
      for (const product of reaction.products) {
        const productVar = addNode(product.species, 'species', undefined, systemId);

        // Rate parameters affect the product species
        for (const rateVar of rateVars) {
          const paramVar = addNode(rateVar, 'parameter', undefined, systemId);
          addDependency(paramVar, productVar, 'rate', reactionIndex, reaction.rate);
        }

        // Reactants affect products through stoichiometry
        if (reaction.reactants) {
          for (const reactant of reaction.reactants) {
            const reactantVar = addNode(reactant.species, 'species', undefined, systemId);
            addDependency(reactantVar, productVar, 'stoichiometric', reactionIndex, reaction.rate);
          }
        }
      }
    }
  }

  // Helper function to process a single expression
  function processExpression(expr: Expr, targetVar: string, equationIndex: number, systemId: string) {
    const targetVariable = addNode(targetVar, 'observed', undefined, systemId);
    const freeVars = freeVariables(expr);

    for (const freeVar of freeVars) {
      const sourceVar = addNode(freeVar, 'parameter', undefined, systemId);
      addDependency(sourceVar, targetVariable, 'multiplicative', equationIndex, expr);
    }
  }

  // Helper function to process coupling (for merge_coupled option)
  function processCoupling(coupling: CouplingEntry[]) {
    for (const entry of coupling) {
      if (entry.type === 'variable_map') {
        // Create cross-system dependencies for variable mappings
        const fromParts = entry.from.split('.');
        const toParts = entry.to.split('.');

        if (fromParts.length >= 2 && toParts.length >= 2) {
          const fromSystem = fromParts[0];
          const fromVar = fromParts.slice(1).join('.');
          const toSystem = toParts[0];
          const toVar = toParts.slice(1).join('.');

          const sourceVar = addNode(fromVar, 'parameter', undefined, fromSystem);
          const targetVar = addNode(toVar, 'parameter', undefined, toSystem);

          // Create coupling dependency
          addDependency(sourceVar, targetVar, 'multiplicative', -1, entry.from);
        }
      }
    }
  }

  // Build adjacency maps for the Graph interface methods
  const adjacencyMap = new Map<string, Set<string>>();
  const predecessorMap = new Map<string, Set<string>>();
  const successorMap = new Map<string, Set<string>>();

  // Initialize maps for all nodes
  for (const node of nodes) {
    adjacencyMap.set(node.name, new Set());
    predecessorMap.set(node.name, new Set());
    successorMap.set(node.name, new Set());
  }

  // Build adjacency relationships from edges
  for (const edge of edges) {
    const { source, target } = edge;

    // Adjacency includes both predecessors and successors
    adjacencyMap.get(source)?.add(target);
    adjacencyMap.get(target)?.add(source);

    // Predecessors (nodes that point TO this node)
    predecessorMap.get(target)?.add(source);

    // Successors (nodes that this node points TO)
    successorMap.get(source)?.add(target);
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
    }
  };
}