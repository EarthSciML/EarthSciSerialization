/**
 * CouplingGraph Demo
 *
 * Interactive demo showcasing the CouplingGraph component with a sample
 * atmospheric chemistry system. Demonstrates visual coupling relationships
 * and interactive features.
 */

import { Component, createSignal } from 'solid-js';
import { CouplingGraph } from './CouplingGraph.tsx';
import type { EsmFile, CouplingEntry } from '../types.js';

// Sample atmospheric chemistry system for demonstration
const sampleEsmFile: EsmFile = {
  esm: '0.1.0',
  metadata: {
    name: 'Atmospheric Chemistry Demo',
    description: 'Sample ESM file demonstrating coupling graph visualization',
    authors: ['ESM Format Team'],
    created: new Date().toISOString()
  },
  models: {
    'AtmosphericTransport': {
      reference: {
        notes: '3D atmospheric transport model with advection and diffusion',
        doi: '10.1000/example.transport'
      },
      variables: {
        u_wind: { type: 'parameter', units: 'm/s', default: 5.0, description: 'Zonal wind velocity' },
        v_wind: { type: 'parameter', units: 'm/s', default: 2.0, description: 'Meridional wind velocity' },
        w_wind: { type: 'parameter', units: 'm/s', default: 0.1, description: 'Vertical wind velocity' },
        Kh: { type: 'parameter', units: 'm^2/s', default: 1000.0, description: 'Horizontal diffusivity' }
      },
      equations: [
        {
          lhs: { op: 'derivative', args: ['c', 't'] },
          rhs: {
            op: '+',
            args: [
              { op: '*', args: [{ op: '-', args: ['u_wind'] }, { op: 'derivative', args: ['c', 'x'] }] },
              { op: '*', args: ['Kh', { op: 'derivative', args: ['c', 'x', 'x'] }] }
            ]
          }
        }
      ]
    },
    'BoundaryLayer': {
      reference: { notes: 'Planetary boundary layer parameterization' },
      variables: {
        h_pbl: { type: 'state', units: 'm', default: 1000.0, description: 'PBL height' },
        ustar: { type: 'parameter', units: 'm/s', default: 0.3, description: 'Friction velocity' }
      },
      equations: []
    }
  },
  reaction_systems: {
    'TroposphericChemistry': {
      reference: {
        notes: 'Tropospheric ozone chemistry mechanism',
        citation: 'Seinfeld & Pandis (2016)'
      },
      species: {
        O3: { units: 'mol/mol', default: 40e-9, description: 'Ozone' },
        NO: { units: 'mol/mol', default: 0.1e-9, description: 'Nitric oxide' },
        NO2: { units: 'mol/mol', default: 1.0e-9, description: 'Nitrogen dioxide' },
        CO: { units: 'mol/mol', default: 100e-9, description: 'Carbon monoxide' }
      },
      parameters: {
        T: { units: 'K', default: 298.15, description: 'Temperature' },
        P: { units: 'Pa', default: 101325.0, description: 'Pressure' },
        jNO2: { units: '1/s', default: 0.005, description: 'NO2 photolysis rate' }
      },
      reactions: [
        {
          id: 'R1',
          substrates: [{ species: 'NO', stoichiometry: 1 }, { species: 'O3', stoichiometry: 1 }],
          products: [{ species: 'NO2', stoichiometry: 1 }],
          rate: { op: '*', args: [1.8e-12, { op: 'exp', args: [{ op: '/', args: [-1370, 'T'] }] }] }
        },
        {
          id: 'R2',
          substrates: [{ species: 'NO2', stoichiometry: 1 }],
          products: [{ species: 'NO', stoichiometry: 1 }, { species: 'O3', stoichiometry: 1 }],
          rate: 'jNO2'
        }
      ]
    },
    'StratosphericChemistry': {
      reference: { notes: 'Simplified stratospheric ozone chemistry' },
      species: {
        O3: { units: 'mol/mol', default: 8e-6, description: 'Stratospheric ozone' },
        ClO: { units: 'mol/mol', default: 1e-9, description: 'Chlorine monoxide' }
      },
      reactions: []
    }
  },
  data_loaders: {
    'GEOS-FP_Meteorology': {
      type: 'netcdf',
      path: '/data/GEOS-FP/{{YYYY}}/{{MM}}/GEOSFP.{{YYYYMMDD}}.A3dyn.nc',
      variables: ['T', 'U', 'V', 'OMEGA'],
      reference: { notes: 'GEOS Forward Processing meteorological data' }
    },
    'EmissionInventory': {
      type: 'netcdf',
      path: '/data/emissions/NEI2017_{{MM}}.nc',
      variables: ['E_NO', 'E_CO', 'E_VOC'],
      reference: { notes: '2017 National Emissions Inventory' }
    },
    'SatelliteObservations': {
      type: 'hdf5',
      path: '/data/satellite/OMI_{{YYYYMMDD}}.h5',
      variables: ['NO2_column', 'O3_column'],
      reference: { notes: 'OMI satellite observations' }
    }
  },
  operators: {
    'GriddedInterpolation': {
      type: 'spatial',
      config: { method: 'bilinear', extrapolate: false },
      reference: { notes: 'Spatial interpolation between grids' }
    },
    'ChemicalIntegrator': {
      type: 'numerical',
      config: { solver: 'rosenbrock', rtol: 1e-3, atol: 1e-12 },
      reference: { notes: 'Chemical kinetics integration' }
    },
    'VerticalMixing': {
      type: 'physical',
      config: { scheme: 'K-profile' },
      reference: { notes: 'Vertical mixing in boundary layer' }
    }
  },
  coupling: [
    {
      type: 'operator_compose',
      systems: ['AtmosphericTransport', 'TroposphericChemistry'],
      description: 'Couple transport with tropospheric chemistry'
    },
    {
      type: 'operator_compose',
      systems: ['AtmosphericTransport', 'StratosphericChemistry'],
      description: 'Couple transport with stratospheric chemistry'
    },
    {
      type: 'variable_map',
      from: 'GEOS-FP_Meteorology.T',
      to: 'TroposphericChemistry.T',
      description: 'Temperature from meteorological data'
    },
    {
      type: 'variable_map',
      from: 'GEOS-FP_Meteorology.U',
      to: 'AtmosphericTransport.u_wind',
      description: 'Zonal wind component'
    },
    {
      type: 'variable_map',
      from: 'GEOS-FP_Meteorology.V',
      to: 'AtmosphericTransport.v_wind',
      description: 'Meridional wind component'
    },
    {
      type: 'variable_map',
      from: 'EmissionInventory.E_NO',
      to: 'TroposphericChemistry.E_NO_surface',
      description: 'Surface NO emissions'
    },
    {
      type: 'operator_apply',
      operator: 'GriddedInterpolation',
      system: 'GEOS-FP_Meteorology',
      description: 'Interpolate meteorological fields to model grid'
    },
    {
      type: 'operator_apply',
      operator: 'ChemicalIntegrator',
      system: 'TroposphericChemistry',
      description: 'Integrate chemical kinetics'
    },
    {
      type: 'operator_apply',
      operator: 'VerticalMixing',
      system: 'BoundaryLayer',
      description: 'Apply vertical mixing in boundary layer'
    },
    {
      type: 'couple2',
      systems: ['TroposphericChemistry', 'StratosphericChemistry'],
      description: 'Exchange species between troposphere and stratosphere'
    }
  ]
};

export const CouplingGraphDemo: Component = () => {
  const [selectedComponent, setSelectedComponent] = createSignal<string | null>(null);
  const [editingCoupling, setEditingCoupling] = createSignal<{ coupling: CouplingEntry, edgeId: string } | null>(null);
  const [logMessages, setLogMessages] = createSignal<string[]>([]);

  const addLogMessage = (message: string) => {
    setLogMessages(prev => [...prev.slice(-9), message]); // Keep last 10 messages
  };

  const handleSelectComponent = (componentId: string) => {
    setSelectedComponent(componentId);
    addLogMessage(`Selected component: ${componentId}`);
  };

  const handleEditCoupling = (coupling: CouplingEntry, edgeId: string) => {
    setEditingCoupling({ coupling, edgeId });
    addLogMessage(`Edit coupling: ${coupling.type} (${edgeId})`);
  };

  const closeCouplingEditor = () => {
    setEditingCoupling(null);
    addLogMessage('Closed coupling editor');
  };

  return (
    <div style={{ padding: '20px', font: '14px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif' }}>
      <h1 style={{ margin: '0 0 20px 0', color: '#333' }}>CouplingGraph Demo</h1>
      <p style={{ margin: '0 0 20px 0', color: '#666', 'line-height': '1.5' }}>
        Interactive visualization of ESM coupling relationships. Click nodes to select components,
        click edges to edit coupling rules, drag nodes to reposition.
      </p>

      <div style={{ border: '1px solid #ddd', 'border-radius': '8px', overflow: 'hidden' }}>
        <CouplingGraph
          esmFile={sampleEsmFile}
          onSelectComponent={handleSelectComponent}
          onEditCoupling={handleEditCoupling}
          width={1000}
          height={700}
          interactive={true}
        />
      </div>

      {/* Component Selection Info */}
      <div style={{ margin: '20px 0', display: 'grid', 'grid-template-columns': '1fr 1fr', gap: '20px' }}>
        <div>
          <h3 style={{ margin: '0 0 10px 0', color: '#333' }}>Selected Component</h3>
          <div style={{
            padding: '12px',
            background: selectedComponent() ? '#f0f9ff' : '#f8f9fa',
            border: '1px solid ' + (selectedComponent() ? '#0078d4' : '#dee2e6'),
            'border-radius': '6px',
            'min-height': '60px'
          }}>
            {selectedComponent() ? (
              <div>
                <strong>{selectedComponent()}</strong>
                <p style={{ margin: '5px 0 0 0', 'font-size': '12px', color: '#666' }}>
                  Click a node in the graph to select a component
                </p>
              </div>
            ) : (
              <p style={{ margin: 0, color: '#666' }}>No component selected</p>
            )}
          </div>
        </div>

        <div>
          <h3 style={{ margin: '0 0 10px 0', color: '#333' }}>Activity Log</h3>
          <div style={{
            padding: '12px',
            background: '#f8f9fa',
            border: '1px solid #dee2e6',
            'border-radius': '6px',
            'min-height': '60px',
            'max-height': '120px',
            'overflow-y': 'auto'
          }}>
            {logMessages().length > 0 ? (
              <div style={{ 'font-family': 'monospace', 'font-size': '11px' }}>
                {logMessages().map((msg, i) => (
                  <div key={i} style={{ margin: '2px 0', color: '#555' }}>{msg}</div>
                ))}
              </div>
            ) : (
              <p style={{ margin: 0, color: '#666' }}>No activity yet</p>
            )}
          </div>
        </div>
      </div>

      {/* Coupling Editor Modal */}
      {editingCoupling() && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          'align-items': 'center',
          'justify-content': 'center',
          'z-index': 1000
        }}>
          <div style={{
            background: 'white',
            padding: '24px',
            'border-radius': '12px',
            'box-shadow': '0 8px 32px rgba(0, 0, 0, 0.2)',
            'max-width': '500px',
            'max-height': '80vh',
            'overflow-y': 'auto'
          }}>
            <h3 style={{ margin: '0 0 16px 0', color: '#333' }}>Edit Coupling Rule</h3>

            <div style={{ margin: '12px 0' }}>
              <strong>Type:</strong> {editingCoupling()!.coupling.type}
            </div>

            <div style={{ margin: '12px 0' }}>
              <strong>Description:</strong> {editingCoupling()!.coupling.description || 'No description'}
            </div>

            <div style={{ margin: '12px 0' }}>
              <strong>Configuration:</strong>
              <pre style={{
                background: '#f8f9fa',
                padding: '8px',
                'border-radius': '4px',
                'font-size': '12px',
                'white-space': 'pre-wrap',
                'overflow-x': 'auto',
                margin: '8px 0 0 0'
              }}>
                {JSON.stringify(editingCoupling()!.coupling, null, 2)}
              </pre>
            </div>

            <div style={{ margin: '20px 0 0 0', 'text-align': 'right' }}>
              <button
                onClick={closeCouplingEditor}
                style={{
                  background: '#0078d4',
                  color: 'white',
                  border: 'none',
                  padding: '8px 16px',
                  'border-radius': '6px',
                  cursor: 'pointer',
                  'font-size': '14px'
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* System Summary */}
      <div style={{ margin: '30px 0 0 0' }}>
        <h3 style={{ margin: '0 0 15px 0', color: '#333' }}>System Summary</h3>
        <div style={{ display: 'grid', 'grid-template-columns': 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
          <div style={{ padding: '12px', background: '#e6f3ff', 'border-radius': '6px' }}>
            <strong style={{ color: '#0078d4' }}>Models: {Object.keys(sampleEsmFile.models || {}).length}</strong>
            <ul style={{ margin: '8px 0 0 0', 'padding-left': '20px', 'font-size': '13px' }}>
              {Object.keys(sampleEsmFile.models || {}).map(name => (
                <li key={name}>{name}</li>
              ))}
            </ul>
          </div>

          <div style={{ padding: '12px', background: '#fff0e6', 'border-radius': '6px' }}>
            <strong style={{ color: '#ca5010' }}>Reaction Systems: {Object.keys(sampleEsmFile.reaction_systems || {}).length}</strong>
            <ul style={{ margin: '8px 0 0 0', 'padding-left': '20px', 'font-size': '13px' }}>
              {Object.keys(sampleEsmFile.reaction_systems || {}).map(name => (
                <li key={name}>{name}</li>
              ))}
            </ul>
          </div>

          <div style={{ padding: '12px', background: '#f0f9e6', 'border-radius': '6px' }}>
            <strong style={{ color: '#498205' }}>Data Loaders: {Object.keys(sampleEsmFile.data_loaders || {}).length}</strong>
            <ul style={{ margin: '8px 0 0 0', 'padding-left': '20px', 'font-size': '13px' }}>
              {Object.keys(sampleEsmFile.data_loaders || {}).map(name => (
                <li key={name}>{name}</li>
              ))}
            </ul>
          </div>

          <div style={{ padding: '12px', background: '#f9e6ff', 'border-radius': '6px' }}>
            <strong style={{ color: '#881798' }}>Operators: {Object.keys(sampleEsmFile.operators || {}).length}</strong>
            <ul style={{ margin: '8px 0 0 0', 'padding-left': '20px', 'font-size': '13px' }}>
              {Object.keys(sampleEsmFile.operators || {}).map(name => (
                <li key={name}>{name}</li>
              ))}
            </ul>
          </div>
        </div>

        <div style={{ margin: '15px 0 0 0', padding: '12px', background: '#f8f9fa', 'border-radius': '6px' }}>
          <strong>Coupling Rules: {sampleEsmFile.coupling?.length || 0}</strong>
          <p style={{ margin: '8px 0 0 0', 'font-size': '13px', color: '#666' }}>
            Click on graph edges to inspect and edit coupling configurations
          </p>
        </div>
      </div>
    </div>
  );
};