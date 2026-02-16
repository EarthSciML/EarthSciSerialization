import { describe, it, beforeEach, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@solidjs/testing-library';
import { createSignal } from 'solid-js';
import { ExpressionNode } from './ExpressionNode';

describe('ExpressionNode', () => {
  const mockProps = {
    path: ['test'],
    highlightedVars: () => new Set<string>(),
    onHoverVar: vi.fn(),
    onSelect: vi.fn(),
    onReplace: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders number literals correctly', () => {
    render(() => <ExpressionNode expr={42} {...mockProps} />);

    const element = screen.getByText('42');
    expect(element).toBeInTheDocument();
    expect(element).toHaveClass('esm-num');
  });

  it('renders variable references correctly', () => {
    render(() => <ExpressionNode expr="CO2" {...mockProps} />);

    const element = screen.getByText('CO₂');
    expect(element).toBeInTheDocument();
    expect(element).toHaveClass('esm-var');
  });

  it('handles hover events for variables', () => {
    const onHoverVar = vi.fn();
    render(() => <ExpressionNode expr="H2O" {...mockProps} onHoverVar={onHoverVar} />);

    const element = screen.getByText('H₂O');

    fireEvent.mouseEnter(element.parentElement!);
    expect(onHoverVar).toHaveBeenCalledWith('H2O');

    fireEvent.mouseLeave(element.parentElement!);
    expect(onHoverVar).toHaveBeenCalledWith(null);
  });

  it('handles click events', () => {
    const onSelect = vi.fn();
    render(() => <ExpressionNode expr="x" {...mockProps} onSelect={onSelect} />);

    const element = screen.getByRole('button');
    fireEvent.click(element);

    expect(onSelect).toHaveBeenCalledWith(['test']);
  });

  it('highlights variables when they are in highlightedVars set', () => {
    const [highlightedVars] = createSignal(new Set(['x']));

    render(() => (
      <ExpressionNode
        expr="x"
        {...mockProps}
        highlightedVars={highlightedVars}
      />
    ));

    const element = screen.getByRole('button');
    expect(element).toHaveClass('highlighted');
  });

  it('renders operator nodes with OperatorLayout', () => {
    const operatorExpr = {
      op: '+' as const,
      args: [1, 2]
    };

    render(() => <ExpressionNode expr={operatorExpr} {...mockProps} />);

    const element = screen.getByText('+');
    expect(element).toBeInTheDocument();
    expect(element.parentElement).toHaveAttribute('data-operator', '+');
  });

  it('formats numbers with scientific notation for large numbers', () => {
    render(() => <ExpressionNode expr={1234567} {...mockProps} />);

    const element = screen.getByText('1.235e+6');
    expect(element).toBeInTheDocument();
  });

  it('formats numbers with scientific notation for small numbers', () => {
    render(() => <ExpressionNode expr={0.0001} {...mockProps} />);

    const element = screen.getByText('1.000e-4');
    expect(element).toBeInTheDocument();
  });
});