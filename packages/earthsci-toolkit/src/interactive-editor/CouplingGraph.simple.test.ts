/**
 * CouplingGraph Simple Tests
 *
 * Tests for the CouplingGraph utility functions and data structures,
 * avoiding client-side DOM testing complexity.
 */

import { describe, it, expect } from 'vitest';
import { component_graph, componentExists, getComponentType } from '../graph.js';
import type { EsmFile } from '../types.js';

describe('CouplingGraph Utilities', () => {
  const mockEsmFile: EsmFile = {
    esm: '0.1.0',
    metadata: {
      name: 'Test System',
      description: 'Test coupling graph',
      authors: ['Test Author']
    },
    models: {
      'Transport': {
        reference: { notes: '3D transport model' },
        variables: {
          u_wind: { type: 'parameter', units: 'm/s', default: 5.0 }
        },
        equations: []
      },
      'Chemistry': {
        reference: { notes: 'Atmospheric chemistry' },
        variables: {
          O3: { type: 'state', units: 'mol/mol', default: 40e-9 }
        },
        equations: []
      }
    },
    reaction_systems: {
      'SimpleReactions': {
        species: {
          'A': { units: 'mol/mol', default: 1e-6 },
          'B': { units: 'mol/mol', default: 2e-6 }
        },
        reactions: []
      }
    },
    data_loaders: {
      'WeatherData': {
        type: 'netcdf',
        path: '/data/weather.nc',
        variables: ['temperature', 'pressure']
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
      }
    ]
  };

  describe('component_graph', () => {
    it('should extract all component nodes', () => {
      const graph = component_graph(mockEsmFile);

      expect(graph.nodes).toHaveLength(5);

      // Check models
      const transportNode = graph.nodes.find(n => n.id === 'Transport');
      expect(transportNode).toBeDefined();
      expect(transportNode?.type).toBe('model');
      expect(transportNode?.description).toBe('3D transport model');

      const chemistryNode = graph.nodes.find(n => n.id === 'Chemistry');
      expect(chemistryNode).toBeDefined();
      expect(chemistryNode?.type).toBe('model');

      // Check reaction systems
      const reactionsNode = graph.nodes.find(n => n.id === 'SimpleReactions');
      expect(reactionsNode).toBeDefined();
      expect(reactionsNode?.type).toBe('reaction_system');

      // Check data loaders
      const weatherNode = graph.nodes.find(n => n.id === 'WeatherData');
      expect(weatherNode).toBeDefined();
      expect(weatherNode?.type).toBe('data_loader');

      // Check operators
      const diffusionNode = graph.nodes.find(n => n.id === 'Diffusion');
      expect(diffusionNode).toBeDefined();
      expect(diffusionNode?.type).toBe('operator');
    });

    it('should extract coupling edges correctly', () => {
      const graph = component_graph(mockEsmFile);

      expect(graph.edges).toHaveLength(3);

      // Check operator_compose edge
      const composeEdge = graph.edges.find(e => e.type === 'operator_compose');
      expect(composeEdge).toBeDefined();
      expect(composeEdge?.from).toBe('Transport');
      expect(composeEdge?.to).toBe('Chemistry');
      expect(composeEdge?.label).toBe('compose');

      // Check variable_map edge
      const mapEdge = graph.edges.find(e => e.type === 'variable_map');
      expect(mapEdge).toBeDefined();
      expect(mapEdge?.from).toBe('WeatherData');
      expect(mapEdge?.to).toBe('Chemistry');
      expect(mapEdge?.label).toBe('temperature');

      // Check operator_apply edge
      const applyEdge = graph.edges.find(e => e.type === 'operator_apply');
      expect(applyEdge).toBeDefined();
      expect(applyEdge?.from).toBe('Diffusion');
      expect(applyEdge?.to).toBe('Transport');
      expect(applyEdge?.label).toBe('apply');
    });

    it('should handle empty ESM file gracefully', () => {
      const emptyEsmFile: EsmFile = {
        esm: '0.1.0',
        metadata: {
          name: 'Empty',
          authors: []
        }
      };

      const graph = component_graph(emptyEsmFile);
      expect(graph.nodes).toHaveLength(0);
      expect(graph.edges).toHaveLength(0);
    });

    it('should handle ESM file with only components (no coupling)', () => {
      const noConnectionsFile: EsmFile = {
        ...mockEsmFile,
        coupling: undefined
      };

      const graph = component_graph(noConnectionsFile);
      expect(graph.nodes).toHaveLength(5); // All components
      expect(graph.edges).toHaveLength(0); // No edges
    });

    it('should handle couple2 coupling type', () => {
      const couple2File: EsmFile = {
        ...mockEsmFile,
        coupling: [
          {
            type: 'couple2',
            systems: ['Transport', 'Chemistry'],
            description: 'Direct coupling'
          }
        ]
      };

      const graph = component_graph(couple2File);
      const edge = graph.edges.find(e => e.type === 'couple2');
      expect(edge).toBeDefined();
      expect(edge?.from).toBe('Transport');
      expect(edge?.to).toBe('Chemistry');
      expect(edge?.label).toBe('couple');
    });

    it('should handle callback coupling type', () => {
      const callbackFile: EsmFile = {
        ...mockEsmFile,
        coupling: [
          {
            type: 'callback',
            source: 'Transport',
            target: 'Chemistry',
            callback: 'custom_callback',
            description: 'Custom callback'
          }
        ]
      };

      const graph = component_graph(callbackFile);
      const edge = graph.edges.find(e => e.type === 'callback');
      expect(edge).toBeDefined();
      expect(edge?.from).toBe('Transport');
      expect(edge?.to).toBe('Chemistry');
      expect(edge?.label).toBe('custom_callback');
    });
  });

  describe('componentExists', () => {
    it('should return true for existing components', () => {
      expect(componentExists(mockEsmFile, 'Transport')).toBe(true);
      expect(componentExists(mockEsmFile, 'Chemistry')).toBe(true);
      expect(componentExists(mockEsmFile, 'SimpleReactions')).toBe(true);
      expect(componentExists(mockEsmFile, 'WeatherData')).toBe(true);
      expect(componentExists(mockEsmFile, 'Diffusion')).toBe(true);
    });

    it('should return false for non-existing components', () => {
      expect(componentExists(mockEsmFile, 'NonExistent')).toBe(false);
      expect(componentExists(mockEsmFile, 'AnotherMissing')).toBe(false);
    });
  });

  describe('getComponentType', () => {
    it('should return correct types for existing components', () => {
      expect(getComponentType(mockEsmFile, 'Transport')).toBe('model');
      expect(getComponentType(mockEsmFile, 'Chemistry')).toBe('model');
      expect(getComponentType(mockEsmFile, 'SimpleReactions')).toBe('reaction_system');
      expect(getComponentType(mockEsmFile, 'WeatherData')).toBe('data_loader');
      expect(getComponentType(mockEsmFile, 'Diffusion')).toBe('operator');
    });

    it('should return null for non-existing components', () => {
      expect(getComponentType(mockEsmFile, 'NonExistent')).toBe(null);
      expect(getComponentType(mockEsmFile, 'AnotherMissing')).toBe(null);
    });
  });

  describe('edge parsing edge cases', () => {
    it('should handle variable_map with complex variable paths', () => {
      const complexMapFile: EsmFile = {
        ...mockEsmFile,
        coupling: [
          {
            type: 'variable_map',
            from: 'WeatherData.nested.deep.temperature',
            to: 'Chemistry.params.T',
            description: 'Complex variable mapping'
          }
        ]
      };

      const graph = component_graph(complexMapFile);
      const edge = graph.edges.find(e => e.type === 'variable_map');
      expect(edge).toBeDefined();
      expect(edge?.from).toBe('WeatherData');
      expect(edge?.to).toBe('Chemistry');
      expect(edge?.label).toBe('nested.deep.temperature');
    });

    it('should handle operator_compose with multiple systems', () => {
      const multiComposeFile: EsmFile = {
        ...mockEsmFile,
        coupling: [
          {
            type: 'operator_compose',
            systems: ['Transport', 'Chemistry', 'SimpleReactions'],
            description: 'Multi-system composition'
          }
        ]
      };

      const graph = component_graph(multiComposeFile);
      const composeEdges = graph.edges.filter(e => e.type === 'operator_compose');
      expect(composeEdges).toHaveLength(2); // n-1 edges for n systems
      expect(composeEdges[0].from).toBe('Transport');
      expect(composeEdges[0].to).toBe('Chemistry');
      expect(composeEdges[1].from).toBe('Chemistry');
      expect(composeEdges[1].to).toBe('SimpleReactions');
    });

    it('should ignore invalid coupling entries gracefully', () => {
      const invalidCouplingFile: EsmFile = {
        ...mockEsmFile,
        coupling: [
          {
            type: 'variable_map',
            from: 'InvalidFormat', // Missing component.variable format
            to: 'AlsoInvalid',
            description: 'Invalid mapping'
          },
          {
            type: 'operator_compose',
            systems: ['OnlyOneSystem'], // Should have at least 2 systems
            description: 'Invalid composition'
          }
        ]
      };

      const graph = component_graph(invalidCouplingFile);
      expect(graph.edges).toHaveLength(0); // Both invalid, no edges created
    });
  });
});