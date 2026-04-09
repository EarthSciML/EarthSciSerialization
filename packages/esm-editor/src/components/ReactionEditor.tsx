/**
 * ReactionEditor - Chemical reaction system editor with chemical notation
 *
 * This component provides an interactive editor for reaction systems,
 * displaying reactions in chemical notation (e.g., NO + O₃ →[k] NO₂)
 * with clickable rate expressions that expand to full ExpressionEditor.
 * Features:
 * - Chemical notation display with proper subscripts
 * - Species panel with chemical formulas
 * - Parameter panel for rate constants
 * - UI for adding/removing reactions
 */

import { Component, createSignal, createMemo, For, Show, JSX } from 'solid-js';
import type { ReactionSystem, Reaction, Species, ModelVariable, Expression } from 'earthsci-toolkit';
import { ExpressionNode } from './ExpressionNode';

export interface ReactionEditorProps {
  /** The reaction system to display and edit */
  reactionSystem: ReactionSystem;

  /** Callback when the reaction system is modified */
  onReactionSystemChange?: (newReactionSystem: ReactionSystem) => void;

  /** Currently highlighted variable equivalence class */
  highlightedVars?: Set<string>;

  /** Whether the editor is in read-only mode */
  readonly?: boolean;

  /** CSS class for styling */
  class?: string;
}

/**
 * Helper function to render chemical formulas with subscripts
 */
const renderChemicalFormula = (formula: string): string => {
  // Convert numbers to subscripts (already done in ExpressionNode, but good to be consistent)
  return formula.replace(/(\d+)/g, (match) => {
    const subscripts = '₀₁₂₃₄₅₆₇₈₉';
    return match
      .split('')
      .map((digit) => subscripts[parseInt(digit, 10)])
      .join('');
  });
};

/**
 * Component for rendering a single chemical reaction
 */
const ReactionItem: Component<{
  reaction: Reaction;
  index: number;
  species: { [k: string]: Species };
  onEditReaction?: (index: number, reaction: Reaction) => void;
  onRemoveReaction?: (index: number) => void;
  highlightedVars?: Set<string>;
  readonly?: boolean;
}> = (props) => {
  const [isExpanded, setIsExpanded] = createSignal(false);
  const [selectedPath, setSelectedPath] = createSignal<(string | number)[] | null>(null);
  const [hoveredVar, setHoveredVar] = createSignal<string | null>(null);

  // Create species lookup for chemical formulas
  const speciesMap = createMemo(() => props.species || {});

  // Create reactive highlighted vars set
  const highlightedVars = createMemo(() => {
    const baseHighlighted = props.highlightedVars || new Set<string>();
    const hovered = hoveredVar();

    if (hovered && !baseHighlighted.has(hovered)) {
      return new Set([...baseHighlighted, hovered]);
    }
    return baseHighlighted;
  });

  // Render reactants with chemical notation
  const renderReactants = () => {
    if (!props.reaction.reactants) return '';

    return props.reaction.reactants
      .map((reactant, idx) => {
        const species = speciesMap()[reactant.species];
        const formula = species?.formula || reactant.species;
        const stoichiometry = reactant.stoichiometry !== undefined ? reactant.stoichiometry : 1;

        return `${stoichiometry > 1 ? stoichiometry : ''}${renderChemicalFormula(formula)}`;
      })
      .join(' + ');
  };

  // Render products with chemical notation
  const renderProducts = () => {
    if (!props.reaction.products) return '';

    return props.reaction.products
      .map((product, idx) => {
        const species = speciesMap()[product.species];
        const formula = species?.formula || product.species;
        const stoichiometry = product.stoichiometry !== undefined ? product.stoichiometry : 1;

        return `${stoichiometry > 1 ? stoichiometry : ''}${renderChemicalFormula(formula)}`;
      })
      .join(' + ');
  };

  // Handle rate expression editing
  const handleRateClick = () => {
    if (!props.readonly) {
      setIsExpanded(!isExpanded());
    }
  };

  const handleRateChange = (newRate: Expression) => {
    if (props.readonly || !props.onEditReaction) return;

    const newReaction = { ...props.reaction, rate: newRate };
    props.onEditReaction(props.index, newReaction);
  };

  const handleRemove = () => {
    if (!props.readonly) {
      props.onRemoveReaction?.(props.index);
    }
  };

  return (
    <div class="reaction-item">
      <div class="reaction-header">
        <div class="reaction-equation">
          {/* Reactants */}
          <span class="reactants">{renderReactants()}</span>

          {/* Arrow with rate */}
          <span class="reaction-arrow">
            →
            <span
              class={`rate-expression ${isExpanded() ? 'expanded' : ''} ${!props.readonly ? 'clickable' : ''}`}
              onClick={handleRateClick}
              title={props.readonly ? undefined : 'Click to edit rate expression'}
            >
              [{props.reaction.rate ? 'k' : '?'}]
            </span>
          </span>

          {/* Products */}
          <span class="products">{renderProducts()}</span>
        </div>

        <div class="reaction-controls">
          <Show when={props.reaction.name}>
            <span class="reaction-name" title="Reaction name">
              {props.reaction.name}
            </span>
          </Show>

          <Show when={!props.readonly}>
            <button
              class="reaction-remove-btn"
              onClick={handleRemove}
              title="Remove reaction"
              aria-label={`Remove reaction ${props.index + 1}`}
            >
              ×
            </button>
          </Show>
        </div>
      </div>

      {/* Expanded rate expression editor */}
      <Show when={isExpanded()}>
        <div class="reaction-rate-editor">
          <div class="rate-editor-header">
            <span>Rate Expression:</span>
            <button
              class="collapse-btn"
              onClick={() => setIsExpanded(false)}
              title="Collapse rate editor"
            >
              ▲
            </button>
          </div>

          <div class="rate-editor-content">
            <Show when={props.reaction.rate} fallback={
              <div class="no-rate-placeholder">
                <span>No rate expression defined</span>
                <button
                  class="add-rate-btn"
                  onClick={() => handleRateChange('k_rate')}
                >
                  Add rate constant
                </button>
              </div>
            }>
              <ExpressionNode
                expr={props.reaction.rate!}
                path={['rate']}
                highlightedVars={() => highlightedVars()}
                onHoverVar={setHoveredVar}
                onSelect={setSelectedPath}
                onReplace={(path, newExpr) => {
                  // Only update if the path is for the rate expression
                  if (path.length === 1 && path[0] === 'rate') {
                    handleRateChange(newExpr);
                  }
                }}
                selectedPath={selectedPath()}
              />
            </Show>
          </div>
        </div>
      </Show>

      <Show when={props.reaction.description}>
        <div class="reaction-description">{props.reaction.description}</div>
      </Show>
    </div>
  );
};

/**
 * Species panel component
 */
const SpeciesPanel: Component<{
  species?: Species[];
  onAddSpecies?: () => void;
  onEditSpecies?: (species: Species) => void;
  onRemoveSpecies?: (name: string) => void;
  readonly?: boolean;
}> = (props) => {
  const [isExpanded, setIsExpanded] = createSignal(true);

  return (
    <div class="species-panel">
      <div class="panel-header" onClick={() => setIsExpanded(!isExpanded())}>
        <span class={`expand-icon ${isExpanded() ? 'expanded' : ''}`}>▶</span>
        <h3>Species ({(props.species || []).length})</h3>
        <Show when={!props.readonly}>
          <button
            class="add-btn"
            onClick={(e) => { e.stopPropagation(); props.onAddSpecies?.(); }}
            title="Add new species"
            aria-label="Add new species"
          >
            +
          </button>
        </Show>
      </div>

      <Show when={isExpanded()}>
        <div class="species-content">
          <For each={props.species || []}>
            {(species) => (
              <div class="species-item" onClick={() => props.onEditSpecies?.(species)}>
                <div class="species-info">
                  <span class="species-formula">
                    {renderChemicalFormula(species.formula || species.name)}
                  </span>
                  <Show when={species.name !== species.formula}>
                    <span class="species-name">({species.name})</span>
                  </Show>
                </div>

                <Show when={species.description}>
                  <div class="species-description">{species.description}</div>
                </Show>

                <Show when={!props.readonly}>
                  <button
                    class="species-remove-btn"
                    onClick={(e) => { e.stopPropagation(); props.onRemoveSpecies?.(species.name); }}
                    title="Remove species"
                    aria-label={`Remove species ${species.name}`}
                  >
                    ×
                  </button>
                </Show>
              </div>
            )}
          </For>

          <Show when={(props.species || []).length === 0}>
            <div class="empty-state">
              <div class="empty-icon">🧪</div>
              <div class="empty-text">No species defined</div>
              <Show when={!props.readonly}>
                <button class="add-first-btn" onClick={props.onAddSpecies}>
                  Add first species
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
 * Parameters panel component
 */
const ParametersPanel: Component<{
  parameters?: ModelVariable[];
  onAddParameter?: () => void;
  onEditParameter?: (parameter: ModelVariable) => void;
  onRemoveParameter?: (name: string) => void;
  readonly?: boolean;
}> = (props) => {
  const [isExpanded, setIsExpanded] = createSignal(true);

  // Filter for rate constants and reaction parameters
  const reactionParameters = createMemo(() => {
    return (props.parameters || []).filter(param =>
      param.name.startsWith('k_') ||
      param.name.includes('rate') ||
      param.name.includes('const')
    );
  });

  return (
    <div class="parameters-panel">
      <div class="panel-header" onClick={() => setIsExpanded(!isExpanded())}>
        <span class={`expand-icon ${isExpanded() ? 'expanded' : ''}`}>▶</span>
        <h3>Parameters ({reactionParameters().length})</h3>
        <Show when={!props.readonly}>
          <button
            class="add-btn"
            onClick={(e) => { e.stopPropagation(); props.onAddParameter?.(); }}
            title="Add new parameter"
            aria-label="Add new parameter"
          >
            +
          </button>
        </Show>
      </div>

      <Show when={isExpanded()}>
        <div class="parameters-content">
          <For each={reactionParameters()}>
            {(param) => (
              <div class="parameter-item" onClick={() => props.onEditParameter?.(param)}>
                <div class="parameter-info">
                  <span class="parameter-name">{param.name}</span>
                  <Show when={param.unit}>
                    <span class="parameter-unit">[{param.unit}]</span>
                  </Show>
                  <Show when={param.default_value !== undefined}>
                    <span class="parameter-value">= {param.default_value}</span>
                  </Show>
                </div>

                <Show when={param.description}>
                  <div class="parameter-description">{param.description}</div>
                </Show>

                <Show when={!props.readonly}>
                  <button
                    class="parameter-remove-btn"
                    onClick={(e) => { e.stopPropagation(); props.onRemoveParameter?.(param.name); }}
                    title="Remove parameter"
                    aria-label={`Remove parameter ${param.name}`}
                  >
                    ×
                  </button>
                </Show>
              </div>
            )}
          </For>

          <Show when={reactionParameters().length === 0}>
            <div class="empty-state">
              <div class="empty-icon">⚗️</div>
              <div class="empty-text">No parameters defined</div>
              <Show when={!props.readonly}>
                <button class="add-first-btn" onClick={props.onAddParameter}>
                  Add first parameter
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
 * Main ReactionEditor component
 */
export const ReactionEditor: Component<ReactionEditorProps> = (props) => {
  // Handle reaction system modifications
  const handleReactionSystemChange = (changes: Partial<ReactionSystem>) => {
    if (props.readonly || !props.onReactionSystemChange) return;

    const newReactionSystem = { ...props.reactionSystem, ...changes };
    props.onReactionSystemChange(newReactionSystem);
  };

  // Reaction management handlers
  const handleAddReaction = () => {
    const newReaction: Reaction = {
      reactants: [{ species: 'A', stoichiometry: 1 }],
      products: [{ species: 'B', stoichiometry: 1 }],
      rate: 'k_rate'
    };
    const newReactions = [...(props.reactionSystem.reactions || []), newReaction];
    handleReactionSystemChange({ reactions: newReactions });
  };

  const handleEditReaction = (index: number, reaction: Reaction) => {
    const newReactions = [...(props.reactionSystem.reactions || [])];
    newReactions[index] = reaction;
    handleReactionSystemChange({ reactions: newReactions });
  };

  const handleRemoveReaction = (index: number) => {
    const newReactions = (props.reactionSystem.reactions || []).filter((_, i) => i !== index);
    handleReactionSystemChange({ reactions: newReactions });
  };

  // Species management handlers
  const handleAddSpecies = () => {
    const name = prompt('Enter species name:');
    if (!name || !name.trim()) return;

    const formula = prompt('Enter chemical formula:', name);
    const description = prompt('Enter description (optional):', '');

    const newSpecies = {
      formula: formula || name.trim(),
      description: description || undefined
    };

    const updatedSpecies = {
      ...(props.reactionSystem.species || {}),
      [name.trim()]: newSpecies
    };
    handleReactionSystemChange({ species: updatedSpecies });
  };

  const handleEditSpecies = (species: Species) => {
    const newName = prompt('Enter species name:', species.name);
    if (!newName || !newName.trim()) return;

    const newFormula = prompt('Enter chemical formula:', species.formula || species.name);
    const newDescription = prompt('Enter description:', species.description || '');

    const updatedSpecies = { ...(props.reactionSystem.species || {}) };

    // Remove old species if name changed
    if (newName.trim() !== species.name) {
      delete updatedSpecies[species.name];
    }

    // Add/update species with new values
    updatedSpecies[newName.trim()] = {
      formula: newFormula || newName.trim(),
      description: newDescription || undefined
    };

    handleReactionSystemChange({ species: updatedSpecies });
  };

  const handleRemoveSpecies = (name: string) => {
    if (!confirm(`Remove species "${name}"? This may affect reactions that reference it.`)) return;

    const updatedSpecies = { ...(props.reactionSystem.species || {}) };
    delete updatedSpecies[name];
    handleReactionSystemChange({ species: updatedSpecies });
  };

  // Parameter management handlers
  const handleAddParameter = () => {
    const name = prompt('Enter parameter name (e.g., k_rate):');
    if (!name || !name.trim()) return;

    const value = prompt('Enter default value:', '1.0');
    const unit = prompt('Enter unit (optional):', '');
    const description = prompt('Enter description (optional):', '');

    const newParameter = {
      value: parseFloat(value || '1.0') || 1.0,
      unit: unit || undefined,
      description: description || undefined
    };

    const updatedParameters = {
      ...(props.reactionSystem.parameters || {}),
      [name.trim()]: newParameter
    };

    handleReactionSystemChange({ parameters: updatedParameters });
  };

  const handleEditParameter = (parameter: ModelVariable) => {
    const newName = prompt('Enter parameter name:', parameter.name);
    if (!newName || !newName.trim()) return;

    const newValue = prompt('Enter value:', String(parameter.default_value || 1.0));
    const newUnit = prompt('Enter unit:', parameter.unit || '');
    const newDescription = prompt('Enter description:', parameter.description || '');

    const updatedParameters = { ...(props.reactionSystem.parameters || {}) };

    // Remove old parameter if name changed
    if (newName.trim() !== parameter.name) {
      delete updatedParameters[parameter.name];
    }

    // Add/update parameter with new values
    updatedParameters[newName.trim()] = {
      value: parseFloat(newValue || '1.0') || 1.0,
      unit: newUnit || undefined,
      description: newDescription || undefined
    };

    handleReactionSystemChange({ parameters: updatedParameters });
  };

  const handleRemoveParameter = (name: string) => {
    if (!confirm(`Remove parameter "${name}"? This may affect reactions that reference it.`)) return;

    const updatedParameters = { ...(props.reactionSystem.parameters || {}) };
    delete updatedParameters[name];

    handleReactionSystemChange({ parameters: updatedParameters });
  };

  const editorClasses = () => {
    const classes = ['reaction-editor'];
    if (props.readonly) classes.push('readonly');
    if (props.class) classes.push(props.class);
    return classes.join(' ');
  };

  return (
    <div class={editorClasses()}>
      <div class="reaction-editor-layout">
        {/* Main reactions panel */}
        <div class="reactions-main">
          <div class="reactions-header">
            <h2>Reactions ({(props.reactionSystem.reactions || []).length})</h2>
            <Show when={!props.readonly}>
              <button
                class="add-reaction-btn"
                onClick={handleAddReaction}
                title="Add new reaction"
              >
                + Add Reaction
              </button>
            </Show>
          </div>

          <div class="reactions-list">
            <For each={props.reactionSystem.reactions || []}>
              {(reaction, index) => (
                <ReactionItem
                  reaction={reaction}
                  index={index()}
                  species={props.reactionSystem.species || {}}
                  onEditReaction={handleEditReaction}
                  onRemoveReaction={handleRemoveReaction}
                  highlightedVars={props.highlightedVars}
                  readonly={props.readonly}
                />
              )}
            </For>

            <Show when={(props.reactionSystem.reactions || []).length === 0}>
              <div class="empty-state">
                <div class="empty-icon">⚛️</div>
                <div class="empty-text">No reactions defined</div>
                <Show when={!props.readonly}>
                  <button class="add-first-btn" onClick={handleAddReaction}>
                    Add first reaction
                  </button>
                </Show>
              </div>
            </Show>
          </div>
        </div>

        {/* Side panels */}
        <div class="reaction-sidebar">
          <SpeciesPanel
            species={Object.entries(props.reactionSystem.species || {}).map(([name, species]) => ({
              ...species,
              name
            }))}
            onAddSpecies={handleAddSpecies}
            onEditSpecies={handleEditSpecies}
            onRemoveSpecies={handleRemoveSpecies}
            readonly={props.readonly}
          />

          <ParametersPanel
            parameters={Object.entries(props.reactionSystem.parameters || {}).map(([name, param]) => ({
              name,
              type: 'parameter',
              unit: param.unit,
              description: param.description,
              default_value: param.value
            }))}
            onAddParameter={handleAddParameter}
            onEditParameter={handleEditParameter}
            onRemoveParameter={handleRemoveParameter}
            readonly={props.readonly}
          />
        </div>
      </div>
    </div>
  );
};

export default ReactionEditor;