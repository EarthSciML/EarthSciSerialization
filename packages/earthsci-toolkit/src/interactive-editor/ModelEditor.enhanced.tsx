/**
 * Enhanced ModelEditor - SolidJS component with export functionality
 *
 * Extends the base ModelEditor with comprehensive export capabilities,
 * enhanced validation, and performance monitoring as required by the task.
 */

import { Component, Show, For, createSignal, createMemo, createEffect, Accessor } from 'solid-js';
import { ExpressionNode } from './ExpressionNode.js';
import { exportModel, downloadExport, getAvailableFormats, getFileExtension, type ExportFormat, type ExportOptions } from './ModelExportUtils.js';
import type { Model, ModelVariable, Equation, DiscreteEvent, ContinuousEvent, Expression } from '../types.js';

export interface EnhancedModelEditorProps {
  /** The model to edit (reactive) */
  model: Model;

  /** Callback when the model is updated */
  onChange: (updatedModel: Model) => void;

  /** Currently highlighted variable equivalence class */
  highlightedVars?: Accessor<Set<string>>;

  /** Whether inline editing is enabled (default: true) */
  allowEditing?: boolean;

  /** Whether to show validation errors inline (default: true) */
  showValidation?: boolean;

  /** Optional validation errors to display */
  validationErrors?: string[];

  /** Enable export functionality (default: true) */
  enableExport?: boolean;

  /** Enable performance monitoring (default: false) */
  enablePerformanceMonitoring?: boolean;

  /** Enhanced validation callback */
  onValidate?: (model: Model) => string[];
}

/**
 * Enhanced ModelEditor component with export and advanced features
 */
export const EnhancedModelEditor: Component<EnhancedModelEditorProps> = (props) => {
  const [selectedVarName, setSelectedVarName] = createSignal<string | null>(null);
  const [selectedEquationIndex, setSelectedEquationIndex] = createSignal<number | null>(null);
  const [selectedEventIndex, setSelectedEventIndex] = createSignal<number | null>(null);
  const [hoveredVarName, setHoveredVarName] = createSignal<string | null>(null);
  const [activeTab, setActiveTab] = createSignal<'variables' | 'equations' | 'events' | 'export'>('variables');
  const [showExportDialog, setShowExportDialog] = createSignal(false);
  const [selectedExportFormat, setSelectedExportFormat] = createSignal<ExportFormat>('esm-json');
  const [exportOptions, setExportOptions] = createSignal<ExportOptions>({
    includeComments: true,
    prettyPrint: true,
    includeMetadata: true,
    mathStyle: 'display'
  });
  const [performanceMetrics, setPerformanceMetrics] = createSignal<{
    renderTime: number;
    lastUpdate: number;
    nodeCount: number;
  }>({ renderTime: 0, lastUpdate: Date.now(), nodeCount: 0 });

  // Performance monitoring
  const startTime = performance.now();
  createEffect(() => {
    if (props.enablePerformanceMonitoring) {
      const endTime = performance.now();
      const nodeCount = document.querySelectorAll('.esm-model-editor *').length;
      setPerformanceMetrics({
        renderTime: endTime - startTime,
        lastUpdate: Date.now(),
        nodeCount
      });
    }
  });

  // Enhanced validation
  const validationErrors = createMemo(() => {
    let errors: string[] = [...(props.validationErrors || [])];

    if (props.onValidate) {
      errors = [...errors, ...props.onValidate(props.model)];
    }

    // Built-in validation checks
    const varNames = new Set(Object.keys(props.model.variables));

    // Check for undefined variables in equations
    props.model.equations.forEach((eq, i) => {
      const varsInEq = extractVariablesFromExpression(eq.lhs).concat(extractVariablesFromExpression(eq.rhs));
      varsInEq.forEach(varName => {
        if (!varNames.has(varName)) {
          errors.push(`Equation ${i + 1}: Undefined variable "${varName}"`);
        }
      });
    });

    // Check for circular dependencies
    const dependencies = new Map<string, Set<string>>();
    props.model.equations.forEach(eq => {
      if (typeof eq.lhs === 'string') {
        const lhsVar = eq.lhs;
        const rhsVars = extractVariablesFromExpression(eq.rhs);
        dependencies.set(lhsVar, new Set(rhsVars));
      }
    });

    // Simple cycle detection
    for (const [variable, deps] of dependencies.entries()) {
      if (deps.has(variable)) {
        errors.push(`Variable "${variable}" depends on itself`);
      }
    }

    // Check parameter defaults
    Object.entries(props.model.variables).forEach(([name, variable]) => {
      if (variable.type === 'parameter' && variable.default === undefined) {
        errors.push(`Parameter "${name}" has no default value`);
      }
    });

    return errors;
  });

  // Compute highlighted variables from props or hover state
  const highlightedVars = createMemo(() => {
    const highlighted = new Set<string>();

    // Add variables from props if provided
    if (props.highlightedVars) {
      props.highlightedVars().forEach(name => highlighted.add(name));
    }

    // Add hovered variable
    const hovered = hoveredVarName();
    if (hovered) {
      highlighted.add(hovered);
    }

    return highlighted;
  });

  // Group variables by type for better organization
  const variablesByType = createMemo(() => {
    const groups: { [key: string]: Array<[string, ModelVariable]> } = {
      state: [],
      parameter: [],
      observed: []
    };

    Object.entries(props.model.variables).forEach(([name, variable]) => {
      groups[variable.type].push([name, variable]);
    });

    return groups;
  });

  // Handle variable hover
  const handleVarHover = (name: string | null) => {
    setHoveredVarName(name);
  };

  // Handle variable selection
  const handleVarSelect = (name: string) => {
    setSelectedVarName(name === selectedVarName() ? null : name);
  };

  // Handle equation selection
  const handleEquationSelect = (index: number) => {
    setSelectedEquationIndex(index === selectedEquationIndex() ? null : index);
  };

  // Handle expression replacement in equations
  const handleExpressionReplace = (equationIndex: number, side: 'lhs' | 'rhs', path: (string | number)[], newExpr: Expression) => {
    const updatedModel = { ...props.model };
    const equation = { ...updatedModel.equations[equationIndex] };

    // Replace the expression at the given path
    const target = side === 'lhs' ? equation.lhs : equation.rhs;
    const updated = replaceExpressionAtPath(target, path, newExpr);

    if (side === 'lhs') {
      equation.lhs = updated;
    } else {
      equation.rhs = updated;
    }

    updatedModel.equations[equationIndex] = equation;
    props.onChange(updatedModel);
  };

  // Add a new variable
  const addVariable = (type: 'state' | 'parameter' | 'observed') => {
    const name = prompt(`Enter name for new ${type} variable:`);
    if (!name || name in props.model.variables) return;

    const updatedModel = { ...props.model };
    updatedModel.variables = {
      ...updatedModel.variables,
      [name]: {
        type,
        units: '',
        default: type === 'parameter' ? 1.0 : undefined,
        description: ''
      }
    };
    props.onChange(updatedModel);
  };

  // Remove a variable
  const removeVariable = (name: string) => {
    if (!confirm(`Remove variable "${name}"? This may break equations that reference it.`)) return;

    const updatedModel = { ...props.model };
    const { [name]: removed, ...remainingVars } = updatedModel.variables;
    updatedModel.variables = remainingVars;
    props.onChange(updatedModel);
  };

  // Update a variable
  const updateVariable = (name: string, field: keyof ModelVariable, value: any) => {
    const updatedModel = { ...props.model };
    updatedModel.variables = {
      ...updatedModel.variables,
      [name]: {
        ...updatedModel.variables[name],
        [field]: value
      }
    };
    props.onChange(updatedModel);
  };

  // Add a new equation
  const addEquation = () => {
    const updatedModel = { ...props.model };
    updatedModel.equations = [
      ...updatedModel.equations,
      {
        lhs: { op: 'D', args: ['new_var'], wrt: 't' },
        rhs: 0
      } as Equation
    ];
    props.onChange(updatedModel);
  };

  // Remove an equation
  const removeEquation = (index: number) => {
    if (!confirm('Remove this equation?')) return;

    const updatedModel = { ...props.model };
    updatedModel.equations = updatedModel.equations.filter((_, i) => i !== index);
    props.onChange(updatedModel);
  };

  // Handle export
  const handleExport = () => {
    const format = selectedExportFormat();
    const opts = exportOptions();

    try {
      const content = exportModel(props.model, format, opts);
      const filename = `model.${getFileExtension(format)}`;

      const mimeTypes: Record<ExportFormat, string> = {
        'esm-json': 'application/json',
        'latex': 'application/x-latex',
        'mathml': 'application/mathml+xml',
        'python': 'text/x-python',
        'julia': 'text/julia',
        'markdown': 'text/markdown'
      };

      downloadExport(content, filename, mimeTypes[format]);
      setShowExportDialog(false);
    } catch (error) {
      alert(`Export failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  return (
    <div class="esm-model-editor">
      {/* Header */}
      <header class="esm-model-header">
        <div class="esm-model-title-row">
          <h2 class="esm-model-title">Enhanced Model Editor</h2>
          <Show when={props.enableExport !== false}>
            <button
              class="esm-export-btn"
              onClick={() => setShowExportDialog(true)}
              title="Export model to various formats"
            >
              📤 Export
            </button>
          </Show>
        </div>
        <Show when={props.model.reference?.citation}>
          <p class="esm-model-reference">{props.model.reference?.citation}</p>
        </Show>
        <Show when={props.enablePerformanceMonitoring}>
          <div class="esm-performance-info">
            <small>
              Render: {performanceMetrics().renderTime.toFixed(1)}ms |
              Nodes: {performanceMetrics().nodeCount} |
              Updated: {new Date(performanceMetrics().lastUpdate).toLocaleTimeString()}
            </small>
          </div>
        </Show>
      </header>

      {/* Tab Navigation */}
      <nav class="esm-model-tabs" role="tablist">
        <button
          class={`esm-tab ${activeTab() === 'variables' ? 'active' : ''}`}
          role="tab"
          aria-selected={activeTab() === 'variables'}
          onClick={() => setActiveTab('variables')}
        >
          Variables ({Object.keys(props.model.variables).length})
        </button>
        <button
          class={`esm-tab ${activeTab() === 'equations' ? 'active' : ''}`}
          role="tab"
          aria-selected={activeTab() === 'equations'}
          onClick={() => setActiveTab('equations')}
        >
          Equations ({props.model.equations.length})
        </button>
        <button
          class={`esm-tab ${activeTab() === 'events' ? 'active' : ''}`}
          role="tab"
          aria-selected={activeTab() === 'events'}
          onClick={() => setActiveTab('events')}
        >
          Events ({(props.model.discrete_events?.length || 0) + (props.model.continuous_events?.length || 0)})
        </button>
        <Show when={props.enableExport !== false}>
          <button
            class={`esm-tab ${activeTab() === 'export' ? 'active' : ''}`}
            role="tab"
            aria-selected={activeTab() === 'export'}
            onClick={() => setActiveTab('export')}
          >
            Export
          </button>
        </Show>
      </nav>

      {/* Variables Tab */}
      <Show when={activeTab() === 'variables'}>
        <section class="esm-variables-panel" role="tabpanel" aria-labelledby="variables-tab">
          <For each={Object.entries(variablesByType())}>
            {([type, variables]) => (
              <div class="esm-variable-group">
                <div class="esm-variable-group-header">
                  <h3 class="esm-variable-type-title">
                    {type.charAt(0).toUpperCase() + type.slice(1)} Variables
                    <span class="esm-variable-count">({variables.length})</span>
                  </h3>
                  <Show when={props.allowEditing !== false}>
                    <button
                      class="esm-add-variable-btn"
                      onClick={() => addVariable(type as any)}
                      title={`Add ${type} variable`}
                    >
                      + Add {type}
                    </button>
                  </Show>
                </div>

                <div class="esm-variables-list">
                  <For each={variables}>
                    {([name, variable]) => (
                      <div
                        class={`esm-variable-item ${selectedVarName() === name ? 'selected' : ''} ${highlightedVars().has(name) ? 'highlighted' : ''}`}
                        onMouseEnter={() => handleVarHover(name)}
                        onMouseLeave={() => handleVarHover(null)}
                        onClick={() => handleVarSelect(name)}
                      >
                        <div class="esm-variable-name-row">
                          <span class="esm-variable-name">{name}</span>
                          <span class={`esm-variable-badge esm-badge-${variable.type}`}>
                            {variable.type}
                          </span>
                          <Show when={variable.units}>
                            <span class="esm-variable-units">[{variable.units}]</span>
                          </Show>
                          <Show when={props.allowEditing !== false}>
                            <button
                              class="esm-remove-variable-btn"
                              onClick={(e) => {
                                e.stopPropagation();
                                removeVariable(name);
                              }}
                              title={`Remove ${name}`}
                              aria-label={`Remove variable ${name}`}
                            >
                              ×
                            </button>
                          </Show>
                        </div>

                        <Show when={variable.description}>
                          <p class="esm-variable-description">{variable.description}</p>
                        </Show>

                        <Show when={typeof variable.default !== 'undefined'}>
                          <div class="esm-variable-default">
                            Default: <code>{String(variable.default)}</code>
                          </div>
                        </Show>

                        {/* Expanded variable editor */}
                        <Show when={selectedVarName() === name && props.allowEditing !== false}>
                          <div class="esm-variable-editor">
                            <div class="esm-field-group">
                              <label class="esm-field-label">Units:</label>
                              <input
                                type="text"
                                class="esm-field-input"
                                value={variable.units || ''}
                                onInput={(e) => updateVariable(name, 'units', e.currentTarget.value)}
                                placeholder="e.g., kg/m³, mol/mol"
                              />
                            </div>
                            <div class="esm-field-group">
                              <label class="esm-field-label">Description:</label>
                              <input
                                type="text"
                                class="esm-field-input"
                                value={variable.description || ''}
                                onInput={(e) => updateVariable(name, 'description', e.currentTarget.value)}
                                placeholder="Variable description"
                              />
                            </div>
                            <Show when={variable.type === 'parameter'}>
                              <div class="esm-field-group">
                                <label class="esm-field-label">Default value:</label>
                                <input
                                  type="number"
                                  class="esm-field-input"
                                  value={variable.default || 0}
                                  onInput={(e) => updateVariable(name, 'default', parseFloat(e.currentTarget.value))}
                                  step="any"
                                />
                              </div>
                            </Show>
                          </div>
                        </Show>
                      </div>
                    )}
                  </For>
                </div>
              </div>
            )}
          </For>
        </section>
      </Show>

      {/* Equations Tab - Similar to original ModelEditor */}
      <Show when={activeTab() === 'equations'}>
        <section class="esm-equations-panel" role="tabpanel" aria-labelledby="equations-tab">
          <div class="esm-equations-header">
            <h3>Equations</h3>
            <Show when={props.allowEditing !== false}>
              <button class="esm-add-equation-btn" onClick={addEquation}>
                + Add Equation
              </button>
            </Show>
          </div>

          <div class="esm-equations-list">
            <For each={props.model.equations}>
              {(equation, index) => (
                <div
                  class={`esm-equation-item ${selectedEquationIndex() === index() ? 'selected' : ''}`}
                  onClick={() => handleEquationSelect(index())}
                >
                  <div class="esm-equation-content">
                    <div class="esm-equation-lhs">
                      <ExpressionNode
                        expr={equation.lhs}
                        path={['lhs']}
                        highlightedVars={highlightedVars}
                        onHoverVar={handleVarHover}
                        onSelect={(path) => console.log('Selected LHS:', path)}
                        onReplace={(path, newExpr) => handleExpressionReplace(index(), 'lhs', path.slice(1), newExpr)}
                        allowEditing={props.allowEditing !== false}
                      />
                    </div>
                    <span class="esm-equation-equals">=</span>
                    <div class="esm-equation-rhs">
                      <ExpressionNode
                        expr={equation.rhs}
                        path={['rhs']}
                        highlightedVars={highlightedVars}
                        onHoverVar={handleVarHover}
                        onSelect={(path) => console.log('Selected RHS:', path)}
                        onReplace={(path, newExpr) => handleExpressionReplace(index(), 'rhs', path.slice(1), newExpr)}
                        allowEditing={props.allowEditing !== false}
                      />
                    </div>
                    <Show when={props.allowEditing !== false}>
                      <button
                        class="esm-remove-equation-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          removeEquation(index());
                        }}
                        title="Remove equation"
                      >
                        ×
                      </button>
                    </Show>
                  </div>
                </div>
              )}
            </For>
          </div>
        </section>
      </Show>

      {/* Events Tab - Similar to original ModelEditor */}
      <Show when={activeTab() === 'events'}>
        <section class="esm-events-panel" role="tabpanel" aria-labelledby="events-tab">
          <h3>Events</h3>

          {/* Discrete Events */}
          <Show when={props.model.discrete_events?.length}>
            <div class="esm-event-group">
              <h4>Discrete Events</h4>
              <For each={props.model.discrete_events}>
                {(event) => (
                  <div class="esm-event-item">
                    <h5 class="esm-event-name">{event.name}</h5>
                    <div class="esm-event-trigger">
                      <strong>Trigger:</strong>
                      <code>{JSON.stringify(event.trigger)}</code>
                    </div>
                    <Show when={event.affects?.length}>
                      <div class="esm-event-affects">
                        <strong>Affects:</strong>
                        <For each={event.affects}>
                          {(affect) => (
                            <div class="esm-affect-equation">
                              <ExpressionNode
                                expr={affect.lhs}
                                path={['lhs']}
                                highlightedVars={highlightedVars}
                                onHoverVar={handleVarHover}
                                onSelect={() => {}}
                                onReplace={() => {}}
                                allowEditing={false}
                              />
                              <span>=</span>
                              <ExpressionNode
                                expr={affect.rhs}
                                path={['rhs']}
                                highlightedVars={highlightedVars}
                                onHoverVar={handleVarHover}
                                onSelect={() => {}}
                                onReplace={() => {}}
                                allowEditing={false}
                              />
                            </div>
                          )}
                        </For>
                      </div>
                    </Show>
                  </div>
                )}
              </For>
            </div>
          </Show>

          {/* Continuous Events */}
          <Show when={props.model.continuous_events?.length}>
            <div class="esm-event-group">
              <h4>Continuous Events</h4>
              <For each={props.model.continuous_events}>
                {(event) => (
                  <div class="esm-event-item">
                    <h5 class="esm-event-name">{event.name}</h5>
                    <div class="esm-event-conditions">
                      <strong>Conditions:</strong>
                      <For each={event.conditions}>
                        {(condition) => (
                          <ExpressionNode
                            expr={condition}
                            path={['condition']}
                            highlightedVars={highlightedVars}
                            onHoverVar={handleVarHover}
                            onSelect={() => {}}
                            onReplace={() => {}}
                            allowEditing={false}
                          />
                        )}
                      </For>
                    </div>
                    <Show when={event.affects.length}>
                      <div class="esm-event-affects">
                        <strong>Affects:</strong>
                        <For each={event.affects}>
                          {(affect) => (
                            <div class="esm-affect-equation">
                              <ExpressionNode
                                expr={affect.lhs}
                                path={['lhs']}
                                highlightedVars={highlightedVars}
                                onHoverVar={handleVarHover}
                                onSelect={() => {}}
                                onReplace={() => {}}
                                allowEditing={false}
                              />
                              <span>=</span>
                              <ExpressionNode
                                expr={affect.rhs}
                                path={['rhs']}
                                highlightedVars={highlightedVars}
                                onHoverVar={handleVarHover}
                                onSelect={() => {}}
                                onReplace={() => {}}
                                allowEditing={false}
                              />
                            </div>
                          )}
                        </For>
                      </div>
                    </Show>
                  </div>
                )}
              </For>
            </div>
          </Show>

          <Show when={!props.model.discrete_events?.length && !props.model.continuous_events?.length}>
            <p class="esm-no-events">No events defined</p>
          </Show>
        </section>
      </Show>

      {/* Export Tab */}
      <Show when={activeTab() === 'export'}>
        <section class="esm-export-panel" role="tabpanel" aria-labelledby="export-tab">
          <h3>Export Model</h3>

          <div class="esm-export-controls">
            <div class="esm-field-group">
              <label class="esm-field-label">Export Format:</label>
              <select
                class="esm-field-input"
                value={selectedExportFormat()}
                onChange={(e) => setSelectedExportFormat(e.currentTarget.value as ExportFormat)}
              >
                <For each={getAvailableFormats()}>
                  {(format) => (
                    <option value={format}>{format.toUpperCase()}</option>
                  )}
                </For>
              </select>
            </div>

            <div class="esm-export-options">
              <h4>Export Options</h4>

              <label class="esm-checkbox-label">
                <input
                  type="checkbox"
                  checked={exportOptions().includeComments}
                  onChange={(e) => setExportOptions(prev => ({
                    ...prev,
                    includeComments: e.currentTarget.checked
                  }))}
                />
                Include comments
              </label>

              <label class="esm-checkbox-label">
                <input
                  type="checkbox"
                  checked={exportOptions().prettyPrint}
                  onChange={(e) => setExportOptions(prev => ({
                    ...prev,
                    prettyPrint: e.currentTarget.checked
                  }))}
                />
                Pretty print
              </label>

              <label class="esm-checkbox-label">
                <input
                  type="checkbox"
                  checked={exportOptions().includeMetadata}
                  onChange={(e) => setExportOptions(prev => ({
                    ...prev,
                    includeMetadata: e.currentTarget.checked
                  }))}
                />
                Include metadata
              </label>

              <Show when={selectedExportFormat() === 'latex' || selectedExportFormat() === 'mathml'}>
                <div class="esm-field-group">
                  <label class="esm-field-label">Math Style:</label>
                  <select
                    class="esm-field-input"
                    value={exportOptions().mathStyle}
                    onChange={(e) => setExportOptions(prev => ({
                      ...prev,
                      mathStyle: e.currentTarget.value as 'display' | 'inline'
                    }))}
                  >
                    <option value="display">Display</option>
                    <option value="inline">Inline</option>
                  </select>
                </div>
              </Show>
            </div>

            <button
              class="esm-export-execute-btn"
              onClick={handleExport}
            >
              Export to {selectedExportFormat().toUpperCase()}
            </button>
          </div>

          {/* Export Preview */}
          <div class="esm-export-preview">
            <h4>Preview</h4>
            <pre class="esm-export-preview-content">
              {(() => {
                try {
                  return exportModel(props.model, selectedExportFormat(), exportOptions()).substring(0, 500) +
                         (exportModel(props.model, selectedExportFormat(), exportOptions()).length > 500 ? '...' : '');
                } catch (error) {
                  return `Error: ${error instanceof Error ? error.message : String(error)}`;
                }
              })()}
            </pre>
          </div>
        </section>
      </Show>

      {/* Enhanced Validation Panel */}
      <Show when={props.showValidation !== false && validationErrors().length}>
        <section class="esm-validation-panel">
          <h3 class="esm-validation-title">
            <span class="esm-error-icon">⚠</span>
            Validation Issues ({validationErrors().length})
          </h3>
          <ul class="esm-validation-errors">
            <For each={validationErrors()}>
              {(error) => (
                <li class={`esm-validation-error ${error.includes('Error') || error.includes('undefined') ? 'error' : 'warning'}`}>
                  {error}
                </li>
              )}
            </For>
          </ul>
        </section>
      </Show>

      {/* Export Dialog */}
      <Show when={showExportDialog()}>
        <div class="esm-modal-overlay" onClick={() => setShowExportDialog(false)}>
          <div class="esm-modal-content" onClick={(e) => e.stopPropagation()}>
            <div class="esm-modal-header">
              <h3>Quick Export</h3>
              <button class="esm-modal-close" onClick={() => setShowExportDialog(false)}>×</button>
            </div>
            <div class="esm-modal-body">
              <p>Choose a format to quickly export your model:</p>
              <div class="esm-export-format-grid">
                <For each={getAvailableFormats()}>
                  {(format) => (
                    <button
                      class="esm-export-format-btn"
                      onClick={() => {
                        setSelectedExportFormat(format);
                        handleExport();
                      }}
                    >
                      {format.toUpperCase()}
                    </button>
                  )}
                </For>
              </div>
            </div>
          </div>
        </div>
      </Show>
    </div>
  );
};

// Helper function to replace expression at given path
function replaceExpressionAtPath(expr: Expression, path: (string | number)[], newExpr: Expression): Expression {
  if (path.length === 0) {
    return newExpr;
  }

  if (typeof expr === 'object' && expr && 'op' in expr) {
    const [head, ...tail] = path;
    if (head === 'args' && tail.length > 0) {
      const argIndex = tail[0] as number;
      const newArgs = [...expr.args];
      newArgs[argIndex] = replaceExpressionAtPath(expr.args[argIndex], tail.slice(1), newExpr);
      return { ...expr, args: newArgs };
    }
  }

  return expr;
}

// Helper function to extract variables from expressions
function extractVariablesFromExpression(expr: Expression): string[] {
  if (typeof expr === 'string') {
    // Simple check - if it's a string and not a number, treat as variable
    return isNaN(Number(expr)) ? [expr] : [];
  }
  if (typeof expr === 'object' && expr && 'args' in expr) {
    const vars: string[] = [];
    expr.args.forEach((arg: any) => {
      vars.push(...extractVariablesFromExpression(arg));
    });
    return vars;
  }
  return [];
}

export default EnhancedModelEditor;