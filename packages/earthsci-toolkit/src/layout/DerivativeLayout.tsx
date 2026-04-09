/**
 * DerivativeLayout - CSS-based derivative notation rendering component
 *
 * Implements derivative notation like ∂x/∂t using the FractionLayout with partial symbols.
 * Supports both ordinary derivatives (d/dx) and partial derivatives (∂/∂x).
 */

import { Component, JSX } from 'solid-js';
import { FractionLayout } from './FractionLayout.js';

export interface DerivativeLayoutProps {
  /** Function or expression being differentiated */
  function: JSX.Element;

  /** Variable with respect to which we're differentiating */
  variable: JSX.Element;

  /** Whether to use partial derivative notation (∂) or ordinary derivative (d) */
  partial?: boolean;

  /** Order of derivative (default 1) */
  order?: number;

  /** Additional CSS classes */
  class?: string;

  /** Inline styles */
  style?: JSX.CSSProperties;
}

/**
 * DerivativeLayout component for displaying mathematical derivatives
 *
 * Renders derivative notation using fraction layout with appropriate d or ∂ symbols.
 * Supports both ordinary and partial derivatives with configurable order.
 */
export const DerivativeLayout: Component<DerivativeLayoutProps> = (props) => {
  const symbol = () => props.partial !== false ? '∂' : 'd';
  const order = () => props.order || 1;

  const renderNumerator = () => (
    <span class="esm-derivative-numerator">
      {order() > 1 && (
        <sup class="esm-derivative-order">{order()}</sup>
      )}
      <span class="esm-derivative-symbol">{symbol()}</span>
      <span class="esm-derivative-function">
        {props.function}
      </span>
    </span>
  );

  const renderDenominator = () => (
    <span class="esm-derivative-denominator">
      <span class="esm-derivative-symbol">{symbol()}</span>
      <span class="esm-derivative-variable">
        {props.variable}
      </span>
      {order() > 1 && (
        <sup class="esm-derivative-order">{order()}</sup>
      )}
    </span>
  );

  return (
    <FractionLayout
      numerator={renderNumerator()}
      denominator={renderDenominator()}
      class={`esm-derivative ${props.class || ''}`}
      style={props.style}
    />
  );
};