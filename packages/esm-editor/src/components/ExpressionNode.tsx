/**
 * ExpressionNode - Core SolidJS component for rendering interactive AST nodes
 *
 * This is a simplified, focused recursive AST renderer for the esm-editor package.
 * It provides the foundation for interactive expression editing with:
 * - Number literals with click-to-select and hover highlighting
 * - Variable references with chemical subscript rendering
 * - Operator nodes that dispatch to OperatorLayout components
 */

import { Component, Accessor, createSignal, createMemo, Show } from 'solid-js';
import type { Expression, ExpressionNode as ExprNode } from 'esm-format';
import { useStructuralEditingContext, DraggableExpression, StructuralEditingMenu, COMMUTATIVE_OPERATORS } from '../primitives/structural-editing';

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

  /** Currently selected path (for showing structural editing menu) */
  selectedPath?: (string | number)[] | null;

  /** Parent path for drag operations */
  parentPath?: (string | number)[];

  /** Index within parent for drag operations */
  indexInParent?: number;
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
 * Enhanced OperatorLayout component with proper mathematical layout and drag-and-drop support
 */
function OperatorLayout(props: {
  node: ExprNode;
  path: (string | number)[];
  highlightedVars: Accessor<Set<string>>;
  onHoverVar: (name: string | null) => void;
  onSelect: (path: (string | number)[]) => void;
  onReplace: (path: (string | number)[], newExpr: Expression) => void;
  selectedPath?: (string | number)[] | null;
}) {
  // Get structural editing context if available
  let structuralEditing: ReturnType<typeof useStructuralEditingContext> | undefined;
  try {
    structuralEditing = useStructuralEditingContext();
  } catch {
    // Not in structural editing context
  }

  const isCommutative = COMMUTATIVE_OPERATORS.has(props.node.op);
  const { op, args } = props.node;

  // Helper to create child nodes with drag support
  const createChildNode = (arg: Expression, index: number) => {
    const argPath = [...props.path, 'args', index];
    const childNode = (
      <ExpressionNode
        expr={arg}
        path={argPath}
        highlightedVars={props.highlightedVars}
        onHoverVar={props.onHoverVar}
        onSelect={props.onSelect}
        onReplace={props.onReplace}
        selectedPath={props.selectedPath}
        parentPath={props.path}
        indexInParent={index}
      />
    );

    // Wrap in draggable component for commutative operations
    if (structuralEditing && isCommutative && (args?.length || 0) > 1) {
      return (
        <DraggableExpression
          path={argPath}
          index={index}
          parentPath={props.path}
          canDrag={true}
        >
          {childNode}
        </DraggableExpression>
      );
    }

    return childNode;
  };

  // Handle different operators with appropriate CSS layouts per Section 5.2.4
  switch (op) {
    case '+':
    case '-':
      return (
        <span class="esm-infix-op" data-operator={op}>
          {args?.map((arg, index) => (
            <>
              <Show when={index > 0}>
                <span class="esm-operator"> {op} </span>
              </Show>
              {createChildNode(arg, index)}
            </>
          ))}
        </span>
      );

    case '*':
      return (
        <span class="esm-multiplication" data-operator={op}>
          {args?.map((arg, index) => (
            <>
              <Show when={index > 0}>
                <span class="esm-multiply">⋅</span>
              </Show>
              {createChildNode(arg, index)}
            </>
          ))}
        </span>
      );

    case '/':
      return (
        <span class="esm-fraction" data-operator={op}>
          <span class="esm-fraction-numerator">
            {args && createChildNode(args[0], 0)}
          </span>
          <span class="esm-fraction-denominator">
            {args && createChildNode(args[1], 1)}
          </span>
        </span>
      );

    case '^':
      return (
        <span class="esm-exponentiation" data-operator={op}>
          <span class="esm-base">
            {args && createChildNode(args[0], 0)}
          </span>
          <span class="esm-exponent">
            {args && createChildNode(args[1], 1)}
          </span>
        </span>
      );

    case 'D':
      return (
        <span class="esm-derivative" data-operator={op}>
          <span class="esm-d-operator">d</span>
          <span class="esm-derivative-body">
            {args && createChildNode(args[0], 0)}
          </span>
          <Show when={(props.node as any).wrt}>
            <span class="esm-derivative-wrt">
              <span class="esm-d-operator">d</span>
              <span class="esm-variable">{(props.node as any).wrt}</span>
            </span>
          </Show>
        </span>
      );

    case 'sqrt':
      return (
        <span class="esm-function esm-sqrt" data-operator={op}>
          <span class="esm-radical">√</span>
          <span class="esm-sqrt-content">
            {args && createChildNode(args[0], 0)}
          </span>
        </span>
      );

    case 'exp':
    case 'log':
    case 'sin':
    case 'cos':
    case 'tan':
      return (
        <span class="esm-function" data-operator={op}>
          <span class="esm-function-name">{op}</span>
          <span class="esm-function-args">
            (
            {args?.map((arg, index) => (
              <>
                <Show when={index > 0}>, </Show>
                {createChildNode(arg, index)}
              </>
            ))}
            )
          </span>
        </span>
      );

    case '>':
    case '<':
    case '>=':
    case '<=':
    case '==':
    case '!=':
      return (
        <span class="esm-comparison" data-operator={op}>
          {args?.map((arg, index) => (
            <>
              <Show when={index > 0}>
                <span class="esm-operator"> {op} </span>
              </Show>
              {createChildNode(arg, index)}
            </>
          ))}
        </span>
      );

    default:
      // Fallback to generic function notation for unknown operators
      return (
        <span class="esm-generic-function" data-operator={op}>
          <span class="esm-function-name">{op}</span>
          <span class="esm-function-args">
            (
            {args?.map((arg, index) => (
              <>
                <Show when={index > 0}>, </Show>
                {createChildNode(arg, index)}
              </>
            ))}
            )
          </span>
        </span>
      );
  }
}

/**
 * Core ExpressionNode component - recursive AST renderer
 */
export const ExpressionNode: Component<ExpressionNodeProps> = (props) => {
  const [isHovered, setIsHovered] = createSignal(false);
  const [showStructuralMenu, setShowStructuralMenu] = createSignal(false);
  const [menuPosition, setMenuPosition] = createSignal({ x: 0, y: 0 });

  // Get structural editing context if available
  let structuralEditing: ReturnType<typeof useStructuralEditingContext> | undefined;
  try {
    structuralEditing = useStructuralEditingContext();
  } catch {
    // Not in structural editing context, continue without
  }

  // Determine if this expression is a variable reference
  const isVariable = createMemo(() =>
    typeof props.expr === 'string' && !isNumericString(props.expr)
  );

  // Check if this variable should be highlighted
  const shouldHighlight = createMemo(() =>
    isVariable() && props.highlightedVars().has(props.expr as string)
  );

  // Check if this node is currently selected
  const isSelected = createMemo(() =>
    props.selectedPath &&
    props.selectedPath.length === props.path.length &&
    props.selectedPath.every((segment, i) => segment === props.path[i])
  );

  // Check if this can be dragged (is in a commutative operation with siblings)
  const canDrag = createMemo(() =>
    structuralEditing &&
    props.parentPath &&
    typeof props.indexInParent === 'number' &&
    props.parentPath.length > 0
  );

  // CSS classes for styling
  const nodeClasses = createMemo(() => {
    const classes = ['esm-expression-node'];

    if (isHovered()) classes.push('hovered');
    if (shouldHighlight()) classes.push('highlighted');
    if (isSelected()) classes.push('selected');
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

  const handleContextMenu = (e: MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    if (structuralEditing) {
      props.onSelect(props.path); // Select the node first
      setMenuPosition({ x: e.clientX, y: e.clientY });
      setShowStructuralMenu(true);
    }
  };

  const handleCloseMenu = () => {
    setShowStructuralMenu(false);
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
          selectedPath={props.selectedPath}
        />
      );
    }

    // Fallback for unknown types
    return <span class="esm-unknown">?</span>;
  };

  const content = (
    <>
      <span
        class={nodeClasses()}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onClick={handleClick}
        onContextMenu={handleContextMenu}
        tabIndex={0}
        role="button"
        aria-label={getAriaLabel()}
        data-path={props.path.join('.')}
      >
        {renderContent()}
      </span>

      <Show when={showStructuralMenu() && structuralEditing}>
        <StructuralEditingMenu
          selectedPath={props.path}
          selectedExpr={props.expr}
          isVisible={showStructuralMenu()}
          position={menuPosition()}
          onClose={handleCloseMenu}
        />
      </Show>
    </>
  );

  // Wrap in draggable component if this can be dragged
  if (canDrag() && structuralEditing && props.parentPath && typeof props.indexInParent === 'number') {
    return (
      <DraggableExpression
        path={props.path}
        index={props.indexInParent}
        parentPath={props.parentPath}
        canDrag={true}
      >
        {content}
      </DraggableExpression>
    );
  }

  return content;

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