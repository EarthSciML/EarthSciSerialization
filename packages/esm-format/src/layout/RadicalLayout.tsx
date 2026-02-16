/**
 * RadicalLayout - CSS-based square root rendering component
 *
 * Implements square root symbol using pure CSS for the sqrt operator.
 * Creates the radical symbol using CSS pseudo-elements and positioning.
 */

import { Component, JSX } from 'solid-js';

export interface RadicalLayoutProps {
  /** Content under the radical */
  radicand: JSX.Element;

  /** Optional index (for nth roots, default to square root) */
  index?: JSX.Element;

  /** Additional CSS classes */
  class?: string;

  /** Inline styles */
  style?: JSX.CSSProperties;
}

/**
 * RadicalLayout component for displaying square roots and nth roots
 *
 * Uses CSS to create the radical symbol without requiring external fonts or SVG.
 * The radical hook and overline are drawn using CSS borders and pseudo-elements.
 */
export const RadicalLayout: Component<RadicalLayoutProps> = (props) => {
  return (
    <span
      class={`esm-radical ${props.class || ''}`}
      style={props.style}
    >
      {props.index && (
        <span class="esm-radical-index">
          {props.index}
        </span>
      )}
      <span class="esm-radical-symbol">√</span>
      <span class="esm-radical-content">
        {props.radicand}
      </span>
    </span>
  );
};