/**
 * Graph Tests
 *
 * Tests for the componentGraph function and Graph interface implementation
 */

import { describe, it, expect } from 'vitest';
import { componentGraph } from './graph.js';
import type { EsmFile } from './types.js';

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