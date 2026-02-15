/**
 * CouplingGraph Component Tests
 *
 * Tests for the CouplingGraph SolidJS component covering:
 * - Basic rendering with nodes and edges
 * - Interactive features (click, hover, drag)
 * - Graph layout and positioning
 * - Component selection and editing
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@solidjs/testing-library';
import '@testing-library/jest-dom';
import { CouplingGraph } from './CouplingGraph.tsx';
import type { EsmFile } from '../types.js';

// Mock d3-force since it's hard to test in JSDOM
vi.mock('d3-force', () => ({
  forceSimulation: vi.fn(() => ({
    force: vi.fn().mockReturnThis(),
    on: vi.fn().mockReturnThis(),
    stop: vi.fn(),
    alphaTarget: vi.fn().mockReturnThis(),
    restart: vi.fn().mockReturnThis(),
  })),
  forceLink: vi.fn(() => ({
    id: vi.fn().mockReturnThis(),
    distance: vi.fn().mockReturnThis(),
  })),
  forceManyBody: vi.fn(() => ({
    strength: vi.fn().mockReturnThis(),
  })),
  forceCenter: vi.fn(),
  forceCollide: vi.fn(() => ({
    radius: vi.fn().mockReturnThis(),
  })),
}));

describe('CouplingGraph', () => {
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

  let mockOnEditCoupling: ReturnType<typeof vi.fn>;
  let mockOnSelectComponent: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockOnEditCoupling = vi.fn();
    mockOnSelectComponent = vi.fn();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders the coupling graph SVG', () => {
    render(() => (
      <CouplingGraph
        esmFile={mockEsmFile}
        width={800}
        height={600}
      />
    ));

    expect(screen.getByRole('img', { hidden: true })).toBeInTheDocument();
    const svg = screen.getByRole('img', { hidden: true });
    expect(svg).toHaveAttribute('width', '800');
    expect(svg).toHaveAttribute('height', '600');
  });

  it('renders nodes for all component types', () => {
    render(() => (
      <CouplingGraph
        esmFile={mockEsmFile}
        width={800}
        height={600}
      />
    ));

    // Check that nodes are rendered with correct classes
    const svg = screen.getByRole('img', { hidden: true });

    // Should have nodes for models, reaction systems, data loaders, and operators
    expect(svg.querySelector('.node-model')).toBeInTheDocument();
    expect(svg.querySelector('.node-reaction_system')).toBeInTheDocument();
    expect(svg.querySelector('.node-data_loader')).toBeInTheDocument();
    expect(svg.querySelector('.node-operator')).toBeInTheDocument();
  });

  it('renders edges for coupling relationships', () => {
    render(() => (
      <CouplingGraph
        esmFile={mockEsmFile}
        width={800}
        height={600}
      />
    ));

    const svg = screen.getByRole('img', { hidden: true });

    // Should have edges for different coupling types
    expect(svg.querySelector('.edge-operator_compose')).toBeInTheDocument();
    expect(svg.querySelector('.edge-variable_map')).toBeInTheDocument();
    expect(svg.querySelector('.edge-operator_apply')).toBeInTheDocument();
  });

  it('displays node labels', () => {
    render(() => (
      <CouplingGraph
        esmFile={mockEsmFile}
        width={800}
        height={600}
      />
    ));

    // Check for component names in node labels
    expect(screen.getByText('Transport')).toBeInTheDocument();
    expect(screen.getByText('Chemistry')).toBeInTheDocument();
    expect(screen.getByText('SimpleReactions')).toBeInTheDocument();
    expect(screen.getByText('WeatherData')).toBeInTheDocument();
    expect(screen.getByText('Diffusion')).toBeInTheDocument();
  });

  it('displays edge labels', () => {
    render(() => (
      <CouplingGraph
        esmFile={mockEsmFile}
        width={800}
        height={600}
      />
    ));

    // Check for coupling labels
    expect(screen.getByText('compose')).toBeInTheDocument();
    expect(screen.getByText('temperature')).toBeInTheDocument();
    expect(screen.getByText('apply')).toBeInTheDocument();
  });

  it('calls onSelectComponent when node is clicked', async () => {
    render(() => (
      <CouplingGraph
        esmFile={mockEsmFile}
        onSelectComponent={mockOnSelectComponent}
        interactive={true}
        width={800}
        height={600}
      />
    ));

    // Find and click a node
    const transportNode = screen.getByText('Transport').closest('.node');
    expect(transportNode).toBeInTheDocument();

    fireEvent.click(transportNode!);

    expect(mockOnSelectComponent).toHaveBeenCalledWith('Transport');
  });

  it('calls onEditCoupling when edge is clicked', async () => {
    render(() => (
      <CouplingGraph
        esmFile={mockEsmFile}
        onEditCoupling={mockOnEditCoupling}
        interactive={true}
        width={800}
        height={600}
      />
    ));

    // Find and click an edge
    const edge = screen.getByRole('img', { hidden: true }).querySelector('.edge-operator_compose');
    expect(edge).toBeInTheDocument();

    fireEvent.click(edge!);

    expect(mockOnEditCoupling).toHaveBeenCalled();
    const [coupling, edgeId] = mockOnEditCoupling.mock.calls[0];
    expect(coupling.type).toBe('operator_compose');
    expect(coupling.systems).toEqual(['Transport', 'Chemistry']);
  });

  it('shows component details panel when node is selected', async () => {
    render(() => (
      <CouplingGraph
        esmFile={mockEsmFile}
        interactive={true}
        width={800}
        height={600}
      />
    ));

    // Click a node to select it
    const transportNode = screen.getByText('Transport').closest('.node');
    fireEvent.click(transportNode!);

    // Wait for details panel to appear
    await waitFor(() => {
      expect(screen.getByText('Transport')).toBeInTheDocument(); // In details panel
      expect(screen.getByText('model')).toBeInTheDocument(); // Component type
      expect(screen.getByText('3D transport model')).toBeInTheDocument(); // Description
    });
  });

  it('closes details panel when close button is clicked', async () => {
    render(() => (
      <CouplingGraph
        esmFile={mockEsmFile}
        interactive={true}
        width={800}
        height={600}
      />
    ));

    // Click a node to select it
    const transportNode = screen.getByText('Transport').closest('.node');
    fireEvent.click(transportNode!);

    // Wait for details panel to appear
    await waitFor(() => {
      expect(screen.getByText('3D transport model')).toBeInTheDocument();
    });

    // Click close button
    const closeButton = screen.getByText('×');
    fireEvent.click(closeButton);

    // Details panel should disappear
    await waitFor(() => {
      expect(screen.queryByText('3D transport model')).not.toBeInTheDocument();
    });
  });

  it('handles empty ESM file gracefully', () => {
    const emptyEsmFile: EsmFile = {
      esm: '0.1.0',
      metadata: {
        name: 'Empty',
        authors: []
      }
    };

    render(() => (
      <CouplingGraph
        esmFile={emptyEsmFile}
        width={800}
        height={600}
      />
    ));

    // Should render SVG without errors
    expect(screen.getByRole('img', { hidden: true })).toBeInTheDocument();
  });

  it('applies correct CSS classes based on component types', () => {
    render(() => (
      <CouplingGraph
        esmFile={mockEsmFile}
        width={800}
        height={600}
      />
    ));

    const svg = screen.getByRole('img', { hidden: true });

    // Check node type classes
    expect(svg.querySelector('.node-model')).toBeInTheDocument();
    expect(svg.querySelector('.node-reaction_system')).toBeInTheDocument();
    expect(svg.querySelector('.node-data_loader')).toBeInTheDocument();
    expect(svg.querySelector('.node-operator')).toBeInTheDocument();

    // Check edge type classes
    expect(svg.querySelector('.edge-operator_compose')).toBeInTheDocument();
    expect(svg.querySelector('.edge-variable_map')).toBeInTheDocument();
    expect(svg.querySelector('.edge-operator_apply')).toBeInTheDocument();
  });

  it('uses default dimensions when width/height not provided', () => {
    render(() => (
      <CouplingGraph esmFile={mockEsmFile} />
    ));

    const svg = screen.getByRole('img', { hidden: true });
    expect(svg).toHaveAttribute('width', '800'); // Default width
    expect(svg).toHaveAttribute('height', '600'); // Default height
  });

  it('disables interaction when interactive=false', () => {
    render(() => (
      <CouplingGraph
        esmFile={mockEsmFile}
        onSelectComponent={mockOnSelectComponent}
        interactive={false}
        width={800}
        height={600}
      />
    ));

    // Click a node - should not call callback
    const transportNode = screen.getByText('Transport').closest('.node');
    fireEvent.click(transportNode!);

    expect(mockOnSelectComponent).not.toHaveBeenCalled();
  });
});