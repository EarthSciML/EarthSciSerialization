/**
 * Graph Tests
 *
 * Tests for the componentGraph function and Graph interface implementation
 */

import { describe, it, expect } from 'vitest';
import { componentGraph, expressionGraph } from './graph.js';
import type { EsmFile, Model, ReactionSystem, Equation, Reaction } from './types.js';

describe('componentGraph function', () => {
  const mockEsmFile: EsmFile = {
    esm: '0.1.0',
    metadata: {
      name: 'Test System',
      description: 'Test component graph',
      authors: ['Test Author']
    },
    models: {
      'Transport': {
        reference: { notes: '3D transport model' },
        variables: {
          u_wind: { type: 'parameter', units: 'm/s', default: 5.0 },
          v_wind: { type: 'parameter', units: 'm/s', default: 3.0 },
          temperature: { type: 'state', units: 'K', default: 298.15 }
        },
        equations: [
          { lhs: 'du_dt', rhs: '0' },
          { lhs: 'dv_dt', rhs: '0' }
        ]
      },
      'Chemistry': {
        reference: { notes: 'Atmospheric chemistry' },
        variables: {
          O3: { type: 'state', units: 'mol/mol', default: 40e-9 }
        },
        equations: [
          { lhs: 'dO3_dt', rhs: '-k1 * O3' }
        ]
      }
    },
    reaction_systems: {
      'SimpleReactions': {
        species: {
          'A': { units: 'mol/mol', default: 1e-6 },
          'B': { units: 'mol/mol', default: 2e-6 },
          'C': { units: 'mol/mol', default: 0e-6 }
        },
        reactions: [
          { reactants: ['A'], products: ['B'], rate: 'k1' },
          { reactants: ['B'], products: ['C'], rate: 'k2' }
        ]
      }
    },
    data_loaders: {
      'WeatherData': {
        type: 'netcdf',
        path: '/data/weather.nc',
        variables: ['temperature', 'pressure', 'humidity']
      }
    },
    operators: {
      'Diffusion': {
        type: 'spatial',
        config: { method: 'finite_difference' }
      }
    },
    coupling: [
      {
        type: 'operator_compose',
        systems: ['Transport', 'Chemistry'],
        description: 'Couple transport with chemistry'
      },
      {
        type: 'variable_map',
        from: 'WeatherData.temperature',
        to: 'Chemistry.T',
        description: 'Map temperature data'
      },
      {
        type: 'operator_apply',
        operator: 'Diffusion',
        system: 'Transport',
        description: 'Apply diffusion to transport'
      },
      {
        type: 'couple2',
        systems: ['Transport', 'SimpleReactions'],
        description: 'Direct coupling between transport and reactions'
      }
    ]
  };

  it('should return a Graph interface with correct structure', () => {
    const graph = componentGraph(mockEsmFile);

    // Check the graph has the required properties
    expect(graph).toHaveProperty('nodes');
    expect(graph).toHaveProperty('edges');
    expect(graph).toHaveProperty('adjacency');
    expect(graph).toHaveProperty('predecessors');
    expect(graph).toHaveProperty('successors');

    // Check methods are functions
    expect(typeof graph.adjacency).toBe('function');
    expect(typeof graph.predecessors).toBe('function');
    expect(typeof graph.successors).toBe('function');
  });

  it('should extract all component nodes with metadata', () => {
    const graph = componentGraph(mockEsmFile);

    expect(graph.nodes).toHaveLength(5);

    // Check Transport model node
    const transportNode = graph.nodes.find(n => n.id === 'Transport');
    expect(transportNode).toBeDefined();
    expect(transportNode?.type).toBe('model');
    expect(transportNode?.description).toBe('3D transport model');
    expect(transportNode?.metadata.var_count).toBe(3); // u_wind, v_wind, temperature
    expect(transportNode?.metadata.eq_count).toBe(2); // du_dt, dv_dt
    expect(transportNode?.metadata.species_count).toBe(0);

    // Check Chemistry model node
    const chemistryNode = graph.nodes.find(n => n.id === 'Chemistry');
    expect(chemistryNode).toBeDefined();
    expect(chemistryNode?.type).toBe('model');
    expect(chemistryNode?.metadata.var_count).toBe(1); // O3
    expect(chemistryNode?.metadata.eq_count).toBe(1); // dO3_dt
    expect(chemistryNode?.metadata.species_count).toBe(0);

    // Check SimpleReactions reaction system node
    const reactionsNode = graph.nodes.find(n => n.id === 'SimpleReactions');
    expect(reactionsNode).toBeDefined();
    expect(reactionsNode?.type).toBe('reaction_system');
    expect(reactionsNode?.metadata.var_count).toBe(0);
    expect(reactionsNode?.metadata.eq_count).toBe(2); // 2 reactions
    expect(reactionsNode?.metadata.species_count).toBe(3); // A, B, C

    // Check WeatherData data loader node
    const weatherNode = graph.nodes.find(n => n.id === 'WeatherData');
    expect(weatherNode).toBeDefined();
    expect(weatherNode?.type).toBe('data_loader');
    expect(weatherNode?.metadata.var_count).toBe(3); // temperature, pressure, humidity
    expect(weatherNode?.metadata.eq_count).toBe(0);
    expect(weatherNode?.metadata.species_count).toBe(0);

    // Check Diffusion operator node
    const diffusionNode = graph.nodes.find(n => n.id === 'Diffusion');
    expect(diffusionNode).toBeDefined();
    expect(diffusionNode?.type).toBe('operator');
    expect(diffusionNode?.metadata.var_count).toBe(0);
    expect(diffusionNode?.metadata.eq_count).toBe(0);
    expect(diffusionNode?.metadata.species_count).toBe(0);
  });

  it('should extract coupling edges in Graph format', () => {
    const graph = componentGraph(mockEsmFile);

    expect(graph.edges).toHaveLength(4);

    // Check edge structure
    const firstEdge = graph.edges[0];
    expect(firstEdge).toHaveProperty('source');
    expect(firstEdge).toHaveProperty('target');
    expect(firstEdge).toHaveProperty('data');

    // Check operator_compose edge
    const composeEdge = graph.edges.find(e => e.data.type === 'operator_compose');
    expect(composeEdge).toBeDefined();
    expect(composeEdge?.source).toBe('Transport');
    expect(composeEdge?.target).toBe('Chemistry');
    expect(composeEdge?.data.label).toBe('compose');

    // Check variable_map edge
    const mapEdge = graph.edges.find(e => e.data.type === 'variable_map');
    expect(mapEdge).toBeDefined();
    expect(mapEdge?.source).toBe('WeatherData');
    expect(mapEdge?.target).toBe('Chemistry');
    expect(mapEdge?.data.label).toBe('temperature');

    // Check operator_apply edge
    const applyEdge = graph.edges.find(e => e.data.type === 'operator_apply');
    expect(applyEdge).toBeDefined();
    expect(applyEdge?.source).toBe('Diffusion');
    expect(applyEdge?.target).toBe('Transport');
    expect(applyEdge?.data.label).toBe('apply');

    // Check couple2 edge
    const couple2Edge = graph.edges.find(e => e.data.type === 'couple2');
    expect(couple2Edge).toBeDefined();
    expect(couple2Edge?.source).toBe('Transport');
    expect(couple2Edge?.target).toBe('SimpleReactions');
    expect(couple2Edge?.data.label).toBe('couple');
  });

  it('should implement adjacency method correctly', () => {
    const graph = componentGraph(mockEsmFile);

    // Transport is connected to Chemistry, SimpleReactions, and Diffusion (incoming)
    const transportAdjacent = graph.adjacency('Transport');
    expect(transportAdjacent).toContain('Chemistry');
    expect(transportAdjacent).toContain('SimpleReactions');
    expect(transportAdjacent).toContain('Diffusion');

    // Chemistry is connected to Transport and WeatherData
    const chemistryAdjacent = graph.adjacency('Chemistry');
    expect(chemistryAdjacent).toContain('Transport');
    expect(chemistryAdjacent).toContain('WeatherData');

    // WeatherData is only connected to Chemistry
    const weatherAdjacent = graph.adjacency('WeatherData');
    expect(weatherAdjacent).toContain('Chemistry');
    expect(weatherAdjacent).toHaveLength(1);

    // Non-existent node should return empty array
    const nonExistentAdjacent = graph.adjacency('NonExistent');
    expect(nonExistentAdjacent).toEqual([]);
  });

  it('should implement predecessors method correctly', () => {
    const graph = componentGraph(mockEsmFile);

    // Transport has Diffusion as predecessor (Diffusion applies to Transport)
    const transportPredecessors = graph.predecessors('Transport');
    expect(transportPredecessors).toContain('Diffusion');

    // Chemistry has Transport and WeatherData as predecessors
    const chemistryPredecessors = graph.predecessors('Chemistry');
    expect(chemistryPredecessors).toContain('Transport');
    expect(chemistryPredecessors).toContain('WeatherData');

    // SimpleReactions has Transport as predecessor
    const reactionsPredecessors = graph.predecessors('SimpleReactions');
    expect(reactionsPredecessors).toContain('Transport');

    // WeatherData has no predecessors
    const weatherPredecessors = graph.predecessors('WeatherData');
    expect(weatherPredecessors).toEqual([]);

    // Diffusion has no predecessors
    const diffusionPredecessors = graph.predecessors('Diffusion');
    expect(diffusionPredecessors).toEqual([]);
  });

  it('should implement successors method correctly', () => {
    const graph = componentGraph(mockEsmFile);

    // Transport has Chemistry and SimpleReactions as successors
    const transportSuccessors = graph.successors('Transport');
    expect(transportSuccessors).toContain('Chemistry');
    expect(transportSuccessors).toContain('SimpleReactions');

    // WeatherData has Chemistry as successor
    const weatherSuccessors = graph.successors('WeatherData');
    expect(weatherSuccessors).toContain('Chemistry');
    expect(weatherSuccessors).toHaveLength(1);

    // Diffusion has Transport as successor
    const diffusionSuccessors = graph.successors('Diffusion');
    expect(diffusionSuccessors).toContain('Transport');
    expect(diffusionSuccessors).toHaveLength(1);

    // Chemistry has no successors (end node in these connections)
    const chemistrySuccessors = graph.successors('Chemistry');
    expect(chemistrySuccessors).toEqual([]);

    // SimpleReactions has no successors
    const reactionsSuccessors = graph.successors('SimpleReactions');
    expect(reactionsSuccessors).toEqual([]);
  });

  it('should handle empty ESM file gracefully', () => {
    const emptyEsmFile: EsmFile = {
      esm: '0.1.0',
      metadata: {
        name: 'Empty',
        authors: []
      }
    };

    const graph = componentGraph(emptyEsmFile);
    expect(graph.nodes).toHaveLength(0);
    expect(graph.edges).toHaveLength(0);

    // Methods should return empty arrays for any node
    expect(graph.adjacency('AnyNode')).toEqual([]);
    expect(graph.predecessors('AnyNode')).toEqual([]);
    expect(graph.successors('AnyNode')).toEqual([]);
  });

  it('should handle components with no coupling', () => {
    const noCouplingFile: EsmFile = {
      ...mockEsmFile,
      coupling: undefined
    };

    const graph = componentGraph(noCouplingFile);
    expect(graph.nodes).toHaveLength(5); // All components
    expect(graph.edges).toHaveLength(0); // No edges

    // All nodes should have no adjacent nodes
    for (const node of graph.nodes) {
      expect(graph.adjacency(node.id)).toEqual([]);
      expect(graph.predecessors(node.id)).toEqual([]);
      expect(graph.successors(node.id)).toEqual([]);
    }
  });
});

describe('expressionGraph function', () => {
  const mockModel: Model = {
    variables: {
      u: { type: 'state', units: 'm/s', default: 0.0 },
      v: { type: 'parameter', units: 'm/s', default: 1.0 },
      w: { type: 'observed', units: 'm/s', expression: { op: '+', args: ['u', 'v'] } }
    },
    equations: [
      { lhs: 'du_dt', rhs: { op: '*', args: ['k1', 'u'] } },
      { lhs: 'dv_dt', rhs: 0 }
    ]
  };

  const mockReactionSystem: ReactionSystem = {
    species: {
      A: { units: 'mol/mol', default: 1e-6 },
      B: { units: 'mol/mol', default: 2e-6 },
      C: { units: 'mol/mol', default: 0e-6 }
    },
    parameters: {
      k1: { units: 's-1', default: 1e-3 },
      k2: { units: 's-1', default: 2e-3 }
    },
    reactions: [
      {
        reactants: [{ species: 'A', stoichiometry: 1 }],
        products: [{ species: 'B', stoichiometry: 1 }],
        rate: 'k1'
      },
      {
        reactants: [{ species: 'B', stoichiometry: 1 }],
        products: [{ species: 'C', stoichiometry: 1 }],
        rate: 'k2'
      }
    ]
  };

  it('should return a Graph interface with correct structure for a Model', () => {
    const graph = expressionGraph(mockModel);

    // Check the graph has the required properties
    expect(graph).toHaveProperty('nodes');
    expect(graph).toHaveProperty('edges');
    expect(graph).toHaveProperty('adjacency');
    expect(graph).toHaveProperty('predecessors');
    expect(graph).toHaveProperty('successors');

    // Check methods are functions
    expect(typeof graph.adjacency).toBe('function');
    expect(typeof graph.predecessors).toBe('function');
    expect(typeof graph.successors).toBe('function');
  });

  it('should extract variable nodes from a Model', () => {
    const graph = expressionGraph(mockModel);

    expect(graph.nodes.length).toBeGreaterThan(0);

    // Check for state variable
    const uNode = graph.nodes.find(n => n.name === 'u');
    expect(uNode).toBeDefined();
    expect(uNode?.kind).toBe('state');
    expect(uNode?.units).toBe('m/s');
    expect(uNode?.system).toBe('default');

    // Check for parameter variable
    const vNode = graph.nodes.find(n => n.name === 'v');
    expect(vNode).toBeDefined();
    expect(vNode?.kind).toBe('parameter');
    expect(vNode?.units).toBe('m/s');

    // Check for observed variable
    const wNode = graph.nodes.find(n => n.name === 'w');
    expect(wNode).toBeDefined();
    expect(wNode?.kind).toBe('observed');
    expect(wNode?.units).toBe('m/s');

    // Check for derived variables from equations
    const duDtNode = graph.nodes.find(n => n.name === 'du_dt');
    expect(duDtNode).toBeDefined();
    expect(duDtNode?.kind).toBe('state');

    const k1Node = graph.nodes.find(n => n.name === 'k1');
    expect(k1Node).toBeDefined();
    expect(k1Node?.kind).toBe('parameter');
  });

  it('should create dependency edges for Model equations', () => {
    const graph = expressionGraph(mockModel);

    expect(graph.edges.length).toBeGreaterThan(0);

    // Check for edge from observed variable dependency (u, v -> w)
    const uToWEdge = graph.edges.find(e => e.source === 'u' && e.target === 'w');
    expect(uToWEdge).toBeDefined();
    expect(uToWEdge?.data.relationship).toBe('multiplicative');
    expect(uToWEdge?.data.equation_index).toBe(-1); // observed variable

    const vToWEdge = graph.edges.find(e => e.source === 'v' && e.target === 'w');
    expect(vToWEdge).toBeDefined();
    expect(vToWEdge?.data.relationship).toBe('multiplicative');

    // Check for edge from equation (k1, u -> du_dt)
    const k1ToDuDtEdge = graph.edges.find(e => e.source === 'k1' && e.target === 'du_dt');
    expect(k1ToDuDtEdge).toBeDefined();
    expect(k1ToDuDtEdge?.data.relationship).toBe('additive');
    expect(k1ToDuDtEdge?.data.equation_index).toBe(0);

    const uToDuDtEdge = graph.edges.find(e => e.source === 'u' && e.target === 'du_dt');
    expect(uToDuDtEdge).toBeDefined();
    expect(uToDuDtEdge?.data.relationship).toBe('additive');
    expect(uToDuDtEdge?.data.equation_index).toBe(0);
  });

  it('should extract species and parameters from a ReactionSystem', () => {
    const graph = expressionGraph(mockReactionSystem);

    // Check species nodes
    const aNode = graph.nodes.find(n => n.name === 'A');
    expect(aNode).toBeDefined();
    expect(aNode?.kind).toBe('species');
    expect(aNode?.units).toBe('mol/mol');

    const bNode = graph.nodes.find(n => n.name === 'B');
    expect(bNode).toBeDefined();
    expect(bNode?.kind).toBe('species');

    const cNode = graph.nodes.find(n => n.name === 'C');
    expect(cNode).toBeDefined();
    expect(cNode?.kind).toBe('species');

    // Check parameter nodes
    const k1Node = graph.nodes.find(n => n.name === 'k1');
    expect(k1Node).toBeDefined();
    expect(k1Node?.kind).toBe('parameter');
    expect(k1Node?.units).toBe('s-1');

    const k2Node = graph.nodes.find(n => n.name === 'k2');
    expect(k2Node).toBeDefined();
    expect(k2Node?.kind).toBe('parameter');
  });

  it('should create rate and stoichiometric dependencies for ReactionSystem', () => {
    const graph = expressionGraph(mockReactionSystem);

    // Check rate dependencies (k1 -> A, k1 -> B for first reaction)
    const k1ToAEdge = graph.edges.find(e => e.source === 'k1' && e.target === 'A');
    expect(k1ToAEdge).toBeDefined();
    expect(k1ToAEdge?.data.relationship).toBe('rate');
    expect(k1ToAEdge?.data.equation_index).toBe(0);

    const k1ToBEdge = graph.edges.find(e => e.source === 'k1' && e.target === 'B');
    expect(k1ToBEdge).toBeDefined();
    expect(k1ToBEdge?.data.relationship).toBe('rate');

    // Check stoichiometric dependencies (A -> B for first reaction)
    const aToBEdge = graph.edges.find(e => e.source === 'A' && e.target === 'B');
    expect(aToBEdge).toBeDefined();
    expect(aToBEdge?.data.relationship).toBe('stoichiometric');

    // Check second reaction (k2 -> B, k2 -> C, B -> C)
    const k2ToBEdge = graph.edges.find(e => e.source === 'k2' && e.target === 'B');
    expect(k2ToBEdge).toBeDefined();
    expect(k2ToBEdge?.data.relationship).toBe('rate');
    expect(k2ToBEdge?.data.equation_index).toBe(1);

    const k2ToCEdge = graph.edges.find(e => e.source === 'k2' && e.target === 'C');
    expect(k2ToCEdge).toBeDefined();
    expect(k2ToCEdge?.data.relationship).toBe('rate');

    const bToCEdge = graph.edges.find(e => e.source === 'B' && e.target === 'C');
    expect(bToCEdge).toBeDefined();
    expect(bToCEdge?.data.relationship).toBe('stoichiometric');
  });

  it('should handle single Equation input', () => {
    const equation: Equation = { lhs: 'dy_dt', rhs: { op: '*', args: ['a', 'y'] } };
    const graph = expressionGraph(equation);

    // Should have nodes for dy_dt, a, and y
    expect(graph.nodes).toHaveLength(3);

    const dyDtNode = graph.nodes.find(n => n.name === 'dy_dt');
    expect(dyDtNode).toBeDefined();
    expect(dyDtNode?.kind).toBe('state');

    const aNode = graph.nodes.find(n => n.name === 'a');
    expect(aNode).toBeDefined();
    expect(aNode?.kind).toBe('parameter');

    const yNode = graph.nodes.find(n => n.name === 'y');
    expect(yNode).toBeDefined();
    expect(yNode?.kind).toBe('parameter');

    // Should have dependencies a -> dy_dt and y -> dy_dt
    expect(graph.edges).toHaveLength(2);

    const aToYEdge = graph.edges.find(e => e.source === 'a' && e.target === 'dy_dt');
    expect(aToYEdge).toBeDefined();
    expect(aToYEdge?.data.relationship).toBe('additive');

    const yToYEdge = graph.edges.find(e => e.source === 'y' && e.target === 'dy_dt');
    expect(yToYEdge).toBeDefined();
    expect(yToYEdge?.data.relationship).toBe('additive');
  });

  it('should handle single Reaction input', () => {
    const reaction: Reaction = {
      reactants: [{ species: 'X', stoichiometry: 2 }],
      products: [{ species: 'Y', stoichiometry: 1 }],
      rate: { op: '*', args: ['k', 'X'] }
    };
    const graph = expressionGraph(reaction);

    // Should have nodes for species X, Y and parameters k, X (as parameter in rate)
    const xSpeciesNode = graph.nodes.find(n => n.name === 'X' && n.kind === 'species');
    expect(xSpeciesNode).toBeDefined();

    const ySpeciesNode = graph.nodes.find(n => n.name === 'Y' && n.kind === 'species');
    expect(ySpeciesNode).toBeDefined();

    const kParamNode = graph.nodes.find(n => n.name === 'k' && n.kind === 'parameter');
    expect(kParamNode).toBeDefined();

    // Should have rate dependencies and stoichiometric dependencies
    const rateDeps = graph.edges.filter(e => e.data.relationship === 'rate');
    expect(rateDeps.length).toBeGreaterThan(0);

    const stoichDeps = graph.edges.filter(e => e.data.relationship === 'stoichiometric');
    expect(stoichDeps.length).toBeGreaterThan(0);
  });

  it('should handle Expression input', () => {
    const expr = { op: '+', args: ['x', { op: '*', args: ['y', 'z'] }] };
    const graph = expressionGraph(expr);

    // Should have nodes for expr_result, x, y, z
    expect(graph.nodes).toHaveLength(4);

    const resultNode = graph.nodes.find(n => n.name === 'expr_result');
    expect(resultNode).toBeDefined();
    expect(resultNode?.kind).toBe('observed');

    const xNode = graph.nodes.find(n => n.name === 'x');
    expect(xNode).toBeDefined();
    expect(xNode?.kind).toBe('parameter');

    // Should have dependencies x -> expr_result, y -> expr_result, z -> expr_result
    expect(graph.edges).toHaveLength(3);

    const xDep = graph.edges.find(e => e.source === 'x' && e.target === 'expr_result');
    expect(xDep).toBeDefined();
    expect(xDep?.data.relationship).toBe('multiplicative');
  });

  it('should implement adjacency methods correctly', () => {
    const graph = expressionGraph(mockModel);

    // Test adjacency (bidirectional)
    const adjacentToU = graph.adjacency('u');
    expect(adjacentToU.length).toBeGreaterThan(0);

    // Test predecessors and successors
    const predecessorsOfDuDt = graph.predecessors('du_dt');
    expect(predecessorsOfDuDt).toContain('k1');
    expect(predecessorsOfDuDt).toContain('u');

    const successorsOfU = graph.successors('u');
    expect(successorsOfU.length).toBeGreaterThan(0);

    // Non-existent node should return empty arrays
    expect(graph.adjacency('nonexistent')).toEqual([]);
    expect(graph.predecessors('nonexistent')).toEqual([]);
    expect(graph.successors('nonexistent')).toEqual([]);
  });

  it('should handle scoped variables in EsmFile', () => {
    const esmFile: EsmFile = {
      esm: '0.1.0',
      metadata: { name: 'Test', authors: [] },
      models: {
        'ModelA': {
          variables: { temp: { type: 'state', units: 'K', default: 300 } },
          equations: [{ lhs: 'dtemp_dt', rhs: { op: '*', args: ['rate', 'temp'] } }]
        },
        'ModelB': {
          variables: { press: { type: 'parameter', units: 'Pa', default: 101325 } },
          equations: [{ lhs: 'dpress_dt', rhs: 'zero' }]
        }
      }
    };

    const graph = expressionGraph(esmFile);

    // Check scoped variable names
    const modelATempNode = graph.nodes.find(n => n.name === 'ModelA.temp');
    expect(modelATempNode).toBeDefined();
    expect(modelATempNode?.system).toBe('ModelA');

    const modelBPressNode = graph.nodes.find(n => n.name === 'ModelB.press');
    expect(modelBPressNode).toBeDefined();
    expect(modelBPressNode?.system).toBe('ModelB');

    const modelARateNode = graph.nodes.find(n => n.name === 'ModelA.rate');
    expect(modelARateNode).toBeDefined();
    expect(modelARateNode?.system).toBe('ModelA');
  });
});