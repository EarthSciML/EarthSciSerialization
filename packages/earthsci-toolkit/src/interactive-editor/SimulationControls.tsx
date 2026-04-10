/**
 * SimulationControls Component - Control simulation execution and parameters
 *
 * Provides controls for running simulations, adjusting parameters, and
 * monitoring simulation status.
 */

import { Component, Show, createSignal, createMemo, For, onCleanup } from 'solid-js';
import type { EsmFile, Model, ReactionSystem } from '../types.js';

export interface SimulationControlsProps {
  /** The ESM file to simulate */
  esmFile: EsmFile;

  /** Whether simulation is currently running */
  isRunning?: boolean;

  /** Current simulation progress (0-100) */
  progress?: number;

  /** Simulation status message */
  statusMessage?: string;

  /** Available simulation backends */
  availableBackends?: string[];

  /** Current selected backend */
  selectedBackend?: string;

  /** Simulation parameters */
  simulationParams?: SimulationParameters;

  /** Callback when simulation is started */
  onStartSimulation?: (params: SimulationParameters) => void;

  /** Callback when simulation is stopped */
  onStopSimulation?: () => void;

  /** Callback when simulation is paused/resumed */
  onPauseResume?: (isPaused: boolean) => void;

  /** Callback when parameters are changed */
  onParametersChange?: (params: SimulationParameters) => void;

  /** Callback when backend is changed */
  onBackendChange?: (backend: string) => void;
}

export interface SimulationParameters {
  startTime: number;
  endTime: number;
  timeStep: number;
  outputInterval: number;
  solver: string;
  tolerance: number;
  maxIterations: number;
  adaptiveTimeStep: boolean;
}

export const SimulationControls: Component<SimulationControlsProps> = (props) => {
  // Local state for simulation parameters
  const [localParams, setLocalParams] = createSignal<SimulationParameters>(
    props.simulationParams || {
      startTime: 0,
      endTime: 100,
      timeStep: 0.1,
      outputInterval: 1,
      solver: 'rk4',
      tolerance: 1e-6,
      maxIterations: 1000,
      adaptiveTimeStep: false
    }
  );

  const [isPaused, setIsPaused] = createSignal(false);
  const [showAdvanced, setShowAdvanced] = createSignal(false);

  // Compute estimated runtime
  const estimatedSteps = createMemo(() => {
    const params = localParams();
    return Math.ceil((params.endTime - params.startTime) / params.timeStep);
  });

  const estimatedDuration = createMemo(() => {
    const steps = estimatedSteps();
    // Rough estimate: assume 1000 steps per second
    const seconds = steps / 1000;
    if (seconds < 60) {
      return `~${Math.round(seconds)}s`;
    } else if (seconds < 3600) {
      return `~${Math.round(seconds / 60)}m`;
    } else {
      return `~${Math.round(seconds / 3600)}h`;
    }
  });

  // Validate parameters
  const paramErrors = createMemo(() => {
    const params = localParams();
    const errors: string[] = [];

    if (params.endTime <= params.startTime) {
      errors.push('End time must be greater than start time');
    }
    if (params.timeStep <= 0) {
      errors.push('Time step must be positive');
    }
    if (params.outputInterval <= 0) {
      errors.push('Output interval must be positive');
    }
    if (params.tolerance <= 0) {
      errors.push('Tolerance must be positive');
    }
    if (params.maxIterations <= 0) {
      errors.push('Max iterations must be positive');
    }

    return errors;
  });

  const canStartSimulation = createMemo(() => {
    return !props.isRunning && paramErrors().length === 0 && props.esmFile.components?.length > 0;
  });

  const updateParam = <K extends keyof SimulationParameters>(
    key: K,
    value: SimulationParameters[K]
  ) => {
    const newParams = { ...localParams(), [key]: value };
    setLocalParams(newParams);
    if (props.onParametersChange) {
      props.onParametersChange(newParams);
    }
  };

  const handleStartSimulation = () => {
    if (canStartSimulation() && props.onStartSimulation) {
      props.onStartSimulation(localParams());
    }
  };

  const handleStopSimulation = () => {
    if (props.onStopSimulation) {
      props.onStopSimulation();
    }
    setIsPaused(false);
  };

  const handlePauseResume = () => {
    const newPausedState = !isPaused();
    setIsPaused(newPausedState);
    if (props.onPauseResume) {
      props.onPauseResume(newPausedState);
    }
  };

  const handleBackendChange = (backend: string) => {
    if (props.onBackendChange) {
      props.onBackendChange(backend);
    }
  };

  return (
    <div class="esm-simulation-controls">
      {/* Header */}
      <div class="controls-header">
        <h3>Simulation Controls</h3>
        <div class="status-indicator">
          <Show
            when={props.isRunning}
            fallback={
              <span class="status-badge idle">
                <span class="status-dot"></span>
                Ready
              </span>
            }
          >
            <Show
              when={isPaused()}
              fallback={
                <span class="status-badge running">
                  <span class="status-dot"></span>
                  Running
                </span>
              }
            >
              <span class="status-badge paused">
                <span class="status-dot"></span>
                Paused
              </span>
            </Show>
          </Show>
        </div>
      </div>

      {/* Progress Bar */}
      <Show when={props.isRunning && typeof props.progress === 'number'}>
        <div class="progress-section">
          <div class="progress-bar-container">
            <div
              class="progress-bar-fill"
              style={{ width: `${props.progress || 0}%` }}
            ></div>
          </div>
          <div class="progress-info">
            <span class="progress-percentage">{Math.round(props.progress || 0)}%</span>
            <Show when={props.statusMessage}>
              <span class="progress-status">{props.statusMessage}</span>
            </Show>
          </div>
        </div>
      </Show>

      {/* Main Control Buttons */}
      <div class="main-controls">
        <Show
          when={props.isRunning}
          fallback={
            <button
              class={`control-btn start ${canStartSimulation() ? '' : 'disabled'}`}
              onClick={handleStartSimulation}
              disabled={!canStartSimulation()}
            >
              <span class="btn-icon">▶</span>
              Start Simulation
            </button>
          }
        >
          <div class="running-controls">
            <button
              class="control-btn pause-resume"
              onClick={handlePauseResume}
            >
              <span class="btn-icon">{isPaused() ? '▶' : '⏸'}</span>
              {isPaused() ? 'Resume' : 'Pause'}
            </button>
            <button
              class="control-btn stop"
              onClick={handleStopSimulation}
            >
              <span class="btn-icon">⏹</span>
              Stop
            </button>
          </div>
        </Show>
      </div>

      {/* Backend Selection */}
      <Show when={props.availableBackends && props.availableBackends.length > 1}>
        <div class="backend-section">
          <label class="section-label">Simulation Backend:</label>
          <select
            class="backend-select"
            value={props.selectedBackend || props.availableBackends![0]}
            onChange={(e) => handleBackendChange(e.currentTarget.value)}
            disabled={props.isRunning}
          >
            <For each={props.availableBackends}>
              {(backend) => (
                <option value={backend}>{backend}</option>
              )}
            </For>
          </select>
        </div>
      </Show>

      {/* Time Parameters */}
      <div class="params-section">
        <div class="section-header">
          <label class="section-label">Time Parameters</label>
        </div>
        <div class="params-grid">
          <div class="param-group">
            <label class="param-label">Start Time:</label>
            <input
              type="number"
              class="param-input"
              value={localParams().startTime}
              onChange={(e) => updateParam('startTime', parseFloat(e.currentTarget.value))}
              disabled={props.isRunning}
              step="any"
            />
          </div>
          <div class="param-group">
            <label class="param-label">End Time:</label>
            <input
              type="number"
              class="param-input"
              value={localParams().endTime}
              onChange={(e) => updateParam('endTime', parseFloat(e.currentTarget.value))}
              disabled={props.isRunning}
              step="any"
            />
          </div>
          <div class="param-group">
            <label class="param-label">Time Step:</label>
            <input
              type="number"
              class="param-input"
              value={localParams().timeStep}
              onChange={(e) => updateParam('timeStep', parseFloat(e.currentTarget.value))}
              disabled={props.isRunning}
              step="any"
            />
          </div>
          <div class="param-group">
            <label class="param-label">Output Interval:</label>
            <input
              type="number"
              class="param-input"
              value={localParams().outputInterval}
              onChange={(e) => updateParam('outputInterval', parseFloat(e.currentTarget.value))}
              disabled={props.isRunning}
              step="any"
            />
          </div>
        </div>
      </div>

      {/* Advanced Parameters */}
      <div class="advanced-section">
        <button
          class="advanced-toggle"
          onClick={() => setShowAdvanced(!showAdvanced())}
        >
          <span class={`toggle-icon ${showAdvanced() ? 'expanded' : ''}`}>▼</span>
          Advanced Parameters
        </button>

        <Show when={showAdvanced()}>
          <div class="advanced-params">
            <div class="params-grid">
              <div class="param-group">
                <label class="param-label">Solver:</label>
                <select
                  class="param-select"
                  value={localParams().solver}
                  onChange={(e) => updateParam('solver', e.currentTarget.value)}
                  disabled={props.isRunning}
                >
                  <option value="euler">Euler</option>
                  <option value="rk4">Runge-Kutta 4</option>
                  <option value="adaptive">Adaptive</option>
                  <option value="implicit">Implicit</option>
                </select>
              </div>
              <div class="param-group">
                <label class="param-label">Tolerance:</label>
                <input
                  type="number"
                  class="param-input"
                  value={localParams().tolerance}
                  onChange={(e) => updateParam('tolerance', parseFloat(e.currentTarget.value))}
                  disabled={props.isRunning}
                  step="any"
                />
              </div>
              <div class="param-group">
                <label class="param-label">Max Iterations:</label>
                <input
                  type="number"
                  class="param-input"
                  value={localParams().maxIterations}
                  onChange={(e) => updateParam('maxIterations', parseInt(e.currentTarget.value))}
                  disabled={props.isRunning}
                  step="1"
                />
              </div>
              <div class="param-group checkbox-group">
                <label class="checkbox-label">
                  <input
                    type="checkbox"
                    class="param-checkbox"
                    checked={localParams().adaptiveTimeStep}
                    onChange={(e) => updateParam('adaptiveTimeStep', e.currentTarget.checked)}
                    disabled={props.isRunning}
                  />
                  Adaptive Time Step
                </label>
              </div>
            </div>
          </div>
        </Show>
      </div>

      {/* Simulation Info */}
      <div class="simulation-info">
        <div class="info-item">
          <span class="info-label">Estimated Steps:</span>
          <span class="info-value">{estimatedSteps().toLocaleString()}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Est. Duration:</span>
          <span class="info-value">{estimatedDuration()}</span>
        </div>
        <Show when={props.esmFile.components}>
          <div class="info-item">
            <span class="info-label">Components:</span>
            <span class="info-value">{props.esmFile.components!.length}</span>
          </div>
        </Show>
      </div>

      {/* Parameter Errors */}
      <Show when={paramErrors().length > 0}>
        <div class="parameter-errors">
          <div class="error-header">
            <span class="error-icon">⚠</span>
            Parameter Errors:
          </div>
          <For each={paramErrors()}>
            {(error) => (
              <div class="error-message">{error}</div>
            )}
          </For>
        </div>
      </Show>
    </div>
  );
};

// CSS classes used (to be added to web-components.css):
// .esm-simulation-controls
// .controls-header, .status-indicator
// .status-badge (with .idle, .running, .paused modifiers)
// .status-dot
// .progress-section, .progress-bar-container, .progress-bar-fill
// .progress-info, .progress-percentage, .progress-status
// .main-controls, .running-controls
// .control-btn (with .start, .stop, .pause-resume, .disabled modifiers)
// .btn-icon
// .backend-section, .backend-select
// .params-section, .section-header, .section-label
// .params-grid, .param-group
// .param-label, .param-input, .param-select
// .advanced-section, .advanced-toggle, .toggle-icon (with .expanded modifier)
// .advanced-params
// .checkbox-group, .checkbox-label, .param-checkbox
// .simulation-info, .info-item, .info-label, .info-value
// .parameter-errors, .error-header, .error-icon, .error-message