/**
 * SuperscriptLayout - CSS-based superscript rendering component
 *
 * Implements superscript positioning using vertical-align: super and reduced font size
 * for mathematical exponentiation (^ operator).
 */

import { Component, JSX } from 'solid-js';

export interface SuperscriptLayoutProps {
  /** Base content */
  base: JSX.Element;

  /** Superscript content */
  superscript: JSX.Element;

  /** Additional CSS classes */
  class?: string;

  /** Inline styles */
  style?: JSX.CSSProperties;
}

/**
 * SuperscriptLayout component for displaying mathematical superscripts
 *
 * Renders base content followed by superscript content with proper positioning.
 */
export const SuperscriptLayout: Component<SuperscriptLayoutProps> = (props) => {
  return (
    <span
      class={`esm-superscript ${props.class || ''}`}
      style={props.style}
    >
      <span class="esm-superscript-base">
        {props.base}
      </span>
      <sup class="esm-superscript-sup">
        {props.superscript}
      </sup>
    </span>
  );
};