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

// Element lookup table for chemical subscript detection (118 elements)
const ELEMENTS = new Set([
  // Period 1
  'H', 'He',
  // Period 2
  'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne',
  // Period 3
  'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar',
  // Period 4
  'K', 'Ca', 'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr',
  // Period 5
  'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn', 'Sb', 'Te', 'I', 'Xe',
  // Period 6
  'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu',
  'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg', 'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn',
  // Period 7
  'Fr', 'Ra', 'Ac', 'Th', 'Pa', 'U', 'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf', 'Es', 'Fm', 'Md', 'No', 'Lr',
  'Rf', 'Db', 'Sg', 'Bh', 'Hs', 'Mt', 'Ds', 'Rg', 'Cn', 'Nh', 'Fl', 'Mc', 'Lv', 'Ts', 'Og'
]);

// Unicode subscripts for digits 0-9
const SUBSCRIPT_DIGITS = '₀₁₂₃₄₅₆₇₈₉';

/**
 * Check if a variable has element patterns (for chemical formula detection)
 * Must be PURELY a chemical formula (no non-element characters)
 */
function hasElementPattern(variable: string): boolean {
  // Remove underscores for pure chemical formula check
  const cleanVariable = variable.replace(/_/g, '');

  let i = 0;
  let hasElement = false;

  while (i < cleanVariable.length) {
    // Skip non-alphabetic characters at the start
    while (i < cleanVariable.length && !/[A-Za-z]/.test(cleanVariable[i])) {
      i++;
    }

    if (i >= cleanVariable.length) break;

    let foundElement = false;

    // Try 2-character element first
    if (i + 1 < cleanVariable.length) {
      const twoChar = cleanVariable.slice(i, i + 2);
      if (ELEMENTS.has(twoChar)) {
        hasElement = true;
        foundElement = true;
        i += 2;
        // Skip digits
        while (i < cleanVariable.length && /\d/.test(cleanVariable[i])) {
          i++;
        }
        continue;
      }
    }

    // Try 1-character element
    if (!foundElement) {
      const oneChar = cleanVariable[i];
      if (ELEMENTS.has(oneChar)) {
        hasElement = true;
        foundElement = true;
        i++;
        // Skip digits
        while (i < cleanVariable.length && /\d/.test(cleanVariable[i])) {
          i++;
        }
        continue;
      }
    }

    // If we encounter a non-element character, this is not a pure chemical formula
    if (!foundElement) {
      return false;
    }
  }

  return hasElement;
}

/**
 * Extract chemical formula suffix from a variable name
 */
function getChemicalSuffix(variable: string): { prefix: string; suffix: string } | null {
  // Handle patterns like k_NO_O3 (with underscore)
  if (variable.includes('_')) {
    const parts = variable.split('_');
    if (parts.length === 2) {
      const [prefix, suffix] = parts;
      if (hasElementPattern(suffix) && !hasElementPattern(prefix)) {
        return { prefix, suffix };
      }
    }
    // For patterns like k_NO_O3, try treating NO_O3 as the chemical part
    if (parts.length === 3) {
      const prefix = parts[0];
      const suffix = parts.slice(1).join('_');  // Keep underscore within chemical formula
      if (hasElementPattern(suffix) && !hasElementPattern(prefix)) {
        return { prefix, suffix };
      }
    }
  }

  // Handle patterns like jNO2 (without underscore)
  // Try each position to split into non-element prefix and element suffix
  for (let i = 1; i < variable.length; i++) {
    const prefix = variable.substring(0, i);
    const suffix = variable.substring(i);

    if (hasElementPattern(suffix) && !hasElementPattern(prefix)) {
      return { prefix, suffix };
    }
  }

  return null;
}

/**
 * Apply element-aware chemical subscript formatting to a variable name.
 * Uses greedy 2-char-before-1-char matching for element detection.
 */
function renderChemicalName(variable: string): string {
  // Check if variable looks like a chemical formula (starts with element and has digits)
  const hasElements = hasElementPattern(variable);

  if (!hasElements) {
    // Check if it's a mixed variable (non-element prefix + chemical suffix)
    const chemicalInfo = getChemicalSuffix(variable);
    if (chemicalInfo) {
      // Split into prefix and chemical part
      const { prefix, suffix } = chemicalInfo;
      const chemicalPart = renderChemicalName(suffix);
      // For variables without underscores (like jNO2), don't add underscores
      if (!variable.includes('_')) {
        return `${prefix}${chemicalPart}`;
      }
      // For variables with underscores (like k_NO_O3), preserve them
      return `${prefix}_${chemicalPart}`;
    }
    // No element pattern found, return as-is
    return variable;
  }

  // For element-aware subscript detection
  let result = '';
  let i = 0;

  while (i < variable.length) {
    let matched = false;

    // Try 2-character element first
    if (i + 1 < variable.length) {
      const twoChar = variable.slice(i, i + 2);
      if (ELEMENTS.has(twoChar)) {
        result += twoChar;
        i += 2;
        // Convert following digits to subscripts
        while (i < variable.length && /\d/.test(variable[i])) {
          result += SUBSCRIPT_DIGITS[parseInt(variable[i])];
          i++;
        }
        matched = true;
      }
    }

    // Try 1-character element if 2-char didn't match
    if (!matched && i < variable.length) {
      const oneChar = variable[i];
      if (ELEMENTS.has(oneChar)) {
        result += oneChar;
        i++;
        // Convert following digits to subscripts
        while (i < variable.length && /\d/.test(variable[i])) {
          result += SUBSCRIPT_DIGITS[parseInt(variable[i])];
          i++;
        }
        matched = true;
      }
    }

    // If not an element, copy character as-is
    if (!matched) {
      result += variable[i];
      i++;
    }
  }

  return result;
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
  // Format number according to ESM spec Section 6.1
  if (num === 0) return '0';

  const absNum = Math.abs(num);

  // Use scientific notation for very small or large numbers
  if (absNum < 0.01 || absNum >= 10000) {
    const exp = num.toExponential();
    const [mantissa, exponent] = exp.split('e');

    // Convert to Unicode superscript notation
    const cleanMantissa = parseFloat(mantissa).toString(); // Remove trailing zeros
    const expNum = parseInt(exponent, 10);
    const superscriptExp = formatSuperscript(expNum);

    return `${cleanMantissa}×10${superscriptExp}`;
  }

  // For integers, show as plain integer
  if (Number.isInteger(num)) {
    return num.toString();
  }

  // For decimals, use standard notation
  return num.toString();
}

function formatSuperscript(exp: number): string {
  // Convert number to Unicode superscript
  const superscriptMap: { [key: string]: string } = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
    '-': '⁻', '+': '⁺'
  };

  return exp.toString().split('').map(char => superscriptMap[char] || char).join('');
}

export default ExpressionNode;