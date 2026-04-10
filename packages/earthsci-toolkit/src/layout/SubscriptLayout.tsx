/**
 * SubscriptLayout - CSS-based subscript rendering component
 *
 * Implements subscript positioning for chemical formulas and mathematical notation
 * using vertical-align: sub and reduced font size.
 */

import { Component, JSX } from 'solid-js';

export interface SubscriptLayoutProps {
  /** Base content */
  base: JSX.Element;

  /** Subscript content */
  subscript: JSX.Element;

  /** Additional CSS classes */
  class?: string;

  /** Inline styles */
  style?: JSX.CSSProperties;
}

/**
 * SubscriptLayout component for displaying mathematical subscripts
 *
 * Renders base content followed by subscript content with proper positioning.
 * Commonly used for chemical formulas (H₂O) and variable indices (xᵢ).
 */
export const SubscriptLayout: Component<SubscriptLayoutProps> = (props) => {
  return (
    <span
      class={`esm-subscript ${props.class || ''}`}
      style={props.style}
    >
      <span class="esm-subscript-base">
        {props.base}
      </span>
      <sub class="esm-subscript-sub">
        {props.subscript}
      </sub>
    </span>
  );
};