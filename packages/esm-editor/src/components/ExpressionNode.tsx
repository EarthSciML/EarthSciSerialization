/**
 * ExpressionNode - Core SolidJS component for rendering interactive AST nodes
 *
 * This is a simplified, focused recursive AST renderer for the esm-editor package.
 * It provides the foundation for interactive expression editing with:
 * - Number literals with click-to-select and hover highlighting
 * - Variable references with chemical subscript rendering
 * - Operator nodes that dispatch to OperatorLayout components
 */

import { Component, Accessor, createSignal, createMemo } from 'solid-js';
import type { Expression, ExpressionNode as ExprNode } from 'esm-format';

export interface ExpressionNodeProps {
  /** The expression to render (reactive from Solid store) */
  expr: Expression;

  /** AST path for unique identification and updates */
  path: (string | number)[];

  /** Currently highlighted variable equivalence class */
  highlightedVars: Accessor<Set<string>>;

  /** Callback when hovering over a variable */
  onHoverVar: (name: string | null) => void;

  /** Callback when selecting a node */
  onSelect: (path: (string | number)[]) => void;

  /** Callback when replacing a node with new expression */
  onReplace: (path: (string | number)[], newExpr: Expression) => void;
}

/**
 * Placeholder for chemical name rendering
 * TODO: Implement proper chemical subscript rendering
 */
function renderChemicalName(name: string): string {
  // Basic placeholder - convert numbers to subscripts
  return name.replace(/(\d+)/g, (match) => {
    const subscripts = '₀₁₂₃₄₅₆₇₈₉';
    return match
      .split('')
      .map((digit) => subscripts[parseInt(digit, 10)])
      .join('');
  });
}

/**
 * Placeholder for OperatorLayout component
 * TODO: Implement proper operator layout selection
 */
function OperatorLayout(props: { node: ExprNode; path: (string | number)[]; highlightedVars: Accessor<Set<string>>; onHoverVar: (name: string | null) => void; onSelect: (path: (string | number)[]) => void; onReplace: (path: (string | number)[], newExpr: Expression) => void; }) {
  // Placeholder implementation - just render operator name and args
  return (
    <span class="esm-operator-layout" data-operator={props.node.op}>
      <span class="esm-operator-name">{props.node.op}</span>
      <span class="esm-operator-args">
        ({props.node.args?.map((arg: Expression, index: number) => (
          <ExpressionNode
            expr={arg}
            path={[...props.path, 'args', index]}
            highlightedVars={props.highlightedVars}
            onHoverVar={props.onHoverVar}
            onSelect={props.onSelect}
            onReplace={props.onReplace}
          />
        )).join(', ')})
      </span>
    </span>
  );
}

/**
 * Core ExpressionNode component - recursive AST renderer
 */
export const ExpressionNode: Component<ExpressionNodeProps> = (props) => {
  const [isHovered, setIsHovered] = createSignal(false);

  // Determine if this expression is a variable reference
  const isVariable = createMemo(() =>
    typeof props.expr === 'string' && !isNumericString(props.expr)
  );

  // Check if this variable should be highlighted
  const shouldHighlight = createMemo(() =>
    isVariable() && props.highlightedVars().has(props.expr as string)
  );

  // CSS classes for styling
  const nodeClasses = createMemo(() => {
    const classes = ['esm-expression-node'];

    if (isHovered()) classes.push('hovered');
    if (shouldHighlight()) classes.push('highlighted');
    if (isVariable()) classes.push('variable');
    if (typeof props.expr === 'number') classes.push('number');
    if (typeof props.expr === 'object') classes.push('operator');

    return classes.join(' ');
  });

  // Handle mouse events
  const handleMouseEnter = () => {
    setIsHovered(true);
    if (isVariable()) {
      props.onHoverVar(props.expr as string);
    }
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    if (isVariable()) {
      props.onHoverVar(null);
    }
  };

  const handleClick = (e: MouseEvent) => {
    e.stopPropagation();
    props.onSelect(props.path);
  };

  // Render based on expression type
  const renderContent = () => {
    // Number literal
    if (typeof props.expr === 'number') {
      return (
        <span class="esm-num" title={`Number: ${props.expr}`}>
          {formatNumber(props.expr)}
        </span>
      );
    }

    // Variable reference
    if (typeof props.expr === 'string') {
      return (
        <span class="esm-var" title={`Variable: ${props.expr}`}>
          {renderChemicalName(props.expr)}
        </span>
      );
    }

    // Operator node - dispatch to OperatorLayout
    if (typeof props.expr === 'object' && props.expr !== null && 'op' in props.expr) {
      return (
        <OperatorLayout
          node={props.expr as ExprNode}
          path={props.path}
          highlightedVars={props.highlightedVars}
          onHoverVar={props.onHoverVar}
          onSelect={props.onSelect}
          onReplace={props.onReplace}
        />
      );
    }

    // Fallback for unknown types
    return <span class="esm-unknown">?</span>;
  };

  return (
    <span
      class={nodeClasses()}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={handleClick}
      tabIndex={0}
      role="button"
      aria-label={getAriaLabel()}
      data-path={props.path.join('.')}
    >
      {renderContent()}
    </span>
  );

  // Get ARIA label for accessibility
  function getAriaLabel(): string {
    if (typeof props.expr === 'number') {
      return `Number: ${props.expr}`;
    }
    if (typeof props.expr === 'string') {
      return `Variable: ${props.expr}`;
    }
    if (typeof props.expr === 'object' && props.expr !== null && 'op' in props.expr) {
      return `Operator: ${(props.expr as ExprNode).op}`;
    }
    return 'Expression';
  }
};

// Helper functions
function isNumericString(str: string): boolean {
  return /^-?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/.test(str);
}

function formatNumber(num: number): string {
  // Format number for display (scientific notation if needed)
  if (Math.abs(num) >= 1e6 || (Math.abs(num) < 1e-3 && num !== 0)) {
    return num.toExponential(3);
  }
  return num.toString();
}

export default ExpressionNode;