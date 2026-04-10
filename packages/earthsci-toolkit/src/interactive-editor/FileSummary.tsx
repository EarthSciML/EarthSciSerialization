/**
 * FileSummary Component - Display ESM file overview and statistics
 *
 * Shows high-level information about the ESM file including component counts,
 * coupling statistics, and file metadata.
 */

import { Component, For, Show, createMemo } from 'solid-js';
import type { EsmFile, Model, ReactionSystem, DataLoader } from '../types.js';

export interface FileSummaryProps {
  /** The ESM file to summarize */
  esmFile: EsmFile;

  /** Whether to show detailed statistics */
  showDetails?: boolean;

  /** Whether to show export options */
  showExportOptions?: boolean;

  /** Callback when a component type is clicked for navigation */
  onComponentTypeClick?: (componentType: string) => void;

  /** Callback when export is requested */
  onExport?: (format: 'json' | 'yaml' | 'toml') => void;
}

interface ComponentStatistics {
  models: number;
  reactionSystems: number;
  dataLoaders: number;
  operators: number;
  total: number;
}

interface CouplingStatistics {
  totalCouplings: number;
  uniqueVariables: Set<string>;
  complexCouplings: number; // Couplings with transformations
}

interface FileMetadata {
  version: string;
  totalLines: number;
  variableCount: number;
  equationCount: number;
}

export const FileSummary: Component<FileSummaryProps> = (props) => {
  // Compute component statistics
  const componentStats = createMemo<ComponentStatistics>(() => {
    const components = props.esmFile.components || [];

    const stats = {
      models: 0,
      reactionSystems: 0,
      dataLoaders: 0,
      operators: 0,
      total: components.length
    };

    components.forEach(component => {
      switch (component.type) {
        case 'model':
          stats.models++;
          break;
        case 'reaction_system':
          stats.reactionSystems++;
          break;
        case 'data_loader':
          stats.dataLoaders++;
          break;
        case 'operator':
          stats.operators++;
          break;
      }
    });

    return stats;
  });

  // Compute coupling statistics
  const couplingStats = createMemo<CouplingStatistics>(() => {
    const couplings = props.esmFile.coupling || [];
    const uniqueVariables = new Set<string>();
    let complexCouplings = 0;

    couplings.forEach(coupling => {
      // Collect unique variable names
      if (coupling.output_variable) uniqueVariables.add(coupling.output_variable);
      if (coupling.input_variable) uniqueVariables.add(coupling.input_variable);

      // Count complex couplings (those with transformations)
      if (coupling.transform) {
        complexCouplings++;
      }
    });

    return {
      totalCouplings: couplings.length,
      uniqueVariables,
      complexCouplings
    };
  });

  // Compute file metadata
  const metadata = createMemo<FileMetadata>(() => {
    const components = props.esmFile.components || [];
    let totalVariables = 0;
    let totalEquations = 0;

    components.forEach(component => {
      if (component.type === 'model') {
        const model = component as Model;
        totalVariables += Object.keys(model.variables || {}).length;
        totalEquations += (model.equations || []).length;
      }
    });

    return {
      version: props.esmFile.version || '1.0',
      totalLines: JSON.stringify(props.esmFile, null, 2).split('\n').length,
      variableCount: totalVariables,
      equationCount: totalEquations
    };
  });

  const handleComponentTypeClick = (componentType: string) => {
    if (props.onComponentTypeClick) {
      props.onComponentTypeClick(componentType);
    }
  };

  const handleExport = (format: 'json' | 'yaml' | 'toml') => {
    if (props.onExport) {
      props.onExport(format);
    }
  };

  return (
    <div class="esm-file-summary">
      {/* Header */}
      <div class="summary-header">
        <div class="summary-title">
          <h2>ESM File Summary</h2>
          <Show when={props.esmFile.metadata?.name}>
            <p class="file-name">{props.esmFile.metadata?.name}</p>
          </Show>
        </div>

        <Show when={props.showExportOptions}>
          <div class="export-options">
            <button
              class="export-btn"
              onClick={() => handleExport('json')}
              title="Export as JSON"
            >
              JSON
            </button>
            <button
              class="export-btn"
              onClick={() => handleExport('yaml')}
              title="Export as YAML"
            >
              YAML
            </button>
            <button
              class="export-btn"
              onClick={() => handleExport('toml')}
              title="Export as TOML"
            >
              TOML
            </button>
          </div>
        </Show>
      </div>

      {/* Overview Cards */}
      <div class="summary-cards">
        {/* Components Overview */}
        <div class="summary-card components-card">
          <div class="card-header">
            <h3>Components</h3>
            <span class="card-count">{componentStats().total}</span>
          </div>
          <div class="card-content">
            <div class="component-breakdown">
              <Show when={componentStats().models > 0}>
                <div
                  class="component-type-item"
                  onClick={() => handleComponentTypeClick('model')}
                >
                  <span class="component-icon">🧮</span>
                  <span class="component-label">Models</span>
                  <span class="component-count">{componentStats().models}</span>
                </div>
              </Show>

              <Show when={componentStats().reactionSystems > 0}>
                <div
                  class="component-type-item"
                  onClick={() => handleComponentTypeClick('reaction_system')}
                >
                  <span class="component-icon">⚗️</span>
                  <span class="component-label">Reaction Systems</span>
                  <span class="component-count">{componentStats().reactionSystems}</span>
                </div>
              </Show>

              <Show when={componentStats().dataLoaders > 0}>
                <div
                  class="component-type-item"
                  onClick={() => handleComponentTypeClick('data_loader')}
                >
                  <span class="component-icon">📊</span>
                  <span class="component-label">Data Loaders</span>
                  <span class="component-count">{componentStats().dataLoaders}</span>
                </div>
              </Show>

              <Show when={componentStats().operators > 0}>
                <div
                  class="component-type-item"
                  onClick={() => handleComponentTypeClick('operator')}
                >
                  <span class="component-icon">⚙️</span>
                  <span class="component-label">Operators</span>
                  <span class="component-count">{componentStats().operators}</span>
                </div>
              </Show>
            </div>
          </div>
        </div>

        {/* Coupling Overview */}
        <div class="summary-card coupling-card">
          <div class="card-header">
            <h3>Coupling</h3>
            <span class="card-count">{couplingStats().totalCouplings}</span>
          </div>
          <div class="card-content">
            <div class="coupling-breakdown">
              <div class="coupling-stat">
                <span class="stat-label">Total Connections</span>
                <span class="stat-value">{couplingStats().totalCouplings}</span>
              </div>
              <div class="coupling-stat">
                <span class="stat-label">Unique Variables</span>
                <span class="stat-value">{couplingStats().uniqueVariables.size}</span>
              </div>
              <div class="coupling-stat">
                <span class="stat-label">Transformations</span>
                <span class="stat-value">{couplingStats().complexCouplings}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Model Statistics */}
        <div class="summary-card model-stats-card">
          <div class="card-header">
            <h3>Model Details</h3>
          </div>
          <div class="card-content">
            <div class="model-breakdown">
              <div class="model-stat">
                <span class="stat-label">Variables</span>
                <span class="stat-value">{metadata().variableCount}</span>
              </div>
              <div class="model-stat">
                <span class="stat-label">Equations</span>
                <span class="stat-value">{metadata().equationCount}</span>
              </div>
              <div class="model-stat">
                <span class="stat-label">Version</span>
                <span class="stat-value">{metadata().version}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Detailed Information */}
      <Show when={props.showDetails}>
        <div class="summary-details">
          <div class="details-section">
            <h4>File Information</h4>
            <div class="details-grid">
              <div class="detail-item">
                <span class="detail-label">Size:</span>
                <span class="detail-value">{metadata().totalLines} lines</span>
              </div>
              <Show when={props.esmFile.metadata?.description}>
                <div class="detail-item full-width">
                  <span class="detail-label">Description:</span>
                  <span class="detail-value">{props.esmFile.metadata?.description}</span>
                </div>
              </Show>
              <Show when={props.esmFile.metadata?.author}>
                <div class="detail-item">
                  <span class="detail-label">Author:</span>
                  <span class="detail-value">{props.esmFile.metadata?.author}</span>
                </div>
              </Show>
              <Show when={props.esmFile.metadata?.created}>
                <div class="detail-item">
                  <span class="detail-label">Created:</span>
                  <span class="detail-value">{props.esmFile.metadata?.created}</span>
                </div>
              </Show>
            </div>
          </div>

          <Show when={componentStats().total > 0}>
            <div class="details-section">
              <h4>Components</h4>
              <For each={props.esmFile.components}>
                {(component) => (
                  <div class="component-detail-item">
                    <div class="component-detail-header">
                      <span class="component-detail-name">{component.name}</span>
                      <span class={`component-detail-type ${component.type}`}>
                        {component.type}
                      </span>
                    </div>
                    <Show when={component.description}>
                      <p class="component-detail-description">{component.description}</p>
                    </Show>
                  </div>
                )}
              </For>
            </div>
          </Show>
        </div>
      </Show>
    </div>
  );
};

// CSS classes used (to be added to web-components.css):
// .esm-file-summary
// .summary-header, .summary-title, .file-name
// .export-options, .export-btn
// .summary-cards
// .summary-card (with .components-card, .coupling-card, .model-stats-card modifiers)
// .card-header, .card-content, .card-count
// .component-breakdown, .component-type-item
// .component-icon, .component-label, .component-count
// .coupling-breakdown, .coupling-stat
// .stat-label, .stat-value
// .model-breakdown, .model-stat
// .summary-details, .details-section
// .details-grid, .detail-item (with .full-width modifier)
// .detail-label, .detail-value
// .component-detail-item, .component-detail-header
// .component-detail-name, .component-detail-type (with type modifiers)
// .component-detail-description