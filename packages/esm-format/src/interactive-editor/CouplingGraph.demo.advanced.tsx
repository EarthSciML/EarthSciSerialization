/**
 * Advanced CouplingGraph Demo
 *
 * Demonstrates all the advanced features of the CouplingGraph component:
 * - Multiple layout algorithms
 * - Zoom and pan functionality
 * - Multi-select with Ctrl/Cmd key
 * - Export functionality (SVG/PNG)
 * - Filtering by component types and coupling types
 * - Search functionality
 * - Analysis overlays (circular dependencies, critical path)
 * - Minimap navigation
 * - Real-time statistics
 */

import { Component, createSignal, For } from 'solid-js';
import { CouplingGraph } from './CouplingGraph.tsx';
import type { EsmFile } from '../types.js';
import type { ComponentNode } from '../graph.js';

const advancedDemoEsmFile: EsmFile = {
  esm: '0.1.0',
  metadata: {
    name: 'Advanced Atmospheric Chemistry System',
    description: 'Complex multi-scale atmospheric chemistry model with transport, chemistry, and emissions',
    authors: ['Demo Author'],
    version: '2.0.0'
  },
  models: {
    'Transport3D': {
      reference: { notes: 'High-resolution 3D transport model with advection and diffusion' },
      variables: {
        u_wind: { type: 'parameter', units: 'm/s', default: 5.0 },
        v_wind: { type: 'parameter', units: 'm/s', default: 3.0 },
        w_wind: { type: 'parameter', units: 'm/s', default: 0.1 }
      },
      equations: []
    },
    'ChemistryKinetics': {
      reference: { notes: 'Detailed chemical kinetics with 200+ species and 500+ reactions' },
      variables: {
        temperature: { type: 'state', units: 'K', default: 298.15 },
        pressure: { type: 'state', units: 'Pa', default: 101325 }
      },
      equations: []
    },
    'Photolysis': {
      reference: { notes: 'Photolysis rate calculations based on solar zenith angle and aerosols' },
      variables: {
        solar_zenith: { type: 'parameter', units: 'rad', default: 0.5 },
        j_no2: { type: 'state', units: '1/s', default: 1e-3 }
      },
      equations: []
    },
    'Emissions': {
      reference: { notes: 'Anthropogenic and biogenic emissions with temporal variability' },
      variables: {
        nox_emissions: { type: 'parameter', units: 'kg/m2/s', default: 1e-8 },
        voc_emissions: { type: 'parameter', units: 'kg/m2/s', default: 5e-9 }
      },
      equations: []
    }
  },
  reaction_systems: {
    'TroposphericChemistry': {
      species: {
        'O3': { units: 'mol/mol', default: 40e-9 },
        'NO': { units: 'mol/mol', default: 1e-9 },
        'NO2': { units: 'mol/mol', default: 2e-9 },
        'OH': { units: 'mol/mol', default: 1e-12 }
      },
      reactions: []
    },
    'AerosolChemistry': {
      species: {
        'SO4': { units: 'µg/m3', default: 5.0 },
        'NH4': { units: 'µg/m3', default: 2.0 },
        'NO3': { units: 'µg/m3', default: 3.0 }
      },
      reactions: []
    }
  },
  data_loaders: {
    'MeteoData': {
      type: 'netcdf',
      path: '/data/meteo/ECMWF_reanalysis.nc',
      variables: ['temperature', 'pressure', 'wind_u', 'wind_v']
    },
    'EmissionInventory': {
      type: 'netcdf',
      path: '/data/emissions/CAMS_global.nc',
      variables: ['nox', 'co', 'voc', 'so2']
    },
    'SatelliteData': {
      type: 'netcdf',
      path: '/data/satellite/OMI_NO2.nc',
      variables: ['tropospheric_no2_column']
    }
  },
  operators: {
    'AdvectionScheme': {
      type: 'spatial',
      config: { method: 'upstream', order: 3 }
    },
    'DiffusionSolver': {
      type: 'spatial',
      config: { method: 'implicit_euler', timestep: 300 }
    },
    'ChemicalSolver': {
      type: 'temporal',
      config: { method: 'rosenbrock', tolerance: 1e-6 }
    }
  },
  coupling: [
    {
      type: 'operator_compose',
      systems: ['Transport3D', 'ChemistryKinetics'],
      description: 'Couple transport with chemistry using operator splitting'
    },
    {
      type: 'variable_map',
      from: 'MeteoData.temperature',
      to: 'ChemistryKinetics.temperature',
      description: 'Map meteorological temperature to chemistry model'
    },
    {
      type: 'variable_map',
      from: 'MeteoData.pressure',
      to: 'ChemistryKinetics.pressure',
      description: 'Map meteorological pressure to chemistry model'
    },
    {
      type: 'variable_map',
      from: 'EmissionInventory.nox',
      to: 'Emissions.nox_emissions',
      description: 'Map emission inventory NOx to emissions model'
    },
    {
      type: 'operator_apply',
      operator: 'AdvectionScheme',
      system: 'Transport3D',
      description: 'Apply advection scheme to transport model'
    },
    {
      type: 'operator_apply',
      operator: 'DiffusionSolver',
      system: 'Transport3D',
      description: 'Apply diffusion solver to transport model'
    },
    {
      type: 'operator_apply',
      operator: 'ChemicalSolver',
      system: 'ChemistryKinetics',
      description: 'Apply chemical solver to chemistry model'
    },
    {
      type: 'couple2',
      systems: ['Photolysis', 'ChemistryKinetics'],
      description: 'Bidirectional coupling between photolysis and chemistry'
    },
    {
      type: 'variable_map',
      from: 'Emissions.nox_emissions',
      to: 'Transport3D.source_nox',
      description: 'Map NOx emissions as source term in transport'
    },
    // This creates a circular dependency for demonstration
    {
      type: 'variable_map',
      from: 'ChemistryKinetics.temperature',
      to: 'Transport3D.air_density',
      description: 'Temperature affects air density in transport'
    }
  ]
};

export const AdvancedCouplingGraphDemo: Component = () => {
  // State for demo controls
  const [layoutAlgorithm, setLayoutAlgorithm] = createSignal<'force-directed' | 'hierarchical' | 'circular' | 'grid'>('force-directed');
  const [showCircularDeps, setShowCircularDeps] = createSignal(true);
  const [showCriticalPath, setShowCriticalPath] = createSignal(false);
  const [searchTerm, setSearchTerm] = createSignal('');
  const [selectedComponentTypes, setSelectedComponentTypes] = createSignal<ComponentNode['type'][]>([]);
  const [selectedCouplingTypes, setSelectedCouplingTypes] = createSignal<string[]>([]);
  const [exportMessage, setExportMessage] = createSignal('');

  const handleExport = (format: 'svg' | 'png' | 'pdf', data: string) => {
    setExportMessage(`Exported as ${format.toUpperCase()}! Data length: ${data.length} characters`);
    setTimeout(() => setExportMessage(''), 3000);
  };

  const handleSelectComponent = (componentId: string) => {
    console.log('Selected component:', componentId);
  };

  const handleEditCoupling = (coupling: any, edgeId: string) => {
    console.log('Edit coupling:', coupling, edgeId);
  };

  const componentTypes: ComponentNode['type'][] = ['model', 'reaction_system', 'data_loader', 'operator'];
  const couplingTypes = ['operator_compose', 'couple2', 'variable_map', 'operator_apply', 'callback'];

  return (
    <div style={{ width: '100%', height: '100vh', display: 'flex', 'flex-direction': 'column' }}>
      <div style={{
        padding: '16px',
        background: '#f8f9fa',
        border: '1px solid #e0e0e0',
        display: 'flex',
        'flex-wrap': 'wrap',
        gap: '16px',
        'align-items': 'center'
      }}>
        <h2 style={{ margin: '0', color: '#333' }}>Advanced CouplingGraph Demo</h2>

        <div style={{ display: 'flex', gap: '8px', 'align-items': 'center' }}>
          <label>Layout:</label>
          <select
            value={layoutAlgorithm()}
            onInput={(e) => setLayoutAlgorithm(e.target.value as any)}
            style={{ padding: '4px 8px' }}
          >
            <option value="force-directed">Force Directed</option>
            <option value="hierarchical">Hierarchical</option>
            <option value="circular">Circular</option>
            <option value="grid">Grid</option>
          </select>
        </div>

        <div style={{ display: 'flex', gap: '8px', 'align-items': 'center' }}>
          <label>Search:</label>
          <input
            type="text"
            value={searchTerm()}
            onInput={(e) => setSearchTerm(e.target.value)}
            placeholder="Search components..."
            style={{ padding: '4px 8px', width: '150px' }}
          />
        </div>

        <div style={{ display: 'flex', gap: '8px', 'align-items': 'center' }}>
          <label>Analysis:</label>
          <label>
            <input
              type="checkbox"
              checked={showCircularDeps()}
              onChange={(e) => setShowCircularDeps(e.target.checked)}
            />
            Circular Deps
          </label>
          <label>
            <input
              type="checkbox"
              checked={showCriticalPath()}
              onChange={(e) => setShowCriticalPath(e.target.checked)}
            />
            Critical Path
          </label>
        </div>

        <div style={{ color: '#007acc', 'font-weight': 'bold' }}>
          {exportMessage()}
        </div>
      </div>

      <div style={{ display: 'flex', gap: '16px', padding: '16px', 'flex-wrap': 'wrap' }}>
        <div style={{ display: 'flex', 'flex-direction': 'column', gap: '8px' }}>
          <label style={{ 'font-weight': 'bold' }}>Component Types:</label>
          <For each={componentTypes}>
            {(type) => (
              <label style={{ display: 'flex', gap: '4px', 'align-items': 'center' }}>
                <input
                  type="checkbox"
                  checked={selectedComponentTypes().length === 0 || selectedComponentTypes().includes(type)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      if (selectedComponentTypes().length === componentTypes.length - 1) {
                        setSelectedComponentTypes([]);  // If checking the last unchecked, show all
                      } else {
                        setSelectedComponentTypes([...selectedComponentTypes(), type]);
                      }
                    } else {
                      setSelectedComponentTypes(selectedComponentTypes().filter(t => t !== type));
                    }
                  }}
                />
                {type.replace('_', ' ')}
              </label>
            )}
          </For>
        </div>

        <div style={{ display: 'flex', 'flex-direction': 'column', gap: '8px' }}>
          <label style={{ 'font-weight': 'bold' }}>Coupling Types:</label>
          <For each={couplingTypes}>
            {(type) => (
              <label style={{ display: 'flex', gap: '4px', 'align-items': 'center' }}>
                <input
                  type="checkbox"
                  checked={selectedCouplingTypes().length === 0 || selectedCouplingTypes().includes(type)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      if (selectedCouplingTypes().length === couplingTypes.length - 1) {
                        setSelectedCouplingTypes([]);  // If checking the last unchecked, show all
                      } else {
                        setSelectedCouplingTypes([...selectedCouplingTypes(), type]);
                      }
                    } else {
                      setSelectedCouplingTypes(selectedCouplingTypes().filter(t => t !== type));
                    }
                  }}
                />
                {type.replace('_', ' ')}
              </label>
            )}
          </For>
        </div>
      </div>

      <div style={{ flex: '1', position: 'relative' }}>
        <CouplingGraph
          esmFile={advancedDemoEsmFile}
          width={1200}
          height={800}
          interactive={true}
          layoutAlgorithm={layoutAlgorithm()}
          onExport={handleExport}
          onSelectComponent={handleSelectComponent}
          onEditCoupling={handleEditCoupling}
          filters={{
            componentTypes: selectedComponentTypes().length > 0 ? selectedComponentTypes() : undefined,
            couplingTypes: selectedCouplingTypes().length > 0 ? selectedCouplingTypes() : undefined,
            searchTerm: searchTerm() || undefined
          }}
          showAnalysis={{
            circularDependencies: showCircularDeps(),
            criticalPath: showCriticalPath()
          }}
        />
      </div>

      <div style={{
        padding: '16px',
        background: '#f8f9fa',
        border: '1px solid #e0e0e0',
        'font-size': '14px'
      }}>
        <strong>Features demonstrated:</strong>
        <ul style={{ margin: '8px 0', 'padding-left': '20px' }}>
          <li><strong>Multiple layouts:</strong> Force-directed, hierarchical, circular, grid</li>
          <li><strong>Zoom & pan:</strong> Mouse wheel to zoom, drag to pan, reset button</li>
          <li><strong>Multi-select:</strong> Ctrl/Cmd+click to select multiple nodes</li>
          <li><strong>Export:</strong> SVG and PNG export via toolbar buttons</li>
          <li><strong>Filtering:</strong> Filter by component types, coupling types, and search term</li>
          <li><strong>Analysis:</strong> Circular dependency detection and critical path analysis</li>
          <li><strong>Minimap:</strong> Navigate large graphs with the minimap (bottom-right)</li>
          <li><strong>Statistics:</strong> Real-time graph statistics (bottom-left)</li>
        </ul>
      </div>
    </div>
  );
};

export default AdvancedCouplingGraphDemo;