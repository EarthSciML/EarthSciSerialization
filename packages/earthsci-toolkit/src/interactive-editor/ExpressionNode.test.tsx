/**
 * ExpressionNode Component Tests
 *
 * Tests the core functionality of the ExpressionNode component including:
 * - Rendering different expression types (numbers, variables, operators)
 * - Interactive features (click, hover, editing)
 * - CSS math layout
 * - Accessibility features
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent } from '@solidjs/testing-library';
import { createSignal } from 'solid-js';
import { ExpressionNode } from './ExpressionNode.tsx';
import type { Expression } from '../types.js';

describe('ExpressionNode', () => {
  // Mock functions for callbacks
  const mockOnHoverVar = vi.fn();
  const mockOnSelect = vi.fn();
  const mockOnReplace = vi.fn();

  // Helper to create a test component
  const createTestNode = (expr: Expression, props: Partial<any> = {}) => {
    const [highlightedVars] = createSignal(new Set<string>());

    return render(() =>
      <ExpressionNode
        expr={expr}
        path={['test']}
        highlightedVars={highlightedVars}
        onHoverVar={mockOnHoverVar}
        onSelect={mockOnSelect}
        onReplace={mockOnReplace}
        allowEditing={true}
        {...props}
      />
    );
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Number Rendering', () => {
    it('should render a simple number', () => {
      const { container } = createTestNode(42);
      const numberElement = container.querySelector('.esm-number');

      expect(numberElement).toBeTruthy();
      expect(numberElement?.textContent).toBe('42');
    });

    it('should render scientific notation for large numbers', () => {
      const { container } = createTestNode(1234567);
      const numberElement = container.querySelector('.esm-number');

      expect(numberElement?.textContent).toMatch(/1\.235e\+6/);
    });

    it('should render scientific notation for small numbers', () => {
      const { container } = createTestNode(0.0001);
      const numberElement = container.querySelector('.esm-number');

      expect(numberElement?.textContent).toMatch(/1\.000e-4/);
    });

    it('should handle negative numbers', () => {
      const { container } = createTestNode(-3.14);
      const numberElement = container.querySelector('.esm-number');

      expect(numberElement?.textContent).toBe('-3.14');
    });
  });

  describe('Variable Rendering', () => {
    it('should render a variable name', () => {
      const { container } = createTestNode('temperature');
      const variableElement = container.querySelector('.esm-variable');

      expect(variableElement).toBeTruthy();
      expect(variableElement?.textContent).toBe('temperature');
    });

    it('should apply variable styling class', () => {
      const { container } = createTestNode('x');
      const nodeElement = container.querySelector('.esm-expression-node');

      expect(nodeElement?.classList.contains('variable')).toBe(true);
    });

    it('should show tooltip on hover', () => {
      const { container } = createTestNode('pressure');
      const variableElement = container.querySelector('.esm-variable');

      expect(variableElement?.getAttribute('title')).toBe('Variable: pressure');
    });
  });

  describe('Operator Rendering', () => {
    it('should render addition operator', () => {
      const expr = {
        op: '+' as const,
        args: [1, 2]
      };

      const { container } = createTestNode(expr);
      const operatorElement = container.querySelector('.esm-operator');

      expect(operatorElement?.textContent?.trim()).toBe('+');
    });

    it('should render multiplication with dot symbol', () => {
      const expr = {
        op: '*' as const,
        args: ['x', 'y']
      };

      const { container } = createTestNode(expr);
      const multiplyElement = container.querySelector('.esm-multiply');

      expect(multiplyElement?.textContent).toBe('⋅');
    });

    it('should render fraction layout for division', () => {
      const expr = {
        op: '/' as const,
        args: ['numerator', 'denominator']
      };

      const { container } = createTestNode(expr);
      const fractionElement = container.querySelector('.esm-fraction');
      const numeratorElement = container.querySelector('.esm-fraction-numerator');
      const denominatorElement = container.querySelector('.esm-fraction-denominator');

      expect(fractionElement).toBeTruthy();
      expect(numeratorElement).toBeTruthy();
      expect(denominatorElement).toBeTruthy();
    });

    it('should render exponentiation with superscript', () => {
      const expr = {
        op: '^' as const,
        args: ['x', 2]
      };

      const { container } = createTestNode(expr);
      const baseElement = container.querySelector('.esm-base');
      const exponentElement = container.querySelector('.esm-exponent');

      expect(baseElement).toBeTruthy();
      expect(exponentElement).toBeTruthy();
    });

    it('should render derivative notation', () => {
      const expr = {
        op: 'D' as const,
        args: ['x'],
        wrt: 't'
      };

      const { container } = createTestNode(expr);
      const derivativeElement = container.querySelector('.esm-derivative');
      const dOperators = container.querySelectorAll('.esm-d-operator');

      expect(derivativeElement).toBeTruthy();
      expect(dOperators.length).toBe(2); // One for d/dx and one for dx
    });

    it('should render function calls', () => {
      const expr = {
        op: 'sin' as const,
        args: ['x']
      };

      const { container } = createTestNode(expr);
      const functionElement = container.querySelector('.esm-function');
      const functionName = container.querySelector('.esm-function-name');

      expect(functionElement).toBeTruthy();
      expect(functionName?.textContent).toBe('sin');
    });
  });

  describe('Interactive Features', () => {
    it('should call onSelect when clicked', () => {
      const { container } = createTestNode(42);
      const nodeElement = container.querySelector('.esm-expression-node');

      fireEvent.click(nodeElement!);

      expect(mockOnSelect).toHaveBeenCalledWith(['test']);
    });

    it('should call onHoverVar when hovering variable', () => {
      const { container } = createTestNode('temperature');
      const nodeElement = container.querySelector('.esm-expression-node');

      fireEvent.mouseEnter(nodeElement!);

      expect(mockOnHoverVar).toHaveBeenCalledWith('temperature');
    });

    it('should clear hover when mouse leaves variable', () => {
      const { container } = createTestNode('temperature');
      const nodeElement = container.querySelector('.esm-expression-node');

      fireEvent.mouseEnter(nodeElement!);
      fireEvent.mouseLeave(nodeElement!);

      expect(mockOnHoverVar).toHaveBeenLastCalledWith(null);
    });

    it('should enter edit mode on double-click for numbers', async () => {
      const { container } = createTestNode(42);
      const nodeElement = container.querySelector('.esm-expression-node');

      fireEvent.dblClick(nodeElement!);

      const editInput = container.querySelector('.esm-expression-edit');
      expect(editInput).toBeTruthy();
      expect((editInput as HTMLInputElement)?.value).toBe('42');
    });

    it('should enter edit mode on double-click for variables', () => {
      const { container } = createTestNode('x');
      const nodeElement = container.querySelector('.esm-expression-node');

      fireEvent.dblClick(nodeElement!);

      const editInput = container.querySelector('.esm-expression-edit');
      expect(editInput).toBeTruthy();
      expect((editInput as HTMLInputElement)?.value).toBe('x');
    });

    it('should save edit on Enter key', async () => {
      const { container } = createTestNode(42);
      const nodeElement = container.querySelector('.esm-expression-node');

      fireEvent.dblClick(nodeElement!);

      const editInput = container.querySelector('.esm-expression-edit') as HTMLInputElement;
      fireEvent.input(editInput, { target: { value: '123' } });
      fireEvent.keyDown(editInput, { key: 'Enter' });

      expect(mockOnReplace).toHaveBeenCalledWith(['test'], 123);
    });

    it('should cancel edit on Escape key', () => {
      const { container } = createTestNode(42);
      const nodeElement = container.querySelector('.esm-expression-node');

      fireEvent.dblClick(nodeElement!);

      const editInput = container.querySelector('.esm-expression-edit') as HTMLInputElement;
      fireEvent.input(editInput, { target: { value: '123' } });
      fireEvent.keyDown(editInput, { key: 'Escape' });

      expect(mockOnReplace).not.toHaveBeenCalled();
      expect(container.querySelector('.esm-expression-edit')).toBeNull();
    });
  });

  describe('CSS Classes and Styling', () => {
    it('should apply selected class when isSelected prop is true', () => {
      const { container } = createTestNode(42, { isSelected: true });
      const nodeElement = container.querySelector('.esm-expression-node');

      expect(nodeElement?.classList.contains('selected')).toBe(true);
    });

    it('should apply highlighted class for highlighted variables', () => {
      const [highlightedVars] = createSignal(new Set(['x']));

      const { container } = render(() =>
        <ExpressionNode
          expr="x"
          path={['test']}
          highlightedVars={highlightedVars}
          onHoverVar={mockOnHoverVar}
          onSelect={mockOnSelect}
          onReplace={mockOnReplace}
        />
      );

      const nodeElement = container.querySelector('.esm-expression-node');
      expect(nodeElement?.classList.contains('highlighted')).toBe(true);
    });

    it('should apply appropriate type classes', () => {
      const { container: numContainer } = createTestNode(42);
      const { container: varContainer } = createTestNode('x');
      const { container: opContainer } = createTestNode({ op: '+', args: [1, 2] });

      expect(numContainer.querySelector('.esm-expression-node')?.classList.contains('number')).toBe(true);
      expect(varContainer.querySelector('.esm-expression-node')?.classList.contains('variable')).toBe(true);
      expect(opContainer.querySelector('.esm-expression-node')?.classList.contains('operator')).toBe(true);
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels for numbers', () => {
      const { container } = createTestNode(42);
      const nodeElement = container.querySelector('.esm-expression-node');

      expect(nodeElement?.getAttribute('aria-label')).toBe('Number: 42');
    });

    it('should have proper ARIA labels for variables', () => {
      const { container } = createTestNode('temperature');
      const nodeElement = container.querySelector('.esm-expression-node');

      expect(nodeElement?.getAttribute('aria-label')).toBe('Variable: temperature');
    });

    it('should have proper ARIA labels for operators', () => {
      const expr = { op: '+' as const, args: [1, 2] };
      const { container } = createTestNode(expr);
      const nodeElement = container.querySelector('.esm-expression-node');

      expect(nodeElement?.getAttribute('aria-label')).toBe('Operator: +');
    });

    it('should be focusable with tab key', () => {
      const { container } = createTestNode(42);
      const nodeElement = container.querySelector('.esm-expression-node');

      expect(nodeElement?.getAttribute('tabIndex')).toBe('0');
    });

    it('should have button role for interactivity', () => {
      const { container } = createTestNode(42);
      const nodeElement = container.querySelector('.esm-expression-node');

      expect(nodeElement?.getAttribute('role')).toBe('button');
    });

    it('should provide edit input label', () => {
      const { container } = createTestNode(42);
      const nodeElement = container.querySelector('.esm-expression-node');

      fireEvent.dblClick(nodeElement!);

      const editInput = container.querySelector('.esm-expression-edit');
      expect(editInput?.getAttribute('aria-label')).toBe('Edit number');
    });
  });

  describe('Path Tracking', () => {
    it('should set data-path attribute correctly', () => {
      const { container } = createTestNode(42, { path: ['model', 'equations', 0, 'rhs'] });
      const nodeElement = container.querySelector('.esm-expression-node');

      expect(nodeElement?.getAttribute('data-path')).toBe('model.equations.0.rhs');
    });

    it('should pass correct paths to nested nodes', () => {
      const expr = {
        op: '+' as const,
        args: [1, 'x']
      };

      const { container } = createTestNode(expr, { path: ['test'] });
      const nestedNodes = container.querySelectorAll('[data-path]');

      expect(nestedNodes.length).toBeGreaterThan(1);
      // Check that nested paths are correctly constructed
      const paths = Array.from(nestedNodes).map(node => node.getAttribute('data-path'));
      expect(paths).toContain('test.args.0');
      expect(paths).toContain('test.args.1');
    });
  });

  describe('Complex Expressions', () => {
    it('should render nested expressions correctly', () => {
      const expr = {
        op: '+' as const,
        args: [
          {
            op: '*' as const,
            args: ['a', 'b']
          },
          {
            op: '/' as const,
            args: ['c', 'd']
          }
        ]
      };

      const { container } = createTestNode(expr);

      // Check that both sub-expressions are rendered
      expect(container.querySelector('.esm-multiplication')).toBeTruthy();
      expect(container.querySelector('.esm-fraction')).toBeTruthy();
      expect(container.querySelectorAll('.esm-variable')).toHaveLength(4);
    });

    it('should handle empty or malformed expressions gracefully', () => {
      // Test with null/undefined
      const { container: nullContainer } = createTestNode(null as any);
      expect(nullContainer.querySelector('.esm-unknown')).toBeTruthy();

      // Test with empty object
      const { container: emptyContainer } = createTestNode({} as any);
      expect(emptyContainer.querySelector('.esm-unknown')).toBeTruthy();
    });
  });
});