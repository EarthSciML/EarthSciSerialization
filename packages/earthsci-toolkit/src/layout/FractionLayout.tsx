/**
 * FractionLayout - CSS-based fraction rendering component
 *
 * Implements proper mathematical fraction layout using inline-flex and column direction
 * as specified in Section 5.2.4 of the ESM format specification.
 *
 * Uses CSS classes: .esm-frac, .esm-frac-num, .esm-frac-bar, .esm-frac-den
 */

import { Component, JSX } from 'solid-js';

export interface FractionLayoutProps {
  /** Numerator content */
  numerator: JSX.Element;

  /** Denominator content */
  denominator: JSX.Element;

  /** Additional CSS classes */
  class?: string;

  /** Inline styles */
  style?: JSX.CSSProperties;
}

/**
 * FractionLayout component for displaying mathematical fractions
 *
 * Renders as a vertical flexbox with numerator, horizontal bar, and denominator.
 * Follows the ESM format specification for CSS class naming.
 */
export const FractionLayout: Component<FractionLayoutProps> = (props) => {
  return (
    <span
      class={`esm-frac ${props.class || ''}`}
      style={props.style}
    >
      <span class="esm-frac-num">
        {props.numerator}
      </span>
      <span class="esm-frac-bar" />
      <span class="esm-frac-den">
        {props.denominator}
      </span>
    </span>
  );
};