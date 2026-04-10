/**
 * Web Components Demo - Comprehensive showcase of all ESM web components
 *
 * This demo provides interactive examples of all web components with
 * realistic data and use cases, demonstrating the framework-agnostic
 * nature of the components.
 */

import { Component, createSignal, Show, For } from 'solid-js';
import type { EsmFile, Model, ValidationError } from '../types.js';
import { ValidationPanel } from '../interactive-editor/ValidationPanel.tsx';
import { FileSummary } from '../interactive-editor/FileSummary.tsx';
import { SimulationControls } from '../interactive-editor/SimulationControls.tsx';
import { ModelEditor } from '../interactive-editor/ModelEditor.tsx';
import { CouplingGraph } from '../interactive-editor/CouplingGraph.tsx';
import { ExpressionNode } from '../interactive-editor/ExpressionNode.tsx';

// Sample data for demonstrations
const sampleModel: Model = {
  name: "atmospheric_chemistry",
  type: "model",
  description: "Basic atmospheric chemistry model with O3 photolysis",
  variables: {
    "O3": {
      type: "state_variable",
      units: "molecules/cm³",
      description: "Ozone concentration"
    },
    "NO": {
      type: "state_variable",
      units: "molecules/cm³",
      description: "Nitric oxide concentration"
    },
    "NO2": {
      type: "state_variable",
      units: "molecules/cm³",
      description: "Nitrogen dioxide concentration"
    },
    "j_O3": {
      type: "parameter",
      units: "1/s",
      description: "O3 photolysis rate"
    },
    "k_NO_O3": {
      type: "parameter",
      units: "cm³/molecules/s",
      description: "Rate constant for NO + O3 reaction"
    }
  },
  equations: [
    {
      variable: "O3",
      expression: {
        op: "-",
        args: [
          { op: "*", args: ["j_O3", "O3"] },
          { op: "*", args: [{ op: "*", args: ["k_NO_O3", "NO"] }, "O3"] }
        ]
      }
    },
    {
      variable: "NO",
      expression: {
        op: "-",
        args: [
          "NO",
          { op: "*", args: [{ op: "*", args: ["k_NO_O3", "NO"] }, "O3"] }
        ]
      }
    },
    {
      variable: "NO2",
      expression: {
        op: "*",
        args: [{ op: "*", args: ["k_NO_O3", "NO"] }, "O3"]
      }
    }
  ]
};

const sampleEsmFile: EsmFile = {
  version: "1.0",
  metadata: {
    name: "Atmospheric Chemistry Simulation",
    description: "Multi-component atmospheric chemistry model",
    author: "EarthSciML Team",
    created: "2024-02-15"
  },
  components: [
    sampleModel,
    {
      name: "emissions_data",
      type: "data_loader",
      description: "Emission source data loader",
      source: {
        type: "csv",
        path: "/data/emissions.csv"
      },
      variables: {
        "emission_rate": {
          type: "observed_variable",
          units: "molecules/cm³/s"
        }
      }
    },
    {
      name: "meteorology",
      type: "data_loader",
      description: "Meteorological data loader",
      source: {
        type: "netcdf",
        path: "/data/meteo.nc"
      },
      variables: {
        "temperature": {
          type: "observed_variable",
          units: "K"
        },
        "pressure": {
          type: "observed_variable",
          units: "Pa"
        }
      }
    }
  ],
  coupling: [
    {
      type: "variable_coupling",
      output_component: "emissions_data",
      output_variable: "emission_rate",
      input_component: "atmospheric_chemistry",
      input_variable: "source_NO",
      transform: {
        op: "*",
        args: ["emission_rate", 0.8]
      }
    },
    {
      type: "variable_coupling",
      output_component: "meteorology",
      output_variable: "temperature",
      input_component: "atmospheric_chemistry",
      input_variable: "temperature"
    }
  ]
};

const sampleValidationErrors: ValidationError[] = [
  {
    id: "missing_units",
    type: "semantic",
    message: "Variable 'temperature' is missing units specification",
    path: ["components", "0", "variables", "temperature"],
    severity: "warning",
    suggestion: "Add units field to variable definition"
  },
  {
    id: "undefined_variable",
    type: "reference",
    message: "Referenced variable 'source_NO' is not defined in model",
    path: ["components", "0", "equations", "0"],
    severity: "error",
    description: "The equation references a variable that doesn't exist in the model's variable definitions",
    code: "UNDEFINED_VARIABLE"
  }
];

export const WebComponentsDemo: Component = () => {
  const [selectedTab, setSelectedTab] = createSignal<string>('overview');
  const [modelEditState, setModelEditState] = createSignal(sampleModel);
  const [simulationRunning, setSimulationRunning] = createSignal(false);
  const [simulationProgress, setSimulationProgress] = createSignal(0);
  const [selectedComponent, setSelectedComponent] = createSignal<string | null>(null);

  const tabs = [
    { id: 'overview', label: 'Overview', icon: '📋' },
    { id: 'validation', label: 'Validation', icon: '✅' },
    { id: 'editor', label: 'Model Editor', icon: '✏️' },
    { id: 'graph', label: 'Coupling Graph', icon: '🔗' },
    { id: 'simulation', label: 'Simulation', icon: '⚡' },
    { id: 'expression', label: 'Expression Node', icon: '🧮' }
  ];

  const handleModelChange = (updatedModel: Model) => {
    setModelEditState(updatedModel);
  };

  const handleStartSimulation = () => {
    setSimulationRunning(true);
    setSimulationProgress(0);

    // Simulate progress
    const interval = setInterval(() => {
      setSimulationProgress(prev => {
        if (prev >= 100) {
          setSimulationRunning(false);
          clearInterval(interval);
          return 100;
        }
        return prev + 2;
      });
    }, 100);
  };

  const handleStopSimulation = () => {
    setSimulationRunning(false);
    setSimulationProgress(0);
  };

  return (
    <div class="web-components-demo">
      <div class="demo-header">
        <h1>ESM Web Components Demo</h1>
        <p>Interactive showcase of all ESM format web components with realistic data</p>
      </div>

      <div class="demo-tabs">
        <For each={tabs}>
          {(tab) => (
            <button
              class={`demo-tab ${selectedTab() === tab.id ? 'active' : ''}`}
              onClick={() => setSelectedTab(tab.id)}
            >
              <span class="tab-icon">{tab.icon}</span>
              <span class="tab-label">{tab.label}</span>
            </button>
          )}
        </For>
      </div>

      <div class="demo-content">
        <Show when={selectedTab() === 'overview'}>
          <div class="demo-section">
            <h2>📋 File Summary Component</h2>
            <p>High-level overview of ESM file structure and statistics</p>
            <div class="component-showcase">
              <FileSummary
                esmFile={sampleEsmFile}
                showDetails={true}
                showExportOptions={true}
                onComponentTypeClick={(type) => console.log('Component type clicked:', type)}
                onExport={(format) => console.log('Export requested:', format)}
              />
            </div>
          </div>
        </Show>

        <Show when={selectedTab() === 'validation'}>
          <div class="demo-section">
            <h2>✅ Validation Panel Component</h2>
            <p>Display validation errors and warnings with detailed information</p>
            <div class="component-showcase">
              <ValidationPanel
                model={modelEditState()}
                validationErrors={sampleValidationErrors.filter(e => e.severity === 'error')}
                validationWarnings={sampleValidationErrors.filter(e => e.severity === 'warning')}
                showDetails={true}
                onErrorClick={(error) => console.log('Error clicked:', error)}
              />
            </div>
          </div>
        </Show>

        <Show when={selectedTab() === 'editor'}>
          <div class="demo-section">
            <h2>✏️ Model Editor Component</h2>
            <p>Interactive model editing with live validation</p>
            <div class="component-showcase">
              <ModelEditor
                model={modelEditState()}
                onChange={handleModelChange}
                allowEditing={true}
                showValidation={true}
                validationErrors={sampleValidationErrors.map(e => e.message)}
              />
            </div>
          </div>
        </Show>

        <Show when={selectedTab() === 'graph'}>
          <div class="demo-section">
            <h2>🔗 Coupling Graph Component</h2>
            <p>Visual representation of component relationships and data flow</p>
            <div class="component-showcase">
              <CouplingGraph
                esmFile={sampleEsmFile}
                width={800}
                height={600}
                interactive={true}
                onSelectComponent={(id) => setSelectedComponent(id)}
                onEditCoupling={(coupling, edgeId) => console.log('Edit coupling:', coupling, edgeId)}
              />
            </div>
            <Show when={selectedComponent()}>
              <div class="selected-component-info">
                <h4>Selected Component: {selectedComponent()}</h4>
                <button onClick={() => setSelectedComponent(null)}>Clear Selection</button>
              </div>
            </Show>
          </div>
        </Show>

        <Show when={selectedTab() === 'simulation'}>
          <div class="demo-section">
            <h2>⚡ Simulation Controls Component</h2>
            <p>Control simulation execution with parameter adjustment</p>
            <div class="component-showcase">
              <SimulationControls
                esmFile={sampleEsmFile}
                isRunning={simulationRunning()}
                progress={simulationProgress()}
                statusMessage={simulationRunning() ? 'Running simulation...' : 'Ready'}
                availableBackends={['Julia', 'Python', 'C++']}
                selectedBackend="Julia"
                onStartSimulation={handleStartSimulation}
                onStopSimulation={handleStopSimulation}
                onPauseResume={(isPaused) => console.log('Pause/Resume:', isPaused)}
                onParametersChange={(params) => console.log('Parameters changed:', params)}
                onBackendChange={(backend) => console.log('Backend changed:', backend)}
              />
            </div>
          </div>
        </Show>

        <Show when={selectedTab() === 'expression'}>
          <div class="demo-section">
            <h2>🧮 Expression Node Component</h2>
            <p>Interactive mathematical expression rendering</p>
            <div class="component-showcase">
              <div class="expression-examples">
                <h4>Simple Expression:</h4>
                <ExpressionNode
                  expr={{ op: "+", args: [2, 3] }}
                  path={["simple"]}
                  highlightedVars={() => new Set()}
                  allowEditing={true}
                  onHoverVar={(var_name) => console.log('Hover variable:', var_name)}
                  onSelect={(path) => console.log('Selected path:', path)}
                  onReplace={(path, expr) => console.log('Replace at', path, 'with', expr)}
                />

                <h4>Complex Expression:</h4>
                <ExpressionNode
                  expr={{
                    op: "*",
                    args: [
                      { op: "+", args: ["k_NO_O3", { op: "/", args: ["temperature", 298] }] },
                      { op: "*", args: ["NO", "O3"] }
                    ]
                  }}
                  path={["complex"]}
                  highlightedVars={() => new Set(["temperature", "NO"])}
                  allowEditing={true}
                  onHoverVar={(var_name) => console.log('Hover variable:', var_name)}
                  onSelect={(path) => console.log('Selected path:', path)}
                  onReplace={(path, expr) => console.log('Replace at', path, 'with', expr)}
                />

                <h4>Fraction Expression:</h4>
                <ExpressionNode
                  expr={{
                    op: "/",
                    args: [
                      { op: "*", args: ["d_O3", "dt"] },
                      { op: "+", args: ["O3", 1e-10] }
                    ]
                  }}
                  path={["fraction"]}
                  highlightedVars={() => new Set()}
                  allowEditing={true}
                  onHoverVar={(var_name) => console.log('Hover variable:', var_name)}
                  onSelect={(path) => console.log('Selected path:', path)}
                  onReplace={(path, expr) => console.log('Replace at', path, 'with', expr)}
                />
              </div>
            </div>
          </div>
        </Show>
      </div>

      <div class="demo-footer">
        <h3>Web Component Usage Examples</h3>
        <div class="usage-examples">
          <div class="usage-example">
            <h4>HTML Usage:</h4>
            <pre><code>{`<!-- ESM File Summary -->
<esm-file-summary
  esm-file='{"components": [...], "coupling": [...]}'
  show-details="true"
  show-export-options="true">
</esm-file-summary>

<!-- Validation Panel -->
<esm-validation-panel
  model='{"variables": {...}, "equations": [...]}'
  validation-errors='[{"message": "Error", "path": "..."}]'
  show-details="true">
</esm-validation-panel>

<!-- Simulation Controls -->
<esm-simulation-controls
  esm-file='{"components": [...], "coupling": [...]}'
  available-backends='["julia", "python"]'
  is-running="false">
</esm-simulation-controls>`}</code></pre>
          </div>

          <div class="usage-example">
            <h4>React Usage:</h4>
            <pre><code>{`import 'earthsci-toolkit/web-components';

function MyApp() {
  return (
    <div>
      <esm-file-summary
        esm-file={JSON.stringify(myEsmFile)}
        show-details="true"
        onExport={(e) => console.log(e.detail.format)}
      />
    </div>
  );
}`}</code></pre>
          </div>

          <div class="usage-example">
            <h4>Vue Usage:</h4>
            <pre><code>{`<template>
  <div>
    <esm-coupling-graph
      :esm-file="JSON.stringify(esmFile)"
      width="800"
      height="600"
      interactive="true"
      @componentSelect="handleComponentSelect"
    />
  </div>
</template>

<script>
import 'earthsci-toolkit/web-components';

export default {
  methods: {
    handleComponentSelect(event) {
      console.log(event.detail.componentId);
    }
  }
}
</script>`}</code></pre>
          </div>
        </div>
      </div>
    </div>
  );
};

// CSS for demo styling (would typically be in a separate file)
const demoStyles = `
.web-components-demo {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
}

.demo-header {
  text-align: center;
  margin-bottom: 30px;
}

.demo-header h1 {
  color: #1f2937;
  margin-bottom: 10px;
}

.demo-header p {
  color: #6b7280;
  font-size: 16px;
}

.demo-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 30px;
  border-bottom: 2px solid #e5e7eb;
  overflow-x: auto;
}

.demo-tab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border: none;
  background: none;
  cursor: pointer;
  color: #6b7280;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
  white-space: nowrap;
  border-bottom: 3px solid transparent;
}

.demo-tab:hover {
  color: #374151;
  background: #f9fafb;
}

.demo-tab.active {
  color: #3b82f6;
  border-bottom-color: #3b82f6;
}

.demo-section {
  margin-bottom: 40px;
}

.demo-section h2 {
  color: #1f2937;
  margin-bottom: 10px;
}

.demo-section p {
  color: #6b7280;
  margin-bottom: 20px;
}

.component-showcase {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 20px;
  background: #fafafa;
}

.expression-examples {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.expression-examples h4 {
  margin: 0 0 10px;
  color: #374151;
}

.selected-component-info {
  margin-top: 15px;
  padding: 10px;
  background: #dbeafe;
  border-radius: 6px;
}

.demo-footer {
  margin-top: 50px;
  padding-top: 30px;
  border-top: 2px solid #e5e7eb;
}

.usage-examples {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.usage-example {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}

.usage-example h4 {
  margin: 0;
  padding: 12px 16px;
  background: #f3f4f6;
  color: #374151;
  font-size: 14px;
  font-weight: 600;
}

.usage-example pre {
  margin: 0;
  padding: 16px;
  background: #1f2937;
  color: #f9fafb;
  font-size: 13px;
  overflow-x: auto;
}

.usage-example code {
  font-family: 'SF Mono', Monaco, 'Inconsolata', 'Roboto Mono', monospace;
}
`;

// Inject styles
if (typeof document !== 'undefined') {
  const styleEl = document.createElement('style');
  styleEl.textContent = demoStyles;
  document.head.appendChild(styleEl);
}