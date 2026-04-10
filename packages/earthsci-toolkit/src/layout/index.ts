/**
 * Layout Components - Mathematical Typography for ESM Format
 *
 * Pure CSS-based mathematical layout components for the ESM format interactive editor.
 * These components implement Section 5.2.4 of the ESM format specification.
 *
 * Features:
 * - FractionLayout: display: inline-flex, flex-direction: column for fractions
 * - SuperscriptLayout: vertical-align: super for exponentiation
 * - SubscriptLayout: chemical and mathematical subscripts
 * - RadicalLayout: CSS-rendered square root symbols
 * - DelimiterLayout: auto-sizing parentheses and brackets
 * - DerivativeLayout: ∂x/∂t notation using FractionLayout
 */

// Export all layout components
export { FractionLayout } from './FractionLayout.js';
export type { FractionLayoutProps } from './FractionLayout.js';

export { SuperscriptLayout } from './SuperscriptLayout.js';
export type { SuperscriptLayoutProps } from './SuperscriptLayout.js';

export { SubscriptLayout } from './SubscriptLayout.js';
export type { SubscriptLayoutProps } from './SubscriptLayout.js';

export { RadicalLayout } from './RadicalLayout.js';
export type { RadicalLayoutProps } from './RadicalLayout.js';

export { DelimiterLayout } from './DelimiterLayout.js';
export type { DelimiterLayoutProps, DelimiterType } from './DelimiterLayout.js';

export { DerivativeLayout } from './DerivativeLayout.js';
export type { DerivativeLayoutProps } from './DerivativeLayout.js';

// Import CSS styles (bundled with components)
import './index.css';