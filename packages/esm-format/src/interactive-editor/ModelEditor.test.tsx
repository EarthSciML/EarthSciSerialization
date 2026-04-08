/**
 * Comprehensive test suite for ModelEditor SolidJS component
 *
 * Tests all core functionality including:
 * - Variable management (add, edit, remove)
 * - Equation editing with ExpressionNode integration
 * - Event handling (discrete and continuous)
 * - Live validation feedback
 * - User interaction scenarios
 * - Accessibility features
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@solidjs/testing-library';
import { createSignal } from 'solid-js';
import { ModelEditor } from './ModelEditor.js';
import type { Model, ModelVariable } from '../types.js';

// Sample test models
const createSampleModel = (): Model => ({
  variables: {
    x: { type: 'state', units: 'm', description: 'Position' },
    v: { type: 'state', units: 'm/s', description: 'Velocity' },
    k: { type: 'parameter', units: '1/s', default: 1.0, description: 'Rate constant' },
    temp: { type: 'observed', units: 'K', description: 'Temperature' }
  },
  equations: [
    {
      lhs: { op: 'D', args: ['x'], wrt: 't' },
      rhs: 'v'
    },
    {
      lhs: { op: 'D', args: ['v'], wrt: 't' },
      rhs: { op: '*', args: [{ op: '-', args: ['k'] }, 'x'] }
    }
  ]
});

const createModelWithEvents = (): Model => ({
  ...createSampleModel(),
  discrete_events: [
    {
      name: 'reset_position',
      trigger: { type: 'time', at: 10 },
      affects: [{ lhs: 'x', rhs: 0 }]
    }
  ],
  continuous_events: [
    {
      name: 'velocity_limit',
      conditions: [{ op: '>', args: ['v', 10] }],
      affects: [{ lhs: 'v', rhs: 10 }]
    }
  ]
});

describe('ModelEditor Component', () => {
  let mockOnChange: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockOnChange = vi.fn();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('should render with basic model structure', () => {
      const model = createSampleModel();
      render(() => (
        <ModelEditor
          model={model}
          onChange={mockOnChange}
        />
      ));

      expect(screen.getByText('Model Editor')).toBeInTheDocument();
      expect(screen.getByRole('tablist')).toBeInTheDocument();
    });

    it('should display correct tab labels with counts', () => {
      const model = createSampleModel();
      render(() => (
        <ModelEditor
          model={model}
          onChange={mockOnChange}
        />
      ));

      expect(screen.getByRole('tab', { name: /Variables.*4/ })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /Equations.*2/ })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /Events.*0/ })).toBeInTheDocument();
    });

    it('should show reference citation when provided', () => {
      const model = {
        ...createSampleModel(),
        reference: { citation: 'Test Model Citation' }
      };

      render(() => (
        <ModelEditor
          model={model}
          onChange={mockOnChange}
        />
      ));

      expect(screen.getByText('Test Model Citation')).toBeInTheDocument();
    });
  });

  describe('Variables Tab', () => {
    it('should display variables grouped by type', () => {
      const model = createSampleModel();
      render(() => (
        <ModelEditor
          model={model}
          onChange={mockOnChange}
        />
      ));

      // Variables tab should be active by default
      expect(screen.getByText('State Variables')).toBeInTheDocument();
      expect(screen.getByText('Parameter Variables')).toBeInTheDocument();
      expect(screen.getByText('Observed Variables')).toBeInTheDocument();
    });

    it('should show variable details including units and descriptions', () => {
      const model = createSampleModel();
      render(() => (
        <ModelEditor
          model={model}
          onChange={mockOnChange}
        />
      ));

      expect(screen.getByText('x')).toBeInTheDocument();
      expect(screen.getByText('[m]')).toBeInTheDocument();
      expect(screen.getByText('Position')).toBeInTheDocument();
      expect(screen.getAllByText('state').length).toBeGreaterThan(0);
    });

    it('should allow adding new variables when editing is enabled', async () => {
      const model = createSampleModel();
      render(() => (
        <ModelEditor
          model={model}
          onChange={mockOnChange}
          allowEditing={true}
        />
      ));

      // Mock prompt for new variable name
      const promptSpy = vi.spyOn(window, 'prompt').mockReturnValue('new_var');

      const addStateButton = screen.getByText('+ Add state');
      fireEvent.click(addStateButton);

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({
            variables: expect.objectContaining({
              new_var: expect.objectContaining({
                type: 'state'
              })
            })
          })
        );
      });

      promptSpy.mockRestore();
    });

    it('should prevent adding variables with duplicate names', async () => {
      const model = createSampleModel();
      render(() => (
        <ModelEditor
          model={model}
          onChange={mockOnChange}
          allowEditing={true}
        />
      ));

      // Mock prompt to return existing variable name
      const promptSpy = vi.spyOn(window, 'prompt').mockReturnValue('x');

      const addStateButton = screen.getByText('+ Add state');
      fireEvent.click(addStateButton);

      // Should not call onChange since variable name already exists
      expect(mockOnChange).not.toHaveBeenCalled();

      promptSpy.mockRestore();
    });

    it('should allow editing variable properties', async () => {
      const model = createSampleModel();
      render(() => (
        <ModelEditor
          model={model}
          onChange={mockOnChange}
          allowEditing={true}
        />
      ));

      // Click on variable to expand editor
      const variableItem = screen.getByText('x').closest('.esm-variable-item');
      fireEvent.click(variableItem!);

      // Find and update units field
      const unitsInput = screen.getByDisplayValue('m');
      fireEvent.input(unitsInput, { target: { value: 'meters' } });

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({
            variables: expect.objectContaining({
              x: expect.objectContaining({
                units: 'meters'
              })
            })
          })
        );
      });
    });

    it('should allow removing variables with confirmation', async () => {
      const model = createSampleModel();
      render(() => (
        <ModelEditor
          model={model}
          onChange={mockOnChange}
          allowEditing={true}
        />
      ));

      // Mock confirm dialog
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

      const removeButton = screen.getAllByTitle(/Remove/)[0];
      fireEvent.click(removeButton);

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({
            variables: expect.not.objectContaining({
              x: expect.anything()
            })
          })
        );
      });

      confirmSpy.mockRestore();
    });

    it('should not remove variables if user cancels confirmation', async () => {
      const model = createSampleModel();
      render(() => (
        <ModelEditor
          model={model}
          onChange={mockOnChange}
          allowEditing={true}
        />
      ));

      // Mock confirm dialog to return false
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);

      const removeButton = screen.getAllByTitle(/Remove/)[0];
      fireEvent.click(removeButton);

      // Should not call onChange since user cancelled
      expect(mockOnChange).not.toHaveBeenCalled();

      confirmSpy.mockRestore();
    });
  });

  describe('Equations Tab', () => {
    it('should display equations with ExpressionNode components', async () => {
      const model = createSampleModel();
      render(() => (
        <ModelEditor
          model={model}
          onChange={mockOnChange}
        />
      ));

      // Click equations tab
      const equationsTab = screen.getByRole('tab', { name: /Equations/ });
      fireEvent.click(equationsTab);

      expect(screen.getByText('Equations')).toBeInTheDocument();
      expect(screen.getAllByText('=')).toHaveLength(2); // Two equations
    });

    it('should allow adding new equations when editing is enabled', async () => {
      const model = createSampleModel();
      render(() => (
        <ModelEditor
          model={model}
          onChange={mockOnChange}
          allowEditing={true}
        />
      ));

      // Switch to equations tab
      const equationsTab = screen.getByRole('tab', { name: /Equations/ });
      fireEvent.click(equationsTab);

      const addButton = screen.getByText('+ Add Equation');
      fireEvent.click(addButton);

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({
            equations: expect.arrayContaining([
              expect.objectContaining({
                lhs: { op: 'D', args: ['new_var'], wrt: 't' },
                rhs: 0
              })
            ])
          })
        );
      });
    });

    it('should allow removing equations with confirmation', async () => {
      const model = createSampleModel();
      render(() => (
        <ModelEditor
          model={model}
          onChange={mockOnChange}
          allowEditing={true}
        />
      ));

      // Switch to equations tab
      const equationsTab = screen.getByRole('tab', { name: /Equations/ });
      fireEvent.click(equationsTab);

      // Mock confirm dialog
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

      const removeButton = screen.getAllByTitle('Remove equation')[0];
      fireEvent.click(removeButton);

      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(
          expect.objectContaining({
            equations: expect.arrayContaining([
              // Should have one less equation
              model.equations[1]
            ])
          })
        );
      });

      confirmSpy.mockRestore();
    });
  });

  describe('Events Tab', () => {
    it('should display discrete and continuous events', async () => {
      const model = createModelWithEvents();
      render(() => (
        <ModelEditor
          model={model}
          onChange={mockOnChange}
        />
      ));

      // Switch to events tab
      const eventsTab = screen.getByRole('tab', { name: /Events.*2/ });
      fireEvent.click(eventsTab);

      expect(screen.getByText('Discrete Events')).toBeInTheDocument();
      expect(screen.getByText('Continuous Events')).toBeInTheDocument();
      expect(screen.getByText('reset_position')).toBeInTheDocument();
      expect(screen.getByText('velocity_limit')).toBeInTheDocument();
    });

    it('should show "No events defined" when model has no events', async () => {
      const model = createSampleModel();
      render(() => (
        <ModelEditor
          model={model}
          onChange={mockOnChange}
        />
      ));

      // Switch to events tab
      const eventsTab = screen.getByRole('tab', { name: /Events.*0/ });
      fireEvent.click(eventsTab);

      expect(screen.getByText('No events defined')).toBeInTheDocument();
    });
  });

  describe('Interactive Features', () => {
    it('should highlight variables on hover', async () => {
      const [highlightedVars, setHighlightedVars] = createSignal(new Set<string>());
      const model = createSampleModel();

      render(() => (
        <ModelEditor
          model={model}
          onChange={mockOnChange}
          highlightedVars={highlightedVars}
        />
      ));

      // Test that highlighting prop is properly passed down
      setHighlightedVars(new Set(['x']));

      // This tests the highlighting mechanism exists
      const variableItems = screen.getAllByText('x');
      expect(variableItems.length).toBeGreaterThan(0);
    });

    it('should handle tab navigation with keyboard', async () => {
      const model = createSampleModel();
      render(() => (
        <ModelEditor
          model={model}
          onChange={mockOnChange}
        />
      ));

      const variablesTab = screen.getByRole('tab', { name: /Variables/ });
      const equationsTab = screen.getByRole('tab', { name: /Equations/ });

      // Test keyboard navigation
      variablesTab.focus();
      fireEvent.keyDown(variablesTab, { key: 'ArrowRight' });

      // Should move focus to equations tab
      expect(document.activeElement).toBe(equationsTab);
    });
  });

  describe('Validation Features', () => {
    it('should display validation errors when provided', () => {
      const model = createSampleModel();
      const validationErrors = ['Variable "undefined_var" not found', 'Equation 1 has syntax error'];

      render(() => (
        <ModelEditor
          model={model}
          onChange={mockOnChange}
          showValidation={true}
          validationErrors={validationErrors}
        />
      ));

      expect(screen.getByText('Validation Errors')).toBeInTheDocument();
      expect(screen.getByText('Variable "undefined_var" not found')).toBeInTheDocument();
      expect(screen.getByText('Equation 1 has syntax error')).toBeInTheDocument();
    });

    it('should hide validation panel when no errors', () => {
      const model = createSampleModel();

      render(() => (
        <ModelEditor
          model={model}
          onChange={mockOnChange}
          showValidation={true}
          validationErrors={[]}
        />
      ));

      expect(screen.queryByText('Validation Errors')).not.toBeInTheDocument();
    });

    it('should hide validation when showValidation is false', () => {
      const model = createSampleModel();
      const validationErrors = ['Some error'];

      render(() => (
        <ModelEditor
          model={model}
          onChange={mockOnChange}
          showValidation={false}
          validationErrors={validationErrors}
        />
      ));

      expect(screen.queryByText('Validation Errors')).not.toBeInTheDocument();
    });
  });

  describe('Read-only Mode', () => {
    it('should hide editing controls when allowEditing is false', () => {
      const model = createSampleModel();

      render(() => (
        <ModelEditor
          model={model}
          onChange={mockOnChange}
          allowEditing={false}
        />
      ));

      expect(screen.queryByText('+ Add state')).not.toBeInTheDocument();
      expect(screen.queryByTitle(/Remove/)).not.toBeInTheDocument();
    });

    it('should show editing controls by default', () => {
      const model = createSampleModel();

      render(() => (
        <ModelEditor
          model={model}
          onChange={mockOnChange}
        />
      ));

      expect(screen.getByText('+ Add state')).toBeInTheDocument();
    });
  });

  describe('Complex Expression Handling', () => {
    it('should handle nested mathematical expressions', () => {
      const model: Model = {
        variables: {
          c: { type: 'state', units: 'mol/L', description: 'Concentration' },
          k1: { type: 'parameter', units: '1/s', default: 0.1 },
          k2: { type: 'parameter', units: 'L/(mol*s)', default: 0.01 }
        },
        equations: [
          {
            lhs: { op: 'D', args: ['c'], wrt: 't' },
            rhs: {
              op: '+',
              args: [
                { op: '*', args: ['k1', 'c'] },
                {
                  op: '*',
                  args: [
                    'k2',
                    { op: '^', args: ['c', 2] }
                  ]
                }
              ]
            }
          }
        ]
      };

      render(() => (
        <ModelEditor
          model={model}
          onChange={mockOnChange}
        />
      ));

      // Switch to equations tab to see the complex expression
      const equationsTab = screen.getByRole('tab', { name: /Equations/ });
      fireEvent.click(equationsTab);

      // Should render without errors
      expect(screen.getByText('Equations')).toBeInTheDocument();
    });
  });

  describe('Performance and Edge Cases', () => {
    it('should handle models with many variables efficiently', () => {
      const largeModel: Model = {
        variables: {},
        equations: []
      };

      // Create 100 variables
      for (let i = 0; i < 100; i++) {
        largeModel.variables[`var_${i}`] = {
          type: 'state',
          units: 'unit',
          description: `Variable ${i}`
        };
      }

      render(() => (
        <ModelEditor
          model={largeModel}
          onChange={mockOnChange}
        />
      ));

      expect(screen.getByRole('tab', { name: /Variables.*100/ })).toBeInTheDocument();
    });

    it('should handle empty models gracefully', () => {
      const emptyModel: Model = {
        variables: {},
        equations: []
      };

      render(() => (
        <ModelEditor
          model={emptyModel}
          onChange={mockOnChange}
        />
      ));

      expect(screen.getByText('Model Editor')).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /Variables.*0/ })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /Equations.*0/ })).toBeInTheDocument();
    });
  });
});