/**
 * ModelEditor - Complete model editing interface
 *
 * This component provides a comprehensive view for editing entire models,
 * including:
 * - Variables panel grouped by type (state/parameter/observed) with badges, units, and defaults
 * - Equation list with each equation as an EquationEditor
 * - Event editors for both continuous and discrete events
 * - Collapsible subsystems
 * - UI for adding/removing variables and equations
 */

import { Component, createSignal, createMemo, For, Show, JSX } from 'solid-js';
import type { Model, ModelVariable, Equation, ContinuousEvent, DiscreteEvent } from 'esm-format';
import { EquationEditor } from './EquationEditor';
import { ExpressionPalette } from './ExpressionPalette';

export interface ModelEditorProps {
  /** The model to display and edit */
  model: Model;

  /** Callback when the model is modified */
  onModelChange?: (newModel: Model) => void;

  /** Whether the editor is in read-only mode */
  readonly?: boolean;

  /** CSS class for styling */
  class?: string;

  /** Whether to show the expression palette */
  showPalette?: boolean;
}

// Variable type definitions for categorization
type VariableType = 'state' | 'parameter' | 'observed' | 'other';

// Badge configuration for different variable types
const VARIABLE_TYPE_CONFIG = {
  state: { label: 'State', color: 'blue', description: 'State variable' },
  parameter: { label: 'Param', color: 'green', description: 'Parameter' },
  observed: { label: 'Obs', color: 'orange', description: 'Observed variable' },
  other: { label: 'Var', color: 'gray', description: 'Variable' }
};

/**
 * Component for individual variable item in the variables panel
 */
const VariableItem: Component<{
  variable: ModelVariable;
  type: VariableType;
  onEdit?: (variable: ModelVariable) => void;
  onRemove?: (name: string) => void;
  readonly?: boolean;
}> = (props) => {
  const [isHovered, setIsHovered] = createSignal(false);

  const typeConfig = () => VARIABLE_TYPE_CONFIG[props.type];

  const handleEdit = () => {
    if (!props.readonly) {
      props.onEdit?.(props.variable);
    }
  };

  const handleRemove = (e: MouseEvent) => {
    e.stopPropagation();
    if (!props.readonly) {
      props.onRemove?.(props.variable.name);
    }
  };

  return (
    <div
      class={`variable-item ${isHovered() ? 'hovered' : ''}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={handleEdit}
      role="button"
      tabIndex={0}
    >
      <div class="variable-info">
        <div class="variable-header">
          <span class="variable-name">{props.variable.name}</span>
          <span class={`variable-type-badge ${typeConfig().color}`} title={typeConfig().description}>
            {typeConfig().label}
          </span>
        </div>

        <Show when={props.variable.unit}>
          <div class="variable-unit" title="Unit">
            [{props.variable.unit}]
          </div>
        </Show>

        <Show when={props.variable.default_value !== undefined}>
          <div class="variable-default" title="Default value">
            = {props.variable.default_value}
          </div>
        </Show>

        <Show when={props.variable.description}>
          <div class="variable-description" title="Description">
            {props.variable.description}
          </div>
        </Show>
      </div>

      <Show when={!props.readonly && isHovered()}>
        <button
          class="variable-remove-btn"
          onClick={handleRemove}
          title="Remove variable"
          aria-label={`Remove variable ${props.variable.name}`}
        >
          ×
        </button>
      </Show>
    </div>
  );
};

/**
 * Variables panel component
 */
const VariablesPanel: Component<{
  variables?: ModelVariable[];
  onAddVariable?: () => void;
  onEditVariable?: (variable: ModelVariable) => void;
  onRemoveVariable?: (name: string) => void;
  readonly?: boolean;
}> = (props) => {
  const [isExpanded, setIsExpanded] = createSignal(true);

  // Group variables by type
  const groupedVariables = createMemo(() => {
    const variables = props.variables || [];
    const groups: Record<VariableType, ModelVariable[]> = {
      state: [],
      parameter: [],
      observed: [],
      other: []
    };

    variables.forEach(variable => {
      // Use the actual type field from ModelVariable, fall back to 'other' if not specified
      const type: VariableType =
        ('type' in variable && variable.type) ? variable.type : 'other';

      groups[type].push(variable);
    });

    return groups;
  });

  return (
    <div class="variables-panel">
      <div class="panel-header" onClick={() => setIsExpanded(!isExpanded())}>
        <span class={`expand-icon ${isExpanded() ? 'expanded' : ''}`}>▶</span>
        <h3>Variables ({(props.variables || []).length})</h3>
        <Show when={!props.readonly}>
          <button
            class="add-btn"
            onClick={(e) => { e.stopPropagation(); props.onAddVariable?.(); }}
            title="Add new variable"
            aria-label="Add new variable"
          >
            +
          </button>
        </Show>
      </div>

      <Show when={isExpanded()}>
        <div class="variables-content">
          <For each={Object.entries(groupedVariables()) as [VariableType, ModelVariable[]][]}>
            {([type, variables]) => (
              <Show when={variables.length > 0}>
                <div class="variable-group">
                  <h4 class="group-title">
                    <span class={`group-badge ${VARIABLE_TYPE_CONFIG[type].color}`}>
                      {VARIABLE_TYPE_CONFIG[type].label}
                    </span>
                    {VARIABLE_TYPE_CONFIG[type].description}s ({variables.length})
                  </h4>
                  <div class="variables-list">
                    <For each={variables}>
                      {(variable) => (
                        <VariableItem
                          variable={variable}
                          type={type}
                          onEdit={props.onEditVariable}
                          onRemove={props.onRemoveVariable}
                          readonly={props.readonly}
                        />
                      )}
                    </For>
                  </div>
                </div>
              </Show>
            )}
          </For>

          <Show when={(props.variables || []).length === 0}>
            <div class="empty-state">
              <div class="empty-icon">📊</div>
              <div class="empty-text">No variables defined</div>
              <Show when={!props.readonly}>
                <button class="add-first-btn" onClick={props.onAddVariable}>
                  Add first variable
                </button>
              </Show>
            </div>
          </Show>
        </div>
      </Show>
    </div>
  );
};

/**
 * Equations panel component
 */
const EquationsPanel: Component<{
  equations?: Equation[];
  highlightedVars?: Set<string>;
  onAddEquation?: () => void;
  onEditEquation?: (index: number, equation: Equation) => void;
  onRemoveEquation?: (index: number) => void;
  readonly?: boolean;
}> = (props) => {
  const [isExpanded, setIsExpanded] = createSignal(true);

  return (
    <div class="equations-panel">
      <div class="panel-header" onClick={() => setIsExpanded(!isExpanded())}>
        <span class={`expand-icon ${isExpanded() ? 'expanded' : ''}`}>▶</span>
        <h3>Equations ({(props.equations || []).length})</h3>
        <Show when={!props.readonly}>
          <button
            class="add-btn"
            onClick={(e) => { e.stopPropagation(); props.onAddEquation?.(); }}
            title="Add new equation"
            aria-label="Add new equation"
          >
            +
          </button>
        </Show>
      </div>

      <Show when={isExpanded()}>
        <div class="equations-content">
          <For each={props.equations || []}>
            {(equation, index) => (
              <div class="equation-item">
                <EquationEditor
                  equation={equation}
                  highlightedVars={props.highlightedVars}
                  onEquationChange={(newEquation) => props.onEditEquation?.(index(), newEquation)}
                  readonly={props.readonly}
                  class="model-equation"
                />
                <Show when={!props.readonly}>
                  <button
                    class="equation-remove-btn"
                    onClick={() => props.onRemoveEquation?.(index())}
                    title="Remove equation"
                    aria-label={`Remove equation ${index() + 1}`}
                  >
                    ×
                  </button>
                </Show>
              </div>
            )}
          </For>

          <Show when={(props.equations || []).length === 0}>
            <div class="empty-state">
              <div class="empty-icon">⚖️</div>
              <div class="empty-text">No equations defined</div>
              <Show when={!props.readonly}>
                <button class="add-first-btn" onClick={props.onAddEquation}>
                  Add first equation
                </button>
              </Show>
            </div>
          </Show>
        </div>
      </Show>
    </div>
  );
};

/**
 * Events panel component
 */
const EventsPanel: Component<{
  continuousEvents?: ContinuousEvent[];
  discreteEvents?: DiscreteEvent[];
  onAddContinuousEvent?: () => void;
  onAddDiscreteEvent?: () => void;
  readonly?: boolean;
}> = (props) => {
  const [isExpanded, setIsExpanded] = createSignal(true);

  const totalEvents = () =>
    (props.continuousEvents || []).length + (props.discreteEvents || []).length;

  return (
    <div class="events-panel">
      <div class="panel-header" onClick={() => setIsExpanded(!isExpanded())}>
        <span class={`expand-icon ${isExpanded() ? 'expanded' : ''}`}>▶</span>
        <h3>Events ({totalEvents()})</h3>
        <Show when={!props.readonly}>
          <div class="event-add-buttons">
            <button
              class="add-btn"
              onClick={(e) => { e.stopPropagation(); props.onAddContinuousEvent?.(); }}
              title="Add continuous event"
            >
              + Continuous
            </button>
            <button
              class="add-btn"
              onClick={(e) => { e.stopPropagation(); props.onAddDiscreteEvent?.(); }}
              title="Add discrete event"
            >
              + Discrete
            </button>
          </div>
        </Show>
      </div>

      <Show when={isExpanded()}>
        <div class="events-content">
          <Show when={(props.continuousEvents || []).length > 0}>
            <div class="event-group">
              <h4>Continuous Events</h4>
              <For each={props.continuousEvents || []}>
                {(event) => (
                  <div class="event-item continuous">
                    <div class="event-name">{event.name || 'Unnamed Event'}</div>
                    <Show when={event.description}>
                      <div class="event-description">{event.description}</div>
                    </Show>
                    {/* TODO: Add condition and affect editors */}
                  </div>
                )}
              </For>
            </div>
          </Show>

          <Show when={(props.discreteEvents || []).length > 0}>
            <div class="event-group">
              <h4>Discrete Events</h4>
              <For each={props.discreteEvents || []}>
                {(event) => (
                  <div class="event-item discrete">
                    <div class="event-name">{event.name || 'Unnamed Event'}</div>
                    <Show when={event.description}>
                      <div class="event-description">{event.description}</div>
                    </Show>
                    {/* TODO: Add trigger and affect editors */}
                  </div>
                )}
              </For>
            </div>
          </Show>

          <Show when={totalEvents() === 0}>
            <div class="empty-state">
              <div class="empty-icon">⚡</div>
              <div class="empty-text">No events defined</div>
              <Show when={!props.readonly}>
                <div class="empty-actions">
                  <button class="add-first-btn" onClick={props.onAddContinuousEvent}>
                    Add continuous event
                  </button>
                  <button class="add-first-btn" onClick={props.onAddDiscreteEvent}>
                    Add discrete event
                  </button>
                </div>
              </Show>
            </div>
          </Show>
        </div>
      </Show>
    </div>
  );
};

/**
 * Main ModelEditor component
 */
export const ModelEditor: Component<ModelEditorProps> = (props) => {
  const [highlightedVars, setHighlightedVars] = createSignal<Set<string>>(new Set());

  // Handle model modifications
  const handleModelChange = (changes: Partial<Model>) => {
    if (props.readonly || !props.onModelChange) return;

    const newModel = { ...props.model, ...changes };
    props.onModelChange(newModel);
  };

  // Variable management handlers
  const handleAddVariable = () => {
    // TODO: Open variable creation dialog
    console.log('Add variable');
  };

  const handleEditVariable = (variable: ModelVariable) => {
    // TODO: Open variable editing dialog
    console.log('Edit variable:', variable.name);
  };

  const handleRemoveVariable = (name: string) => {
    const newVariables = (props.model.variables || []).filter(v => v.name !== name);
    handleModelChange({ variables: newVariables });
  };

  // Equation management handlers
  const handleAddEquation = () => {
    // TODO: Create default equation
    const newEquation: Equation = {
      lhs: '_placeholder_',
      rhs: 0
    };
    const newEquations = [...(props.model.equations || []), newEquation];
    handleModelChange({ equations: newEquations });
  };

  const handleEditEquation = (index: number, equation: Equation) => {
    const newEquations = [...(props.model.equations || [])];
    newEquations[index] = equation;
    handleModelChange({ equations: newEquations });
  };

  const handleRemoveEquation = (index: number) => {
    const newEquations = (props.model.equations || []).filter((_, i) => i !== index);
    handleModelChange({ equations: newEquations });
  };

  // Event management handlers
  const handleAddContinuousEvent = () => {
    // TODO: Create default continuous event
    console.log('Add continuous event');
  };

  const handleAddDiscreteEvent = () => {
    // TODO: Create default discrete event
    console.log('Add discrete event');
  };

  const editorClasses = () => {
    const classes = ['model-editor'];
    if (props.readonly) classes.push('readonly');
    if (props.class) classes.push(props.class);
    return classes.join(' ');
  };

  return (
    <div class={editorClasses()}>
      <div class="model-editor-layout">
        {/* Main content area */}
        <div class="model-content">
          <div class="model-header">
            <h2 class="model-name">{props.model.name || 'Untitled Model'}</h2>
            <Show when={props.model.description}>
              <div class="model-description">{props.model.description}</div>
            </Show>
          </div>

          <div class="model-panels">
            <VariablesPanel
              variables={props.model.variables}
              onAddVariable={handleAddVariable}
              onEditVariable={handleEditVariable}
              onRemoveVariable={handleRemoveVariable}
              readonly={props.readonly}
            />

            <EquationsPanel
              equations={props.model.equations}
              highlightedVars={highlightedVars()}
              onAddEquation={handleAddEquation}
              onEditEquation={handleEditEquation}
              onRemoveEquation={handleRemoveEquation}
              readonly={props.readonly}
            />

            <EventsPanel
              continuousEvents={props.model.continuous_events}
              discreteEvents={props.model.discrete_events}
              onAddContinuousEvent={handleAddContinuousEvent}
              onAddDiscreteEvent={handleAddDiscreteEvent}
              readonly={props.readonly}
            />
          </div>
        </div>

        {/* Expression palette sidebar */}
        <Show when={props.showPalette && !props.readonly}>
          <div class="palette-sidebar">
            <ExpressionPalette
              currentModel={props.model}
              visible={true}
            />
          </div>
        </Show>
      </div>
    </div>
  );
};

export default ModelEditor;