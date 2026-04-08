/**
 * FileSummary - Read-only overview of entire ESM file
 *
 * This component provides a comprehensive overview of the ESM file structure
 * matching spec Section 6.3 format. Shows: version, metadata, reaction systems
 * summary, models summary, data loaders, coupling rules, domain, solver.
 * Section headers are clickable links that scroll to / select the relevant
 * editor section.
 */

import { Component, createMemo, For, Show } from 'solid-js';
import type { EsmFile, Model, ReactionSystem, DataLoader, CouplingEntry } from 'esm-format';

export interface FileSummaryProps {
  /** The ESM file to summarize */
  esmFile: EsmFile;

  /** Callback when a section header is clicked */
  onSectionClick?: (sectionType: string, sectionId?: string) => void;

  /** CSS class for styling */
  class?: string;

  /** Whether the summary is collapsed */
  collapsed?: boolean;

  /** Callback when collapse state changes */
  onToggleCollapsed?: (collapsed: boolean) => void;
}

/**
 * Helper to count items in an object or return 0 if undefined
 */
function countItems(obj: Record<string, any> | undefined): number {
  return obj ? Object.keys(obj).length : 0;
}

/**
 * Helper to get coupling type description
 */
function getCouplingDescription(coupling: CouplingEntry): string {
  switch (coupling.type) {
    case 'operator_compose':
      return `Compose: ${coupling.systems?.join(', ') || 'N/A'}`;
    case 'couple2':
      return `Couple2: ${coupling.systems?.join(', ') || 'N/A'}`;
    case 'operator_apply':
      return `Apply operator: ${coupling.operator || 'N/A'}`;
    default:
      return 'Unknown coupling type';
  }
}

/**
 * Helper to format model/reaction system summary
 */
function getSystemSummary(system: Model | ReactionSystem): string {
  const items = [];

  if ('variables' in system && system.variables) {
    items.push(`${Object.keys(system.variables).length} variables`);
  }

  if ('species' in system && system.species) {
    items.push(`${Object.keys(system.species).length} species`);
  }

  if ('parameters' in system && system.parameters) {
    items.push(`${Object.keys(system.parameters).length} parameters`);
  }

  if ('equations' in system && system.equations) {
    items.push(`${system.equations.length} equations`);
  }

  if ('reactions' in system && system.reactions) {
    items.push(`${system.reactions.length} reactions`);
  }

  if ('subsystems' in system && system.subsystems) {
    items.push(`${Object.keys(system.subsystems).length} subsystems`);
  }

  return items.join(', ') || 'Empty system';
}

/**
 * Main FileSummary component
 */
export const FileSummary: Component<FileSummaryProps> = (props) => {
  // Reactive summaries
  const modelCount = createMemo(() => countItems(props.esmFile.models));
  const reactionSystemCount = createMemo(() => countItems(props.esmFile.reaction_systems));
  const dataLoaderCount = createMemo(() => countItems(props.esmFile.data_loaders));
  const operatorCount = createMemo(() => countItems(props.esmFile.operators));
  const couplingCount = createMemo(() => props.esmFile.coupling?.length || 0);

  // Handle section click
  const handleSectionClick = (sectionType: string, sectionId?: string) => {
    if (props.onSectionClick) {
      props.onSectionClick(sectionType, sectionId);
    }
  };

  // Handle collapse toggle
  const handleToggleCollapsed = () => {
    if (props.onToggleCollapsed) {
      props.onToggleCollapsed(!props.collapsed);
    }
  };

  // CSS classes
  const summaryClasses = () => {
    const classes = ['file-summary'];
    if (props.collapsed) classes.push('collapsed');
    if (props.class) classes.push(props.class);
    return classes.join(' ');
  };

  return (
    <div class={summaryClasses()}>
      {/* Summary header */}
      <div class="summary-header" onClick={handleToggleCollapsed}>
        <h3 class="summary-title">File Summary</h3>
        <button
          class="collapse-toggle"
          aria-label={props.collapsed ? 'Expand file summary' : 'Collapse file summary'}
        >
          {props.collapsed ? '▶' : '▼'}
        </button>
      </div>

      {/* Summary content - only shown when not collapsed */}
      <Show when={!props.collapsed}>
        <div class="summary-content">
          {/* Version and Metadata */}
          <div class="summary-section">
            <h4 class="section-title">Format Information</h4>
            <div class="section-content">
              <div class="info-item">
                <strong>Version:</strong> {props.esmFile.esm_version || 'Not specified'}
              </div>
              <Show when={props.esmFile.metadata}>
                <div class="info-item">
                  <strong>Title:</strong> {props.esmFile.metadata!.title || 'Untitled'}
                </div>
                <Show when={props.esmFile.metadata!.description}>
                  <div class="info-item">
                    <strong>Description:</strong> {props.esmFile.metadata!.description}
                  </div>
                </Show>
                <Show when={props.esmFile.metadata!.authors && props.esmFile.metadata!.authors.length > 0}>
                  <div class="info-item">
                    <strong>Authors:</strong> {props.esmFile.metadata!.authors!.join(', ')}
                  </div>
                </Show>
                <Show when={props.esmFile.metadata!.created_date}>
                  <div class="info-item">
                    <strong>Created:</strong> {props.esmFile.metadata!.created_date}
                  </div>
                </Show>
              </Show>
            </div>
          </div>

          {/* Models Summary */}
          <Show when={modelCount() > 0}>
            <div class="summary-section">
              <h4
                class="section-title clickable-section"
                onClick={() => handleSectionClick('models')}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleSectionClick('models');
                  }
                }}
              >
                Models ({modelCount()}) →
              </h4>
              <div class="section-content">
                <For each={Object.entries(props.esmFile.models || {})}>
                  {([modelName, model]) => (
                    <div class="system-item">
                      <div
                        class="system-name clickable"
                        onClick={() => handleSectionClick('models', modelName)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            handleSectionClick('models', modelName);
                          }
                        }}
                      >
                        <strong>{modelName}</strong> →
                      </div>
                      <div class="system-summary">
                        {getSystemSummary(model)}
                      </div>
                    </div>
                  )}
                </For>
              </div>
            </div>
          </Show>

          {/* Reaction Systems Summary */}
          <Show when={reactionSystemCount() > 0}>
            <div class="summary-section">
              <h4
                class="section-title clickable-section"
                onClick={() => handleSectionClick('reaction_systems')}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleSectionClick('reaction_systems');
                  }
                }}
              >
                Reaction Systems ({reactionSystemCount()}) →
              </h4>
              <div class="section-content">
                <For each={Object.entries(props.esmFile.reaction_systems || {})}>
                  {([systemName, system]) => (
                    <div class="system-item">
                      <div
                        class="system-name clickable"
                        onClick={() => handleSectionClick('reaction_systems', systemName)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            handleSectionClick('reaction_systems', systemName);
                          }
                        }}
                      >
                        <strong>{systemName}</strong> →
                      </div>
                      <div class="system-summary">
                        {getSystemSummary(system)}
                      </div>
                    </div>
                  )}
                </For>
              </div>
            </div>
          </Show>

          {/* Data Loaders Summary */}
          <Show when={dataLoaderCount() > 0}>
            <div class="summary-section">
              <h4
                class="section-title clickable-section"
                onClick={() => handleSectionClick('data_loaders')}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleSectionClick('data_loaders');
                  }
                }}
              >
                Data Loaders ({dataLoaderCount()}) →
              </h4>
              <div class="section-content">
                <For each={Object.entries(props.esmFile.data_loaders || {})}>
                  {([loaderName, loader]) => (
                    <div class="system-item">
                      <div
                        class="system-name clickable"
                        onClick={() => handleSectionClick('data_loaders', loaderName)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            handleSectionClick('data_loaders', loaderName);
                          }
                        }}
                      >
                        <strong>{loaderName}</strong> →
                      </div>
                      <div class="system-summary">
                        Type: {loader.type || 'Unknown'}
                        {loader.source && ` | Source: ${loader.source}`}
                        {loader.description && ` | ${loader.description}`}
                      </div>
                    </div>
                  )}
                </For>
              </div>
            </div>
          </Show>

          {/* Operators Summary */}
          <Show when={operatorCount() > 0}>
            <div class="summary-section">
              <h4
                class="section-title clickable-section"
                onClick={() => handleSectionClick('operators')}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleSectionClick('operators');
                  }
                }}
              >
                Operators ({operatorCount()}) →
              </h4>
              <div class="section-content">
                <For each={Object.entries(props.esmFile.operators || {})}>
                  {([operatorName, operator]) => (
                    <div class="system-item">
                      <div
                        class="system-name clickable"
                        onClick={() => handleSectionClick('operators', operatorName)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            handleSectionClick('operators', operatorName);
                          }
                        }}
                      >
                        <strong>{operatorName}</strong> →
                      </div>
                      <div class="system-summary">
                        Type: {operator.type || 'Unknown'}
                        {operator.description && ` | ${operator.description}`}
                      </div>
                    </div>
                  )}
                </For>
              </div>
            </div>
          </Show>

          {/* Coupling Rules Summary */}
          <Show when={couplingCount() > 0}>
            <div class="summary-section">
              <h4
                class="section-title clickable-section"
                onClick={() => handleSectionClick('coupling')}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleSectionClick('coupling');
                  }
                }}
              >
                Coupling Rules ({couplingCount()}) →
              </h4>
              <div class="section-content">
                <For each={props.esmFile.coupling || []}>
                  {(coupling, index) => (
                    <div class="system-item">
                      <div
                        class="system-name clickable"
                        onClick={() => handleSectionClick('coupling', index().toString())}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            handleSectionClick('coupling', index().toString());
                          }
                        }}
                      >
                        <strong>Rule {index() + 1}</strong> →
                      </div>
                      <div class="system-summary">
                        {getCouplingDescription(coupling)}
                      </div>
                    </div>
                  )}
                </For>
              </div>
            </div>
          </Show>

          {/* Domain Summary */}
          <Show when={props.esmFile.domain}>
            <div class="summary-section">
              <h4
                class="section-title clickable-section"
                onClick={() => handleSectionClick('domain')}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleSectionClick('domain');
                  }
                }}
              >
                Domain Configuration →
              </h4>
              <div class="section-content">
                <Show when={props.esmFile.domain!.time}>
                  <div class="info-item">
                    <strong>Time:</strong>
                    Start: {props.esmFile.domain!.time!.start ?? 'N/A'},
                    End: {props.esmFile.domain!.time!.end ?? 'N/A'}
                    {props.esmFile.domain!.time!.step && `, Step: ${props.esmFile.domain!.time!.step}`}
                  </div>
                </Show>
                <Show when={props.esmFile.domain!.spatial}>
                  <div class="info-item">
                    <strong>Spatial:</strong> {props.esmFile.domain!.spatial!.type || 'Unknown type'}
                  </div>
                </Show>
              </div>
            </div>
          </Show>

          {/* Solver Summary */}
          <Show when={props.esmFile.solver}>
            <div class="summary-section">
              <h4
                class="section-title clickable-section"
                onClick={() => handleSectionClick('solver')}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleSectionClick('solver');
                  }
                }}
              >
                Solver Configuration →
              </h4>
              <div class="section-content">
                <div class="info-item">
                  <strong>Type:</strong> {props.esmFile.solver!.type || 'Not specified'}
                </div>
                <Show when={props.esmFile.solver!.tolerances}>
                  <div class="info-item">
                    <strong>Tolerances:</strong>
                    {props.esmFile.solver!.tolerances!.absolute && ` Absolute: ${props.esmFile.solver!.tolerances!.absolute}`}
                    {props.esmFile.solver!.tolerances!.relative && ` Relative: ${props.esmFile.solver!.tolerances!.relative}`}
                  </div>
                </Show>
                <Show when={props.esmFile.solver!.max_steps}>
                  <div class="info-item">
                    <strong>Max Steps:</strong> {props.esmFile.solver!.max_steps}
                  </div>
                </Show>
              </div>
            </div>
          </Show>

          {/* Empty state message */}
          <Show when={modelCount() === 0 && reactionSystemCount() === 0 && dataLoaderCount() === 0 && couplingCount() === 0}>
            <div class="empty-state">
              <p>This ESM file appears to be empty or contains no major components.</p>
            </div>
          </Show>
        </div>
      </Show>
    </div>
  );
};

export default FileSummary;