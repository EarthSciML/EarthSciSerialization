/**
 * SuperscriptLayout Tests
 */

import { render } from '@solidjs/testing-library';
import { describe, it, expect } from 'vitest';
import { SuperscriptLayout } from './SuperscriptLayout.js';

describe('SuperscriptLayout', () => {
  it('should render base and superscript content', () => {
    const { getByText } = render(() =>
      <SuperscriptLayout
        base={<span>x</span>}
        superscript={<span>2</span>}
      />
    );

    expect(getByText('x')).toBeTruthy();
    expect(getByText('2')).toBeTruthy();
  });

  it('should apply correct CSS classes', () => {
    const { container } = render(() =>
      <SuperscriptLayout
        base={<span>a</span>}
        superscript={<span>n</span>}
        class="custom-class"
      />
    );

    const superscriptElement = container.querySelector('.esm-superscript');
    expect(superscriptElement).toBeTruthy();
    expect(superscriptElement?.classList.contains('custom-class')).toBe(true);

    const base = container.querySelector('.esm-superscript-base');
    const sup = container.querySelector('.esm-superscript-sup');

    expect(base).toBeTruthy();
    expect(sup).toBeTruthy();
    expect(sup?.tagName.toLowerCase()).toBe('sup');
  });

  it('should handle complex expressions', () => {
    const { container } = render(() =>
      <SuperscriptLayout
        base={<span>e</span>}
        superscript={<span>i<span>π</span></span>}
      />
    );

    const base = container.querySelector('.esm-superscript-base');
    const sup = container.querySelector('.esm-superscript-sup');

    expect(base?.textContent).toBe('e');
    expect(sup?.textContent).toBe('iπ');
  });
});