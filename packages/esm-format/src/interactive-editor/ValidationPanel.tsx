/**
 * ValidationPanel Component - Display model validation results and errors
 *
 * Shows validation errors, warnings, and success states with detailed
 * information about model structure and consistency.
 */

import { Component, For, Show, createSignal, createMemo } from 'solid-js';
import type { Model, ValidationError } from '../types.js';

export interface ValidationPanelProps {
  /** The model being validated */
  model: Model;

  /** List of validation errors */
  validationErrors: ValidationError[];

  /** List of validation warnings */
  validationWarnings?: ValidationError[];

  /** Whether the panel should auto-update when model changes */
  autoValidate?: boolean;

  /** Whether to show detailed error information */
  showDetails?: boolean;

  /** Callback when an error is clicked for navigation */
  onErrorClick?: (error: ValidationError) => void;
}

interface ValidationSummary {
  errorCount: number;
  warningCount: number;
  isValid: boolean;
}

export const ValidationPanel: Component<ValidationPanelProps> = (props) => {
  const [expandedErrors, setExpandedErrors] = createSignal<Set<string>>(new Set());
  const [selectedSeverity, setSelectedSeverity] = createSignal<'all' | 'error' | 'warning'>('all');

  // Compute validation summary
  const summary = createMemo<ValidationSummary>(() => {
    const errorCount = props.validationErrors?.length || 0;
    const warningCount = props.validationWarnings?.length || 0;
    return {
      errorCount,
      warningCount,
      isValid: errorCount === 0
    };
  });

  // Filter errors and warnings based on selected severity
  const filteredIssues = createMemo(() => {
    const errors = (props.validationErrors || []).map(err => ({ ...err, severity: 'error' as const }));
    const warnings = (props.validationWarnings || []).map(warn => ({ ...warn, severity: 'warning' as const }));

    const allIssues = [...errors, ...warnings];

    if (selectedSeverity() === 'error') {
      return allIssues.filter(issue => issue.severity === 'error');
    } else if (selectedSeverity() === 'warning') {
      return allIssues.filter(issue => issue.severity === 'warning');
    }

    return allIssues;
  });

  const toggleErrorExpanded = (errorId: string) => {
    const expanded = expandedErrors();
    const newExpanded = new Set(expanded);

    if (expanded.has(errorId)) {
      newExpanded.delete(errorId);
    } else {
      newExpanded.add(errorId);
    }

    setExpandedErrors(newExpanded);
  };

  const handleErrorClick = (error: ValidationError) => {
    if (props.onErrorClick) {
      props.onErrorClick(error);
    }
  };

  const getSeverityColor = (severity: 'error' | 'warning') => {
    return severity === 'error' ? 'text-red-600' : 'text-orange-600';
  };

  const getSeverityBgColor = (severity: 'error' | 'warning') => {
    return severity === 'error' ? 'bg-red-50' : 'bg-orange-50';
  };

  const getSeverityBorderColor = (severity: 'error' | 'warning') => {
    return severity === 'error' ? 'border-red-200' : 'border-orange-200';
  };

  return (
    <div class="esm-validation-panel">
      {/* Header with summary */}
      <div class="validation-header">
        <div class="validation-summary">
          <Show
            when={summary().isValid}
            fallback={
              <div class="validation-status error">
                <span class="status-icon">⚠</span>
                <span class="status-text">
                  {summary().errorCount} error{summary().errorCount !== 1 ? 's' : ''}
                  {summary().warningCount > 0 && `, ${summary().warningCount} warning${summary().warningCount !== 1 ? 's' : ''}`}
                </span>
              </div>
            }
          >
            <div class="validation-status success">
              <span class="status-icon">✓</span>
              <span class="status-text">Model is valid</span>
            </div>
          </Show>
        </div>

        {/* Severity filter */}
        <Show when={summary().errorCount > 0 || summary().warningCount > 0}>
          <div class="severity-filter">
            <button
              class={`filter-btn ${selectedSeverity() === 'all' ? 'active' : ''}`}
              onClick={() => setSelectedSeverity('all')}
            >
              All ({summary().errorCount + summary().warningCount})
            </button>
            <Show when={summary().errorCount > 0}>
              <button
                class={`filter-btn error ${selectedSeverity() === 'error' ? 'active' : ''}`}
                onClick={() => setSelectedSeverity('error')}
              >
                Errors ({summary().errorCount})
              </button>
            </Show>
            <Show when={summary().warningCount > 0}>
              <button
                class={`filter-btn warning ${selectedSeverity() === 'warning' ? 'active' : ''}`}
                onClick={() => setSelectedSeverity('warning')}
              >
                Warnings ({summary().warningCount})
              </button>
            </Show>
          </div>
        </Show>
      </div>

      {/* Validation issues list */}
      <div class="validation-content">
        <Show
          when={filteredIssues().length > 0}
          fallback={
            <div class="empty-state">
              <span class="empty-icon">✨</span>
              <p class="empty-text">No validation issues found</p>
              <p class="empty-subtext">Your model structure looks good!</p>
            </div>
          }
        >
          <For each={filteredIssues()}>
            {(issue, index) => {
              const issueId = `issue-${index()}`;
              const isExpanded = () => expandedErrors().has(issueId);

              return (
                <div
                  class={`validation-issue ${issue.severity} ${getSeverityBgColor(issue.severity)} ${getSeverityBorderColor(issue.severity)}`}
                >
                  <div
                    class="issue-header"
                    onClick={() => {
                      toggleErrorExpanded(issueId);
                      handleErrorClick(issue);
                    }}
                  >
                    <div class="issue-main">
                      <span class={`issue-severity-icon ${getSeverityColor(issue.severity)}`}>
                        {issue.severity === 'error' ? '❌' : '⚠️'}
                      </span>
                      <span class="issue-message">{issue.message}</span>
                    </div>

                    <div class="issue-meta">
                      <Show when={issue.path}>
                        <span class="issue-path">{issue.path}</span>
                      </Show>

                      <Show when={props.showDetails}>
                        <button
                          class={`expand-btn ${isExpanded() ? 'expanded' : ''}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleErrorExpanded(issueId);
                          }}
                        >
                          {isExpanded() ? '−' : '+'}
                        </button>
                      </Show>
                    </div>
                  </div>

                  <Show when={props.showDetails && isExpanded()}>
                    <div class="issue-details">
                      <Show when={issue.description}>
                        <p class="issue-description">{issue.description}</p>
                      </Show>

                      <Show when={issue.suggestion}>
                        <div class="issue-suggestion">
                          <strong>Suggestion:</strong>
                          <p>{issue.suggestion}</p>
                        </div>
                      </Show>

                      <Show when={issue.code}>
                        <div class="issue-code">
                          <strong>Error Code:</strong> <code>{issue.code}</code>
                        </div>
                      </Show>
                    </div>
                  </Show>
                </div>
              );
            }}
          </For>
        </Show>
      </div>

      {/* Quick actions */}
      <Show when={summary().errorCount > 0}>
        <div class="validation-actions">
          <button
            class="action-btn expand-all"
            onClick={() => {
              const allIssueIds = filteredIssues().map((_, index) => `issue-${index}`);
              setExpandedErrors(new Set(allIssueIds));
            }}
          >
            Expand All
          </button>
          <button
            class="action-btn collapse-all"
            onClick={() => setExpandedErrors(new Set())}
          >
            Collapse All
          </button>
        </div>
      </Show>
    </div>
  );
};

// CSS classes used (to be added to web-components.css):
// .esm-validation-panel
// .validation-header
// .validation-summary
// .validation-status (with .success and .error modifiers)
// .status-icon, .status-text
// .severity-filter
// .filter-btn (with .active, .error, .warning modifiers)
// .validation-content
// .validation-issue (with severity classes)
// .issue-header, .issue-main, .issue-meta
// .issue-severity-icon, .issue-message, .issue-path
// .expand-btn (with .expanded modifier)
// .issue-details
// .issue-description, .issue-suggestion, .issue-code
// .validation-actions
// .action-btn (with .expand-all, .collapse-all modifiers)
// .empty-state
// .empty-icon, .empty-text, .empty-subtext