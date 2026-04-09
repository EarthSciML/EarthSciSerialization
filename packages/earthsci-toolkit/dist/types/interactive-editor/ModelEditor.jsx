/**
 * ModelEditor - SolidJS component for comprehensive model editing
 *
 * This component displays all equations in a model with editable variables panel,
 * equation list, and event editor. Provides full model editing capabilities with
 * live validation feedback and integration with ExpressionNode.
 *
 * Features:
 * - Variables panel with type badges (state/parameter/observed) and units
 * - Equation list with inline editing via ExpressionNode
 * - Event editor for discrete and continuous events
 * - Add/remove equations via UI
 * - Live validation feedback
 * - Accessible design with full keyboard navigation
 */
import { Show, For, createSignal, createMemo } from 'solid-js';
import { ExpressionNode } from './ExpressionNode.js';
/**
 * Main ModelEditor component that provides comprehensive model editing interface
 */
export const ModelEditor = (props) => {
    const [selectedVarName, setSelectedVarName] = createSignal(null);
    const [selectedEquationIndex, setSelectedEquationIndex] = createSignal(null);
    const [selectedEventIndex, setSelectedEventIndex] = createSignal(null);
    const [hoveredVarName, setHoveredVarName] = createSignal(null);
    const [activeTab, setActiveTab] = createSignal('variables');
    // Compute highlighted variables from props or hover state
    const highlightedVars = createMemo(() => {
        const highlighted = new Set();
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
        const groups = {
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
    const handleVarHover = (name) => {
        setHoveredVarName(name);
    };
    // Handle variable selection
    const handleVarSelect = (name) => {
        setSelectedVarName(name === selectedVarName() ? null : name);
    };
    // Handle equation selection
    const handleEquationSelect = (index) => {
        setSelectedEquationIndex(index === selectedEquationIndex() ? null : index);
    };
    // Handle keyboard navigation between tabs
    const handleTabKeyDown = (e, currentTab) => {
        const tabs = ['variables', 'equations', 'events'];
        const currentIndex = tabs.indexOf(currentTab);
        if (e.key === 'ArrowRight' && currentIndex < tabs.length - 1) {
            e.preventDefault();
            const nextTab = tabs[currentIndex + 1];
            setActiveTab(nextTab);
            // Move focus to the next tab button
            const nextButton = e.target.parentElement?.children[currentIndex + 1];
            nextButton?.focus();
        }
        else if (e.key === 'ArrowLeft' && currentIndex > 0) {
            e.preventDefault();
            const prevTab = tabs[currentIndex - 1];
            setActiveTab(prevTab);
            // Move focus to the previous tab button
            const prevButton = e.target.parentElement?.children[currentIndex - 1];
            prevButton?.focus();
        }
    };
    // Handle expression replacement in equations
    const handleExpressionReplace = (equationIndex, side, path, newExpr) => {
        const updatedModel = { ...props.model };
        const equation = { ...updatedModel.equations[equationIndex] };
        // Replace the expression at the given path
        const target = side === 'lhs' ? equation.lhs : equation.rhs;
        const updated = replaceExpressionAtPath(target, path, newExpr);
        if (side === 'lhs') {
            equation.lhs = updated;
        }
        else {
            equation.rhs = updated;
        }
        updatedModel.equations[equationIndex] = equation;
        props.onChange(updatedModel);
    };
    // Add a new variable
    const addVariable = (type) => {
        const name = prompt(`Enter name for new ${type} variable:`);
        if (!name || name in props.model.variables)
            return;
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
    const removeVariable = (name) => {
        if (!confirm(`Remove variable "${name}"? This may break equations that reference it.`))
            return;
        const updatedModel = { ...props.model };
        const { [name]: removed, ...remainingVars } = updatedModel.variables;
        updatedModel.variables = remainingVars;
        props.onChange(updatedModel);
    };
    // Update a variable
    const updateVariable = (name, field, value) => {
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
            }
        ];
        props.onChange(updatedModel);
    };
    // Remove an equation
    const removeEquation = (index) => {
        if (!confirm('Remove this equation?'))
            return;
        const updatedModel = { ...props.model };
        updatedModel.equations = updatedModel.equations.filter((_, i) => i !== index);
        props.onChange(updatedModel);
    };
    return (<div class="esm-model-editor">
      {/* Header */}
      <header class="esm-model-header">
        <h2 class="esm-model-title">Model Editor</h2>
        <Show when={props.model.reference?.citation}>
          <p class="esm-model-reference">{props.model.reference?.citation}</p>
        </Show>
      </header>

      {/* Tab Navigation */}
      <nav class="esm-model-tabs" role="tablist">
        <button class={`esm-tab ${activeTab() === 'variables' ? 'active' : ''}`} role="tab" aria-selected={activeTab() === 'variables'} onClick={() => setActiveTab('variables')} onKeyDown={(e) => handleTabKeyDown(e, 'variables')}>
          Variables ({Object.keys(props.model.variables).length})
        </button>
        <button class={`esm-tab ${activeTab() === 'equations' ? 'active' : ''}`} role="tab" aria-selected={activeTab() === 'equations'} onClick={() => setActiveTab('equations')} onKeyDown={(e) => handleTabKeyDown(e, 'equations')}>
          Equations ({props.model.equations.length})
        </button>
        <button class={`esm-tab ${activeTab() === 'events' ? 'active' : ''}`} role="tab" aria-selected={activeTab() === 'events'} onClick={() => setActiveTab('events')} onKeyDown={(e) => handleTabKeyDown(e, 'events')}>
          Events ({(props.model.discrete_events?.length || 0) + (props.model.continuous_events?.length || 0)})
        </button>
      </nav>

      {/* Variables Tab */}
      <Show when={activeTab() === 'variables'}>
        <section class="esm-variables-panel" role="tabpanel" aria-labelledby="variables-tab">
          <For each={Object.entries(variablesByType())}>
            {([type, variables]) => (<div class="esm-variable-group">
                <div class="esm-variable-group-header">
                  <h3 class="esm-variable-type-title">
                    {type.charAt(0).toUpperCase() + type.slice(1)} Variables
                    <span class="esm-variable-count">({variables.length})</span>
                  </h3>
                  <Show when={props.allowEditing !== false}>
                    <button class="esm-add-variable-btn" onClick={() => addVariable(type)} title={`Add ${type} variable`}>
                      + Add {type}
                    </button>
                  </Show>
                </div>

                <div class="esm-variables-list">
                  <For each={variables}>
                    {([name, variable]) => (<div class={`esm-variable-item ${selectedVarName() === name ? 'selected' : ''} ${highlightedVars().has(name) ? 'highlighted' : ''}`} onMouseEnter={() => handleVarHover(name)} onMouseLeave={() => handleVarHover(null)} onClick={() => handleVarSelect(name)}>
                        <div class="esm-variable-name-row">
                          <span class="esm-variable-name">{name}</span>
                          <span class={`esm-variable-badge esm-badge-${variable.type}`}>
                            {variable.type}
                          </span>
                          <Show when={variable.units}>
                            <span class="esm-variable-units">[{variable.units}]</span>
                          </Show>
                          <Show when={props.allowEditing !== false}>
                            <button class="esm-remove-variable-btn" onClick={(e) => {
                    e.stopPropagation();
                    removeVariable(name);
                }} title={`Remove ${name}`} aria-label={`Remove variable ${name}`}>
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
                              <input type="text" class="esm-field-input" value={variable.units || ''} onInput={(e) => updateVariable(name, 'units', e.currentTarget.value)} placeholder="e.g., kg/m³, mol/mol"/>
                            </div>
                            <div class="esm-field-group">
                              <label class="esm-field-label">Description:</label>
                              <input type="text" class="esm-field-input" value={variable.description || ''} onInput={(e) => updateVariable(name, 'description', e.currentTarget.value)} placeholder="Variable description"/>
                            </div>
                            <Show when={variable.type === 'parameter'}>
                              <div class="esm-field-group">
                                <label class="esm-field-label">Default value:</label>
                                <input type="number" class="esm-field-input" value={variable.default || 0} onInput={(e) => updateVariable(name, 'default', parseFloat(e.currentTarget.value))} step="any"/>
                              </div>
                            </Show>
                          </div>
                        </Show>
                      </div>)}
                  </For>
                </div>
              </div>)}
          </For>
        </section>
      </Show>

      {/* Equations Tab */}
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
              {(equation, index) => (<div class={`esm-equation-item ${selectedEquationIndex() === index() ? 'selected' : ''}`} onClick={() => handleEquationSelect(index())}>
                  <div class="esm-equation-content">
                    <div class="esm-equation-lhs">
                      <ExpressionNode expr={equation.lhs} path={['lhs']} highlightedVars={highlightedVars} onHoverVar={handleVarHover} onSelect={(path) => console.log('Selected LHS:', path)} onReplace={(path, newExpr) => handleExpressionReplace(index(), 'lhs', path.slice(1), newExpr)} allowEditing={props.allowEditing !== false}/>
                    </div>
                    <span class="esm-equation-equals">=</span>
                    <div class="esm-equation-rhs">
                      <ExpressionNode expr={equation.rhs} path={['rhs']} highlightedVars={highlightedVars} onHoverVar={handleVarHover} onSelect={(path) => console.log('Selected RHS:', path)} onReplace={(path, newExpr) => handleExpressionReplace(index(), 'rhs', path.slice(1), newExpr)} allowEditing={props.allowEditing !== false}/>
                    </div>
                    <Show when={props.allowEditing !== false}>
                      <button class="esm-remove-equation-btn" onClick={(e) => {
                e.stopPropagation();
                removeEquation(index());
            }} title="Remove equation">
                        ×
                      </button>
                    </Show>
                  </div>
                </div>)}
            </For>
          </div>
        </section>
      </Show>

      {/* Events Tab */}
      <Show when={activeTab() === 'events'}>
        <section class="esm-events-panel" role="tabpanel" aria-labelledby="events-tab">
          <h3>Events</h3>

          {/* Discrete Events */}
          <Show when={props.model.discrete_events?.length}>
            <div class="esm-event-group">
              <h4>Discrete Events</h4>
              <For each={props.model.discrete_events}>
                {(event) => (<div class="esm-event-item">
                    <h5 class="esm-event-name">{event.name}</h5>
                    <div class="esm-event-trigger">
                      <strong>Trigger:</strong>
                      <code>{JSON.stringify(event.trigger)}</code>
                    </div>
                    <Show when={event.affects?.length}>
                      <div class="esm-event-affects">
                        <strong>Affects:</strong>
                        <For each={event.affects}>
                          {(affect) => (<div class="esm-affect-equation">
                              <ExpressionNode expr={affect.lhs} path={['lhs']} highlightedVars={highlightedVars} onHoverVar={handleVarHover} onSelect={() => { }} onReplace={() => { }} allowEditing={false}/>
                              <span>=</span>
                              <ExpressionNode expr={affect.rhs} path={['rhs']} highlightedVars={highlightedVars} onHoverVar={handleVarHover} onSelect={() => { }} onReplace={() => { }} allowEditing={false}/>
                            </div>)}
                        </For>
                      </div>
                    </Show>
                  </div>)}
              </For>
            </div>
          </Show>

          {/* Continuous Events */}
          <Show when={props.model.continuous_events?.length}>
            <div class="esm-event-group">
              <h4>Continuous Events</h4>
              <For each={props.model.continuous_events}>
                {(event) => (<div class="esm-event-item">
                    <h5 class="esm-event-name">{event.name}</h5>
                    <div class="esm-event-conditions">
                      <strong>Conditions:</strong>
                      <For each={event.conditions}>
                        {(condition) => (<ExpressionNode expr={condition} path={['condition']} highlightedVars={highlightedVars} onHoverVar={handleVarHover} onSelect={() => { }} onReplace={() => { }} allowEditing={false}/>)}
                      </For>
                    </div>
                    <Show when={event.affects.length}>
                      <div class="esm-event-affects">
                        <strong>Affects:</strong>
                        <For each={event.affects}>
                          {(affect) => (<div class="esm-affect-equation">
                              <ExpressionNode expr={affect.lhs} path={['lhs']} highlightedVars={highlightedVars} onHoverVar={handleVarHover} onSelect={() => { }} onReplace={() => { }} allowEditing={false}/>
                              <span>=</span>
                              <ExpressionNode expr={affect.rhs} path={['rhs']} highlightedVars={highlightedVars} onHoverVar={handleVarHover} onSelect={() => { }} onReplace={() => { }} allowEditing={false}/>
                            </div>)}
                        </For>
                      </div>
                    </Show>
                  </div>)}
              </For>
            </div>
          </Show>

          <Show when={!props.model.discrete_events?.length && !props.model.continuous_events?.length}>
            <p class="esm-no-events">No events defined</p>
          </Show>
        </section>
      </Show>

      {/* Validation Panel */}
      <Show when={props.showValidation !== false && props.validationErrors?.length}>
        <section class="esm-validation-panel">
          <h3 class="esm-validation-title">
            <span class="esm-error-icon">⚠</span>
            Validation Errors
          </h3>
          <ul class="esm-validation-errors">
            <For each={props.validationErrors}>
              {(error) => (<li class="esm-validation-error">{error}</li>)}
            </For>
          </ul>
        </section>
      </Show>
    </div>);
};
// Helper function to replace expression at given path
function replaceExpressionAtPath(expr, path, newExpr) {
    if (path.length === 0) {
        return newExpr;
    }
    if (typeof expr === 'object' && expr && 'op' in expr) {
        const [head, ...tail] = path;
        if (head === 'args' && tail.length > 0) {
            const argIndex = tail[0];
            const newArgs = [...expr.args];
            newArgs[argIndex] = replaceExpressionAtPath(expr.args[argIndex], tail.slice(1), newExpr);
            return { ...expr, args: newArgs };
        }
    }
    return expr;
}
export default ModelEditor;
//# sourceMappingURL=ModelEditor.jsx.map