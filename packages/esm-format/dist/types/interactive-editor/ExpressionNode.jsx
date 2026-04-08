/**
 * ExpressionNode - Core SolidJS component for rendering interactive AST nodes
 *
 * This component renders a single AST node as interactive DOM with CSS math layout,
 * handles click/hover events, supports inline editing, and provides the foundation
 * for all expression editing capabilities.
 *
 * Features:
 * - Click-to-select nodes with visual feedback
 * - Hover highlighting with equivalence classes
 * - Double-click inline editing of numbers/variables
 * - CSS-based math rendering (fractions, superscripts, derivatives)
 * - Reactive updates via Solid store
 * - Full keyboard accessibility
 */
import { Show, For, createSignal, createMemo } from 'solid-js';
/**
 * Core ExpressionNode component that renders any Expression as interactive DOM
 */
export const ExpressionNode = (props) => {
    const [isHovered, setIsHovered] = createSignal(false);
    const [isEditing, setIsEditing] = createSignal(false);
    const [editValue, setEditValue] = createSignal('');
    // Determine if this expression is a variable reference
    const isVariable = createMemo(() => typeof props.expr === 'string' &&
        !isNumericString(props.expr));
    // Check if this variable should be highlighted
    const shouldHighlight = createMemo(() => isVariable() &&
        props.highlightedVars().has(props.expr));
    // CSS classes for styling
    const nodeClasses = createMemo(() => {
        const classes = ['esm-expression-node'];
        if (props.isSelected)
            classes.push('selected');
        if (isHovered())
            classes.push('hovered');
        if (shouldHighlight())
            classes.push('highlighted');
        if (isEditing())
            classes.push('editing');
        if (isVariable())
            classes.push('variable');
        if (typeof props.expr === 'number')
            classes.push('number');
        if (typeof props.expr === 'object')
            classes.push('operator');
        return classes.join(' ');
    });
    // Handle mouse events
    const handleMouseEnter = () => {
        setIsHovered(true);
        if (isVariable()) {
            props.onHoverVar(props.expr);
        }
    };
    const handleMouseLeave = () => {
        setIsHovered(false);
        if (isVariable()) {
            props.onHoverVar(null);
        }
    };
    const handleClick = (e) => {
        e.stopPropagation();
        props.onSelect(props.path);
    };
    const handleDoubleClick = (e) => {
        e.stopPropagation();
        if (!props.allowEditing)
            return;
        // Only allow editing of literals (numbers/variables)
        if (typeof props.expr === 'number' || typeof props.expr === 'string') {
            setEditValue(String(props.expr));
            setIsEditing(true);
        }
    };
    // Handle inline editing
    const handleEditKeyDown = (e) => {
        if (e.key === 'Enter') {
            saveEdit();
        }
        else if (e.key === 'Escape') {
            cancelEdit();
        }
    };
    const saveEdit = () => {
        const value = editValue().trim();
        if (value === '') {
            cancelEdit();
            return;
        }
        // Try to parse as number, otherwise treat as string
        const newExpr = isNumericString(value) ? parseFloat(value) : value;
        props.onReplace(props.path, newExpr);
        setIsEditing(false);
    };
    const cancelEdit = () => {
        setIsEditing(false);
        setEditValue('');
    };
    // Render different expression types
    const renderExpression = () => {
        // Show edit input if editing
        if (isEditing()) {
            return (<input type="text" value={editValue()} onInput={(e) => setEditValue(e.currentTarget.value)} onKeyDown={handleEditKeyDown} onBlur={saveEdit} class="esm-expression-edit" autoFocus aria-label={`Edit ${typeof props.expr === 'number' ? 'number' : 'variable'}`}/>);
        }
        // Render based on expression type
        if (typeof props.expr === 'number') {
            return <span class="esm-number">{formatNumber(props.expr)}</span>;
        }
        if (typeof props.expr === 'string') {
            return (<span class="esm-variable" title={`Variable: ${props.expr}`}>
          {props.expr}
        </span>);
        }
        // Render operator node
        if (typeof props.expr === 'object' && props.expr !== null && 'op' in props.expr) {
            return renderOperatorNode(props.expr);
        }
        return <span class="esm-unknown">?</span>;
    };
    // Render operator nodes with proper mathematical layout
    const renderOperatorNode = (node) => {
        const { op, args } = node;
        // Handle different operators with appropriate CSS layouts
        switch (op) {
            case '+':
            case '-':
                return renderInfixOperator(op, args);
            case '*':
                return renderMultiplication(args);
            case '/':
                return renderFraction(args);
            case '^':
                return renderExponentiation(args);
            case 'D':
                return renderDerivative(node);
            case 'exp':
            case 'log':
            case 'sin':
            case 'cos':
            case 'tan':
            case 'sqrt':
                return renderFunction(op, args);
            case '>':
            case '<':
            case '>=':
            case '<=':
            case '==':
            case '!=':
                return renderComparison(op, args);
            default:
                return renderGenericFunction(op, args);
        }
    };
    // Render infix operators like +, -
    const renderInfixOperator = (op, args) => (<span class="esm-infix-op">
      <For each={args}>
        {(arg, index) => (<>
            <Show when={index() > 0}>
              <span class="esm-operator"> {op} </span>
            </Show>
            <ExpressionNode expr={arg} path={[...props.path, 'args', index()]} highlightedVars={props.highlightedVars} onHoverVar={props.onHoverVar} onSelect={props.onSelect} onReplace={props.onReplace} allowEditing={props.allowEditing}/>
          </>)}
      </For>
    </span>);
    // Render multiplication (implicit or explicit)
    const renderMultiplication = (args) => (<span class="esm-multiplication">
      <For each={args}>
        {(arg, index) => (<>
            <Show when={index() > 0}>
              <span class="esm-multiply">⋅</span>
            </Show>
            <ExpressionNode expr={arg} path={[...props.path, 'args', index()]} highlightedVars={props.highlightedVars} onHoverVar={props.onHoverVar} onSelect={props.onSelect} onReplace={props.onReplace} allowEditing={props.allowEditing}/>
          </>)}
      </For>
    </span>);
    // Render fraction with CSS layout
    const renderFraction = (args) => (<span class="esm-fraction">
      <span class="esm-fraction-numerator">
        <ExpressionNode expr={args[0]} path={[...props.path, 'args', 0]} highlightedVars={props.highlightedVars} onHoverVar={props.onHoverVar} onSelect={props.onSelect} onReplace={props.onReplace} allowEditing={props.allowEditing}/>
      </span>
      <span class="esm-fraction-denominator">
        <ExpressionNode expr={args[1]} path={[...props.path, 'args', 1]} highlightedVars={props.highlightedVars} onHoverVar={props.onHoverVar} onSelect={props.onSelect} onReplace={props.onReplace} allowEditing={props.allowEditing}/>
      </span>
    </span>);
    // Render exponentiation with superscript
    const renderExponentiation = (args) => (<span class="esm-exponentiation">
      <span class="esm-base">
        <ExpressionNode expr={args[0]} path={[...props.path, 'args', 0]} highlightedVars={props.highlightedVars} onHoverVar={props.onHoverVar} onSelect={props.onSelect} onReplace={props.onReplace} allowEditing={props.allowEditing}/>
      </span>
      <span class="esm-exponent">
        <ExpressionNode expr={args[1]} path={[...props.path, 'args', 1]} highlightedVars={props.highlightedVars} onHoverVar={props.onHoverVar} onSelect={props.onSelect} onReplace={props.onReplace} allowEditing={props.allowEditing}/>
      </span>
    </span>);
    // Render derivative notation
    const renderDerivative = (node) => (<span class="esm-derivative">
      <span class="esm-d-operator">d</span>
      <span class="esm-derivative-body">
        <ExpressionNode expr={node.args[0]} path={[...props.path, 'args', 0]} highlightedVars={props.highlightedVars} onHoverVar={props.onHoverVar} onSelect={props.onSelect} onReplace={props.onReplace} allowEditing={props.allowEditing}/>
      </span>
      <Show when={node.wrt}>
        <span class="esm-derivative-wrt">
          <span class="esm-d-operator">d</span>
          <span class="esm-variable">{node.wrt}</span>
        </span>
      </Show>
    </span>);
    // Render function calls
    const renderFunction = (name, args) => (<span class="esm-function">
      <span class="esm-function-name">{name}</span>
      <span class="esm-function-args">
        (
        <For each={args}>
          {(arg, index) => (<>
              <Show when={index() > 0}>, </Show>
              <ExpressionNode expr={arg} path={[...props.path, 'args', index()]} highlightedVars={props.highlightedVars} onHoverVar={props.onHoverVar} onSelect={props.onSelect} onReplace={props.onReplace} allowEditing={props.allowEditing}/>
            </>)}
        </For>
        )
      </span>
    </span>);
    // Render comparison operators
    const renderComparison = (op, args) => (<span class="esm-comparison">
      <For each={args}>
        {(arg, index) => (<>
            <Show when={index() > 0}>
              <span class="esm-operator"> {op} </span>
            </Show>
            <ExpressionNode expr={arg} path={[...props.path, 'args', index()]} highlightedVars={props.highlightedVars} onHoverVar={props.onHoverVar} onSelect={props.onSelect} onReplace={props.onReplace} allowEditing={props.allowEditing}/>
          </>)}
      </For>
    </span>);
    // Generic function renderer for unknown operators
    const renderGenericFunction = (op, args) => (<span class="esm-generic-function">
      <span class="esm-function-name">{op}</span>
      (
      <For each={args}>
        {(arg, index) => (<>
            <Show when={index() > 0}>, </Show>
            <ExpressionNode expr={arg} path={[...props.path, 'args', index()]} highlightedVars={props.highlightedVars} onHoverVar={props.onHoverVar} onSelect={props.onSelect} onReplace={props.onReplace} allowEditing={props.allowEditing}/>
          </>)}
      </For>
      )
    </span>);
    return (<span class={nodeClasses()} onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave} onClick={handleClick} onDblClick={handleDoubleClick} tabIndex={0} role="button" aria-label={getAriaLabel()} data-path={props.path.join('.')}>
      {renderExpression()}
    </span>);
    // Get ARIA label for accessibility
    function getAriaLabel() {
        if (typeof props.expr === 'number') {
            return `Number: ${props.expr}`;
        }
        if (typeof props.expr === 'string') {
            return `Variable: ${props.expr}`;
        }
        if (typeof props.expr === 'object' && props.expr !== null && 'op' in props.expr) {
            return `Operator: ${props.expr.op}`;
        }
        return 'Expression';
    }
};
// Helper functions
function isNumericString(str) {
    return /^-?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/.test(str);
}
function formatNumber(num) {
    // Format number according to ESM spec Section 6.1
    if (num === 0)
        return '0';
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
function formatSuperscript(exp) {
    // Convert number to Unicode superscript
    const superscriptMap = {
        '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
        '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
        '-': '⁻', '+': '⁺'
    };
    return exp.toString().split('').map(char => superscriptMap[char] || char).join('');
}
export default ExpressionNode;
//# sourceMappingURL=ExpressionNode.jsx.map