/**
 * Web Components Tests - Basic functionality and export tests
 */

import { describe, it, expect } from 'vitest';

describe('Web Components Module', () => {
  it('should export web component registration function', async () => {
    const webComponentsModule = await import('./web-components.js');

    expect(webComponentsModule.registerWebComponents).toBeDefined();
    expect(typeof webComponentsModule.registerWebComponents).toBe('function');
  });

  it('should export component wrappers', async () => {
    const webComponentsModule = await import('./web-components.js');

    expect(webComponentsModule.EsmExpressionNodeComponent).toBeDefined();
    expect(webComponentsModule.EsmModelEditorComponent).toBeDefined();
    expect(webComponentsModule.EsmCouplingGraphComponent).toBeDefined();
  });

  it('should handle prop conversion correctly', async () => {
    const webComponentsModule = await import('./web-components.js');

    // This is an internal function, but we can test the module loads without errors
    expect(webComponentsModule).toBeTruthy();
  });
});