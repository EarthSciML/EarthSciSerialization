/**
 * FractionLayout Tests
 */

import { render } from '@solidjs/testing-library';
import { describe, it, expect } from 'vitest';
import { FractionLayout } from './FractionLayout.js';

describe('FractionLayout', () => {
  it('should render a fraction with numerator and denominator', () => {
    const { getByText } = render(() =>
      <FractionLayout
        numerator={<span>x</span>}
        denominator={<span>y</span>}
      />
    );

    expect(getByText('x')).toBeTruthy();
    expect(getByText('y')).toBeTruthy();
  });

  it('should apply correct CSS classes', () => {
    const { container } = render(() =>
      <FractionLayout
        numerator={<span>a</span>}
        denominator={<span>b</span>}
        class="custom-class"
      />
    );

    const fractionElement = container.querySelector('.esm-frac');
    expect(fractionElement).toBeTruthy();
    expect(fractionElement?.classList.contains('custom-class')).toBe(true);

    const numerator = container.querySelector('.esm-frac-num');
    const denominator = container.querySelector('.esm-frac-den');
    const bar = container.querySelector('.esm-frac-bar');

    expect(numerator).toBeTruthy();
    expect(denominator).toBeTruthy();
    expect(bar).toBeTruthy();
  });

  it('should support inline styles', () => {
    const { container } = render(() =>
      <FractionLayout
        numerator={<span>1</span>}
        denominator={<span>2</span>}
        style={{ 'font-size': '20px' }}
      />
    );

    const fractionElement = container.querySelector('.esm-frac') as HTMLElement;
    expect(fractionElement?.style.fontSize).toBe('20px');
  });
});