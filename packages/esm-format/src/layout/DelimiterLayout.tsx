/**
 * DelimiterLayout - CSS-based auto-sizing delimiter rendering component
 *
 * Implements auto-sizing parentheses, brackets, and braces that grow with content height.
 * Uses CSS flexbox to automatically match the height of the enclosed content.
 */

import { Component, JSX } from 'solid-js';

export type DelimiterType = 'parentheses' | 'brackets' | 'braces' | 'pipes' | 'angles';

export interface DelimiterLayoutProps {
  /** Content enclosed by delimiters */
  children: JSX.Element;

  /** Type of delimiter to use */
  type?: DelimiterType;

  /** Override left delimiter */
  left?: string;

  /** Override right delimiter */
  right?: string;

  /** Additional CSS classes */
  class?: string;

  /** Inline styles */
  style?: JSX.CSSProperties;
}

/**
 * DelimiterLayout component for auto-sizing delimiters
 *
 * Automatically sizes delimiters to match the height of enclosed content.
 * Supports common mathematical delimiters with proper spacing.
 */
export const DelimiterLayout: Component<DelimiterLayoutProps> = (props) => {
  const getDelimiters = () => {
    if (props.left && props.right) {
      return { left: props.left, right: props.right };
    }

    switch (props.type || 'parentheses') {
      case 'brackets':
        return { left: '[', right: ']' };
      case 'braces':
        return { left: '{', right: '}' };
      case 'pipes':
        return { left: '|', right: '|' };
      case 'angles':
        return { left: '⟨', right: '⟩' };
      case 'parentheses':
      default:
        return { left: '(', right: ')' };
    }
  };

  const delimiters = getDelimiters();

  return (
    <span
      class={`esm-delimiter esm-delimiter-${props.type || 'parentheses'} ${props.class || ''}`}
      style={props.style}
    >
      <span class="esm-delimiter-left">
        {delimiters.left}
      </span>
      <span class="esm-delimiter-content">
        {props.children}
      </span>
      <span class="esm-delimiter-right">
        {delimiters.right}
      </span>
    </span>
  );
};